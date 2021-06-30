#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import selectors
import socket
import threading


class Conn:
    '''
    用于web rdp/vnc, 将所有后端资产交互变化传输到前端websock客户端
    '''

    def __init__(self, *args, **kwargs):
        self.stop = True
        self.poller = selectors.DefaultSelector()  # 循环轮播器

    def select(self, timeout=1):
        '''
        轮询检查轮播器中, 所有后端资产guacd socket管道事件变化,
        '''
        events = self.poller.select(timeout=timeout)  # timeout时间内, 会阻塞

        for key, event in events:
            data = key.data
            func = data[0]
            args = data[1:]
            # print(func, 222, obj)
            try:
                func(*args)
            except Exception as e:
                print(e, 8888)

    def add_guacamole(self, ws_server):
        # 有新的ws连接建立, 注册轮播chan_ser
        self.poller.register(
            ws_server.guacd_cli._client,
            selectors.EVENT_READ,
            [self.read_ser, ws_server],
        )
        self.check()

    def del_guacamole(self, ws_server):
        # ws连接断开, 注销轮播chan_ser
        try:
            if ws_server.guacd_cli._client:
                self.poller.unregister(ws_server.guacd_cli._client)
            else:
                raise
        except Exception:
            for fileno, sel in self.poller._fd_to_key.copy().items():
                if fileno != sel.fileobj.fileno():
                    # guacd_cli._client连接已关闭, fileno改变
                    self.poller._fd_to_key.pop(fileno)

        ws_server.guacd_cli.close()

    def check(self):
        '''
        检查轮播器是否有注册检测的元素, 是否启动线程
        '''
        if self.poller._fd_to_key and self.stop:
            # 开启run线程
            t = threading.Thread(target=self.run)
            t.daemon = True
            t.start()

    def read_ser(self, ws_server):
        '''
        读取后端RDP/VNC数据, 发给前端ws客户端
        后端资产 ==> guacd ==> guacd_cli - ws_server ==> ws_client
        '''
        try:
            instruction = ws_server.guacd_cli.receive()
            if instruction:
                ws_server.send(text_data=instruction)  # 发送信息到WebSock终端显示
            else:
                self.del_guacamole(ws_server)
        except socket.timeout:
            pass

    def run(self):
        self.stop = False
        print('启动 guacamole 线程...')
        while self.poller._fd_to_key:
            # 检查当前asgi进程后端资产guacd管道事件变化
            self.select(2)
        print('退出 guacamole 线程...')
        self.stop = True

