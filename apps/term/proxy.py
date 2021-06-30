# -*- coding: utf-8 -*-

import time
import threading
from django.core.cache import cache

from .session import Session

from . import ssh, models


class Proxy:
    '''
    堡垒机SSHD中转服务器, 衔接 客户端终端/资产服务端SSHD
    ssh_client <<===>>           proxy_sshd          <<===>> sshd_server
    |          chan_cli            <----->           chan_ser          |
    ssh_client <<===>> (proxy_server - proxy_client) <<===>> sshd_server

    '''

    def __init__(self, poller, chan_cli, http_user, hostid, uid):
        '''
        已有前端/客户端渠道, 需生成后端/主机渠道并交互
        poller: 轮询处理交互的轮播器
        '''
        # self.chan_cli = chan_cli

        try:
            proxy_client = ssh.ProxyClient(hostid, uid)  # 连接后端SSH
        except Exception as e:
            print('Error: proxy_client', e)
            chan_cli.send(str(e))
            return

        # transport, 新建与后端资产通信的SSH chan渠道或SFTP Client
        if chan_cli.type == 'subsystem':
            # sftp
            chan_cli.sftp_ser = proxy_client.open_sftp()
        elif chan_cli.type in ('shell', 'ws_client'):
            # ssh终端
            chan_cli.chan_ser = proxy_client.invoke_shell(*chan_cli.pty_args)
            # chan_ser终端窗口和chan_cli保持一致, 并随客户端窗口一致调整

            session = Session(poller, chan_cli)

            shells.newlog(
                session, proxy_client.host.ip, proxy_client.hostuser.username, http_user, cli_type=chan_cli.type
            )  # 创建日志/终端录像
            session.start()  # 开启SSH会话交互
        else:
            print('未知的chan_cli类型: {chan_cli.type}')


class Shells:
    # 终端录像和结束终端，使用缓存记录状态，使网站进程可强制关闭堡垒机进程终端

    sess = {}
    timeout = 60 * 60 * 2  # 终端默认过期时间(秒), 无操作断开.
    maxtime = 60 * 60 * 24  # 终端最大生命时间(秒), 超过直接断开.

    def newlog(self, session, host, host_user, http_user, cli_type='ws_client'):
        # 有新终端连接，初始化终端日志
        cli_type = 1 if cli_type == 'ws_client' else 2
        model = models.Session.objects.create(host=host, host_user=host_user, http_user=http_user, type=cli_type)

        cache.set('proxy_sshd_%d' % model.id, 1, timeout=self.maxtime)
        self.sess[model.id] = session
        session.model = model


shells = Shells()
