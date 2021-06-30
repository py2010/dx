# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
# from django.forms import widgets

from . import models, forms

from readonly.addreadonly import ReadOnlyAdmin, ReadOnlyEditAdmin, MyAdmin as MyAdmin
import suit
# 表单编辑界面input等默认宽度为col-lg-7，有些窄，改为col-lg-9
suit.apps.DjangoSuitConfig.form_size['default'] = suit.apps.SUIT_FORM_SIZE_XXX_LARGE


@admin.register(models.HostGroup)
class HostGroupAdmin(MyAdmin):

    list_display = ('name', 'ip', 'desc')


# class Host_User_Inline(admin.TabularInline):
#     model = models.Host_User


@admin.register(models.Host)
class HostAdmin(MyAdmin):
    # inlines = [
    #     Host_User_Inline,
    # ]
    # form = forms.HostForm
    list_display = ('name', 'hostname', 'ip', 'group', 'changetime')
    search_fields = ('name', 'hostname', 'ip')

    list_filter = ('group', )
    # filter_horizontal = ('usergroup', 'host_user')
    fieldsets = [
        ('基础信息', {'fields': ['name', 'hostname', 'ip', 'other_ip', 'protocols', 'group']}),
        ('软硬件信息', {'fields': ['os', 'kernel', 'cpu_model', 'cpu_num', 'memory', 'disk', 'vendor', 'sn'], }),
        ('业务信息', {'fields': ['status', 'buydate', 'position', 'sernumb', 'sercode', ], 'classes': ['collapse'], }),
        ('其它信息', {'fields': ['createtime', 'text', ], }),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(self.__class__, self).get_readonly_fields(request, obj))
        # print(readonly_fields,33333333333)

        readonly_fields.append('createtime')
        # readonly_fields.append('agenttime')
        # print(readonly_fields)
        return readonly_fields


@admin.register(models.HostUser)
class HostUserAdmin(MyAdmin):
    form = forms.HostUserForm
    list_display = ('name', 'username', 'protocol', 'changetime', 'text')
    search_fields = ('name', 'username')


@admin.register(models.Session)
class SessionAdmin(ReadOnlyAdmin):
    list_display = ('host', 'http_user', 'log', 'start_time', 'end_time', )
    search_fields = ('host', 'user')
    actions = None


@admin.register(models.Perm)
class PermAdmin(MyAdmin):
    list_display = ('name', 'enable', 'changetime')
    search_fields = ('name', 'user')

