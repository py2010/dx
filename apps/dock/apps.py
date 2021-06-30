from django.apps import AppConfig


class DockConfig(AppConfig):
    name = 'dock'  # 为防止与python本身中的docker模块import重名, 取名dock
    verbose_name = '容器管理'
