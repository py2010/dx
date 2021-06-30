# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from . import models

from readonly.addreadonly import ReadOnlyAdmin, ReadOnlyEditAdmin, MyAdmin as MyAdmin


@admin.register(models.DockerHost)
class DockerHostAdmin(MyAdmin):
    list_display = ('name', 'ip', 'port', 'tls', )
    search_fields = ('ip', 'name')


@admin.register(models.DockerYmlGroup)
class DockerYmlGroupAdmin(MyAdmin):
    list_display = ('name', 'path', 'desc')


@admin.register(models.DockerYml)
class DockerYmlAdmin(MyAdmin):
    list_display = ('name', 'group', 'file')
    search_fields = ('name', )
    list_filter = ('group',)


@admin.register(models.DockerCompose)
class DockerComposeAdmin(MyAdmin):
    list_display = ('name', 'dockerhost', 'yml', 'scale', )
    search_fields = ('name', 'yml')
    list_filter = ('dockerhost',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(self.__class__, self).get_readonly_fields(request, obj=None))
        readonly_fields.append('dockerhost')
        readonly_fields.append('yml')
        return readonly_fields
