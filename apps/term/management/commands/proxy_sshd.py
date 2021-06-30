# coding=utf-8

from django.core.management.base import BaseCommand

from ... import sshd

# import sys
# # /usr/lib64/python2.7/site-packages/sitecustomize.py
# reload(sys)
# sys.setdefaultencoding('UTF-8')


class Command(BaseCommand):
    '''
    使用django command运行堡垒机
    '''

    help = 'SSH堡垒机服务端，使网站支持Xshell等客户端软件终端'

    def add_arguments(self, parser):
        parser.add_argument('workers', nargs='?', type=int,
                            # default='3',
                            help='堡垒机启动进程数'
                            )

    def handle(self, *args, **options):
        self.workers = options.get('workers')
        try:
            sshd.SSHServer(workers=self.workers)
        except KeyboardInterrupt:
            ...
            # from ... import ssh
            # import ipdb; ipdb.set_trace()

