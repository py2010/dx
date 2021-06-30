# -*- coding: utf-8 -*-

import errno
import os
import time
import paramiko

from .utils import logger
from .ssh import ProxyClient

# proxy_sshd
# ssh_client ===>> chan_cli - proxy_sshd - sftp_ser ==>> ssh_server
# ssh_client ===>>  (proxy_server <-> proxy_client) ==>> ssh_server


def asbytes(self):
    '''
    Paramiko SFTP目录列表中, 用户/组是ID数值，改为字符
    SFTPServer._read_folder: msg.add_string(attr)

    软链接无效, 仍然是uid, sftp数据包组装原理不明.
    SFTPServer._response: item._pack(msg)
    直接加msg.add_string(longname)不认, 会错位.
    '''
    # if ' xyf' in self.longname:
    #     import traceback
    #     traceback.print_stack()

    return paramiko.py3compat.b(self.longname)

paramiko.SFTPAttributes.asbytes = asbytes  # 猴子补丁


class SftpServer(paramiko.SFTPServer):
    '''
    与前端用户sftp交互
    ssh_client ===>> proxy_server
    proxy_server收到用户subsystem/sftp请求后生成当前类实例,
    注意: 一个sftp_server实例只对应一个sftp客户端/chan_cli.

    重写类, 用于传递后端SSH连接参数.
    由于SFTPInterface只有一个参数proxy_server可以自定义传参,
    其它参数largs, kwargs是在set_subsystem_handler预先设死的,
    为不依赖ServerInterface传参, 重写当前类.
    '''

    def __init__(self, chan_cli, *largs, **kwargs):
        super().__init__(chan_cli, *largs, **kwargs)
        # self.server 为SftpClient实例
        self.server.chan_cli = chan_cli  # sftp_client.chan_cli传参
        self.server.session_started()


class SftpClient(paramiko.SFTPServerInterface):
    '''
    与后端资产sftp交互
    proxy_client ==>> ssh_server
    注意 ProxyServer实例(ServerInterface) 主要用于与 前端/用户 通信,
    但是 当前类实例 (SFTPServerInterface), 主要用于与 后端/资产 通信,

    paramiko设计的SFTPServerInterface是与SFTPServer配套提供SFTP服务.
    '''
    root_path = ''  # sftp主目录对应主机目录, 为空表示主机根目录/,所有目录

    # def __init__(self, proxy_server, *largs, **kwargs):
    #     '''
    #     由SftpServer.super().__init__函数生成当前类实例,
    #     提供了一个参数 proxy_server (ServerInterface实例),

    #     sftp后端通信对象, 和ssh终端一样, 统一从 chan_cli.xxx_ser获取,
    #     因此不使用proxy_server传参, 因为理论上sftp也应当和ssh一样,
    #     当连接复用时, 一个 proxy_server 可以对应多个 channel/sftp_client,
    #     而 paramiko.SFTPServer 与 chan_cli 是一对一关系,
    #     '''
    #     ...
    #     print(proxy_server, 999999999)
    #     super().__init__(proxy_server, *largs, **kwargs)
    #     proxy_client = ProxyClient(*proxy_server.auth_info[1:])
    #     self._sftp = proxy_client.open_sftp()

    def session_started(self):
        # 连接后端SFTP
        # import ipdb; ipdb.set_trace()
        time.sleep(1)
        timeout = 5
        while not hasattr(self.chan_cli, 'sftp_ser'):
            if timeout < 0:
                # 超时
                self.session_ended()
                break
            # 等待Proxy实例生成sftp_ser
            sec = 0.2
            logger.debug(f'waiting conn.run, sleep... {sec}')
            time.sleep(sec)
            timeout -= sec
        self._sftp = self.chan_cli.sftp_ser
        self.chan_ser = self._sftp.get_channel()
        self.transport = self.chan_ser.transport

    def session_ended(self):
        # import ipdb; ipdb.set_trace()
        logger.info('后端SFTP关闭: %s@%s' % (self.transport.get_username(), self.transport.getpeername()[0]))
        super().session_ended()
        ProxyClient.check_close(self.chan_cli, self.chan_ser)
        # self.chan_ser.proxy_client.close(self.chan_ser)
        del self

    def _parsePath(self, path):
        if not self.root_path:
            return path

        # Prevent security violation when root_path provided
        result = os.path.normpath(self.root_path + '/' + path)
        if not result.startswith(self.root_path):
            raise IOError(errno.EACCES)
        return result

    def list_folder(self, path):
        try:
            filelist = self._sftp.listdir_attr(self._parsePath(path))
            # import ipdb; ipdb.set_trace()
            return filelist
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        try:
            return self._sftp.stat(self._parsePath(path))
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def lstat(self, path):
        try:
            return self._sftp.lstat(self._parsePath(path))
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def open(self, path, flags, attr):
        try:
            if (flags & os.O_CREAT) and (attr is not None):
                attr._flags &= ~attr.FLAG_PERMISSIONS
                paramiko.SFTPServer.set_file_attr(self._parsePath(path), attr)

            if flags & os.O_WRONLY:
                if flags & os.O_APPEND:
                    fstr = 'ab'
                else:
                    fstr = 'wb'
            elif flags & os.O_RDWR:
                if flags & os.O_APPEND:
                    fstr = 'a+b'
                else:
                    fstr = 'r+b'
            else:
                # O_RDONLY (== 0)
                fstr = 'rb'

            f = self._sftp.open(self._parsePath(path), fstr)

            fobj = paramiko.SFTPHandle(flags)
            fobj.filename = self._parsePath(path)
            fobj.readfile = f
            fobj.writefile = f
            fobj.client = self._sftp
            return fobj

            # TODO: verify (socket.error when stopping file upload/download)
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)

    def remove(self, path):
        try:
            self._sftp.remove(self._parsePath(path))
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        try:
            self._sftp.rename(self._parsePath(oldpath), self._parsePath(newpath))
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def mkdir(self, path, attr):
        try:
            if attr.st_mode is None:
                self._sftp.mkdir(self._parsePath(path))
            else:
                self._sftp.mkdir(self._parsePath(path), attr.st_mode)
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def rmdir(self, path):
        try:
            self._sftp.rmdir(self._parsePath(path))
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        try:
            if attr._flags & attr.FLAG_PERMISSIONS:
                self._sftp.chmod(self._parsePath(path), attr.st_mode)
            if attr._flags & attr.FLAG_UIDGID:
                self._sftp.chown(self._parsePath(path), attr.st_uid, attr.st_gid)
            if attr._flags & attr.FLAG_AMTIME:
                self._sftp.utime(self._parsePath(path), (attr.st_atime, attr.st_mtime))
            if attr._flags & attr.FLAG_SIZE:
                with self._sftp.open(self._parsePath(path), 'w+') as f:
                    f.truncate(attr.st_size)
        except IOError as e:
            return paramiko.SFTPServer.convert_errno(e.errno)
        return paramiko.SFTP_OK

    def symlink(self, target_path, path):
        # TODO
        return paramiko.SFTP_OP_UNSUPPORTED

    def readlink(self, path):
        # TODO
        return paramiko.SFTP_OP_UNSUPPORTED

