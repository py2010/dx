# -*- coding: utf-8 -*-

from django.core.cache import cache

from cmdb.models import HostGroup, Host, HostUser, Session, User
from .interactive import savelog

'''
不调整表, 所以堡垒机app仅数据库表依赖cmdb, 从cmdb取资产数据.
'''
