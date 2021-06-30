# coding=utf-8
# author: exia@qq.com
import socket
import selectors
import threading
# import traceback
import errno
import time
import os

from .conn import Conn
from .utils import logger, set_logger
from .conf import SSHD

'''
SSH堡垒机启动程序, 使支持客户端软件终端.
前端/用户端  <==>                堡垒机               <==> 后端/资产端
ssh_client <==> chan_cli <- proxy_sshd -> chan_ser <==> sshd_server
'''

HOST = SSHD['host']  # 监听地址
PORT = SSHD['port']
WORKERS = SSHD.get('workers', 2)  # 进程数

cons = 10  # SSHD 预连接缓冲队列, 等待连接的最大请求数


def is_ipv6(addr):
    # 判断是否IP6监听地址
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error:
        # 错误的地址
        return False
    except ValueError:  # ipv6 not supported on this platform
        return False
    return True


class SSHServer:
    '''
    堡垒机SSHD中转服务器, 衔接 客户端终端/资产服务端SSHD
    ssh_client <<==>>           proxy_sshd          <<==>> sshd_server
    ssh_client <<==>> (proxy_server - proxy_client) <<==>> sshd_server

    poller, 对监听sock等fileno()进行轮询, 检测新客户端连接,
    由于SSH终端连接时, transport.start_server需要时间/交互, 不是立即完成,
    所以使用轮播器检测proxy_server.pipe状态, set()表示完成.
    '''
    poller = selectors.DefaultSelector()  # 监听连接 - 循环轮播器

    def __init__(self, socks=[], timeout=30, heartbeat=None, workers=None):
        '''
        Master: 监听进程
        Worker: 工作进程
        由于不想额外开发master/worker进程控制管理,
        当使用gunicorn进行多进程启动时, 则self.socks由gunicorn传参.
        '''
        self.timeout = timeout or 30  # 秒数, 各Worker秒数内状态未更新则认为进程挂了
        self.heartbeat = heartbeat  # 函数, Master心跳检测各Worker状态
        if socks:
            # 使用gunicorn启动时, 当前为一个Worker子进程, 执行run_worker任务.
            for sock in socks:
                self.poller.register(sock, selectors.EVENT_READ, [self.accept])
        else:
            # 未使用gunicorn时, 自己启动主/从多进程
            self.run_master(workers)
        self.run_worker()

    def listen(self):
        # 监听端口
        family = socket.AF_INET6 \
            if is_ipv6(HOST) else socket.AF_INET
        addr = (HOST, PORT)

        logger.info('Starting ssh server at {}:{}'.format(*addr))
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
        sock.bind(addr)
        sock.listen(cons)

        sock.setblocking(False)
        self.poller.register(sock, selectors.EVENT_READ, [self.accept])

    def run_master(self, workers=None):
        # 主进程/监听进程
        self.listen()
        workers = workers or WORKERS
        pid = 1
        while pid != 0 and workers > 1:
            # 主进程中创建子进程
            # r, w = os.pipe()  # 管道 - 跨进程通讯
            pid = os.fork()
            workers -= 1  # 下一个子进程编号
            # print(pid, os.getpid(), 333333)
        if pid == 0:
            psn = workers + 1  # 进程编号, 用于各进程日志进行分离
        else:
            psn = 1  # 主进程编号
            time.sleep(0.2)
        set_logger(f'sshd_{psn}')  # 各进程日志分离
        logger.info(f'进程编号: {psn}, 进程id: {os.getpid()}')

    def run_worker(self):
        '''
        子进程/工作进程
        未使用gunicorn, 由自身启动master时, 不进行子进程管理,
        master除了监听外, 也和其它子进程一样, 进行SSHD任务处理.
        '''
        timeout = min(self.timeout / 2, 10)
        while 1:
            if callable(self.heartbeat):
                # 当使用gunicorn进行多进程启动管理时, 用于worker心跳检测
                self.heartbeat()  # gunicorn: base.Worker.notify()
            try:
                # import ipdb; ipdb.set_trace()
                events = self.poller.select(timeout=timeout)  # timeout时间内, 会阻塞
                for key, event in events:
                    obj = key.fileobj
                    data = key.data
                    if isinstance(data, list):
                        func = data[0]
                        args = [obj, *data[1:]]
                    else:
                        func = data
                        args = [obj]
                    # print(func, 222, obj)
                    func(*args)

                # for fileno, key in self.poller._fd_to_key:
                #     # 移除轮播
                #     ...

            except Exception:
                logger.error('sshd出错:', exc_info=True)
                # traceback.print_exc()

    def accept(self, sock):
        # 新客户端 ==>> 堡垒机, 连接接入
        try:
            client_sock, addr = sock.accept()
        except EnvironmentError as e:
            if e.errno not in (errno.EAGAIN, errno.ECONNABORTED, errno.EWOULDBLOCK):
                raise
            # 队列请求已被其它进程抢先接手, 无需处理
            return

        logger.info(('new client socket:', addr))

        conn = Conn(client_sock)
        # 由于客户端认证交互需要一定时间, 加入轮播器中进行监视状态变化.
        self.poller.register(conn.proxy_server, selectors.EVENT_READ, [self.handle_connection, conn])

    def handle_connection(self, proxy_server, conn):
        # 客户端 ==>> 堡垒机, 前端SSH/SFTP只有认证OK后, 才会创建新线程
        # traceback.print_stack()
        proxy_server.pipe.clear()
        # 与(首个)前端/客户端认证好了, 移出轮播
        self.poller.unregister(proxy_server)

        # 与后端/资产主机对接, 堡垒机 ==>> 资产主机
        t = threading.Thread(target=conn.run)
        t.daemon = True
        t.start()

