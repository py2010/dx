
from gunicorn.workers.base import Worker
# import time


class MyWorker(Worker):
    """
    使用gunicorn的功能来启动堡垒机多进程/支持参数
    gunicorn -k MyWorker asgi:application
    """

    def run(self):
        # print('self.timeout', self.timeout)
        self.wsgi(self.sockets, heartbeat=self.notify, timeout=self.timeout)
        # while self.alive:
        #     self.notify()


'''
python3 -u /usr/local/bin/gunicorn --workers=2 -b 0.0.0.0:22222 -k apps.term.gunicorn.workers.MyWorker apps.term.gunicorn.asgi:application

'''

