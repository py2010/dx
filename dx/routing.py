# -*- coding: utf-8 -*-

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.routing import ChannelNameRouter
from channels.auth import AuthMiddlewareStack

from allapp import URLS_APPS

ws_urlpatterns = []
for app_urls in URLS_APPS.values():
    # 从各app中收集ws_url
    try:
        ws_urlpatterns.extend(app_urls.ws_urlpatterns)
    except Exception:
        # print(e)
        pass


from channels.consumer import SyncConsumer


class PrintConsumer(SyncConsumer):

    def test_print(self, message):
        # 'type': 'test.print',
        print(message, 111111)
        # raise


# import ipdb;ipdb.set_trace()
application = ProtocolTypeRouter({

    # WebSocket chat handler
    "websocket": AuthMiddlewareStack(
        URLRouter(ws_urlpatterns)
    ),

    # "channel": ChannelNameRouter({
    #     # manage.py runworker thumbnails-generate thumbnails-delete
    #     "thumbnails-generate": consumers.GenerateConsumer,
    #     "thunbnails-delete": consumers.DeleteConsumer,
    # }),

    "channel": ChannelNameRouter({
        "testing-print": PrintConsumer,
    }),

    # "http": some_app,  # 默认为channels.http.AsgiHandler

    # # 位置信息 APRS protocol
    # "aprs": APRSNewsConsumer,

    # # 堡垒机 SSHD protocol
    # "sshd": SSHServer,
})

'''
    堡垒机不合并到asgi监听端口中, 使用独立的监听端口.
    三次握手建立连接后, HTTP/websocket都是由客户端先主动发送请求(GET/...),
    而SSH是由服务端先主动发送ssh协议-服务端版本
    (比如b'SSH-2.0-paramiko_2.6.0\r\n') 给客户端,
    客户端再返回ssh banner信息确认.

    相关类/函数: uvicorn.protocols.http.HttpToolsProtocol,
    对于http/ws, 在connection_made之后等待客户端数据data_received,
    如果服务端无差别主动发送ssh协议信息, 在http/ws网络阻塞延时时,
    收到SSH协议信息时浏览器会直接报错.
    如果合并成一个端口, 要么加大SSH连接时等待时长, 要么忍受偶尔触发http/ws访问出错.

'''
