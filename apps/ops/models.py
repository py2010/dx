# coding=utf-8

import logging
# from django.contrib.auth.hashers import make_password, check_password
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils.timezone import now, timedelta

from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q

logger = logging.getLogger()
User = get_user_model()
Group = User.groups.rel.model


class MyManager(models.Manager):
    '''
    QuerySet所有方法取数据时, 自动加上过滤条件
    示例: MyManager(或Q查询1, 反Q查询2, 字段1=xx, 字段2__外键字段=xx)
    多个参数之间为逻辑与, 需要逻辑或逻辑非时, 使用Q(_connector='OR', ...) ~Q(...)
    '''

    def __init__(self, *qs_Q_filter, **qs_field_filter):
        super().__init__()
        self.qs_Q_filter = [q for q in qs_Q_filter if isinstance(q, Q)]
        self.qs_field_filter = qs_field_filter

    def get_queryset(self):
        logger.debug(self.qs_field_filter)
        return super().get_queryset().filter(
            *self.qs_Q_filter,  # Q查询
            **self.qs_field_filter  # 字段过滤
        )


class MyModel(models.Model):
    '''增加自定义qs管理器'''
    objects = models.Manager()  # 保持兼容
    qs = MyManager(enable=True)  # django会把首个作为默认Manager进行替换

    class Meta:
        abstract = True


# class UserProfile(AbstractUser):
class UserProfile(User):
    '''
    历史库/程序依赖auth.User, 为兼容所以不生成新用户表,
    所有表关系仍在原用户表, 新表只用于扩展增加新字段
    '''
    user = models.OneToOneField(
        User, parent_link=True, related_name='profile', on_delete=models.CASCADE)
    name = models.CharField(max_length=20, verbose_name='姓名', default='', blank=True, null=True)
    phone = models.CharField(max_length=11, verbose_name='手机', default='', blank=True, null=True)
    ftp_readonly = models.BooleanField(verbose_name='SFTP只读', default=False, help_text='SFTP文件管理时只读')
    weixin = models.CharField(max_length=100, verbose_name='微信ID', default='', blank=True, null=True, help_text="需要时，用于接收由微信公众号发给当前用户的微信告警信息")
    otp = models.BooleanField(verbose_name='OTP验证', default=False, help_text='当前用户登陆时，是否需进行T-otp验证')
    show_otp = models.BooleanField(verbose_name='显示otp二维码', default=True, help_text='新用户首次登陆，或者手机丢失了otp信息，需重新扫码用于生成otp验证，验证成功后不再提供显示')
    userdays = models.SmallIntegerField(u"账号有效天数", default=365, help_text="用户有效期天数，过期后自动停用")
    usertime = models.DateTimeField('上次过期', default=now, help_text="用于计算/保存用户过期日期")
    pwdtime = models.DateTimeField('上次改密码', default=now, help_text="用于计算密码过期日期")
    pwddays = models.SmallIntegerField(u"密码有效天数", default=90, help_text="密码过期天数，过期后登陆需修改密码")
    # qs = MyManager(is_active=True)

    class Meta:
        verbose_name = '网站用户'
        # auto_created = True

    def __str__(self):
        return f'{self.user.username}({self.name})'

    def chk_userdays(self):
        # 用户有效期检查，若过期则自动禁用用户
        # user = self.user
        today = now().date()
        date = self.usertime.date()
        overday = date + timedelta(days=self.userdays)
        # import ipdb;ipdb.set_trace()
        if today > overday:
            self.is_active = False
            self.usertime = now()
            self.save()
            return 1
        else:
            return 0

    def chk_pwd_expired(self):
        # 密码过期检查，若过期则每次登陆跳转到修改密码页面
        today = now().date()
        date = self.pwdtime.date()
        overday = date + timedelta(days=self.pwddays)
        if today > overday:
            return 1
        else:
            return 0

    @staticmethod
    def new(user):
        # 存在auth.user数据, 但不存在profile数据时
        kwargs = user.__dict__.copy()
        for k in user.__dict__:
            if k.startswith('_'):
                kwargs.pop(k)
        # kwargs.pop('_state', None)
        # kwargs.pop('_password', None)
        kwargs.pop('backend', None)
        # import ipdb;ipdb.set_trace()
        p = UserProfile(**kwargs)
        p.save()
        totpdevice = user.totpdevice_set.filter(confirmed=1)
        if not totpdevice:
            # 创建t-otp device，使user支持t-otp验证
            t = TOTPDevice(name='自动创建', user=user)
            t.save()

        return p


def rewrite_user(cls=User):
    '''
    user反查扩展数据不存在时, 自动创建
    '''
    profile_query = UserProfile.user.field.related_query_name()
    User.profile_bak = getattr(User, profile_query)  # 因profile_query原名函数将替换

    @property
    def userprofile(self):
        # import ipdb; ipdb.set_trace()
        try:
            return self.profile_bak
        except Exception:
            return UserProfile.new(self)

    setattr(User, profile_query, userprofile)
    # print(cls, '已重写profile反查', profile_query)


rewrite_user()
