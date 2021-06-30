from django.conf.urls import url

from guacamole import views
from guacamole.ws import GuacamoleWebsocket, GuacamoleMonitor

urlpatterns = [
    url(r'^(?P<hostid>\d+)/(?P<uid>\d+)/$', views.Index.as_view(), name='guacamole'),
    # url(r'^monitor/(?P<pk>\d+)/', views.Monitor.as_view(), name='monitor'),
    url(r'^replay/(?P<pk>\d+)', views.Replay.as_view(), name='replay'),
    url(r'^monitor/(?P<pk>\d+)', views.Monitor.as_view(), name='monitor'),

    # url(r'^guacamolemonitor/(?P<pk>[0-9]+)/',
    #     views.GuacmoleMonitor.as_view(), name='guacamolemonitor'),
    # url(r'^guacamolekill/$', views.GuacamoleKill.as_view(), name='guacamolekill'),
]

# websocket路由
ws_urlpatterns = [
    url(r'^guacamole/(?P<hostid>\d+)/(?P<uid>\d+)/', GuacamoleWebsocket),
    url(r'^guacamole/monitor/(?P<logid>\d+)/', GuacamoleMonitor),
]

