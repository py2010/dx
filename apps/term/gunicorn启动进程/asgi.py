#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dx.settings")
# import ipdb; ipdb.set_trace()
django.setup()


def get_default_application():
    """
    用于gunicorn启动堡垒机多进程
    """
    from apps.term.sshd import SSHServer
    return SSHServer


application = get_default_application()


if __name__ == '__main__':
    # 需在项目根目录
    application(workers=2)
