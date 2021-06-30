# Generated by Django 2.2 on 2019-09-18 16:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DockerHost',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='标识名称')),
                ('ip', models.GenericIPAddressField(verbose_name='宿主机IP')),
                ('port', models.IntegerField(default=2375, verbose_name='Docker端口')),
                ('tls', models.BooleanField(default=True, help_text='Docker-API不会进行安全验证，任意接入的客户端都能进行所有操作<br/>为安全需配置TLS，客户端使用证书访问API接口', verbose_name='TLS')),
                ('text', models.TextField(blank=True, default='', verbose_name='备注信息')),
            ],
            options={
                'verbose_name': '容器宿主机',
                'permissions': (('images_manage', '镜像管理'), ('containers_manage', '容器管理'), ('net_manage', '容器管理')),
                'unique_together': {('ip', 'port')},
            },
        ),
        migrations.CreateModel(
            name='DockerYmlGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='类名')),
                ('path', models.CharField(max_length=100, unique=True, verbose_name='yml目录')),
                ('desc', models.CharField(blank=True, max_length=100, verbose_name='描述')),
            ],
            options={
                'verbose_name': '容器YML分组',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DockerYml',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='标识名称')),
                ('file', models.CharField(max_length=100, verbose_name='yml文件名')),
                ('text', models.TextField(blank=True, default='', verbose_name='备注')),
                ('state', models.BooleanField(default=True, verbose_name='启用')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dock.DockerYmlGroup', verbose_name='容器YML分组')),
            ],
            options={
                'verbose_name': '容器YML',
                'ordering': ['name'],
                'unique_together': {('group', 'file')},
            },
        ),
        migrations.CreateModel(
            name='DockerImageFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='镜像名')),
                ('ver', models.CharField(blank=True, max_length=100, null=True, verbose_name='版本')),
                ('file', models.CharField(max_length=100, unique=True, verbose_name='文件名')),
                ('size', models.BigIntegerField(default=0, verbose_name='文件大小')),
                ('createtime', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('upload', models.BooleanField(default=False, verbose_name='手工上传')),
                ('text', models.TextField(blank=True, default='', verbose_name='备注')),
                ('dockerhost', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dock.DockerHost', verbose_name='来源/宿主机')),
            ],
            options={
                'verbose_name': '容器镜像包',
                'ordering': ['name'],
                'unique_together': {('name', 'ver', 'dockerhost')},
            },
        ),
        migrations.CreateModel(
            name='DockerCompose',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='标识名称')),
                ('scale', models.CharField(blank=True, default='', help_text='scale参数，默认每个服务只启动1个容器，多个时比如设置web=2,worker=3                             <br/>需启动多个容器的服务，不能配置IP、容器名等唯一项，以免冲突', max_length=100, verbose_name='数量参数')),
                ('createtime', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('changetime', models.DateTimeField(auto_now=True, null=True, verbose_name='修改时间')),
                ('text', models.CharField(blank=True, default='', max_length=300, verbose_name='备注')),
                ('dockerhost', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dock.DockerHost', verbose_name='容器宿主机')),
                ('yml', models.ForeignKey(limit_choices_to={'state': True}, on_delete=django.db.models.deletion.CASCADE, to='dock.DockerYml', verbose_name='容器YML')),
            ],
            options={
                'verbose_name': '容器编排',
                'ordering': ['name'],
                'unique_together': {('yml', 'dockerhost')},
            },
        ),
    ]
