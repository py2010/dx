# -*- coding: utf-8 -*-
from channels.generic.websocket import JsonWebsocketConsumer

import uuid

import traceback
from django.utils import timezone
from asgiref.sync import async_to_sync

from .instruction import GuacamoleInstruction as Instruction
from .client import GuacamoleClient
from . import conf, conn, models

conn = conn.Conn()  # 当前HTTP进程中数据传输: rdp/vnc guacamole服务端 ==> 网页客户端


class GuacamoleWebsocket(JsonWebsocketConsumer):
    '''
    网页-远程桌面/vnc对应的ws服务端
    ws_client <<===>> ws_server - guac_client <==> guacd <<===>> rdp/vnc_server
    '''
    guacd_cli = None

    def connect(self):
        self.accept(subprotocol='guacamole')  # Sec-WebSocket-Protocol
        # super().connect()
        user = self.scope.get("user", None)  # 网站用户

        kwargs = self.scope['url_route']['kwargs']
        # print(kwargs)
        hostid = kwargs.get('hostid')
        uid = kwargs.get('uid')
        if not (hostid and uid):
            return self.send_json({"msg": "请提供连接的用户和主机"})

        try:
            self.host = models.Host.objects.get(id=hostid, enable=True)
            host_user = models.HostUser.objects.get(id=uid)
        except Exception as e:
            return self.send_json({
                "msg": "获取主机或用户失败",
                "error": str(e),
            })

        if not self.host.chk_user_prem(user, 'ssh'):
            # print('用户<%s>没有主机 %s RDP权限:' % user.username, self.host)
            return self.send_json({"msg": f"您没有当前主机({self.host})远程操作权限"})

        self.guacd_cli = GuacamoleClient(conf.guacd_hostname, conf.guacd_port)

        file_log = '%s.%s.log' % (timezone.now().strftime("%Y.%m.%d.%H.%M.%S"), uuid.uuid4().hex[:6])
        # import ipdb; ipdb.set_trace()
        try:
            self.guacd_cli.handshake(
                protocol=host_user.protocol,
                hostname=self.host.ip,
                port=self.host.ALL_PROTOCOLS[host_user.protocol],
                username=host_user.username,
                password=host_user.get_password(),
                recording_name=file_log,  # 录像文件名
                ignore_cert='true',
                security='any',
                **conf.GUACD,
            )
        except Exception:
            traceback.print_exc()
            return

        conn.add_guacamole(self)

        # 录像日志
        self.log = models.Session.objects.create(
            log=file_log,
            host=self.host,
            host_user=host_user,
            http_user=user.username,
            type=8 if host_user.protocol == 'rdp' else 9,  # 8 RDP, 9 VNC
        )
        # 加入channel组, 用于外部强制中止
        async_to_sync(self.channel_layer.group_add)(str(self.log.id), self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        # 网页客户端 ==> rdp/vnc 服务端
        try:
            self.guacd_cli.send(text_data)
        except Exception as e:
            print(e, 66666)
            pass

    def disconnect(self, code):
        print(f'{self.host} guacamole disconnect..........')
        try:
            self.log.end_time = timezone.now()
            self.log.save()
        except Exception:
            pass
        conn.del_guacamole(self)
        if hasattr(self, 'log'):
            async_to_sync(self.channel_layer.group_discard)(str(self.log.id), self.channel_name)
        # self.send('5.error,22.Forcibly disconnected.,3.523;')
        if isinstance(code, dict):
            msg = code.get('msg', '')
            self.send_json({'disconnect': msg})


class GuacamoleMonitor(JsonWebsocketConsumer):
    '''
    guacamole 监视, 不同于CMDB_SSH监视(monitor_send_message)
    这里是利用guacamole可以多人共享共同控制同一界面, 因为图像要初始化界面.

    外部控制强制中断时, 利用group_send群发中断.
    '''

    def connect(self):
        self.accept(subprotocol='guacamole')  # Sec-WebSocket-Protocol
        # super().connect()
        user = self.scope.get("user", None)  # 网站用户

        if not user.has_perm('cmdb.play_session'):
            # print('用户<%s>没有主机 %s RDP权限:' % user.username, self.host)
            return self.send_json({"msg": "当前用户无会话监视权限"})

        kwargs = self.scope['url_route']['kwargs']
        # print(kwargs)
        logid = kwargs.get('logid')
        if not logid:
            return self.send_json({"msg": "logid?"})

        try:
            self.log = models.Session.objects.get(id=logid)
        except Exception as e:
            return self.send_json({
                "msg": "获取监控会话失败",
                "error": str(e),
            })

        # 根据log查询出guacd_cli
        gucamole_client_id = ''  # 所要监视的会话 guacd_cli._id
        for _, sel in conn.poller._fd_to_key.items():
            if sel.data[1].log == self.log:
                gucamole_client_id = sel.data[1].guacd_cli._id
                break
        if not gucamole_client_id:
            return self.send_json({
                "msg": "未找到正在运行的会话, 监视的会话已结束?"
            })

        self.guacd_cli = GuacamoleClient(conf.guacd_hostname, conf.guacd_port)

        # draft version for real time monitor
        self.guacd_cli.send_instruction(Instruction('select', gucamole_client_id))
        instruction = self.guacd_cli.read_instruction()
        kwargs = {
            'read_only': 'true'  # 监视时需只读, 不共享控制
        }
        connection_args = [
            kwargs.get(arg.replace('-', '_'), '') for arg in instruction.args
        ]
        self.guacd_cli.send_instruction(Instruction('size', 800, 600, 96))
        self.guacd_cli.send_instruction(Instruction('audio', ))
        self.guacd_cli.send_instruction(Instruction('video', ))
        self.guacd_cli.send_instruction(Instruction('image', ))
        self.guacd_cli.send_instruction(Instruction('connect', *connection_args))

        conn.add_guacamole(self)
        # 加入channel组, 用于外部强制中止
        async_to_sync(self.channel_layer.group_add)(str(self.log.id), self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        # 网页客户端 ==> rdp/vnc 服务端
        self.guacd_cli.send(text_data)

    def disconnect(self, code):
        if hasattr(self, 'log'):
            print(f'{self.log} Guacamole Monitor  disconnect..........')
            async_to_sync(self.channel_layer.group_discard)(str(self.log.id), self.channel_name)
        if hasattr(self, 'guacd_cli'):
            conn.del_guacamole(self)
            # self.send('5.error,22.Forcibly disconnected.,3.523;')

        if isinstance(code, dict):
            msg = code.get('msg', '')
            self.send_json({'disconnect': msg})

