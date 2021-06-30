# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render_to_response, HttpResponse, get_object_or_404, Http404
from django.http import JsonResponse

from django.views.generic import View, TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model

from django.core.cache import cache
from django.urls import reverse_lazy

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

import random
import json

from term.conf import SSHD
from generic.views import MyDeleteView, MyListView
from . import models, forms

'''主机/终端视图'''
User = get_user_model()
# Group = User.groups.rel.model
channel_layer = get_channel_layer()


class HostGroupView(LoginRequiredMixin, PermissionRequiredMixin):
    '''机组'''
    model = models.HostGroup
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.


class HostGroupList(HostGroupView, ListView):
    # template_name = 'generic/_list.html'
    permission_required = 'cmdb.view_hostgroup'


class HostGroupForm(HostGroupView):
    template_name = "generic/_form.html"
    fields = '__all__'
    # form_class = forms.HostGroupForm
    success_url = reverse_lazy('cmdb:hostgroup_list')


class HostGroupAdd(HostGroupForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'cmdb:add_hostgroup'


class HostGroupUpdate(HostGroupForm, UpdateView):
    permission_required = 'cmdb.change_hostgroup'


class HostGroupDelete(HostGroupView, MyDeleteView):
    # template_name = "cmdb/hostgroup_delete.html"
    permission_required = 'cmdb.delete_hostgroup'


class HostView(LoginRequiredMixin, PermissionRequiredMixin):
    '''主机资产'''
    model = models.Host
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.
    permission_denied_message = '无操作权限'


class HostList(HostView, MyListView):
    template_name = 'cmdb/host_list.html'
    paginate_by = 2
    permission_required = 'cmdb.view_host'

    # filter_orm = True  # 是否开启ORM过滤功能
    filter_fields = [
        # 是否使用模糊搜索多字段功能
        'ip',
        'hostname',
        'name',
    ]


class HostForm(HostView):
    template_name = "generic/_form.html"
    # fields = '__all__'
    form_class = forms.HostForm
    success_url = reverse_lazy('cmdb:host_list')


class HostAdd(HostForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'cmdb:add_host'


class HostUpdate(HostForm, UpdateView):
    permission_required = 'cmdb.change_host'


class HostDelete(HostView, MyDeleteView):
    # template_name = "cmdb/host_delete.html"
    permission_required = 'cmdb.delete_host'


# class Term(View):
class Term(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'cmdb.ssh_host'

    def get(self, request):
        # 主机列表页 -- 终端操作
        hostgroups = []
        hosts = models.Perm.get_host(request.user)  # 过滤筛择用户权限内的主机
        for hostgroup in models.HostGroup.objects.all():
            hostgroup.user_hosts = [h for h in hosts if h.group == hostgroup]
            if hostgroup.user_hosts:
                hostgroups.append(hostgroup)

        windows = 'Windows' in request.META['HTTP_USER_AGENT']
        return render_to_response('cmdb/term.html', locals())

    def post(self, request, *args, **kwargs):
        # 连接主机时, 查询主机的用户清单, 以供前端选择
        # application/json
        # time.sleep(3)
        data = json.loads(request.body)
        hostid = data.get('hostid')
        protocol = data.get('protocol', 'ssh')
        if not hostid:
            raise Http404
        host = get_object_or_404(models.Host, id=hostid)

        us = [{
            'id': u.id,
            'username': u.username,
            'changetime': u.changetime,
        } for u in host.get_hostuser(request.user, protocol=protocol)]
        return JsonResponse(us, safe=False)


# # 修改默认的合法schemes列表，用于主机终端，跳转调用外部程序，比如xshell
# HttpResponseRedirect.allowed_schemes.append(conf.CliSSH['scheme'])


class CliSSH(LoginRequiredMixin, PermissionRequiredMixin, View):
    # 软件终端，比如xshell，客户端需安装/设置支持从网页跳转到xshell
    permission_required = 'cmdb.ssh_host'

    @staticmethod
    def pwd():
        # 生成ssh临时密码
        s = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        pwd = ''
        while len(pwd) < 6:
            pwd = '%s%s' % (pwd, random.choice(s))
        return pwd

    def get(self, request, hostid):
        host = get_object_or_404(models.Host, id=hostid)
        user = request.user
        type = request.GET.get('type', 'ssh')
        uid = request.GET.get('uid')
        if not uid:
            raise Http404

        link = '{scheme}://{user}:{passwd}@{cmdb}:{port}'
        if type == 'sftp':
            # Xftp.exe" /nsurl sftp://网站用户:临时密码@堡垒机:端口/?TabName=SSH用户/SSH主机
            link = '%s/?TabName={username}/{host}' % link
        else:
            # Xshell.exe" ssh://网站用户:临时密码@堡垒机:端口 -newtab SSH用户/SSH主机
            if 'Windows' in request.META['HTTP_USER_AGENT']:
                link = '%s\\" \\"-newtab\\" \\"{username}/{host}' % link
            else:
                # Linux使用的Xshell不加引号
                link = '%s -newtab {username}/{host}' % link

        user, passwd = user.username, CliSSH.pwd()
        key = 'clissh_%s_%s' % (user, passwd)
        cache.set(key, (hostid, uid), timeout=SSHD['password_timeout'])  # 写入缓存

        cmdb = ':'.join(request.META['HTTP_HOST'].split(':')[:-1])  # ip6
        port = SSHD['port']
        scheme = SSHD['scheme'][type]
        host_username = models.HostUser.objects.get(id=uid).username
        return HttpResponse(link.format(
            scheme=scheme,  # 自定义的网页调用外部软件(xshell)协议
            cmdb=cmdb,  # xshell连接主机(cmdb堡垒机代理)
            port=port,
            user=user,  # xshell连接主机的用户(cmdb堡垒机代理)
            passwd=passwd,
            host=host.ip,  # xshell标签显示连接的主机(后端SSH实际主机)
            username=host_username  # xshell标签显示连接的用户(后端SSH实际用户)
        ))


class SshLogList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Session
    template_name = 'cmdb/sessionlist.html'
    permission_required = 'cmdb.play_session'
    raise_exception = True


class SshMonitor(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = models.Session
    template_name = 'cmdb/sshmonitor.html'
    permission_required = 'cmdb.play_session'
    raise_exception = True


class SessionKill(LoginRequiredMixin, PermissionRequiredMixin, View):
    '''
    强制结束在线终端
    操作进程为asgi网站进程, SSH终端进程可能是网站进程, 也可能是堡垒机进程.
    堡垒机进程通过redis proxy_session_id键 来判断终端是否中止

    guacamole由于是asgi进程, 忽略cache.delete, 利用group_send群发结束.
    '''
    permission_required = 'cmdb.kill_session'

    def post(self, request):
        logid = request.POST.get('logid')
        cache.delete('proxy_sshd_%s' % logid)

        # 发送信息给SSH监视者或guacamole
        async_to_sync(channel_layer.group_send)(
            str(logid),  # 群发频道使用表数据的主键
            {
                "type": "disconnect",
                "msg": f'终端连接被管理员 {request.user.username} 强制结束',
            }
        )
        return HttpResponse('')


class SessionDelete(HostView, MyDeleteView):
    model = models.Session
    permission_required = 'cmdb.delete_session'
