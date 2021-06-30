# -*- coding: utf-8 -*-

from channels.generic.websocket import WebsocketConsumer, JsonWebsocketConsumer
# from channels import Group
try:
    import simplejson as json
except ImportError:
    import json
from django.core.exceptions import ObjectDoesNotExist

from django.utils import timezone
import os
# import time
import traceback
# import re
import threading
import weakref
from asgiref.sync import async_to_sync

from .models import Host
# from term.interactive import TTY, redis, async_to_sync
from term.conn import ConnWS
from term import utils

conn = ConnWS()  # 当前HTTP进程中, 用于轮播websocket终端交互
# asgi进程启动shell终端交互轮播器
t = threading.Thread(target=conn.run)
t.daemon = True
t.start()


class Chan:
    """
    相当于堡垒机中的 chan_cli
    使网页终端的chan_cli与软件终端中的统一, 以便同一套程序通用处理.

    ws_client <<===>> chan_cli/ws_server - proxy_client - chan_ser <<===>> sshd_server
    """
    type = 'ws_client'
    pty_args = ['xterm', 90, 32]  # 终端参数默认窗口宽高, 用于传递给chan_ser

    def __init__(self):
        self.pipe = utils.MyEvent()
        self.buffer = []

    def send(self, data):
        # server ==> ws_client
        self.ws_server.send(text_data=json.dumps(['stdout', data]))

    def recv(self, size=None):
        # 由于self.buffer为列表, size忽略
        data = self.buffer.pop(0)
        self.pipe.clear()
        return data

    def add_buffer(self, data):
        self.buffer.append(data)
        self.pipe.set()  # 用于通知轮播器数据有变化, 触发self.recv()

    def fileno(self):
        return self.pipe.fileno()


class Websocket(JsonWebsocketConsumer):
    """
    网页终端websocket服务端, 与前端ws通信.
    ws_client <<===>> ws_server
    相当于堡垒机中的 ssh_client <<===>> proxy_server
    """

    def connect(self):
        super().connect()
        print('start:', self.channel_name, str(timezone.now()))
        self.chan_cli = Chan()
        self.chan_cli.ws_server = weakref.proxy(self)
        # import ipdb; ipdb.set_trace()
        # self.send_json({"msg": "connect ok"})

    def disconnect(self, message=None):
        # import ipdb; ipdb.set_trace()
        self.chan_cli.add_buffer('')

    def receive(self, text_data=None, bytes_data=None):
        # 从前端WebSocket收取数据
        try:
            data = json.loads(text_data)
        except Exception:
            print('非法的json数据格式', text_data)
            return

        try:
            # print(data, 9999999)

            if data[0] == 'connect':
                hostid = data[1]
                try:
                    host = Host.objects.get(id=hostid)
                    if not host.enable:
                        print('主机%s已禁用:' % host)
                        self.send_json(['stdout', u'\033[1;3;31m主机已禁用\033[0m\r\n'])
                        return

                    user = self.scope.get("user", None)
                    if not host.chk_user_prem(user, 'ssh'):
                        print('用户<%s>没有主机终端权限:' % user.username, host)
                        self.send_json(['stdout', f'\033[1;3;31m您没有当前主机({host})终端权限。\033[0m\r\n'])
                        return

                except ObjectDoesNotExist:
                    self.send_json(['stdout', '\033[1;3;31mConnect to server! Server ip doesn\'t exist!\033[0m\r\n'])
                    return

                uid = data[2]

                self.auth_info = [user.username, host.id, uid]
                conn.add_chan_cli(self.chan_cli, self.auth_info)

            elif data[0] in ['stdin']:  # ,'stdout'
                # 前端SSH输入
                self.chan_cli.add_buffer(data[1])
            elif data[0] == 'close':
                self.disconnect()
            else:
                self.send_json(['stdout', '\033[1;3;31mUnknow command found!\033[0m\r\n'])

        except Exception:
            print(traceback.format_exc())


class SshMonitorWebsocket(JsonWebsocketConsumer):
    # 终端监视

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # import ipdb; ipdb.set_trace()
        channel_group = args[0]['url_route']['kwargs']['logid']
        self.channel_group = channel_group.replace('!', '-')  # Group(channel_group)要求只能字母数字、连接符
        # print(channel_group, 223)

    def connect(self):
        super().connect()
        async_to_sync(self.channel_layer.group_add)(self.channel_group, self.channel_name)

        # 发送欢迎消息
        self.send_json(['stdout', '\033[7;3;32m监视连接成功!\033[0m\r\n'])

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.channel_group, self.channel_name)
        if isinstance(code, dict):
            msg = code.get('msg', '')
            self.send_json(['stdout', f'\033[1;3;31m{msg}\033[0m\r\n'])

    def receive(self, text=None, bytes=None, **kwargs):
        pass

    def monitor_send_message(self, event):
        # 函数名需为channels全局唯一
        # event.pop('type')
        msg = event.get('msg', {})
        if type(msg) in (dict, list):
            self.send_json(msg)
        else:
            self.send(msg)
