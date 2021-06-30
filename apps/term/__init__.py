

'''
SSH 堡垒机
author: exia@qq.com


堡垒机通讯流程
前端/客户端  <<===>>                     堡垒机                       <<===>> 后端/资产端
ssh_client <<===>> chan_cli - proxy_server/proxy_client - chan_ser <<===>> sshd_server
'''


'''
程序结构图
上面的依赖下面的, 越下面的越基础

session ⇦⇦  chan_ser

⇧
⇧        ↖
proxy ⇨⇨ transport_ser
       ↖
⇧         chan_cli
⇧        server_interface
conn ⇨⇨ transport_cli

⇧
⇧
sshd

'''

'''
数量关系:

一                             对          多
sshd                                     conn

conn/transport/                         proxy/session/channel/
proxy_server/proxy_client               sftp_server/sftp_client

'''

