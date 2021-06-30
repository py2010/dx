# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect

from django.contrib import auth
from django_otp import match_token
from django.contrib.auth.models import User
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django_otp.plugins.otp_totp.models import TOTPDevice


def index(request):
    # import ipdb;ipdb.set_trace()
    print('HTTP_USER_AGENT', request.META.get('HTTP_USER_AGENT'))
    # import os
    # print(os.getpid(), os.getppid(), '..........')
    # raise
    # import traceback
    # traceback.print_stack()
    return render(request, 'base/index.html')


def login(request):
    # import ipdb;ipdb.set_trace()
    # otp_url = '/otp?%s' % request.META.get('QUERY_STRING', '')
    r_url = request.GET.get('next', '/')
    if request.user.is_authenticated:
        if r_url.startswith('/admin') and not request.user.is_staff:
            # 登陆用户无权限访问后台
            r_url = '/'
        return HttpResponseRedirect(r_url)
    # elif 'login_user_id' in request.session:
    #     # 已登陆但未进行otp验证
    #     return HttpResponseRedirect(otp_url)

    html = 'base/otp.html' if 'login_user_id' in request.session else 'base/login.html'

    if 'login_user_id' in request.session:
        # otp页显示
        uid = request.session['login_user_id']
        try:
            user = User.objects.get(id=uid)
        except Exception:
            print('Error: user_id (%d) del ??????!!!!!!!!' % uid)
            del request.session['login_user_id']
            return HttpResponseRedirect('/login')

        userprofile = user.profile
        if userprofile.show_otp:
            # 首次otp验证或人工设置，显示otp二维码
            show_otp = 1
            try:
                totpdevice = user.totpdevice_set.filter(confirmed=1).first()
                if not totpdevice:
                    # 创建t-otp device，使user支持t-otp验证
                    totpdevice = TOTPDevice(name='自动创建', user=user)
                    totpdevice.save()

                otp_data = totpdevice.config_url  # 二维码对应实际数据otpauth://totp/user?digits=
                # print(otp_data, 444)
                # 提取secret内容，用于Google Authentication
                # import urlparse
                from urllib import parse
                result = parse.urlparse(otp_data)
                secret = parse.parse_qs(result.query).get('secret', ['Error!'])
                # 开始生成二维码
                import qrcode
                from io import BytesIO
                import base64
                mio = BytesIO()  # 用于替代磁盘临时文件，在内存中保存二维码图片
                qr = qrcode.QRCode(version=1, box_size=4, border=1,)
                qr.add_data(otp_data)
                qr.make()
                img = qr.make_image()
                img.save(mio)
                base64_data = base64.b64encode(mio.getvalue()).decode()
                # print(base64_data)
                if not base64_data:
                    error_msg = "(用户 %s) T-otp二维码图片生成失败" % user
                # return render(request, html, locals())

            except IndexError as e:
                # 正常情况下，totpdevice在userprofile创建后自动生成，无需人工添加
                print(e, 77777)
                raise
                error_msg = "Error: 用户 %s otp设备获取失败，请联系管理员登陆后台查看是否有当前用户对应的“TOTP device”，或者device被禁用" % user

    if request.method == "POST":
        totp = request.POST.get("totp")
        u = request.POST.get("username")
        p = request.POST.get("password")

        try:
            if totp:
                # otp验证
                try:
                    # locals()已有变量userprofile、user
                    userprofile
                except Exception:
                    # 非法构建表单进行提交
                    return HttpResponse('', status=404)

                if match_token(user, totp):
                    if userprofile.show_otp:
                        # 首次otp验证通过后，以后登陆将不再显示二维码
                        userprofile.show_otp = 0
                        userprofile.save()
                    # 验证通过
                else:
                    error_msg = "(用户 %s) T-otp验证码失败，请等待otp《数字更新》后，重新尝试，<br/>若仍然失败则可能为网站时间和用户手机时间不一致导致，请联系管理员确认CMDB服务器时间是否为标准时间(%s)" % (user, datetime.now())
                    raise

            else:
                # 用户密码验证
                user = auth.authenticate(username=u, password=p)
                if user:
                    userprofile = user.profile
                    if userprofile.chk_userdays():
                        error_msg = "账号过期，已停用，请联系管理员处理"
                        raise
                    else:
                        request.session['login_user_id'] = user.id
                        if userprofile.otp:
                            return HttpResponseRedirect(request.get_full_path())  # 重新打开页面，用于判断是否显示二维码
                        # 管理员已设置当前用户无需进行otp验证
                    # 验证通过

                else:
                    error_msg = "用户名/密码错误，或用户已停用"
                    raise

            # 用户登陆
            auth.login(request, user)
            # 检查密码过期
            if userprofile.chk_pwd_expired():
                r_url = '/password_change?next=%s' % r_url
            return HttpResponseRedirect(r_url)
        except Exception as e:
            print(e)
            pass

    return render(request, html, locals())


def logout(request):
    '''
    退出session和token-cookie
    注意，由于token机制使其在有效期内都可用，无法中途控制token失效，
    所以当前只是删除token在cookie中的键值，非前后端分离的页面已登出，
    但rest_framework API接口的token在有效期内仍然有效，除非改造JWT规范，
    保存token认证信息到服务端，这就相当于改成session的功能。
    '''
    auth.logout(request)  # Session登出
    # import ipdb;ipdb.set_trace()
    response = HttpResponseRedirect("/login")
    # token_cookie_key = settings.JWT_AUTH.get('JWT_AUTH_COOKIE', '')
    # response.delete_cookie(token_cookie_key)  # token-cookie登出
    return response


@login_required()
def password_change(request):
    if request.method == "POST":
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        password3 = request.POST.get("password3")
        if password2 != password3:
            error_msg = "二次密码输入不一致"
        else:
            user = request.user
            if user.check_password(password):
                user.set_password(password2)
                user.save()
                userprofile = user.profile
                userprofile.pwdtime = datetime.now()
                userprofile.save()
                ok_msg = "密码修改成功"
                # return HttpResponseRedirect(r_url)
            else:
                error_msg = "旧密码错误"

    return render(request, 'base/password.html', locals())


@csrf_exempt
def test(request):
    # /test
    # import web_pdb; web_pdb.set_trace()
    if request.GET.get('pwd') == 'xyf.1234':
        import ipdb
        ipdb.set_trace()
    print(request.META)
    # print(request.body)
    files = request.FILES.getlist('imagefile')
    print(files)
    # import ipdb;ipdb.set_trace()
    return HttpResponse('')
