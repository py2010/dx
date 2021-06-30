# coding=utf-8

from django.contrib import admin

from django.contrib.auth.models import Permission

# from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

"""
不修改官方代码，在Django原有三种权限(写删加)基础上增加只读权限，
首先settings中添加本项目APP，然后需执行Python manage.py migrate，
会执行management.py中的函数在Django权限表`auth_permission`中增加浏览的权限信息;
然后APP中的admin.py中需要增加浏览权限的模型admin继承MyAdmin或MyAdmin2类即可。

Django: 1.11.6
Author: xyf
Date: 2017.11.21
"""


class MyAdmin(admin.ModelAdmin):
    # 只读权限时，可查看《修改历史》等额外权限

    def __init__(self, *args, **kwargs):
        # 设置verbose_name_plural为verbose_name
        super(MyAdmin, self).__init__(*args, **kwargs)
        self.opts.verbose_name_plural = self.opts.verbose_name

    def read_only(self, request):
        opts = self.opts
        has_change_permission = request.user.is_superuser or request.user.has_perm("%s.change_%s" % (opts.app_label, opts.model_name))
        has_view_permission = self.has_view_permission(request, None)
        # print('change:',has_change_permission, 'read',has_view_permission)
        if has_change_permission:
            readonly = 0
        elif has_view_permission:
            readonly = 1
        else:
            # 无读写权限，403
            readonly = -1
        return readonly

    def has_view_permission(self, request, obj=None):
        opts = self.opts
        return request.user.has_perm("%s.view_%s" % (opts.app_label, opts.model_name))

    def has_change_permission(self, request, obj=None):
        perm = False
        if self.read_only(request) != -1:
            # 有只读权限时，也给写权限
            perm = True

        return perm

    def changeform_view(self, request, object_id=None, form_url='', extra_context={}):
        if self.read_only(request) == 1:
            extra_context = {
                # 只读时，不提供按钮 保存/保存并继续
                'show_save': 0,
                'show_save_and_continue': 0,
            }

        return admin.ModelAdmin.changeform_view(self, request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        # print(self.has_change_permission(request, None),9999999999999)
        if self.read_only(request) == 1:
            # 只读权限时，设置所有字段只读
            # import ipdb;ipdb.set_trace()
            return [f.name for f in self.model._meta._get_fields(reverse=False) if not f.primary_key]  # _meta.fields中不含多对多字段
        return list(self.readonly_fields)


# 重写admin首页context增加admin_url (每个app项对应后台网址)，
# admin.site._build_app_dict只根据change权限来判断是否生成admin_url，导致只读浏览时首页出错
# Django_Admin_Base_URL = 'admin'
# def index_decorator(func):
#     def inner(*args, **kwargs):
#         templateresponse = func(*args, **kwargs)
#         for app in templateresponse.context_data['available_apps']:
# import ipdb;ipdb.set_trace()
#             app_label = app['app_label']
#             for model in app['models']:
#                 viewname = u'admin:%s_%s_changelist' % (app_label, model['object_name'])
#                 model_name = model['object_name']
#                 model['admin_url'] = '/%s/%s/%s/' % (Django_Admin_Base_URL, app_label.lower(), model_name.lower())
#                 print(model,111111111111)
#         return templateresponse
#     return inner

# admin.site.index = index_decorator(admin.site.index) #重写首页templateresponse


class MyAdmin2(MyAdmin):
    # 只读时不能查看历史等额外权限

    def has_change_permission(self, request, obj=None):
        readonly = getattr(self, '%s_readonly' % request.user.username, self.read_only(request))
        # print(readonly,3333333)
        if readonly:
            # 只读和无读写权限时，本来都将403
            # 只读权限打开页面时，self.user_readonly将临时修改，给予权限获取页面response后再复原
            return False
        else:
            return True

    def get_model_perms(self, request):
        # 在原有三种权限 写删加 基础上增加浏览权限
        perms = admin.ModelAdmin.get_model_perms(self, request)
        perms['view'] = self.has_view_permission(request)
        change_perm = perms['change']
        if not change_perm:
            perms['change'] = perms['view']
            # 简单处理，只读时直接让权限列表中的change有权限，因为重写admin.site比较麻烦（url、HTML链接等很多地方需处理）
        # print(perms,'get_model_perms')
        return perms

    def changelist_view(self, request, extra_context=None):
        readonly = getattr(self, '%s_readonly' % request.user.username, self.read_only(request))
        if readonly == 1:
            # 只读时，由于Django浏览表行数据需有change权限，所以临时给予写权限，使页面可以打开而不是403
            setattr(self, '%s_readonly' % request.user.username, 0)
        response = admin.ModelAdmin.changelist_view(self, request, extra_context)
        setattr(self, '%s_readonly' % request.user.username, readonly)  # 将临时改写的权限(若有)还原回去
        return response

    def changeform_view(self, request, object_id=None, form_url='', extra_context={}):
        # return super(self.__class__, self).changeform_view(request, object_id, form_url, extra_context)

        readonly = self.read_only(request)
        if readonly == 1:
            # 由于Django浏览表行数据时，需有change权限，所以临时给予写权限，使页面可以打开而不是403
            setattr(self, '%s_readonly' % request.user.username, 0)
            extra_context = {
                # 只读时，不提供保存/保存并继续按钮
                'show_save': 0,
                'show_save_and_continue': 0,
            }

        response = admin.ModelAdmin.changeform_view(self, request, object_id, form_url, extra_context)

        setattr(self, '%s_readonly' % request.user.username, readonly)  # 将临时改写的权限(若有)还原回去
        # print(getattr(self, '%s_readonly'%request.user.username), self.has_change_permission(request, None),77777777777)

        return response


# read_only_users = [
# 只读用户列表，如果用户被设置为超级管理员，则直接有全部权限
#     'readonly',
# ]


# class ADDReadOnlyUser(admin.ModelAdmin):
# 增加只读用户
#     def get_readonly_fields(self,request,obj=None):
#         if not request.user.is_superuser and request.user.username in view_users:
#             return [f.name for f in self.model._meta.fields]
#         return self.readonly_fields


class ReadOnlyAdmin(admin.ModelAdmin):
    # 完全只读，不能添加

    def __init__(self, *args, **kwargs):
        # 设置verbose_name为verbose_name_plural
        super(ReadOnlyAdmin, self).__init__(*args, **kwargs)
        self.opts.verbose_name_plural = self.opts.verbose_name

    def has_add_permission(self, request):
        # 禁止新增和show_save_and_add_another按钮
        return 0

    def has_change_permission(self, request, obj=None):
        opts = self.opts
        return request.user.has_perm("%s.view_%s" % (opts.app_label, opts.model_name)) \
            or request.user.has_perm("%s.change_%s" % (opts.app_label, opts.model_name))

    def changeform_view(self, request, object_id=None, form_url='', extra_context={}, show_save=0, show_save_and_continue=0):
        extra_context = {
            'show_save': show_save,
            'show_save_and_continue': show_save_and_continue,
            # 'show_save_and_add_another': 0, #提前定义变量后，Django会在render_change_form中重设
        }
        return admin.ModelAdmin.changeform_view(self, request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        fs = [f.name for f in self.model._meta._get_fields(reverse=False) if not f.primary_key]
        return fs


class ReadOnlyEditAdmin(ReadOnlyAdmin):
    # 编辑只读，可添加

    def has_add_permission(self, request):
        return request.user.has_perm("%s.add_%s" % (self.opts.app_label, self.opts.model_name))

    def changeform_view(self, request, object_id=None, form_url='', extra_context={}):
        return super(ReadOnlyEditAdmin, self).changeform_view(request, object_id, form_url,
                                                              extra_context, show_save=not object_id,
                                                              show_save_and_continue=not object_id)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            # 编辑时只读
            return super(ReadOnlyEditAdmin, self).get_readonly_fields(request, obj)
        else:
            # 添加时正常
            return admin.ModelAdmin.get_readonly_fields(self, request, obj=None)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        re = admin.ModelAdmin.render_change_form(self, request, context, add, change, form_url, obj)
        if obj:
            re.context_data['has_add_permission'] = False  # 编辑(只读)时，不显示“保存并增加另一个”
        return re
        # import ipdb;ipdb.set_trace()


'''
django-admin增加显示权限表
'''


def get_model_label(obj):
    # import ipdb;ipdb.set_trace()
    model_class = obj.model_class()
    if model_class:
        return '%s / %s' % (model_class._meta.app_config.verbose_name, str(model_class._meta.verbose_name))
    else:
        # 对应模型已删除
        return ''


ContentType.__str__ = get_model_label
ContentType._meta.ordering = ['app_label', 'model']
# ContentType._meta.default_manager.get_queryset

# import ipdb;ipdb.set_trace()


@admin .register(ContentType)
class ContentTypeAdmin (admin .ModelAdmin):
    list_display = ('label', 'app_label', 'model')
    search_fields = ('app_label', 'model')

    def label(self, obj):
        # 增加虚拟字段, 显示app/model对应中文标识
        return get_model_label(obj)

    label.short_description = '模型名'


@admin .register(Permission)
class PermissionAdmin (admin .ModelAdmin):
    list_filter = ('content_type',)
    list_display = ('name', 'content_type', 'codename')
    search_fields = ('name', 'codename')


# @admin .register(LogEntry)
# class LogEntryAdmin (admin .ModelAdmin):
#     list_display = ('content_type', 'action_flag', 'user', 'action_time')
#     list_filter = ('user', 'content_type', 'action_flag', 'action_time')
