# Generated by Django 2.2 on 2020-12-30 14:26

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='profile', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('name', models.CharField(blank=True, default='', max_length=20, null=True, verbose_name='姓名')),
                ('phone', models.CharField(blank=True, default='', max_length=11, null=True, verbose_name='手机')),
                ('ftp_readonly', models.BooleanField(default=False, help_text='SFTP文件管理时只读', verbose_name='SFTP只读')),
                ('weixin', models.CharField(blank=True, default='', help_text='需要时，用于接收由微信公众号发给当前用户的微信告警信息', max_length=100, null=True, verbose_name='微信ID')),
                ('otp', models.BooleanField(default=False, help_text='当前用户登陆时，是否需进行T-otp验证', verbose_name='OTP验证')),
                ('show_otp', models.BooleanField(default=True, help_text='新用户首次登陆，或者手机丢失了otp信息，需重新扫码用于生成otp验证，验证成功后不再提供显示', verbose_name='显示otp二维码')),
                ('userdays', models.SmallIntegerField(default=365, help_text='用户有效期天数，过期后自动停用', verbose_name='账号有效天数')),
                ('usertime', models.DateTimeField(default=django.utils.timezone.now, help_text='用于计算/保存用户过期日期', verbose_name='上次过期')),
                ('pwdtime', models.DateTimeField(default=django.utils.timezone.now, help_text='用于计算密码过期日期', verbose_name='上次改密码')),
                ('pwddays', models.SmallIntegerField(default=90, help_text='密码过期天数，过期后登陆需修改密码', verbose_name='密码有效天数')),
            ],
            options={
                'verbose_name': '网站用户',
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
