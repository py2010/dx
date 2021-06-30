# coding=utf-8
import json
import copy

from django.http import HttpResponse, Http404
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from .exceptions import ElfinderErrorMessages
from .connector import ElfinderConnector
from . import conf
# from django.shortcuts import render_to_response
# from django.shortcuts import get_object_or_404
# from django.core.cache import cache

import re
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin

from .sftpstoragedriver.sftpstorage import SFTPStorage
from django.http import StreamingHttpResponse
# import time

'''网页sftp 视图程序'''

# views.ElfinderConnectorView  ==> connector.ElfinderConnector ==> utils.volumes.instantiate_driver()
# ==> volumes.storage.ElfinderVolumeStorage.mount() ==> sftpstoragedriver.sftpstorage.SFTPStorage


class ElfinderConnectorView(PermissionRequiredMixin, LoginRequiredMixin, View):
    """
    Default elfinder backend view
    streamhttpresponse
    """
    permission_required = 'cmdb.sftp_host'
    raise_exception = True
    elfinder = None

    def render_to_response(self, context, **kwargs):
        """
        It returns a json-encoded response, unless it was otherwise requested
        by the command operation
        """
        # import ipdb;import ipdb; ipdb.set_trace()
        # print(context, 8989898)
        kwargs = {}
        additional_headers = {}
        # create response headers
        if 'header' in context:
            for key in context['header']:
                if key == 'Content-Type':
                    kwargs['content_type'] = context['header'][key]
                elif key.lower() == 'status':
                    kwargs['status'] = context['header'][key]
                else:
                    additional_headers[key] = context['header'][key]
            del context['header']

        # return json if not header
        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

        if 'pointer' in context:  # return file
            if 'text/plain' not in kwargs.get('content_type') and 'storage' in context['volume']._options and isinstance(context['volume']._options['storage'], SFTPStorage):
                # stream sftp file download
                def file_iterator(elfinder, file_name, chunk_size=32768):
                    while True:
                        c = file_name.read(chunk_size)
                        if c:
                            yield c
                        else:
                            context['volume'].close(context['pointer'], context['info']['hash'])
                            # fix sftp open transfer not close session bug
                            if 'storage' in context['volume']._options and isinstance(context['volume']._options['storage'], SFTPStorage):
                                context['volume']._options['storage'].sftp.close()
                            break
                    '''
                    后端transport_ser连接复用时, 可对应多个chan_ser,
                    elfinder不支持websocket, HTTP每次请求后需调用关闭多余的chan_ser
                    只保留一个 "elfinder_sftp" 用于sftp连接缓存.
                    '''
                    elfinder.close()
                the_file_name = additional_headers["Content-Location"]
                response = StreamingHttpResponse(file_iterator(self.elfinder, context['pointer']))  # 读取流文件
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="{0}"'.format(the_file_name)
                return response
            else:
                context['pointer'].seek(0)
                kwargs['content'] = context['pointer'].read()  # 读取文件
                context['volume'].close(context['pointer'], context['info']['hash'])
        elif 'raw' in context and context['raw'] and 'error' in context and context['error']:  # raw error, return only the error list
            kwargs['content'] = context['error']
        elif kwargs['content_type'] == 'application/json':  # return json
            kwargs['content'] = json.dumps(context)
        else:  # return context as is!
            kwargs['content'] = context

        response = HttpResponse(**kwargs)
        for key, value in additional_headers.items():
            response[key] = value

        '''
        后端transport_ser连接复用时, 可对应多个chan_ser,
        elfinder不支持websocket, HTTP每次请求后需调用关闭多余的chan_ser
        只保留一个 "elfinder_sftp" 用于sftp连接缓存.
        '''
        self.elfinder.close()

        return response

    @staticmethod
    def handler_chunk(src, args):
        """
        handler chunk parameter
        """
        if "chunk" in src:
            args['chunk_name'] = re.findall(r'(.*?).\d+_\d+.part$', src['chunk'])[0]
            first_chunk_flag = re.findall(r'.*?.(\d+)_\d+.part$', src['chunk'])[0]
            if int(first_chunk_flag) == 0:
                args['is_first_chunk'] = True
            else:
                args['is_first_chunk'] = False
        else:
            args['chunk_name'] = False
            args['is_first_chunk'] = False

    def output(self, cmd, src):
        """
        Collect command arguments, operate and return self.render_to_response()
        """
        args = {}
        cmd_args = self.elfinder.commandArgsList(cmd)
        for name in cmd_args:
            if name == 'request':
                args['request'] = self.request
            elif name == 'FILES':
                args['FILES'] = self.request.FILES
            elif name == 'targets':
                args[name] = src.getlist('targets[]')
            else:
                arg = name
                if name.endswith('_'):
                    name = name[:-1]
                if name in src:
                    try:
                        args[arg] = src.get(name).strip()
                    except Exception:
                        args[arg] = src.get(name)
        if cmd == 'mkdir':
            args['name'] = src.getlist('dirs[]') if 'dirs[]' in src else src.getlist('name')
        elif cmd == "upload":
            if 'upload_path[]' in src:
                dir_path = src.getlist('upload_path[]')
                if len(list(set(dir_path))) == 1 and dir_path[0] == args['target']:
                    args['upload_path'] = False
                    self.handler_chunk(src, args)
                else:
                    args['upload_path'] = dir_path
                    self.handler_chunk(src, args)
            else:
                args['upload_path'] = False
                self.handler_chunk(src, args)
        elif cmd == "size":
            args['targets'] = src.getlist('targets[0]')
        args['debug'] = src['debug'] if 'debug' in src else False
        # print(args, 99999999)
        res = self.elfinder.execute(cmd, **args)
        # res = elfinders.sftp(self.elfinder, cmd, args)

        return self.render_to_response(res)

    def get_command(self, src):
        """
        Get requested command
        """
        try:
            return src['cmd']
        except KeyError:
            return 'open'

    def get_optionset(self, **kwargs):
        # print(kwargs, 99999999999999)
        set_ = conf.ELFINDER_CONNECTOR_OPTION_SETS[kwargs['optionset']]
        if kwargs['host_id'] != 'default':
            for root in set_['roots']:
                root['startPath'] = kwargs['host_id']
        temp_dict = copy.deepcopy(set_)
        u_id_dict = {'debug': temp_dict['debug'], 'roots': temp_dict['roots']}
        return u_id_dict

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        if not kwargs['optionset'] in conf.ELFINDER_CONNECTOR_OPTION_SETS:
            raise Http404
        # print(kwargs, 7777777888888888)
        return super(ElfinderConnectorView, self).dispatch(*args, **kwargs)

    def get_elfinder(self, request, *args, **kwargs):
        '''
        为防止网络IO重复开销, 改由后端SSH(堡垒机.ssh.ProxyClient)统一负责重用连接,
        HTTP每次请求都会生成ElfinderConnector实例, 无需再额外使用线程进行缓存重用.
        '''
        optinon_sets = self.get_optionset(**kwargs)
        if kwargs['optionset'] == 'sftp':

            optinon_sets['roots'][0]['storageKwArgs'] = {
                'hostid': kwargs['host_id'],
                'userid': kwargs['u_id'],
                'root_path': conf.SFTP_BASE_DIR,  # sftp根目录映射到此路径
                'interactive': False,
                'key_label': 'key_label'
            }
            # import ipdb;ipdb.set_trace()
            optinon_sets['roots'][0]['ftp_readonly'] = request.user.profile.ftp_readonly
        self.elfinder = ElfinderConnector(optinon_sets)

    def get(self, request, *args, **kwargs):
        """
        used in get method calls
        """
        self.get_elfinder(request, *args, **kwargs)
        return self.output(self.get_command(request.GET), request.GET)

    def post(self, request, *args, **kwargs):
        """
        called in post method calls.
        It only allows for the 'upload' command
        """
        self.get_elfinder(request, *args, **kwargs)
        cmd = self.get_command(request.POST)

        if cmd not in ['upload']:
            self.render_to_response({'error': self.elfinder.error(ElfinderErrorMessages.ERROR_UPLOAD, ElfinderErrorMessages.ERROR_UPLOAD_TOTAL_SIZE)})
        return self.output(cmd, request.POST)

