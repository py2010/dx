# -*- coding: utf-8 -*-

import paramiko
from django.core.cache import cache

from . import models
from .utils import MyEvent, logger

proxy_clients = {}  # 用于后端socket连接复用
'''
proxy_clients,  key: 主机id_用户id, value: proxy_client
用于保存当前py进程所连接的所有后端资产ssh连接, 以便进行连接复用,
使相同主机/ssh用户的transport连接, 可对应多个chan_ser渠道.
原理上, 相当于 proxy_client <<===>> sshd_server 复制SSH渠道.

不同py进程之间, 暂不支持复用连接, 因为跨节点/跨进程通信需使用消息队列解藕,
目前chan_cli与chan_ser交互未解偶, 都在同一个进程中进行数据通讯.
'''


class ProxyClient:
    '''
    堡垒机SSH/SFTP客户端 (paramiko.SSHClient)
    proxy_client <<===>> sshd_server
    通过 SSH/SFTP 连接后端资产主机

    一个proxy_client/transport连接可以对应多个chan_ser, 只有所有chan断开后,
    transport才断开连接, 并从proxy_clients中移除proxy_client
    '''
    _transport = None

    def __new__(cls, hostid, uid, timeout=10):
        key = f'{hostid}_{uid}'  # proxy_clients 字典 key
        # import time
        # key = time.time()

        instance = proxy_clients.get(key)  # 尝试后端连接复用
        if not instance:
            instance = super().__new__(cls)
            instance.conn_server(hostid, uid, timeout)
            instance.key = key
            proxy_clients[key] = instance
        return instance

    def get_ssh_args(self, hostid, uid):
        # 准备proxy_client ==>> ssh_server连接参数
        # print(hostid, uid, 6666666)
        self.host = models.Host.objects.get(id=hostid, enable=True)
        self.hostuser = models.HostUser.objects.get(id=uid)
        logger.info((self.hostuser, self.host, 777777))
        ip = self.host.ip
        port = self.host.port_ssh or 22
        username = self.hostuser.username
        password = self.hostuser.get_password()
        rsa_key = self.hostuser.get_rsa_key()
        return (ip, port, username, password, rsa_key)

    def conn_server(self, hostid, uid, timeout):
        # proxy_client ===>> ssh_server
        ssh_args = self.get_ssh_args(hostid, uid)
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info("*** Connecting SSH (%s@%s) ...." % (ssh_args[2], ssh_args[0]))
        ssh.connect(*ssh_args, timeout=timeout)
        transport_ser = ssh._transport
        del ssh
        transport_ser.set_keepalive(60)  # 每x秒发送空数据以保持连接
        self._transport = transport_ser

    def invoke_shell(self, term="vt100", width=80, height=24, width_pixels=0, height_pixels=0, environment=None):
        chan = self._transport.open_session()
        chan.get_pty(term, width, height, width_pixels, height_pixels)
        chan.invoke_shell()
        # chan.proxy_client = self
        return chan

    def open_sftp(self):
        # 软件SFTP
        sftp = self._transport.open_sftp_client()
        # sftp.get_channel().proxy_client = self
        return sftp

    @classmethod
    def check_close(cls, chan_cli, chan_ser):
        # 用于在外部函数中, 关闭chan及后端连接
        if hasattr(chan_cli, 'transport'):
            # 软件终端的chan_cli
            auth_info = chan_cli.transport.server_object.auth_info
        else:
            # 网页终端的chan_cli
            auth_info = chan_cli.ws_server.auth_info

        proxy_client = cls(*auth_info[1:])
        if proxy_client._transport is not chan_ser.transport:
            logger.error(f'chan_cli 与 chan_ser 不配对!?!?\r\n')
            # raise
        return proxy_client.close(chan_ser)

    def close(self, chan_ser):
        '''
        由于可能存在连接复用, self._transport 有多个 chan_ser,
        当前chan_ser关闭时, 同时检查后端transport所有chan_ser是否已关闭,
        如果都关闭了, 则transport移出列表并关闭.
        '''
        chan_ser.close()
        if chan_ser in self._transport._channels.values():
            '''
            当chan_ser关闭时, 不是立即关闭并从transport_ser中去除,
            而是会向资产服务端发送提示消息, 在服务器返回前,
            transport_ser仍包含当前chan_ser
            '''
            self._transport._channels.delete(chan_ser.chanid)
        if len(self._transport._channels) == 0:
            proxy_clients.pop(self.key)._transport.close()
            logger.info(f'断开后端SSH连接, 用户:{self.hostuser}, 主机:{self.host} ')
            del self


class ProxyServer(paramiko.ServerInterface):
    '''
    堡垒机SSH/SFTP服务端
    sshent <<===>> proxy_server
    用于给前端/客户端生成 SSH/SFTP 服务端
    '''

    def __init__(self):
        '''
        由于paramiko.SFTPServerInterface只有一个参数--当前实例self,
        其它参数largs, kwargs是在transport.set_subsystem_handler预先设死,
        所以self必需能提供后端资产SSH连接参数, self.conn.ssh_args
        '''
        self.pipe = MyEvent()
        self.fileno = self.pipe.fileno

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, http_user, password):
        # 验证密码
        if self.auth_client(http_user, password):
            # sshent ===>> proxy_server 验证通过
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def auth_client(self, http_user, password):
        # 验证客户端账号密码
        key = 'clissh_%s_%s' % (http_user, password)
        hostid, uid = cache.get(key) or (None, None)

        # hostid, uid = 2, 1  # DEBUG

        logger.debug((http_user, password))
        if hostid and uid:
            # ssh_client <<===>> proxy_server 验证通过
            self.auth_info = http_user, hostid, uid
            self.pipe.set()  # 用于触发新线程 conn.run
            return True
        return False

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        # 客户端验证通过后执行
        channel.pty_args = [term, width, height, pixelwidth, pixelheight]
        logger.info((channel.pty_args, 7777777777777))
        return True

    def check_channel_shell_request(self, channel):
        logger.debug((channel, 'ssh...............'))
        channel.type = 'shell'  # 与前端/客户端对接SSH完成, 后续将连接后端SSH
        return True

    def check_channel_subsystem_request(self, channel, name):
        # SFTP子系统
        logger.debug((channel, 'sftp...............'))
        channel.type = 'subsystem'  # 与前端/客户端对接sftp完成, 后续将连接后端SFTP
        return super().check_channel_subsystem_request(channel, name)

    def check_channel_window_change_request(self, channel, width, height,
                                            pixelwidth, pixelheight):
        # 客户端调整了终端大小
        logger.debug((channel, width, height, pixelwidth, pixelheight, 88888888))
        if hasattr(channel, 'chan_ser'):
            channel.chan_ser.resize_pty(width, height, pixelwidth, pixelheight)
            return True
        return False

    # def check_channel_direct_tcpip_request(self, chan_id, origin, destination):
    #     # SSH隧道
    #     self.type = 'direct-tcpip'
    #     return 0

    # def check_auth_gssapi_with_mic(
    #     self, username, gss_authenticated=paramiko.AUTH_FAILED, cc_file=None
    # ):
    #     """
    #     .. note::
    #         We are just checking in `AuthHandler` that the given user is a
    #         valid krb5 principal! We don't check if the krb5 principal is
    #         allowed to log in on the server, because there is no way to do that
    #         in python. So if you develop your own SSH server with paramiko for
    #         a certain platform like Linux, you should call ``krb5_kuserok()`` in
    #         your local kerberos library to make sure that the krb5_principal
    #         has an account on the server and is allowed to log in as a user.

    #     .. seealso::
    #         `krb5_kuserok() man page
    #         <http://www.unix.com/man-page/all/3/krb5_kuserok/>`_
    #     """
    #     if gss_authenticated == paramiko.AUTH_SUCCESSFUL:
    #         return paramiko.AUTH_SUCCESSFUL
    #     return paramiko.AUTH_FAILED

    # def check_auth_gssapi_keyex(
    #     self, username, gss_authenticated=paramiko.AUTH_FAILED, cc_file=None
    # ):
    #     if gss_authenticated == paramiko.AUTH_SUCCESSFUL:
    #         return paramiko.AUTH_SUCCESSFUL
    #     return paramiko.AUTH_FAILED

    # def enable_auth_gssapi(self):
    #     return False

    # def get_allowed_auths(self, username):
    #     return "gssapi-keyex,gssapi-with-mic,password,publickey"
