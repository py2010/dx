
import re
from importlib import import_module
from django.conf import settings
import logging

logger = logging.getLogger()

# import ipdb; ipdb.set_trace()

URLS_APPS = {}  # 用于自动路由ws/urls、前端左边栏，使django “app”与“project”解耦合
for app in settings.INSTALLED_APPS:
    # 按settings配置app的先后顺序，生成app:urls字典

    try:
        app_model = import_module(f'apps.{app}')  # 尝试import apps.xxx模块
    except Exception:
        continue
    # print(app, 555555)
    res = re.match(r'(?P<app_name>\w+)($|\.apps\.(?P<app_name2>\w+)Config)', app)
    if res:
        # cmdb 或 cmdb.apps.CmdbConfig，{'app_name': 'cmdb', 'app_name2': 'Cmdb'}
        app_name = res.groupdict()['app_name']
        try:
            app_urls = import_module(f'{app_name}.urls')
        except Exception as e:
            if getattr(e, 'name', None) != f'{app}.urls':
                logger.error(e, exc_info=True)
            continue
        URLS_APPS[app_name] = app_urls

# logger.info(URLS_APPS)

