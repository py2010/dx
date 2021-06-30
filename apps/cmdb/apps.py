# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig


class CmdbConfig(AppConfig):
    name = 'cmdb'
    verbose_name = '资产管理'

    # def ready(self):
    #     # signals are imported, so that they are defined and can be used
    #     import cmdb.signals
