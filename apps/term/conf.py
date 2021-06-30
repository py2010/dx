# -*- coding: utf-8 -*-
import os
from config import priority

'''
根据配置优先级, 设置各配置值.
未指定优先级时, 默认优先级:
环境变量 > project.setting / YML > app.conf

示例:
priority.set_conf(__name__, priority=['env', 'conf'], convert=False)
'''
priority.set_conf(__name__)


SSHD = {
    # 资产系统 -- SSH代理服务端，参数配置
    'workers': 4,  # 堡垒机启动进程个数
    'host': '0.0.0.0' if os.environ.get("IPV6") == '0' else '::',
    'port': 2222,  # SSH监听端口
    'password_timeout': 60 * 1500,  # 堡垒机连接, 临时密码有效期(秒)
    'shell_timeout': 120,  # shell终端闲置分钟, 无操作则断开
    'elfinder_sftp_timeout': 10,  # 网页SFTP后端连接闲置分钟, 无操作则断开
    'zmodem_sz_sleep': 0.02,  # sz下载时, 数据包间隔秒数. 某些客户端/版本发送太快时, 下载出错.
    # 'scheme': {'ssh': 'xshell', 'sftp': 'xftp'},
    'scheme': {
        'ssh': 'ssh',  # 设置ssh的scheme
        'sftp': 'sftp',  # 设置sftp的scheme
        # Xshell.exe  ssh://user:password@192.168.80.238:2222 -newtab 标识名
        # 从网页调用外部程序，自定义的协议名，直接调用xshell时它的值必需为"ssh"，xftp为"sftp"
        # scheme如改为其它名，需通过bat脚本或自行开发客户端调用xshell或securtCRT。注册表[HKEY_CLASSES_ROOT\<scheme>]
    },

}

REPLAY_PATH = 'sshreplay'  # 存放终端录像文件夹，MEDIA_ROOT/REPLAY_PATH

