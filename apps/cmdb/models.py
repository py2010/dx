# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone

# from django.core.cache import cache
# from django import template
from django.contrib.auth import get_user_model
# import traceback
import paramiko
import json

from io import StringIO

# from urllib.parse import urljoin
import uuid
from ops import opt
from ops.models import MyModel

# from django.db.models.options import Options
# old_contribute_to_class = Options.contribute_to_class

# def new_contribute_to_class(instance, cls, name):
#     # 设置verbose_name_plural为verbose_name
#     old_contribute_to_class(instance, cls, name)
#     instance.verbose_name_plural = instance.verbose_name
# models.options.Options.contribute_to_class = new_contribute_to_class

User = get_user_model()
Group = User.groups.rel.model


class HostGroup(models.Model):
    name = models.CharField("组名/区域", max_length=30, unique=True)
    ip = models.CharField(
        "IP匹配", max_length=20, default='', blank=True,
        help_text='IP开头字符，比如Core组IP为10.2.4.开头。用于客户端脚本添加新主机时自动设置组，不支持通配符')
    desc = models.CharField("描述", max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = '主机分组'

    def __str__(self):
        return self.name

    @staticmethod
    def get_group(ip):
        # 客户端脚本自动添加主机时，自动设置主机所属组(区域)

        groups = HostGroup.objects.exclude(ip='').order_by('-ip')
        group_id = 0
        for group in groups:
            if ip.startswith(group.ip):
                group_id = group.id
                break
        return group_id


class HostUser(models.Model):
    # 各服务器资产登陆用户
    PROTOCOLS = (
        ('ssh', 'ssh'),
        ('rdp', 'rdp'),
        ('vnc', 'vnc'),
    )

    name = models.CharField("名称", max_length=50, default='', help_text='标识名称，当不同服务器使用相同的SSH账号名，但密码不同时，此项名称可进行区分。')
    protocol = models.CharField('协议类型', max_length=8, choices=PROTOCOLS, default='ssh')

    username = models.CharField("用户名", max_length=50, default='', blank=True, help_text='VNC协议时用户名忽略, 填任意')
    password = opt.EncryptField("密码", max_length=150, default='', blank=True)
    rsa_key = models.TextField(
        "SSH私钥", default='', null=True, blank=True,
        help_text='SSH协议类型使用密钥登录时输入RSA私钥，如果密码方式登陆，则留空')
    auto = models.BooleanField(verbose_name='自动修改密码', default=False, help_text='开启自动，且RSA私钥为空时，crontab将每天定时修改密码')

    autotime = models.DateTimeField('最近改密', auto_now=True, blank=True, null=True, help_text='最近一次自动修改密码时间')
    changetime = models.DateTimeField('最后修改', auto_now=True, blank=True, null=True)
    enable = models.BooleanField('启用', default=True)
    text = models.TextField("备注信息", default='', null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = '主机用户'
        # unique_together = [('name', 'username'), ]

    def __str__(self):
        return '%s (%s)' % (self.name, self.username)

    def get_password(self):
        return self.password

    def get_rsa_key(self):
        rsa_key = None
        if self.rsa_key:
            try:
                rsa_key = paramiko.RSAKey.from_private_key(
                    StringIO(self.rsa_key),
                    self.get_password(),
                )
            except Exception as e:
                print(self, '错误的RSA私钥\r\n', e)

        return rsa_key


class Host(models.Model):
    # 虚拟机、物理机 等设备
    ALL_PROTOCOLS = {
        'ssh': 22,
        'rdp': 3389,
        'vnc': 5901,
    }
    ASSET_STATUS = (
        (1, "在用"),
        (2, "备用"),
        (3, "故障"),
        (4, "下线"),
        (6, "其它"),
    )

    ASSET_TYPE = (
        (1, "物理机"),
        (2, "虚拟机"),
        (3, "容器"),
        (4, "H3C交换机"),
        (6, "其它")
    )

    group = models.ForeignKey(HostGroup, verbose_name="机组", default=1, on_delete=models.SET_NULL, null=True, blank=True)
    hostname = models.CharField(
        max_length=50, verbose_name="主机名/计算机名", unique=True,
        help_text='关键字段，请谨慎修改')  # 服务器数据以计算机名为锚，以验证身份不重复添加数据
    ip = models.GenericIPAddressField(
        "管理IP", max_length=15,
        help_text='若有多个IP且主机名无指定解析则默认为0.0.0.0，请在客户端/etc/hosts中设置其主机名对应IP解析')
    protocols = models.CharField('协议类型', max_length=150, default='所有', blank=True,
                                 help_text='主机包含的ssh/rdp/vnc协议/端口json数据, '
                                 '所有协议则为{"ssh": 22, "vnc": 5901, "rdp": 3389}'
                                 )
    name = models.CharField('标识名称', max_length=100, default='', null=True, blank=True, help_text='备注标签, 便于人员识别')

    other_ip = models.CharField("其它IP", max_length=100, null=True, blank=True)

    status = models.SmallIntegerField("设备状态", choices=ASSET_STATUS, default=1, null=True, blank=True)
    asset_type = models.SmallIntegerField("设备类型", choices=ASSET_TYPE, default=2, null=True, blank=True)
    # machine = models.ForeignKey('self', verbose_name="所属物理机", limit_choices_to={'asset_type': 1},
    #                             on_delete=models.SET_NULL, null=True, blank=True, help_text='设备类型为虚拟机/容器时，设置所在物理机')
    os = models.CharField("操作系统", max_length=100, default='', null=True, blank=True)

    cpu_model = models.CharField("CPU型号", max_length=100, default='', null=True, blank=True)
    cpu_num = models.CharField(
        "CPU数量", max_length=100, default='', null=True, blank=True,
        help_text='物理核个数, 逻辑核个数(intel超线程)')
    memory = models.CharField("内存大小", max_length=30, default='', null=True, blank=True)
    disk = models.CharField("硬盘信息", max_length=255, default='', null=True, blank=True)
    vendor = models.CharField("供应商", max_length=150, default='', null=True, blank=True)
    sn = models.CharField("主机序列号", max_length=150, default='', null=True, blank=True)
    # ports = models.TextField("监听端口", default='', null=True, blank=True, help_text='主机上处于监听状态的TCP和UDP端口')

    createtime = models.DateTimeField('创建时间',
                                      auto_now_add=True,
                                      # default=now,
                                      blank=True, null=True)
    changetime = models.DateTimeField('修改时间', auto_now=True, blank=True, null=True)
    # agenttime = models.DateTimeField('配置更新', blank=True, null=True, help_text='最近一次主机客户端自动脚本运行更新软硬件信息的时间')

    buydate = models.DateField('购买日期', default=timezone.now, blank=True, null=True)
    position = models.CharField("所处位置", max_length=250, default='', null=True, blank=True)
    sernumb = models.CharField("服务编号", max_length=150, default='', null=True, blank=True)
    sercode = models.CharField("服务代码", max_length=150, default='', null=True, blank=True)

    kernel = models.CharField(max_length=60, verbose_name="系统内核版本", default='', blank=True)

    enable = models.BooleanField('启用', default=True)
    text = models.TextField("备注信息", default='', null=True, blank=True)

    class Meta:
        permissions = (
            # 实现表级别的权限控制
            # ("rdp_host", "远程桌面"),       # RDP登陆
            # ("vnc_host", "VNC连接"),        # VNC登陆
            ("ssh_host", "主机远程控制"),      # 终端登陆/RDP/VNC
            ("sftp_host", "网页sftp"),        # Elfinder文件管理
        )
        ordering = ['group', 'ip']
        verbose_name = '主机'

    def __str__(self):
        return '%s - %s' % (self.name or self.hostname, self.ip)

    def get_port(self, protocol='ssh'):
        protocols = self.protocols.replace("'", '"')
        try:
            protocols = json.loads(protocols)
        except Exception:
            protocols = self.ALL_PROTOCOLS

        return protocols.get(protocol, 0)

    @property
    def port_ssh(self):
        return self.get_port('ssh')

    @property
    def port_rdp(self):
        return self.get_port('rdp')

    @property
    def port_vnc(self):
        return self.get_port('vnc')

    def get_hostuser(self, user, protocol='ssh'):
        # 获取某台主机资产用户列表
        return Perm.get_host_hostuser(user, self, protocol)

    def chk_user_prem(self, user, perm=''):
        # 验证网站用户操作权限，表级别权限和行级别权限
        # import ipdb;ipdb.set_trace()
        if user.is_superuser:
            return 1  # 超级管理员直接有权限
        elif not user.has_perm('cmdb.%s_host' % perm):
            # 验证表级别权限
            return 0  # 未设置用户相对应的主机权限，超级管理员无需设置而直接有权限

        # 验证授权 (行级别权限)
        hosts = Perm.get_host(user)
        return 1 if self in hosts else 0


def get_logname():
    # 生成不重复的回放录像文件名
    return '%s.%s.json' % (timezone.now().strftime("%Y.%m.%d.%H.%M.%S"), uuid.uuid4().hex[:6])


class Session(models.Model):
    # 终端操作回放录像
    SSHTYPE = (
        (1, "WebSSH"),
        (2, "Xshell"),
        (3, "SecureCRT"),
        (8, "RDP"),
        (9, "VNC"),
    )

    host = models.CharField('主机', max_length=255)
    host_user = models.CharField('主机账号', max_length=255, default='', blank=True, null=True, help_text='VNC协议时为空, 无用户')
    http_user = models.CharField('网站用户', max_length=50)
    type = models.SmallIntegerField("终端类型", choices=SSHTYPE, default=1, null=True, blank=True)
    # channel = models.CharField(max_length=100, verbose_name='channel', default='', blank=False, editable=False)
    log = models.CharField(max_length=100, verbose_name='文件名', unique=True,
                           default=get_logname, editable=False, blank=False)
    cmds = models.TextField("命令记录", default='', null=True, blank=True, help_text='用户终端操作所执行的命令记录')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间', blank=True, null=True)

    def __str__(self):
        return '%s' % self.host

    class Meta:
        permissions = (
            ("kill_session", "强制结束终端"),
            ("play_session", "播放操作录像"),
            ("monitor_session", "监视操作"),
        )
        ordering = ['-start_time', ]
        verbose_name = '终端操作记录'


class Perm(MyModel):
    '''
    网站用户/主机/主机用户, 行数据级别权限控制, 当主机数量很大时以便于集中配置授权.
    ALL_PERM_NAME, 用于取消行数据权限控制, 不进行行权限限制 (默认新安装/测试演示时)
    '''
    ALL_PERM_NAME = '__all__'  # 含此名称的权限并启用时, 任何用户有任何主机用户授权

    name = models.CharField("名称", max_length=100, default='')
    web_user = models.ManyToManyField(User, verbose_name='网站用户', blank=True)
    web_usergroup = models.ManyToManyField(Group, verbose_name='网站用户组', blank=True)
    hostgroup = models.ManyToManyField('HostGroup', verbose_name='机组', blank=True)
    host = models.ManyToManyField('Host', verbose_name='主机', blank=True)
    host_user = models.ManyToManyField('HostUser', verbose_name='主机用户', blank=True)

    enable = models.BooleanField('启用', default=True)
    changetime = models.DateTimeField('最后修改', auto_now=True, blank=True, null=True)
    text = models.TextField("备注", default='', null=True, blank=True)

    class Meta:
        verbose_name = '用户主机授权'

    def __str__(self):
        return self.name

    @classmethod
    def is_all_perm(cls):
        '''是否不限授权, 取消(主机授权 - 行级别权限)控制'''
        qs = cls.qs.filter(name=cls.ALL_PERM_NAME)
        return qs.exists()

    @classmethod
    def get_perm(cls, user):
        '''获取网站登录用户的Perm授权列表'''
        qs1 = cls.qs.filter(web_user=user)  # 授权用户
        qs2 = cls.qs.filter(web_usergroup__in=user.groups.all())  # 授权用户组
        return qs1 | qs2  # 并集使用前不会提交SQL事务

    @classmethod
    def get_host(cls, user):
        # 获取网站用户有操作权限的所有主机

        hosts = Host.objects.filter(enable=True)
        if user.is_superuser or cls.is_all_perm():
            return hosts

        perms = cls.get_perm(user)  # 网站用户已有的授权
        qs1 = hosts.filter(perm__in=perms).distinct()  # 授权列表对应的主机
        qs2 = hosts.filter(group__perm__in=perms).distinct()  # 授权列表对应的节点的主机
        return qs1 | qs2

    @classmethod
    def get_host_hostuser(cls, user, host, protocol='ssh'):
        # 获取某主机对应的所有已授权的主机用户
        qs = HostUser.objects.filter(protocol=protocol, enable=True)
        if cls.is_all_perm():
            return qs
        if host not in cls.get_host(user):
            return qs.none()

        perms = cls.get_perm(user)  # 用户已有的授权
        perms = perms.filter(models.Q(host=host) | models.Q(hostgroup=host.group))
        return qs.filter(perm__in=perms)  # 授权列表对应的主机用户


class AssetLog(models.Model):
    '''资产修改 - 历史记录'''

    user = models.ForeignKey(User, verbose_name='用户', editable=False, on_delete=models.SET_NULL, null=True, blank=True)

    fields = models.CharField('字段', max_length=255)
    old = models.TextField('原内容', default='', blank=True, null=True)
    new = models.TextField('新内容', default='', blank=True, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True, blank=True, null=True)

    class Meta:
        abstract = True


def _create_model(asset_model_name, asset_verbose_name, base=()):
    # 创建资产设备日志表模型
    model_name, verbose_name = f'Log_{asset_model_name}', f'日志-{asset_verbose_name}'
    model = type(model_name, base, {
        '__module__': __name__,
        'obj': models.ForeignKey(
            asset_model_name, verbose_name=asset_verbose_name,
            on_delete=models.SET_NULL, null=True, blank=True
        ),
        'Meta': type('Meta', (), {'verbose_name': verbose_name, }),
    })
    return model


assets = [
    # (资产模型名, )，用于生成日志模型
    ('Host', ),
    # ('Switch', ),
    # ('FireWall', ),
    # ('Docker', ),

]
# assets = [
#     (model_name, model) for model_name, model in locals().items()
#     if hasattr(model, '_meta') and not model._meta.abstract
# ]

# for asset_model_name, asset_model in assets:
#     if not asset_model:
#         try:
#             asset_model = locals()[asset_model_name]
#         except Exception as e:
#             print(e)
#             continue

#     if asset_model.__module__ == locals()['__name__']:
#         # 本地model
#         asset_verbose_name = asset_model._meta.verbose_name or asset_model._meta.verbose_name_plural

#         base_models = [AssetLog, ]
#         asset_log_model = _create_model(asset_model_name, asset_verbose_name, tuple(base_models))
#         locals()[asset_log_model.__name__] = asset_log_model  # 创建日志模型
#         # create_signal(model=asset_model, log=asset_log_model)  # 创建signals监视ORM资产模型数据变化, 并记录日志

# # import ipdb;ipdb.set_trace()

