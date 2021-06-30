# coding=utf-8
#

from django.conf.urls import url

from .dk import *
from .ws import DockerWebsocket


urlpatterns = [

    url(r'^info/(?P<pk>\d+)/', info, name="dockerinfo"),
    url(r'^image/(?P<pk>\d+)/do/', image_do, name="docker_image_do"),
    url(r'^image/(?P<pk>\d+)/rm/', image_rm, name="docker_image_rm"),
    url(r'^image/(?P<pk>\d+)/', image, name="docker_image"),
    url(r'^image/', image, name="docker_image"),

    url(r'^container/(?P<pk>\d+)/do/', container_do, name="docker_container_do"),
    url(r'^container/(?P<pk>\d+)/rm/', container_rm, name="docker_container_rm"),
    url(r'^container/(?P<pk>\d+)/add/', container_add, name="docker_container_add"),
    url(r'^container/(?P<pk>\d+)/', container, name="docker_container"),
    url(r'^container/', container, name="docker_container"),

    url(r'^net/(?P<pk>\d+)/do/', net_do, name="docker_net_do"),
    url(r'^net/(?P<pk>\d+)/rm/', net_rm, name="docker_net_rm"),
    url(r'^net/(?P<pk>\d+)/add/', net_add, name="docker_net_add"),
    url(r'^net/(?P<pk>\d+)/', net, name="docker_net"),
    url(r'^net/', net, name="docker_net"),

    url(r'^host/', DockerHostList.as_view(), name="docker_host_list"),

    url(r'^yml/(?P<pk>\d+)/$', DockerYmlEdit.as_view(), name="docker_yml_edit"),
    url(r'^yml/add', DockerYmlAdd.as_view(), name="docker_yml_add"),
    url(r'^yml/', DockerYmlList.as_view(), name="docker_yml_list"),
    url(r'^compose/(?P<ids>.*)/del/', docker_compose_del, name="docker_compose_del"),
    url(r'^compose/(?P<pk>\d+)/do/', DockerComposeDo.as_view(), name="docker_compose_do"),
    url(r'^compose/(?P<pk>\d+)/$', DockerComposeEdit.as_view(), name="docker_compose_edit"),
    url(r'^compose/add', DockerComposeAdd.as_view(), name="docker_compose_add"),
    url(r'^compose/', DockerComposeList.as_view(), name="docker_compose_list"),


    url(r'^imagefile/(?P<ids>.*)/del/', docker_imagefile_del, name="docker_imagefile_del"),
    url(r'^imagefile/(?P<ids>.*)/load/(?P<hostid>\d+)', DockerImageFileLoad.as_view(), name="docker_imagefile_load"),
    url(r'^imagefile/upload/$', DockerComposeUpload.as_view(), name="docker_imagefile_upload"),
    url(r'^imagefile/$', DockerImageFileList.as_view(), name="docker_imagefile_list"),
    url(r'^webssh', DockerWebSSH.as_view(), name="docker_webssh"),

]

# 用于websocket路由URLS解耦
ws_urlpatterns = [
    url(r"^dock/webssh", DockerWebsocket),
]

# import ipdb;ipdb.set_trace()
