# -*- coding: utf-8 -*-

import socket
import selectors
import time
# from django.utils.encoding import smart_text

import re
import os
from asgiref.sync import async_to_sync

from . import conf
from .interactive import channel_layer, savelog
from .utils import logger
from .ssh import ProxyClient


class Session:
    '''
    ssh终端交互
    '''

    def __init__(self, poller, chan_cli):
        self.poller = poller  # 循环轮播器
        self.chan_cli = chan_cli
        self.chan_ser = chan_cli.chan_ser

        self.closed = False

    def read_ser(self, chan_ser):
        '''
        chan_ser有新消息可读时触发
        ser.recv接收 ssh_server ==> proxy
        cli.send发送 proxy ==> ssh_client
        '''
        try:
            size = 4096
            x = self.chan_ser.recv(size)
            if len(x) == 0 and not self.closed:
                self.chan_cli.send("\r\n服务端已断开连接....\r\n")
                return self.close()
            else:
                while len(x) == size and x[-1] > 127:
                    # utf8字符为3位，有时截取时结尾刚好碰到utf8字符，导致汉字被分割成二部分
                    try:
                        x += self.chan_ser.recv(1)
                        size += 1
                        # print(x, 111222)
                    except Exception:
                        logger.error('读取chan_ser消息出错:', exc_info=True)
                        break
                self.chan_cli.send(x)
                self.handle(x)

                if len(x) == size:
                    '''
                    某些环境下chan_cli.send发送太快时, sz下载出错, 和客户端操作系统/工具/版本相关.
                    '''
                    time.sleep(conf.SSHD.get('zmodem_sz_sleep', 0.01))

        except socket.timeout:
            pass

    def read_cli(self, chan_cli):
        '''
        chan_cli有新消息时触发
        cli.recv接收 ssh_client ==> proxy
        ser.send发送 proxy ==> ssh_server
        '''
        logger.debug((chan_cli, os.getpid(), '+++++++++++++++++++++'))
        try:
            x = self.chan_cli.recv(1024)
            if len(x) == 0 and not self.closed:
                logger.info(f"{self.chan_cli} 客户端断开了连接....\r\n")
                return self.close()
            else:
                self.chan_ser.send(x)
                self.stdin = x
        except socket.timeout:
            pass
        except socket.error:
            pass

    def start(self):

        self.last_active_time = time.time()  # 用于长时间无操作则断开
        self.stdin = ''  # 收集用户端按键输入
        self.stdins = ['', ]  # 收集用户端按键输入

        # 用于录像中, 上传下载时过滤zmodem数据
        self._zmodem_recv_start_mark = b'rz waiting to receive.**\x18B0100'
        self._zmodem_send_start_mark = b'**\x18B00000000000000'
        self._zmodem_cancel_mark = b'\x18\x18\x18\x18\x18'
        self._zmodem_end_mark = b'**\x18B0800000000022d'
        self._zmodem_state_send = 'send'
        self._zmodem_state_recv = 'recv'
        self._zmodem_state = ''

        # self.chan_cli.settimeout(0.0)
        self.chan_ser.settimeout(0.0)

        self.stdouts = []  # 收集录像记录
        self.begin_time = self.last_activity_time = time.time()

        self.poller.register(self.chan_cli, selectors.EVENT_READ, self.read_cli)
        self.poller.register(self.chan_ser, selectors.EVENT_READ, self.read_ser)

    def handle(self, data):
        '''
        处理从chan_ser收到的数据, 进行审计/录像记录/群发监视等

        监视原理:
        webssh终端的监视, 前后端所有实例都在asgi进程中, channels库完全支持.
        而在堡垒机终端监视时, 虽然chan_cli和chan_ser未解藕, 不支持跨进程,
        但channels本身功能支持跨进程甚至跨主机通信, 使用缓存/消息队列交互,
        也就是说asgi进程可以接收堡垒机发的信息, (但反过来就不支持, 未做解藕开发)
        这时, chan_cli和chan_ser所在进程为堡垒机进程,
        监视者的ws_cli是在asgi网站进程中.
        '''
        self.last_active_time = now = time.time()

        # 记录操作录像
        delay = round(now - self.last_activity_time, 6)
        # print[delay, data], 999
        if self._zmodem_state:
            # zmodem 传输中
            if data[:24].find(self._zmodem_end_mark) != -1:
                self._zmodem_state = ''
                data = '\b\b\b\b\b下载完成.'
            elif data[:24].find(self._zmodem_cancel_mark) != -1:
                self._zmodem_state = ''
                data = '\b\b\b\b\b下载取消.'

            elif now - self.last_activity_time > 0.2:
                # 录像显示下载中load...动态图标
                icos = {
                    # ↓↙←↖↑↗→↘
                    0: '|',
                    1: '/',
                    2: '―',
                    3: '\\',
                }
                index = int(float(str(now)[7:]) / 0.2) % len(icos)
                data = icos.get(index, '.')
                # random.choice(['|', '/', '-', '\\'])
            else:
                # zmodem 文件数据不录像.
                return
            data = '%s%s' % ('\b' * len(data), data)  # \b 清除刷新之前的数据
        else:
            if data[:50].find(self._zmodem_recv_start_mark) != -1:
                # zmodem开始上传
                self._zmodem_state = self._zmodem_state_recv
            elif data[:24].find(self._zmodem_send_start_mark) != -1:
                # zmodem开始下载
                self._zmodem_state = self._zmodem_state_send
                data = '下载中   '
            else:
                # 非zmodem (sz rz)
                ...

        if isinstance(data, bytes):
            data = data.decode('utf-8', 'replace')
        self.stdouts.append([delay, data])
        self.last_activity_time = now

        # 命令收集
        if self.stdin:
            # 收集输入按键，用于审计生成命令
            self.set_stdins(stdin=self.stdin, stdout=data)
            logger.debug((self.stdins, '-----------------'))
            self.stdin = ''
        elif len(data) < 3 and data.strip('\x07') != '':
            # 按键过快，输出慢的情景
            self.stdins.append(data)

        # 发送到监视 ()
        async_to_sync(channel_layer.group_send)(
            str(self.model.id),  # 群发频道使用表数据的主键
            {
                "type": "monitor_send_message",
                "msg": ['stdout', data],
            }
        )

    def close(self):
        # 关闭ssh终端, 并保存录像
        if not self.closed:
            self.closed = True
            # 必须先注销轮询, 再关闭chan. 因关闭chan时, fileno会变化.
            self.poller.unregister(self.chan_ser)
            self.poller.unregister(self.chan_cli)
            ProxyClient.check_close(self.chan_cli, self.chan_ser)

            times = round(time.time() - self.begin_time, 6)  # 录像总时长
            savelog(self.model, times, self.stdouts, stdins=self.stdins)
            # import ipdb; ipdb.set_trace()

    def set_stdins(self, stdin, stdout):
        """
        根据输入输出，生成命令输入按键字符列表，用于审计
        1.处理输出stdout，虽然界面stdout中包含了所有信息，但复制粘贴一大片带回车的命令时，
          由于输出无延时，输入输出信息同时出现，合成一大片，解析处理复杂，所以忽略，需结合stdin
        2.处理前端输入stdin，由于table键补全、上下方向键历史命令，都无法获知，只有stdout中才有，
          在第三方软件界面，比如vi top等，stdin混杂了很多无需统计的按键输入，处理复杂。
        将输入的信息合成到self.stdins
        """

        if isinstance(stdin, bytes):
            stdin = stdin.decode('utf-8', 'replace')
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', 'replace')

        # import ipdb;ipdb.set_trace()
        if stdin == u'\x1b[2;2R\x1b[>0;276;0c' or u'\x1bP' in stdin or u'\x1b\\' in stdin:
            # 进入vi窗口，前端websocket会自动输入一些终端版面数据
            return
        elif stdin == stdout:
            # 除了控制命令，正常情况下输入命令按键与终端显示输出一样
            self.stdins.append(stdin)
        elif stdin == '\r':
            if stdout.startswith('\r\n'):
                self.stdins.append('\r\n')
            else:
                # 非命令行界面的回车
                self.stdins.append('^C')
        elif '\r' in stdin:
            # 复制粘贴多行，根据输出判断是否直接加入或vi等第三方界面的粘贴
            # 假如粘贴的命令中带tab，无法探测自动补全
            li = stdin.split('\r')
            if li[0]:
                # 第一个命令，stdout开头应当有
                if not stdout.startswith('%s\r' % li[0]):
                    return
            else:
                # 回车
                if not stdout.startswith('\r'):
                    return
            self.stdins.append(stdin.replace('\r', '\r\n').replace('\t', '<Tab键>'))  # 直接加入
            self.stdins.append('\r\n')  # 分隔、结尾退出

        elif stdin == u'\x03':
            if stdout.startswith('^C'):
                self.stdins.append('^C')
        elif stdout.strip(u'\u0007') == '':
            # 输出空效果字符(主板㖓鸣器)
            return
        else:
            if u'\u001b[' in stdout:
                txt = stdout
                for c in [
                    u'\u001b[K',  # 光标
                    u'\u001b[C',  # 右键字符
                    u'\u001b[1@',  # 左右移动光标后，空格分隔的左边输入字符
                ]:
                    txt = txt.replace(c, '')
                p = '(\x1b\[\d+P)'
                txt = re.sub(re.compile(p, re.S), '', txt)  # 上下左右键产生的 u'\u001b[数字P'
                if u'\u001b[' in txt:
                    # 除去退格键、方向键产生的\u001b[字符外，仍有其它非人工输入导致出现在终端界面字符
                    # 非命令输入，不收集。比如vi编辑、top等界面
                    return

            if stdin in (u'\x1b', '\t'):
                # tab esc处理
                if '\r\n' in stdout or stdout == u'\x07':
                    # 用户按tab，终端显示多行内容，需选择补全，不收集
                    return
                stdout = stdout.strip(u'\x07')  # 有些终端补全的字符前带㖓鸣字符

            if stdin in (
                u'\x1b[C',  # 右
                u'\x1b[D',  # 左
                u'\x1b[H',  # Home
                u'\x1b[F',  # End
                u'\x7f',  # 退格
                u'\x1b[3~',  # Delete
            ):
                self.stdins.append(stdin)
                return
            elif '\r\n' in stdout:
                return
            # if stdin not in (
            #     u'\x1b[A',  # 上
            #     u'\x1b[B',  # 下
            #     u'\x7f',  # 退格，输出效果和上下按键一样，合并处理

            #     u'\t',  # tab
            #     u'\x1b',  # Esc

            #     # u'\x1a',  # ctrl+z
            #     # u'\x18',  # ctrl+x
            #     # u'\x1b[2~',  # Insert
            #     # u'\x1b[5~',  # 上页
            #     # u'\x1b[6~',  # 下页
            # ):
            #     if stdout == u'\x1b[1@%s' % stdin:
            #         # 左右方向键后，按键输入，append(stdout)
            #         pass
            #     else:
            #         # 非控制键，按键输入与输出不同，不收集
            #         return
            self.stdins.append(stdout)
            # import ipdb;ipdb.set_trace()
