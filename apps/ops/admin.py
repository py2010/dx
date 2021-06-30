# coding=utf-8

from __future__ import unicode_literals

from readonly.addreadonly import admin, MyAdmin

from . import models


@admin.register(models.UserProfile)
class UserAdmin(MyAdmin):
    list_display = ('username', 'name', 'email', 'weixin', 'phone')
    search_fields = ('username', 'name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

