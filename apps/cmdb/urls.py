# coding=utf-8
#

from django.urls import path
from django.conf.urls import url

# from .host import *  # host, a10, 终端
# from .elfinder.views import ElfinderConnectorView

from . import views, host
from . import ws

# from django.urls import reverse_lazy

urlpatterns = [

    path('hostgroup/add/', host.HostGroupAdd.as_view(), name="hostgroup_add"),
    path('hostgroup/delete/', host.HostGroupDelete.as_view(), name="hostgroup_delete"),
    path('hostgroup/<int:pk>/update/', host.HostGroupUpdate.as_view(), name="hostgroup_update"),
    path('hostgroup/', host.HostGroupList.as_view(), name="hostgroup_list"),

    path('host/add/', host.HostAdd.as_view(), name="host_add"),
    path('host/delete/', host.HostDelete.as_view(), name="host_delete"),
    path('host/<int:pk>/update/', host.HostUpdate.as_view(), name="host_update"),
    path('host/', host.HostList.as_view(), name="host_list"),

    # # url(r'^', include(('.elfinder.urls', 'elfinder'), namespace="elfinder")),
    # url(r'^elfinder/yawd-connector/(?P<optionset>.+)/(?P<host_id>.+)/(?P<u_id>.+)/$', ElfinderConnectorView.as_view(), name='yawdElfinderConnectorView'),

    url(r'^clissh/(?P<hostid>\d+)', host.CliSSH.as_view(), name="clissh"),  # 生成临时账号密码供跳转xshell访问
    url(r'^term', host.Term.as_view(), name="term"),
    # url(r'^sshreplay/(?P<pk>\d+)/', host.SshReplay.as_view(), name='ssh_replay'),
    url(r'^session/kill', host.SessionKill.as_view(), name='session_kill'),
    path('session/delete/', host.SessionDelete.as_view(), name="session_delete"),
    url(r'^session', host.SshLogList.as_view(), name='session'),
    url(r'^sshmonitor/(?P<logid>.*)', host.SshMonitor.as_view(), name='sshmonitor'),

    path('hostuser/add/', views.HostUserAdd.as_view(), name="hostuser_add"),
    path('hostuser/delete/', views.HostUserDelete.as_view(), name="hostuser_delete"),
    path('hostuser/<int:pk>/update/', views.HostUserUpdate.as_view(), name="hostuser_update"),
    # path('hostuser/<int:pk>/', views.HostUserDetail.as_view(), name="hostuser_detail"),
    path('hostuser/', views.HostUserList.as_view(), name="hostuser_list"),

    path('perm/add/', views.PermAdd.as_view(), name="perm_add"),
    path('perm/delete/', views.PermDelete.as_view(), name="perm_delete"),
    path('perm/<int:pk>/update/', views.PermUpdate.as_view(), name="perm_update"),
    path('perm/', views.PermList.as_view(), name="perm_list"),

]

# 用于websocket路由URLS解耦
ws_urlpatterns = [
    url(r"^webssh", ws.Websocket),
    url(r"^monitor/(?P<logid>.*)", ws.SshMonitorWebsocket),
]

# import ipdb;ipdb.set_trace()

