# coding=utf-8

import django
from django.db.models.signals import post_migrate
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

# Django加只读权限，将当前文件management放到任何一个app目录中，执行Python manage.py migrate时就会添加


def add_view_permissions(sender, **kwargs):
    """
    This syncdb hooks takes care of adding a view permission too all our
    content types.
    """
    # for each of our content types
    for content_type in ContentType.objects.all():
        # build our permission slug
        codename = "view_%s" % content_type.model
        # print(codename)
        # if it doesn't exist..
        if not Permission.objects.filter(content_type=content_type, codename=codename):
            # add it
            Permission.objects.create(content_type=content_type,
                                      codename=codename,
                                      name="Can view %s" % content_type.name)
            print("Added view permission for %s" % content_type.name)

# check for all our view permissions after a syncdb


if django.__version__ < '2.0':
    # django 1.* 增加只读权限数据
    # django 2.* 已增加了 只读权限, 所以无需再设置
    post_migrate.connect(add_view_permissions)

