# -*- coding: utf-8 -*-


from channels.generic.websocket import JsonWebsocketConsumer
# from channels import Group
try:
    import simplejson as json
except ImportError:
    import json

from django.utils import timezone
# import os
import time
import traceback
# import re

import threading

import docker
from socket import timeout
from ssl import SSLError
from django.utils.encoding import smart_text

from .models import DockerHost

import django_redis
redis = django_redis.get_redis_connection("default")


class DockerWebsocket(JsonWebsocketConsumer):
    """
    用于容器终端 - Websocket
    实际上，所有Docker终端连接操作全是通过Docker服务端HTTP API完成，
    当前WebSocket只是做为中介，将docker客户端、服务端HTTP交互信息展示给前端
    """

    def connect(self):
        super().connect()
        print('start:', self.channel_name, str(timezone.now()))
        # import ipdb; ipdb.set_trace()

    def disconnect(self, message=None):
        # import ipdb; ipdb.set_trace()
        redis.lpush(self.channel_name, '\x04')
        print('disconnect..................')

    def receive(self, text_data=None, bytes_data=None):
        # 从前端WebSocket收取数据
        try:
            data = json.loads(text_data)
        except Exception:
            print('非法的json数据格式', text_data)
            return

        try:
            if data:
                # print(data, 9999999)

                if data[0] == 'hostid':
                    user = self.scope.get("user", None)
                    # import ipdb; ipdb.set_trace()
                    if not user.has_perm('cmdb.containers_manage'):
                        print('用户<%s>没有容器管理权限' % user.username)
                        self.send(text_data=json.dumps(['stdout', u'\033[1;3;31m非法操作！当前用户无容器管理权限。\033[0m\r\n']))
                        return

                    cli = DockerHost.objects.get(id=data[1]).client
                    """
                    docker exec 方式进入容器终端
                    container = cli.containers.get(data[2])
                    tty = container.exec_run('/bin/bash', stdin=True, socket=True, tty=True)
                    若要自定义终端宽高，需重写官方container.exec_run函数
                    docker官方底层API支持定义终端宽高，
                    1. client.api.exec_create，生成resp['Id']
                    2. client.api.exec_start
                    3. time.sleep
                    4. client.api.exec_resize(resp['Id'], 高, 宽)
                    container.exec_run函数只执行上面二步，但返回的对像，已不含resp连接信息

                    终端参数说明
                    1. socket，必需为True，保持socket连接，类似websocket终端连接. 客户端为网站服务器，服务端为远程宿主机。
                    2. stdin，必需为True，开启输入交互，每次按键都可发给服务端或者回车后将命令发给服务端，上下键历史命令、tab补全功能，需实时将stdin按键发送给容器HTTP服务端。
                    3. tty，建议为True，开启伪终端后，Docker HTTP API stdout输出信息会带终端版面布局、着色等，否则输出不带终端布局字符.
                    """
                    # 开始建立终端连接，tty=True，终端为伪终端，所有终端通讯实质为HTTP API，服务端HTTP返回的信息带终端版面、着色等终端字符。
                    tty_ok = 0
                    shs = ['/bin/bash -l', '/bin/sh -l']  # 终端入口命令，如果容器上没有，将HTTP404
                    for sh in shs:
                        try:
                            resp = cli.api.exec_create(
                                container=data[2], cmd=sh, stdout=True, stderr=True, stdin=True, tty=True,
                                privileged=False, user='', environment=None
                            )
                        except docker.errors.APIError as e:
                            error = '\033[1;3;31mdocker exec执行出错,\r\n%s\033[0m\r\n' % str(e)
                            self.send(text_data=json.dumps(['stdout', error]))
                            return
                        tty = cli.api.exec_start(
                            resp['Id'], detach=False, tty=True, socket=True
                        )
                        time.sleep(1)
                        try:
                            cli.api.exec_resize(resp['Id'], 32, 106)  # 调整终端输出窗口大小
                            tty_ok = 1
                            break
                        except docker.errors.NotFound:
                            continue

                    if tty_ok:
                        '''
                        python3
                        docker == 3.7.3 BUG
                        docker.api.client.APIClient._get_raw_response_socket
                        ===============================================
                        elif six.PY3:
                            sock = response.raw._fp.fp.raw  # socket.SocketIO
                            if 1: # self.base_url.startswith("https://"):
                                sock = sock._sock
                        ===============================================
                        TLS终端正常,非加密的终端也需返回sock._sock才正常
                        '''
                        if hasattr(tty, '_sock'):
                            # TLS False
                            # tty为socket.SocketIO
                            tty = tty._sock
                        # if tty.__class__.__name__ == 'WrappedSocket':
                        #     tty = tty.socket
                        # import ipdb;ipdb.set_trace()
                        th = threading.Thread(target=docker_tty, args=(tty, self))
                        th.setDaemon(True)
                        th.start()  # 启动终端

                    else:
                        error = '\033[1;3;31m生成终端需依赖%s其中之一，请确认当前容器是否含有这些文件\033[0m\r\n' % ' '.join(shs)
                        self.send(text_data=json.dumps(['stdout', error]))
                    return

                elif data[0] in ['stdin']:  # ,'stdout'
                    # 前端输入转发给redis队列左入，后端将从redis队列右取（redis模拟先进先出--消息队列）
                    print(data, '###########')
                    # import ipdb; ipdb.set_trace()
                    redis.lpush(self.channel_name, data[1])

                elif data[0] == 'close':
                    self.disconnect()
                else:
                    self.send(text_data=json.dumps(['stdout', '\033[1;3;31mUnknow command found!\033[0m\r\n']))

        except Exception:
            print(traceback.print_exc())


def docker_tty(chan, ws_channel):
    """
    chan: 后端Docker HTTP 伪终端，当前函数中只收不发
    ws_channel：前端WebSocket，当前函数中只发不收
    redis队列 ==> 后端chan ==> 前端ws_channel
    Docker Server HTTP API 终端不支持汉字
    """

    # import ipdb; ipdb.set_trace()
    chan.settimeout(0.1)
    while 1:
        data = redis.rpop(ws_channel.channel_name)
        if data:
            # print(type(data), 44444444444)
            # import ipdb; ipdb.set_trace()
            if data == '\x04':
                print('websocket断开...')
                break
            else:
                chan.send(data)
        # 循环监视ssh终端输出，实时发给websocket客户端显示
        try:
            # print('stdin:', self.stdin, '!!!!!!!!!!')
            # import ipdb;ipdb.set_trace()
            x = chan.recv(4096)  # 收取ssh-tty打印信息，带着色
            try:
                # while ord(x[-1]) > 127:
                while x[-1] > 127:
                    # utf8字符为3位，有时截取时结尾刚好碰到utf8字符，导致汉字被分割成二部分
                    try:
                        x += chan.recv(1)
                    except Exception:
                        break
            except IndexError:
                break
            # sys.stdout.write(x)
            # sys.stdout.flush()
            x = smart_text(x)
            print('stdout:', [x], 888)
            # import ipdb;ipdb.set_trace()
            # print(111,len(x),222,'<%s>'% x[-1])
            if len(x) == 0:
                ws_channel.send(text_data=json.dumps(['disconnect', smart_text('\r\n*** EOF\r\n')]))
                break

            ws_channel.send(text_data=json.dumps(['stdout', x]))  # 发送信息到WebSock终端显示
            # print(json.dumps(['stdout',smart_text(x)]),555)

        except (timeout, SSLError):
            # 非加密docker API, socket.timeout
            # TLS加密的2375, ssl.SSLError
            # time.sleep(0.1)
            pass
        except UnicodeDecodeError as e:
            # import ipdb;ipdb.set_trace()
            print(e)
            lines = x.splitlines()
            for line in lines:
                # recv(1024字节)，除乱码字符所在行外，将其它行正常显示
                if line:
                    try:
                        ws_channel.send(text_data=json.dumps(['stdout', '%s\r\n' % smart_text(line)]))
                    except UnicodeDecodeError as e:
                        ws_channel.send(text_data=json.dumps(['stdout', 'Error: utf-8编码失败！！！'], ))

        except Exception as e:
            # raise
            print(111, e, 3333)
            ws_channel.send(text_data=json.dumps(['stdout', 'Error: 连接意外中断.' + smart_text(e)], ))
            break
