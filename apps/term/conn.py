#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import selectors
import time

import os
# import threading
from django.core.cache import cache

from . import sftp, proxy, conf
from .ssh import ProxyServer, proxy_clients


class Base:
    shells = proxy.shells  # sess 当前进程所有在线的shell终端session
    shell_last_check = 0

    def __init__(self, *args, **kwargs):
        self.poller = selectors.DefaultSelector()  # shell交互 - 循环轮播器

    def check_close_shell(self):
        '''
        检查各shell状态, 是否被外界强制关闭 / 无操作闲置超时.

        设计原由:
        虽网站asgi进程可以借助channels库进行跨进程通信,
        但堡垒机进程chan_cli与chan_ser交互未做解藕开发,
        所以堡垒机进程可以操作/联系网站进程, 而反过来不行.
        综上, 网站进程为操作结束堡垒机终端, 使用缓存通讯,
        webssh纯asgi进程之间操作, 为和堡垒机程序统一,
        也使用当前结构设定, 不使用channel_layer通讯.
        '''
        now = time.time()
        if now - self.shell_last_check > 10:
            # 防止频繁检查, 检查间隔 > 10秒
            self.shell_last_check = now
            timeout = conf.SSHD.get('shell_timeout', 30)
            for session_id, session in self.shells.sess.copy().items():
                msg = ''
                if now - session.last_active_time > timeout * 60:
                    msg = f'终端无操作空闲时间超过{timeout}分钟, 断开.'
                elif not cache.get('proxy_sshd_%d' % session_id):
                    msg = f'系统管理员已强制中止了您的终端连接'

                if msg:
                    self.shells.sess.pop(session_id)
                    # import ipdb; ipdb.set_trace()
                    if not session.closed:
                        try:
                            session.chan_cli.send(f'\033[1;3;31m{msg}\033[0m\r\n')
                        except Exception:
                            pass
                        session.close()

    def select(self, timeout=1):
        '''
        轮询检查轮播器中, 所有管道事件变化,
        用于本实例中所有chan_cli与各自chan_ser之间的数据交互转发
        '''
        events = self.poller.select(timeout=timeout)  # timeout时间内, 会阻塞
        for key, event in events:
            func = key.data
            obj = key.fileobj
            # print(func, 222, obj)
            func(obj)


class Conn(Base):
    '''
    sshd_server = sshd + conn + proxy
    sshd 与 conn 为一对多关系, 一个py监听进程有多个与前端的连接.
    conn 与 proxy 为一对多关系, 一个前端连接可对应多个shell终端.

    ssh_client <<===>> proxy_server
    新客户端接入, 建立一个socket连接, 只有一个transport_cli/ProxyServer
    每个socket连接, 有一个或多个SSH前端/客户端chan_cli (复制SSH渠道),
    多个chan_cli则对应多个chan_ser, 每个chan_ser可能是不同的transport_ser,
    也可能是复用共同的后端socket/transport_ser (同进程, 同资产和用户时)
    '''
    host_key = paramiko.RSAKey(
        filename=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'rsa_private.key'
        )
    )
    transport_cli = None  # 与ssh_client之间建立的transport

    def __init__(self, client_sock):
        super().__init__()
        self.conn_client(client_sock)

    def conn_client(self, client_sock):
        # ssh_client <<===>> proxy_server SSH/SFTP建立连接/认证交互
        transport = paramiko.Transport(client_sock, gss_kex=False)

        transport.load_server_moduli()

        transport.add_server_key(self.host_key)
        transport.set_subsystem_handler(
            'sftp', handler=sftp.SftpServer,  # *largs, **kwargs
            sftp_si=sftp.SftpClient,
        )

        self.proxy_server = ProxyServer()
        transport.start_server(server=self.proxy_server)  # SSH时输密码 或 SFTP时调用子系统开启SFTP
        self.transport_cli = transport

    def accept(self):
        # transport_cli.accept(), 有新chan_cli接入则处理
        # chan_cli = self.transport_cli.accept(
        #     timeout=0  # 0表示等待前端连接复用时, 不阻塞
        # )
        for chan_cli in self.transport_cli.server_accepts:

            if hasattr(chan_cli, 'type'):
                # accept
                self.transport_cli.server_accepts.remove(chan_cli)
                proxy.Proxy(
                    self.poller, chan_cli,
                    *self.proxy_server.auth_info
                )

    def run(self):
        '''
        SSH有连接复用功能, 一个transport_cli连接,可以对应多个chan_cli终端窗口,
        当第二个chan_cli连接复用时, 无需认证, conn.run线程已处于运行中,
        通过chan_cli.type来判断前端chan_cli是否初始化好了.

        理论上SFTP也是可以连接复用, 但测试使用Xftp在同一个进程窗口中开多个sftp,
        实际是重新建立socket连接, 没有复用的概念.
        为和ssh保持处理一致, sftp的新连接运行处理时, 仍进行循环等待连接复用
        '''
        while self.transport_cli.is_active():
            '''
            self.select() 检查轮播器中SSH终端收发事件变化
            self.accept() 等待SSH socket连接复用 (复制SSH渠道)
            '''
            self.select(0.5)  # 轮播, chan_cli <==> chan_ser 交互

            self.accept()  # transport连接复用
            self.check_close_shell()

        del self


class ConnWS(Base):
    '''
    用于网页wsgi进程调用
    webssh, 客户端为WebSocket, ws服务端相当于 ProxyServer,
    后端等后续处理和堡垒机程序一样.

    因目前chan_cli和chan_ser相互通信未进行解藕, 所以须在同一进程中进行数据交互,
    asgi网站进程和堡垒机端口进程是属于不同的进程, 相互独立,
    这里只是程序保持兼容一致, 以免需维护二套session会话交互.
    '''
    elfinder_sftp_last_check = 0

    def add_chan_cli(self, chan_cli, auth_info):
        proxy.Proxy(self.poller, chan_cli, *auth_info)

    def run(self):
        while 1:
            '''
            检查网页终端轮播器中SSH终端收发事件变化
            webssh 没有前端transport_cli连接复用的概念,
            只可能有后端transport_ser连接复用
            '''

            # 检查当前asgi进程管道事件变化
            self.select(2)  # 轮播, chan_cli <==> chan_ser 交互
            self.check_close_shell()  # webssh
            self.check_close_elfinder()  # websftp

    def check_close_elfinder(self):
        '''
        关闭闲置的网页SFTP elfinder_sftp
        由于elfinder接口程序容易各种意外情况, 出错后缓存连接实例后会一直异常,
        所以改为这边处理/关闭SSH, elfinder接口在每次HTTP请求时都重新生成各实例.
        '''
        now = time.time()
        if now - self.elfinder_sftp_last_check > 30:
            # 防止频繁检查, 检查间隔 > 30秒
            self.elfinder_sftp_last_check = now
            timeout = conf.SSHD.get('elfinder_sftp_timeout', 10)
            for proxy_client in proxy_clients.copy().values():
                if hasattr(proxy_client, 'elfinder_sftp'):
                    if now - proxy_client.elfinder_sftp.last_time > timeout * 60:
                        proxy_client.close(proxy_client.elfinder_sftp.get_channel())
                        del proxy_client.elfinder_sftp
