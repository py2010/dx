"""dx URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.urls import path, re_path, include
from django.urls import re_path, path, include
from django.conf.urls import url
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.views.static import serve
from django.conf import settings

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import index, login, logout, password_change

from allapp import URLS_APPS

import logging
logger = logging.getLogger()


urlpatterns = [
    # re_path('admin/', admin.site.urls),
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/img/favicon.ico', permanent=True), ),

    re_path(r'^admin/login', RedirectView.as_view(pattern_name="login"), ),  # 增加了otp验证
    re_path(r'^admin/logout', RedirectView.as_view(pattern_name="logout"), ),  # 增加了token处理
    re_path(r'^admin/password_change', RedirectView.as_view(pattern_name="password_change"), ),  # 增加了密码过期验证
    re_path(r'^admin/', admin.site.urls, name="admin"),
    re_path(r'^login', login, name="login"),
    re_path(r'^password_change', password_change, name="password_change"),
    # re_path(r'^otp', otp, name="otp"),
    re_path(r'^logout', logout, name="logout"),

    re_path(r'^$', index),

    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, }, name="media"),


    # re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, }),
    # re_path(r'^stati2/(?P<path>.*)$', serv2, {}),

]

urlpatterns += staticfiles_urlpatterns()


for app, app_urls in URLS_APPS.items():
    # 开始自动装载各app.urls

    app_urlresolver = getattr(app_urls, 'urlpatterns', [])

    app_urlpattern = url(f'{app}/', (app_urlresolver, app, app))

    urlpatterns.append(app_urlpattern)

# print(urlpatterns)
# import ipdb;ipdb.set_trace()

