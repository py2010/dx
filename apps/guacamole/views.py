# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render_to_response

from . import models, conf


class Index(LoginRequiredMixin, PermissionRequiredMixin, View):
    '''通过guacamole连接远程主机'''
    permission_required = 'cmdb.ssh_host'

    def get(self, request, hostid, uid):
        return render_to_response('guacamole/index.html', locals())


class Replay(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    '''guacamole录像回放'''
    permission_required = 'cmdb.play_session'
    model = models.Session
    template_name = 'guacamole/replay.html'
    raise_exception = True  # 无权限时403, 否则跳转登录界面

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['REPLAY_PATH'] = conf.REPLAY_PATH
        return context


class Monitor(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    '''guacamole录像回放'''
    permission_required = 'cmdb.play_session'
    model = models.Session
    template_name = 'guacamole/monitor.html'
    raise_exception = True

    # def get(self, request, pk):
    #     res = render_to_response('guacamole/monitor.html', locals())
    #     res['Content-Security-Policy'] = "frame-ancestors http://192.168.80.240:88/ 'self'"
    #     return res
