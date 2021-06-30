# -*- coding: utf-8 -*-

from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
# from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from generic.views import MyDeleteView
from . import models, forms

# User = get_user_model()
# Group = User.groups.rel.model


class HostUser(LoginRequiredMixin, PermissionRequiredMixin):
    '''主机资产登录用户'''
    model = models.HostUser
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.
    permission_denied_message = '无操作权限'


class HostUserList(HostUser, ListView):
    # template_name = 'generic/_list.html'
    permission_required = 'cmdb.view_hostuser'


class HostUserForm(HostUser):
    template_name = "generic/_form.html"
    form_class = forms.HostUserForm
    # fields = '__all__'
    success_url = reverse_lazy('cmdb:hostuser_list')


class HostUserAdd(HostUserForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'cmdb:add_hostuser'


class HostUserUpdate(HostUserForm, UpdateView):
    permission_required = 'cmdb.change_hostuser'


# class HostUserDelete(HostUser, DeleteView):
class HostUserDelete(HostUser, MyDeleteView):
    # template_name = "cmdb/hostuser_delete.html"
    permission_required = 'cmdb.delete_hostuser'


class Perm(LoginRequiredMixin, PermissionRequiredMixin):
    '''主机资产授权, 数据库行级别权限配置'''
    model = models.Perm
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.


class PermDelete(Perm, MyDeleteView):
    permission_required = 'cmdb.delete_perm'


class PermList(Perm, ListView):
    # template_name = 'generic/_list.html'
    permission_required = 'cmdb.view_perm'
    # queryset查询时, 带入多对多字段
    queryset = models.Perm.objects.prefetch_related('web_user', 'web_usergroup', 'hostgroup', 'host', 'host_user')


class PermForm(Perm):
    template_name = "generic/_form.html"
    form_class = forms.PermForm
    # fields = '__all__'
    success_url = reverse_lazy('cmdb:perm_list')


class PermAdd(PermForm, CreateView):
    permission_required = 'cmdb:add_perm'


class PermUpdate(PermForm, UpdateView):
    permission_required = 'cmdb.change_perm'


