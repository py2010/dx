# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
# from django.utils.timezone import now, localdate

import docker
import os
import sys
import io
# import cStringIO
from .conf import YmlDir, ImgDir, DOCKER_CERT_PATH
from compose.cli.main import dispatch as docker_compose
import tarfile
import json


class DockerHost(models.Model):
    # 容器宿主机、物理机，必需已开启监听端口(swarm)，用于cmdb连接远程API
    # CMDB不使用swarm、docker service功能，因网络只能为overlay无法自定义配置

    name = models.CharField(max_length=100, verbose_name=u"标识名称")
    """
    host = models.CharField(verbose_name='宿主机', max_length=50, default='.test.com',
        help_text='Docker容器宿主机、物理机域名，比如xxx.test.com，<br/>\
        为简化配置处理，统一使用泛域名*.test.com SSL证书<br/>')
    """
    ip = models.GenericIPAddressField(u"宿主机IP", max_length=15)
    port = models.IntegerField(verbose_name='Docker端口', default=2375)
    tls = models.BooleanField(verbose_name='TLS', default=True,
                              help_text='Docker-API不会进行安全验证，任意接入的客户端都能进行所有操作<br/>为安全需配置TLS，客户端使用证书访问API接口')
    # ver = models.CharField(max_length=20, verbose_name=u"Docker版本", help_text='Docker服务端版本', null=True, blank=True)
    text = models.TextField(u"备注信息", default='', blank=True)

    class Meta:
        verbose_name = '容器宿主机'
        unique_together = [('ip', 'port'), ]  # 用于同一主机映射多端口对应多个docker服务端
        permissions = (
            # 实现表级别的权限控制
            ("images_manage", "镜像管理"),      # 镜像管理
            ("containers_manage", "容器管理"),  # 容器管理
            ("net_manage", "网络管理"),  # 网络管理
        )

    def __str__(self):
        return '%s (%s)' % (self.name, self.ip)

    # def ip2host(self):
    #     # 将IP转换为虚拟构造的域名，用于泛域名*.test.com SSL证书验证
    #     return '%s.test.com' % self.ip.replace('.', '_')

    @property
    def client(self):
        # tls = 1 if self.tls else ''  # docker.utils.utils.kwargs_from_env
        cert_path = DOCKER_CERT_PATH if self.tls else None
        if docker.tls.ssl.OPENSSL_VERSION_INFO > (1, 0, 1, 0, 0):
            ssl_version = docker.tls.ssl.PROTOCOL_TLSv1_2
        else:
            ssl_version = docker.tls.ssl.PROTOCOL_TLSv1
        try:
            cli = docker.from_env(
                timeout=30,
                assert_hostname=False,
                version='1.30',  # 不同的docker服务端要求版本不同
                ssl_version=ssl_version,
                environment={
                    'DOCKER_HOST': 'tcp://%s:%d' % (self.ip, self.port),
                    'DOCKER_CERT_PATH': cert_path,
                    # 'DOCKER_TLS_VERIFY': tls  # ?????????
                    # 'COMPOSE_TLS_VERSION': 'TLSv1_2',
                }
            )
        except docker.errors.TLSParameterError as e:
            # 默认三个证书文件在django进程用户主目录下的.docker中
            # ~/.docker/ca.pem
            # ~/.docker/cert.pem
            # ~/.docker/key.pem
            print(e)
            error = 'SSL证书不存在？证书目录: %s，TSL验证: %s' % (DOCKER_CERT_PATH, self.tls)
            return error

        cli.dockerhost = self
        return cli


class DockerYmlGroup(models.Model):
    name = models.CharField(u"类名", max_length=30, unique=True)
    path = models.CharField(max_length=100, verbose_name=u"yml目录", unique=True)
    desc = models.CharField(u"描述", max_length=100, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = '容器YML分组'

    def __str__(self):
        return '%s (%s)' % (self.name, self.path)


class DockerYml(models.Model):
    name = models.CharField(max_length=100, verbose_name=u"标识名称")
    group = models.ForeignKey(DockerYmlGroup, verbose_name=u"容器YML分组", on_delete=models.CASCADE,)
    file = models.CharField(max_length=100, verbose_name=u"yml文件名")
    # docker = models.ManyToManyField(Docker, verbose_name='容器宿主机', blank=True)
    text = models.TextField(u"备注", default='', blank=True)
    state = models.BooleanField(verbose_name='启用', default=True)

    class Meta:
        ordering = ['name']
        verbose_name = '容器YML'
        unique_together = [('group', 'file'), ]

    def __str__(self):
        return '%s / %s' % (self.group.path, self.file)

    def get_ymlfile(self):
        # 获取yml完整路径
        # 必需返回字符串，不能为unicode。
        # docker-compose有BUG或者命令行下字符不可能为unicode，它判断yml文件参数，不是str(单文件)就是列表(多文件)
        return str(os.path.join(YmlDir, self.group.path, self.file))


class DockerCompose(models.Model):
    """
    通过dockercompose.yml文件创建的容器编排
    """
    name = models.CharField(max_length=100, verbose_name=u"标识名称")
    yml = models.ForeignKey(DockerYml, verbose_name=u"容器YML",
                            on_delete=models.CASCADE, limit_choices_to={'state': True})
    dockerhost = models.ForeignKey(DockerHost, verbose_name=u"容器宿主机", on_delete=models.CASCADE,)
    scale = models.CharField(max_length=100, verbose_name=u"数量参数", default='', blank=True,
                             help_text='scale参数，默认每个服务只启动1个容器，多个时比如设置web=2,worker=3\
                             <br/>需启动多个容器的服务，不能配置IP、容器名等唯一项，以免冲突')
    createtime = models.DateTimeField('创建时间', auto_now_add=True, blank=True, null=True)
    changetime = models.DateTimeField('修改时间', auto_now=True, blank=True, null=True)
    # state = models.BooleanField(verbose_name='启用', default=True, editable=False)
    text = models.CharField('备注', max_length=300, default='', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = '容器编排'
        unique_together = [('yml', 'dockerhost'), ]

    def __str__(self):
        return self.name

    def get_compose_cmd(self):
        """
        获取docker-compose客户端，用于执行命令，up、start、stop等
        c = DockerCompose.objects.get(id=2)
        cc = c.get_compose_cmd()
        cc.command('up', '-d')
        cc.command('up', '-d', '--scale', 'ng=3')
        cc.command('top')
        """
        class DockerComposeCommand():
            # 执行docker-compose命令

            def __init__(self, dockercompose):
                dockerhost = dockercompose.dockerhost
                self.cmd_args = ['docker-compose']
                self.cmd_args.extend(['-H', 'tcp://%s:%d' % (dockerhost.ip, dockerhost.port)])
                if dockerhost.tls:
                    # import ipdb; ipdb.set_trace()
                    if DOCKER_CERT_PATH:
                        os.environ.setdefault('DOCKER_CERT_PATH', DOCKER_CERT_PATH)
                    else:
                        os.environ.setdefault('DOCKER_CERT_PATH', os.path.join(os.path.expanduser('~'), '.docker'))
                    # 指定客户端(cmdb本机)证书路径环境变量，若不指定，需手工增加证书参数
                    # --tlscacert=/root/.docker/ca.pem --tlscert=/root/.docker/cert.pem --tlskey=/root/.docker/key.pem
                    # '--tlscacert', '/root/.docker/ca.pem', '--tlscert', '/root/.docker/cert.pem', '--tlskey', '/root/.docker/key.pem'
                    self.cmd_args.extend([
                        '--tlsverify',  # tls检查
                        '--skip-hostname-check',  # 忽略域名检查
                    ])
                else:
                    if 'DOCKER_CERT_PATH' in os.environ:
                        """
                        清除环境变量DOCKER_CERT_PATH，以免在加密/非加密HTTP连接切换时，导致HTTP的宿主机使用HTTPS
                        因官方docker-compose是单机服务端命令，设计时不会考虑多宿主机HTTP/HTTPS并存
                        compose.cli.docker_client.tls_config_from_options
                        cert_path = environment.get('DOCKER_CERT_PATH')
                        """
                        os.environ.pop('DOCKER_CERT_PATH')
                self.cmd_args.append('--no-ansi')  # 去掉终端格式字符
                self.cmd_args.extend(['-f', dockercompose.yml.get_ymlfile()])
                # print(self.cmd_args, 8888888888)

            def command(self, cmd, *args):
                # cmd: up、start、stop等
                if cmd not in (
                    'up',
                    'start',
                    'stop',
                    'pause',
                    'restart',
                    'top',
                    'ps',
                    'logs',
                    'down',
                ):
                    return '为了安全，默认只开放部分命令操作权限'
                cmd_args = list(self.cmd_args)
                cmd_args.append(cmd)
                cmd_args.extend(args)

                sys.argv = [str(i.strip()) for i in cmd_args if i.strip()]
                # print(sys.argv, 777777777)

                # strio = cStringIO.StringIO()
                strio = io.StringIO()
                sys.stderr = sys.stdout = strio  # 输出重定向到内存变量，用于显示到网页
                try:
                    docker_compose()()  # 执行docker-compose命令，参数为sys.argv[1:]
                except Exception as e:
                    print('执行docker-compose出错:\r\n', e)
                    raise
                sys.stderr = sys.__stderr__  # 还原输出到控制台
                sys.stdout = sys.__stdout__  # 还原输出到控制台
                msg = strio.getvalue()
                # print('###################')
                # print(msg)
                # print('###################')

                return msg

        try:
            return self.compose_cmd
        except Exception:
            self.compose_cmd = DockerComposeCommand(self)
            return self.compose_cmd

    def compose_up(self):
        # DockerCompose表单保存后，可能需更新容器编排
        compose_cmd = self.get_compose_cmd()
        args = []
        scale = self.scale.strip().replace('，', ',')
        if scale:
            for i in scale.split(','):
                if i.strip():
                    args.extend(['--scale', i])

        compose_cmd.command('up', '-d', '--force-recreate', *args)


class DockerImageFile(models.Model):
    # 备份/保存的镜像包文件
    name = models.CharField(max_length=100, verbose_name=u"镜像名")
    ver = models.CharField(max_length=100, verbose_name=u"版本", null=True, blank=True)
    dockerhost = models.ForeignKey(DockerHost, verbose_name=u"来源/宿主机", blank=True, null=True, on_delete=models.SET_NULL)
    file = models.CharField(max_length=100, verbose_name=u"文件名", unique=True)
    size = models.BigIntegerField(verbose_name=u"文件大小", default=0)
    createtime = models.DateTimeField('创建时间', auto_now_add=True, blank=True, null=True)
    upload = models.BooleanField(verbose_name='手工上传', default=False)
    text = models.TextField(u"备注", default='', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = '容器镜像包'
        unique_together = [('name', 'ver', 'dockerhost'), ]

    def __str__(self):
        return '%s:%s' % (self.name, self.ver)

    def delobj(self):
        # 删除条目，并删除镜像包
        file = os.path.join(ImgDir, self.file)
        if os.path.exists(file):
            os.remove(file)
        self.delete()

    @staticmethod
    def save_file(upload_file):
        """
        手工上传的镜像包，解析处理后保存，返回处理结果
        """
        # import ipdb; ipdb.set_trace()
        filetype = os.path.splitext(upload_file.name)[1].lstrip('.')  # 文件扩展名
        # 开始解析镜像包文件是否合法
        try:
            tf = tarfile.open(fileobj=upload_file.file, mode='r:%s' % filetype)
        except tarfile.ReadError as e:
            return '未知格式的镜像包，%s' % str(e)
        except Exception as e:
            return '解析镜像包出错，%s' % str(e)

        try:
            manifest = tf.getmember('manifest.json')
        except KeyError:
            return '镜像包中没有manifest.json文件，这是一个容器镜像包？'
        except Exception as e:
            return '无法获取镜像包文件manifest.json，%s' % str(e)

        manifest_file = tarfile.ExFileObject(tf, manifest)  # 从包中获取manifest.json文件
        txt = manifest_file.read()  # manifest.json文件内容
        print(txt, 333)
        try:
            image_name = json.loads(txt)[0]['RepoTags'][0]  # busybox:latest
        except Exception as e:
            return '镜像包文件manifest.json内容解析提取镜像(名称:版本)出错，请联系反映BUG. \r\n%s出错信息:%s' % (txt, str(e))

        name, ver = image_name.split(':')
        file = '%s(%s).upload.tar' % (name.replace('/', '#'), ver)
        size = upload_file.size

        filepath = os.path.join(ImgDir, file)
        if os.path.exists(filepath):
            if DockerImageFile.objects.filter(file=file):
                return '之前已曾上传相同(名称:版本)的镜像包，为安全已取消覆盖保存，请先删除之前上传的镜像包{}后再重新上传'.format(file)
        try:
            f = open(filepath, 'w')
            for chunk in upload_file.chunks():
                # print(len(chunk))
                f.write(chunk)
            f.close()

            obj = DockerImageFile(name=name, ver=ver, file=file, size=size, upload=True)
            obj.save()
        except Exception as e:
            return '文件保存失败：%s' % str(e)
        return '上传成功.'

    @staticmethod
    def save_obj(image):
        """
        从宿主机下载保存镜像，相当于docker save命令，
        DOCKER远程API，通过官方函数image.save()下载的镜像包，不含镜像名版本标签"RepoTags":null
        self.client.api.get_image(self.id)
        API: GET https://ip:2375/v1.30/images/镜像ID/get，"RepoTags":null
        self.client.api.get_image(self.tags[0])
        API: GET https://ip:2375/v1.30/images/镜像名/get，"RepoTags":["busybox:latest"] 单个镜像
        API: GET https://ip:2375/v1.30/images/get?names=镜像名1&names=镜像名2，可多个镜像
        """
        def get_image(api, image_name):
            """
            docker client.api.get_image重写
            官方函数api._url特意不对/进行转义，且API网址为images/镜像名/get，
            需进行/转义或改API网址为images/get?names=镜像名
            """
            # image_name = image_name.replace('/', '%2f')
            # url手工转义 / --> %2F后，在api._url中会对%进行转义，导致/字符由%2f变成%252f
            url = api._url("/images/get?names={0}", image_name)
            # print(url, 9999999999)
            # url = url.replace('%25', '%')  # %取消转义
            res = api._get(url, stream=True)
            api._raise_for_status(res)
            return res.raw

        name, ver = image.tags[0].split(':')
        dockerhost = image.client.dockerhost
        img = DockerImageFile.objects.filter(name=name, ver=ver, dockerhost=dockerhost)
        if img:
            return '已有相同的镜像包，当前版本的镜像可能之前曾有过保存操作，为安全忽略此次处理。\r\n若要重新保存，请先删除已有的镜像包后再试。'
        file = '%s(%s).%d.tar' % (name.replace('/', '#'), ver, dockerhost.id)
        # print(datetime.today().strftime("%Y-%m-%d %H:%M:%S"), 1)
        try:
            # data = image.save()  # "RepoTags":null
            image_name = '%s:%s' % (name, ver)
            # data = image.client.api.get_image(image_name)  # "RepoTags":["busybox:latest"]
            data = get_image(image.client.api, image_name)
            # import ipdb; ipdb.set_trace()
            try:
                # docker.__version__ == '2.7.0'
                data = data.stream()
            except Exception:
                # docker.__version__ == '3.3.0'
                # 正式版机器中的docker版本高，data直接为stream
                pass
            f = open(os.path.join(ImgDir, file), 'w')
            for chunk in data:
                # print(len(chunk))
                f.write(chunk)
            f.close()
            size = os.path.getsize(os.path.join(ImgDir, file))
            obj = DockerImageFile(name=name, ver=ver, dockerhost=dockerhost, file=file, size=size)
            obj.save()
            return '镜像保存/备份成功！可在<镜像包>中查看'
        except Exception as e:
            # raise
            return '镜像保存/备份出错:\r\n%s' % str(e)

    def load_obj(self, cli):
        # 将资产系统中的镜像包复制/还原到宿主机docker镜像，相当于docker load命令
        try:
            with open(os.path.join(ImgDir, self.file), 'rb') as f:
                old_timeout, cli.api.timeout = cli.api.timeout, 300
                cli.images.load(f)
                cli.api.timeout = old_timeout
            return '镜像复制/还原成功！'
        except Exception as e:
            raise
            return '镜像复制/还原出错:\r\n%s' % str(e)
