# coding=utf-8
# from importlib import import_module
from allapp import URLS_APPS, settings
import os
from collections import OrderedDict

from django.urls import reverse
from django.core.cache import cache
import logging
import ipdb
from django import template
register = template.Library()
logger = logging.getLogger()

# 菜单配置
MENUS = []  # 自定义增加
APP_MENU_HTML_TIMEOUT = 600  # 增删html菜单文件时,缓存超时时间, 单位秒


@register.filter
def debug(mm, nn=None):
    # 自定义过滤器 - 模板调试 {{ mm|debug:nn }}
    print({'mm': mm, 'nn': nn})
    ipdb.set_trace()
    return


@register.simple_tag
def add(*args):
    # 自定义标签 -- 字段串拼接 {% add a b c %} (内置过滤器add一次只能拼接二个变量, 语法长不直观)
    return ''.join([str(i) for i in args])


@register.simple_tag(takes_context=True)
def load_menus(context, *args, **kwargs):
    # 用于生成左边栏菜单
    # import ipdb; ipdb.set_trace()

    appmenus = cache.get('app_menus', OrderedDict())  # 含有左边栏的app/_menu.html列表
    # redis支持OrderedDict存取, 无需转换

    if not appmenus:

        # 开始生成左边栏菜单
        for app in URLS_APPS:
            html_name = f'{app}/_menu.html'
            html_file = os.path.join(settings.BASE_DIR, 'apps', app, 'templates', html_name)
            logger.info(html_file)
            if os.path.isfile(html_file):
                # app含有左边栏菜单
                # 开始检查app是一级菜单还是二级菜单
                menu_level = 1
                menu_name = app  # 一级菜单名
                if app in MENUS:
                    menu_level = 2
                    menu_name = MENUS[app]  # 一级菜单名

                key = (menu_level, menu_name)
                if key in appmenus:
                    # 通常为2级菜单
                    appmenus[key].append(html_name)
                else:
                    # 1级菜单
                    appmenus[key] = [html_name, ]
                # appmenus.append(html_name)
        cache.set('app_menus', appmenus, APP_MENU_HTML_TIMEOUT)

    # import ipdb;ipdb.set_trace()
    return appmenus


@register.simple_tag(takes_context=True)
def show_menu_url(context, viewname, *perms):
    '''
    根据用户权限返回某项菜单的网址, 用于模板判断是否在左边栏显示菜单
    {% show_menu_url '网址视图' '权限码1' 'and' '权限码2' as url_xx项 %}
    多个权限未提供逻辑与或时, 默认为or, 也就是'or' 可以省略.
    '''
    user = context['request'].user
    if user.is_superuser:
        show_menu = True
    else:
        show_menu = False
        for n, perm in enumerate(perms):
            if perm not in ('and', 'or'):
                logic = perms[n - 1]
                if logic == 'and':
                    show_menu &= user.has_perm(perm)
                else:
                    show_menu |= user.has_perm(perm)

    try:
        return reverse(viewname) if show_menu else ''
    except Exception:
        return ''

