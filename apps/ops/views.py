# coding=utf-8

from django.http import JsonResponse

from django.views.generic import View, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy

from generic.views import MyDeleteView
from . import models, forms


class User(LoginRequiredMixin, PermissionRequiredMixin):
    '''网站登录用户'''
    model = models.UserProfile
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.
    permission_denied_message = '无操作权限'


class UserList(User, ListView):
    permission_required = 'ops.view_user'


class UserForm(User):
    template_name = "generic/_form.html"
    form_class = forms.UserProfileForm
    # fields = '__all__'
    success_url = reverse_lazy('ops:userprofile_list')

    def form_valid(self, form):
        # 设置用户密码
        pwd = form.cleaned_data.get('pwd', '')
        if pwd:
            form.instance.set_password(pwd)
        return super().form_valid(form)


class UserAdd(UserForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'ops:add_userprofile'

    def get_form(self, form_class=None):
        # 创建新用户时, 密码为必填项
        form_class = super().get_form(form_class)
        form_class.fields['pwd'].required = True
        return form_class


class UserUpdate(UserForm, UpdateView):
    permission_required = 'ops.change_userprofile'

    # def __init__(self, *args, **kwargs):
    #     import ipdb; ipdb.set_trace()


# class UserDelete(User, DeleteView):
class UserDelete(User, MyDeleteView):
    permission_required = 'ops.delete_userprofile'


class GroupView(LoginRequiredMixin, PermissionRequiredMixin):
    '''用户组/角色'''
    model = models.Group
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.


class GroupList(GroupView, ListView):
    template_name = 'ops/group_list.html'
    permission_required = 'ops.view_group'


class GroupForm(GroupView):
    template_name = "generic/_form.html"
    fields = '__all__'
    # form_class = forms.GroupForm
    success_url = reverse_lazy('ops:group_list')


class GroupAdd(GroupForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'ops:add_group'


class GroupUpdate(GroupForm, UpdateView):
    permission_required = 'ops.change_group'


class GroupDelete(GroupView, MyDeleteView):
    # template_name = "ops/group_delete.html"
    permission_required = 'ops.delete_group'

