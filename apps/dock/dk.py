# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, render_to_response, redirect, HttpResponse, get_object_or_404, Http404
from django.core.exceptions import PermissionDenied

from .models import DockerHost, docker, DockerYml, DockerCompose, DockerImageFile

import json

from django.views.generic import ListView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from requests import ConnectionError
import time
import datetime
from .forms import ContainerAddForm, DockerYmlForm, DockerComposeForm, NetAddForm
import os
from .conf import DOCKER_LOGS_LINES


class DockerHostList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "dock/host_list.html"
    model = DockerHost
    permission_required = 'dock.view_dockerhost'


def get_dockerhost_id(request, pk):
    # 将用户选择的宿主机保存到session，后续不用再重复选择
    host_id = request.session.get('host_id', 0)
    # print(pk, host_id, 2222222)
    if pk and host_id != pk:
        # 页面选择修改了dockerhost，记入session
        request.session['host_id'] = pk
    dockerhost_id = pk or host_id
    return dockerhost_id


def docker_client(request, pk):
    # docker.DockerClient，docker模块版本2.7.0
    if not request.user.has_perm('dock.change_dockerhost'):
        raise PermissionDenied

    # dk = get_object_or_404(DockerHost, id=pk)
    try:
        dk = DockerHost.objects.get(id=pk)
    except Exception:
        request.session['host_id'] = 0
        raise Http404('宿主机不存在，已删除？')
    cli = dk.client
    if not isinstance(cli, docker.client.DockerClient):
        raise Http404(str(cli))
    return cli


def get_client_method(client, func, *args, **kwargs):
    # 用于异常处理， docker.DockerClient.xxx.xxx...
    p = client
    for m in func.split('.'):
        p = getattr(p, m)
    try:
        res = p(*args, **kwargs)
    except ConnectionError as e:
        res = '连接失败：%s' % str(e)
    except Exception as e:
        res = '出错：%s' % str(e)
    # print(res, 2323232)
    return res


def beijin(timestr):
    # 容器时间+8转换为北京时间
    try:
        t = time.strptime(timestr, '%Y-%m-%d %H:%M')
        d = datetime.datetime(*t[:5]) + datetime.timedelta(hours=8)
        return d.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # import ipdb; ipdb.set_trace()
        return timestr


def info(request, pk):
    # docker info
    # import ipdb; ipdb.set_trace()
    client = docker_client(request, pk)
    dk = client.dockerhost
    text = get_client_method(client, 'info')
    try:
        text = json.dumps(text)
    except Exception:
        pass
    return render(request, 'dock/info.html', locals())


def image(request, pk=0):
    # docker images 镜像管理
    dockerhosts = DockerHost.objects.all()
    dockerhost_id = get_dockerhost_id(request, pk)

    if dockerhost_id:
        client = docker_client(request, dockerhost_id)
        images = get_client_method(client, 'images.list')
        if type(images) != list:
            # docker宿主机连接失败或未知错误
            error = images
        else:
            imgs = []
            for image in images:
                img = {}
                if image.tags:
                    img['name'], img['ver'] = image.tags[0].split(':')
                    # print(image.tags[0].split(':'), 888888888)

                if 'name' not in img:
                    try:
                        img['name'] = image.attrs['RepoDigests'][0].split('@')[0]
                    except Exception:
                        pass

                img['time'] = beijin(image.attrs['Created'][:16].replace('T', ' '))
                img['size'] = image.attrs['Size']
                img['id'] = image.id
                imgs.append(img)
            # imgs.sort(cmp=None, key=lambda s: s['name'], reverse=False)
    return render(request, 'dock/image.html', locals())


def image_rm(request, pk):
    # 删除镜像
    imgid = request.GET.get('img')
    client = docker_client(request, pk)
    try:
        res = get_client_method(client, 'images.remove', imgid, force=True)
        if res:
            msg = {"error": str(res)}
        else:
            msg = {"remove": "ok", "status": True}
    except Exception as e:
        msg = {"error": str(e)}

    return HttpResponse(json.dumps(msg))


def image_do(request, pk):
    # 镜像信息、历史、保存
    imgid = request.GET.get('img')
    do = request.GET.get('do')
    client = docker_client(request, pk)
    try:
        img = get_client_method(client, 'images.get', imgid)
        # import ipdb; ipdb.set_trace()
        # print(img, 8888)
        if isinstance(img, docker.models.images.Image):
            msg = getattr(img, do)
            if do == 'history':
                msg = msg()
            elif do == 'save':
                # 相当于docker save命令
                # import ipdb; ipdb.set_trace()
                old_timeout, client.api.timeout = client.api.timeout, 300
                msg = DockerImageFile.save_obj(img)
                client.api.timeout = old_timeout
        else:
            msg = {"error": str(img)}
        # print(msg, 99999)
    except Exception as e:
        # raise
        msg = str(e)
    # import ipdb; ipdb.set_trace()
    if type(msg) in (list, dict):
        try:
            msg = json.dumps(msg)
        except Exception:
            msg = json.dumps({"error": str(msg)})
    return HttpResponse(msg)


def container(request, pk=0):
    # docker ps -a 容器管理
    dockerhosts = DockerHost.objects.all()
    dockerhost_id = get_dockerhost_id(request, pk)

    if dockerhost_id:
        client = docker_client(request, dockerhost_id)
        containers = get_client_method(client, 'containers.list', all=1)
        if type(containers) != list:
            # docker宿主机连接失败或未知错误
            error = containers
        else:
            cons = []
            for container in containers:
                netype = request.GET.get('net', '')  # 显示指定网络的容器
                if netype and netype not in container.attrs['NetworkSettings']['Networks']:
                    continue
                con = {}
                con['name'] = container.name
                # print(container.name, 777)
                try:
                    con['image'] = container.image.tags[0]  # .split(':')[0].split('/')[-1]
                except Exception:
                    con['image'] = ''

                con['ip'] = ''
                try:
                    ip = container.attrs['NetworkSettings']['IPAddress']
                    if not ip:
                        ips = set()
                        for net in container.attrs['NetworkSettings']['Networks']:
                            ips.add(container.attrs['NetworkSettings']['Networks'][net]['IPAddress'])
                        # print(ips, 33333333)
                        ip = ', '.join(ips)
                    con['ip'] = ip

                except Exception as e:
                    # import ipdb; ipdb.set_trace()
                    print(e, 898989)

                con['status'] = container.status
                con['time'] = beijin(container.attrs['Created'][:16].replace('T', ' '))
                # con['runtime'] = container.attrs['State']['StartedAt'][:16].replace('T', ' ')
                con['id'] = container.id
                cons.append(con)
            # cons.sort(cmp=None, key=lambda s: s['name'], reverse=False)
    return render(request, 'dock/container.html', locals())


def container_rm(request, pk):
    # 删除容器
    conids = request.GET.get('id').strip(',').split(',')
    client = docker_client(request, pk)
    msg = {"remove": "ok", "status": True}
    try:
        for conid in conids:
            container = get_client_method(client, 'containers.get', conid)
            if type(container) == str:
                msg = {"error": str(container)}
            else:
                print(container.remove(force=True))
    except Exception as e:
        msg = {"error": str(e)}

    return HttpResponse(json.dumps(msg))


def container_do(request, pk):
    # 容器信息、操作
    # import ipdb; ipdb.set_trace()
    conid = request.GET.get('id')
    do = request.GET.get('do')
    client = docker_client(request, pk)
    try:
        con = get_client_method(client, 'containers.get', conid)
        # print(con, 8888)
        if isinstance(con, docker.models.containers.Container):
            msg = getattr(con, do)
            if do == 'logs':
                msg = msg(tail=DOCKER_LOGS_LINES)  # 最后xx行, 默认为所有日志tail='all'
                if not msg:
                    msg = "No log."
            elif do != 'attrs':
                msg = msg()
                if not msg:
                    msg = {do: "ok."}
                # print(msg, 9999)
        else:
            msg = {"error": str(con)}
        # print(msg, 99999)
    except Exception as e:
        msg = str(e)
    # if do != 'logs':
    if type(msg) in (list, dict):
        try:
            msg = json.dumps(msg)
        except Exception:
            msg = json.dumps({"error": str(msg)})
    return HttpResponse(msg)


def container_add(request, pk):
    # 容器添加
    # 由于docker_client.containers.run未封装支持设置IP、挂载
    # 所以使用底层模块docker_client.api.create_container
    client = docker_client(request, pk)

    if request.method == 'POST':
        # print(request.POST, 7777777)
        form = ContainerAddForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name', None)
            image = form.cleaned_data.get('image', None)
            network = form.cleaned_data.get('network', None)
            ip = form.cleaned_data.get('ip', None)
            ports = form.cleaned_data.get('ports', '').replace('，', ',').replace('：', ':')
            volumes = form.cleaned_data.get('volumes', '').replace('，', ',').replace('：', ':')
            command = form.cleaned_data.get('command', None)
            start = form.cleaned_data.get('start')
            tty = form.cleaned_data.get('tty')
            stdin = form.cleaned_data.get('stdin')

            kwargs = {'name': name, 'image': image, 'command': command, 'detach': 1}

            host_config = {'NetworkMode': network}
            ps = [port.strip() for port in ports.split(',') if port.strip()]
            vs = [volume.strip() for volume in volumes.split(',') if volume.strip()]

            # 映射端口
            ports = []
            port_bindings = {}
            for p in ps:
                p = p.split(':')
                try:
                    port = int(p[-1])
                except Exception:
                    print('端口必须为数字')
                    continue
                host_ports = []
                if port not in ports:
                    ports.append(port)

                if len(p) in (2, 3):
                    host_port = tuple(p[:-1])
                    if len(host_port) == 1:
                        if '.' in host_port[0]:
                            # 只有监听地址，未设置监听端口，保持和容器端口一致
                            host_port = (p[0], p[-1])
                        else:
                            # 未设置监听地址，有监听端口
                            host_port = host_port[0]  # (80,) --> 80 == ('', 80) == ('0.0.0.0', 80)
                elif len(p) == 1:
                    # 未设置监听地址和监听端口
                    host_port = p[0]
                else:
                    # import ipdb; ipdb.set_trace()
                    print('映射端口，忽略未知输入或错误格式', p)
                    continue
                host_ports = port_bindings.get(port, [])
                host_ports.append(host_port)
                port_bindings.update({port: host_ports})

            host_config.update(client.api.create_host_config(port_bindings=port_bindings))
            kwargs['ports'] = ports

            # 设置挂载
            if vs:
                # print(vs, 888888)
                host_config.update({'Binds': vs})

            kwargs.update({'host_config': host_config})

            # 设置IP和网络
            ip_conf = {'IPAMConfig': {'IPv4Address': ip}} if ip else {}
            networking_config = {
                'EndpointsConfig': {
                    network: ip_conf
                }
            }

            kwargs.update({'networking_config': networking_config})
            if tty == 'on':
                kwargs.update({'tty': True})
            if stdin == 'on':
                kwargs.update({'stdin_open': True})

            print(host_config, 222333)
            print(kwargs, 3444444)
            try:
                res = client.api.create_container(**kwargs)

                if start == 'on':
                    # 启动容器
                    container = client.containers.get(res['Id'])
                    container.start()
                success_url = reverse_lazy('dock:docker_container', kwargs={'pk': pk})
                return redirect(success_url)
            except Exception as e:
                form.errors.update({'错误': str(e)})

        # else:
        #     import ipdb;import ipdb; ipdb.set_trace()

    # 打开表单页面
    images = get_client_method(client, 'images.list')
    imgs = []
    for image in images:
        if image.tags:
            img = {'name': image.tags[0]}
            imgs.append(img)
    imgs.sort(key=lambda s: s['name'], reverse=False)

    networks = get_client_method(client, 'networks.list')
    nets = []
    for network in networks:
        driver = network.attrs['Driver']
        if driver in ('macvlan', 'bridge'):
            net = {'type': driver, 'name': network.name, 'subnet': network.attrs['IPAM']['Config'][0]['Subnet']}
            nets.append(net)
    nets.sort(key=lambda s: s['type'], reverse=False)

    return render(request, 'dock/container_add.html', locals())


def net(request, pk=0):
    # docker network ls 容器网络
    dockerhosts = DockerHost.objects.all()
    dockerhost_id = get_dockerhost_id(request, pk)

    if dockerhost_id:
        client = docker_client(request, dockerhost_id)
        networks = get_client_method(client, 'networks.list')
        if type(networks) != list:
            # docker宿主机连接失败或未知错误
            error = networks
        else:
            nets = []
            for network in networks:
                driver = network.attrs['Driver']
                if driver in ('macvlan', 'bridge'):
                    # import ipdb;ipdb.set_trace()
                    net = {'type': driver, 'name': network.name}
                    try:
                        net['subnet'] = [i['Subnet'] for i in network.attrs['IPAM']['Config']]
                        net['gateway'] = [i['Gateway'] for i in network.attrs['IPAM']['Config']]
                        # net['gateway'] = network.attrs['IPAM']['Config'][0]['Gateway']
                    except Exception:
                        net['subnet'] = ''
                        net['gateway'] = ''
                    net['time'] = network.attrs['Created'][:16].replace('T', ' ')
                    net['id'] = network.id
                    nets.append(net)

    return render(request, 'dock/net.html', locals())


def net_rm(request, pk):
    # 删除容器
    netids = request.GET.get('id').strip(',').split(',')
    client = docker_client(request, pk)
    msg = {"remove": "ok", "status": True}
    try:
        for netid in netids:
            network = get_client_method(client, 'networks.get', netid)
            if type(network) in (unicode, str):
                msg = {"error": str(network)}
            else:
                print(network.remove())
    except Exception as e:
        msg = {"error": str(e)}

    return HttpResponse(json.dumps(msg))


def net_do(request, pk):
    # 容器网络信息、操作
    # import ipdb; ipdb.set_trace()
    netid = request.GET.get('id')
    do = request.GET.get('do')
    client = docker_client(request, pk)
    try:
        net = get_client_method(client, 'networks.get', netid)
        # print(net, 8888)
        if isinstance(net, docker.models.networks.Network):
            msg = getattr(net, do)
        else:
            msg = {"error": str(net)}
        # print(msg, 99999)
    except Exception as e:
        msg = str(e)
    # if do != 'logs':
    if type(msg) in (list, dict):
        try:
            msg = json.dumps(msg)
        except Exception:
            msg = json.dumps({"error": str(msg)})
    return HttpResponse(msg)


def net_add(request, pk):
    # 容器网络添加
    # 由于docker_client.containers.run未封装支持设置IP、挂载
    # 所以使用底层模块docker_client.api.create_container
    client = docker_client(request, pk)

    if request.method == 'POST':
        # print(request.POST, 7777777)
        form = NetAddForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name', None)
            driver = form.cleaned_data.get('driver', 'macvlan')
            interface = form.cleaned_data.get('interface', None)
            ip = form.cleaned_data.get('ip', None)  # 桥接时的--gateway
            subnet = form.cleaned_data.get('subnet', '')
            gateway = form.cleaned_data.get('gateway', '')  # 桥接时的DefaultGatewayIPv4

            # import ipdb; ipdb.set_trace()
            if driver == 'bridge':
                def_gateway, gateway = gateway, ip
                options = {"com.docker.network.bridge.name": interface}
                aux_addresses = {"DefaultGatewayIPv4": def_gateway}
            else:
                options = {"parent": interface}
                aux_addresses = None

            ipam_pool = docker.types.IPAMPool(
                subnet=subnet,
                aux_addresses=aux_addresses,
                gateway=gateway
            )
            ipam = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            try:
                res = client.networks.create(name=name, driver=driver, ipam=ipam, options=options)
                success_url = reverse_lazy('dock:docker_net', kwargs={'pk': pk})
                return redirect(success_url)
            except Exception as e:
                form.errors.update({'错误': str(e)})

        # else:
        #     import ipdb;import ipdb; ipdb.set_trace()

    # 打开表单页面
    return render(request, 'dock/net_add.html', locals())


class DockerWebSSH(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user
        return render_to_response('dock/webssh.html', locals())


class DockerYmlList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "dock/yml_list.html"
    model = DockerYml
    permission_required = 'dock.view_dockeryml'


class DockerYmlView(LoginRequiredMixin, PermissionRequiredMixin):
    template_name = "dock/yml.html"
    model = DockerYml
    form_class = DockerYmlForm
    success_url = reverse_lazy('dock:docker_yml_list')

    def post(self, request, *args, **kwargs):
        # 保存yml文件内容
        # import ipdb; ipdb.set_trace()
        res = super(DockerYmlView, self).post(request, *args, **kwargs)
        if self.get_form().is_valid():
            # 表单验证通过

            yml_file = self.object.get_ymlfile()
            yml_path = os.path.dirname(yml_file)

            if not os.path.exists(yml_path):
                # 组目录不存在
                os.makedirs(yml_path)
                os.mknod(yml_file)
            elif not os.path.exists(yml_file):
                os.mknod(yml_file)

            with open(yml_file, 'r') as f:
                old_yml = f.read()
            new_yml = request.POST.get('yml', '')
            # print(new_yml, 677777)
            if new_yml != old_yml:
                with open(yml_file, 'w') as f:
                    f.write(new_yml)

        return res


class DockerYmlAdd(DockerYmlView, CreateView):
    permission_required = 'dock.can_add_dockeryml'


class DockerYmlEdit(DockerYmlView, UpdateView):
    permission_required = 'dock.can_edit_dockeryml'

    def get_context_data(self, **kwargs):
        # 读取yml文件内容
        obj = self.get_object()
        yml_file = obj.get_ymlfile()
        if os.path.exists(yml_file):
            with open(yml_file, 'r') as f:
                yml = f.read()
        else:
            # 文件已删除
            yml = ''
        # print(yml, 677777)
        kwargs['yml'] = yml

        return super(self.__class__, self).get_context_data(**kwargs)


class DockerComposeList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "dock/compose_list.html"
    model = DockerCompose
    permission_required = 'dock.view_dockercompose'

    def get(self, request, *args, **kwargs):
        # 根据YML、宿主机，进行数据过滤
        res = super(self.__class__, self).get(request, *args, **kwargs)
        yml_id = request.GET.get('yml')
        host_id = request.GET.get('host')
        kwargs = {'yml_id': yml_id} if yml_id else {}
        kwargs.update({'dockerhost_id': host_id}) if host_id else 0
        object_list = self.object_list.filter(**kwargs)
        # import ipdb; ipdb.set_trace()
        res.context_data['object_list'] = object_list
        res.context_data['filter'] = json.dumps(kwargs, encoding='utf-8') if kwargs else None
        return res


class DockerComposeView(LoginRequiredMixin, PermissionRequiredMixin):
    template_name = "dock/compose.html"
    model = DockerCompose
    form_class = DockerComposeForm
    success_url = reverse_lazy('dock:docker_compose_list')

    def post(self, request, *args, **kwargs):
        # 保存DockerCompose表数据，并执行docker-compose更新
        # import ipdb; ipdb.set_trace()
        res = super(DockerComposeView, self).post(request, *args, **kwargs)
        # print(request.POST, 8777)
        if self.get_form().is_valid():
            # 表单验证通过
            up = request.POST.get('up', '')
            if up == 'on':
                # 勾选执行docker-compose up
                self.object.compose_up()

        return res


class DockerComposeAdd(DockerComposeView, CreateView):
    permission_required = 'dock.can_add_dockercompose'


class DockerComposeEdit(DockerComposeView, UpdateView):
    permission_required = 'dock.can_edit_dockercompose'


class DockerComposeDo(LoginRequiredMixin, PermissionRequiredMixin, View):
    # 容器组 - 操作
    permission_required = 'dock.can_edit_dockercompose'

    def get(self, request, *args, **kwargs):

        do = request.GET.get('do')
        args = request.GET.get('args', '').split(',')
        obj = get_object_or_404(DockerCompose, id=kwargs.get('pk'))
        compose_cmd = obj.get_compose_cmd()
        print(do, args, 9999999)
        msg = compose_cmd.command(do, *args)

        return HttpResponse(msg)


def docker_compose_del(request, ids=''):
    # print(ids, 8888)
    # import ipdb; ipdb.set_trace()
    if not request.user.has_perm('dock.delete_dockercompose'):
        raise PermissionDenied
    ret = {"remove": "ok", "status": True}
    try:
        # ids = [id.strip() for id in ids.split(',')]
        DockerCompose.objects.filter(id__in=ids.strip(',').split(',')).delete()
    except Exception as e:
        ret = {
            "static": False,
            "error": '删除请求错误,{}'.format(e)
        }
    return HttpResponse(json.dumps(ret))


class DockerImageFileList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "dock/imagefile_list.html"
    model = DockerImageFile
    permission_required = 'dock.view_dockerimagefile'

    def get_context_data(self, **kwargs):
        kwargs['dockerhosts'] = DockerHost.objects.all()
        return super(self.__class__, self).get_context_data(**kwargs)


def docker_imagefile_del(request, ids=''):
    # print(ids, 8888)
    # import ipdb; ipdb.set_trace()
    if not request.user.has_perm('dock.delete_dockerimagefile'):
        raise PermissionDenied
    ret = {"remove": "ok", "status": True}
    try:
        # ids = [id.strip() for id in ids.split(',')]
        objs = DockerImageFile.objects.filter(id__in=ids.strip(',').split(','))
        for obj in objs:
            obj.delobj()
    except Exception as e:
        ret = {
            "static": False,
            "error": '删除请求错误,{}'.format(e)
        }
    return HttpResponse(json.dumps(ret))


class DockerImageFileLoad(LoginRequiredMixin, PermissionRequiredMixin, View):
    # 镜像包还原到宿主机 - 相当于docker load命令
    permission_required = 'dock.can_edit_dockerimagefile'

    def get(self, request, *args, **kwargs):

        hostid = kwargs.get('hostid')
        dockerhost = get_object_or_404(DockerHost, id=hostid)
        cli = dockerhost.client

        ids = kwargs.get('ids').strip(',').split(',')
        imagefiles = DockerImageFile.objects.filter(id__in=ids)
        msg = ''
        for imagefile in imagefiles:
            msg = '%s\r\n\r\n%s: %s' % (msg, imagefile, imagefile.load_obj(cli))
        if not msg:
            msg = '找不到任何有效的镜像包，已删除？'

        return HttpResponse(msg)


class DockerComposeUpload(LoginRequiredMixin, PermissionRequiredMixin, View):
    # 手工上传镜像包到资产系统中
    permission_required = 'dock.can_add_dockerimagefile'

    def post(self, request, *args, **kwargs):
        # 解析并保存上传的镜像包文件
        # import ipdb; ipdb.set_trace()
        files = request.FILES.getlist('imagefile')
        print(files)
        msgs = []  # 收集各文件上传处理返回的信息
        for file in files:
            msg = DockerImageFile.save_file(file)
            msgs.append('%s 返回信息：\r\n%s' % (file.name, msg))

        return HttpResponse('\r\n\r\n'.join(msgs))
