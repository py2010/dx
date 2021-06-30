# -*- coding: utf-8 -*-

import socket
import os
import logging

# %(levelname)5s对齐. WARNING长度太长, 超过5字符
logging.addLevelName(logging.WARNING, 'WARN')

logger = logging.getLogger('sshd')
# 配置在 settings.LOGGING['loggers']['sshd']


def set_logger(file_name):
    '''
    使堡垒机各进程日志隔离, 存放到不同文件
    '''
    handler = logging.FileHandler('logs/%s.log' % file_name, encoding='utf-8')
    # 定义格式器,添加到处理器中
    # fmt = '%(asctime)s , %(levelname)s , %(filename)s %(funcName)s line %(lineno)s , %(message)s'
    fmt = '[%(levelname)5s][%(asctime)s] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    log_fmt = logging.Formatter(fmt=fmt, datefmt=datefmt)
    handler.setFormatter(log_fmt)
    logger.addHandler(handler)


'''
三种管道区别:
# os.mkfifo(path)
os.pipe() 单向管道, 支持跨进程通讯
socket.socketpair() 无名套接字, 相当于双向管道, 可跨进程通讯
multiprocessing.Pipe() 双向管道, 支持跨进程通讯
'''


class MyPipe:
    # 使不支持select轮播的对象支持select
    def __init__(self):
        # 目前只用单向 p2 --> p1
        self.p1, self.p2 = socket.socketpair()

    def set(self):
        self.p2.send(b'0')

    def clear(self):
        self.p1.recv(1)

    def fileno(self):
        return self.p1.fileno()

    def __getattr__(self, item):
        return getattr(self.p1, item)


class MyEvent:
    # 使不支持select轮播的对象支持select
    def __init__(self):
        self.r, self.w = os.pipe()

    def set(self):
        os.write(self.w, b'0')

    def clear(self):
        os.read(self.r, 1)

    def fileno(self):
        return self.r

