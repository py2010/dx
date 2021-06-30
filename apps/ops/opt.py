# coding=utf-8

from __future__ import unicode_literals

import base64
from Crypto.Cipher import AES
import magic
import mimetypes
from django.conf import settings
from django.db import models

AES_KEY = getattr(settings, 'AES_KEY', '0123456789')


def get_mime(file=None, buf=None):
    # 获取MIME类型
    mime = None
    if file:
        try:
            # 读取本地文件头来判断
            mime = magic.from_file(file, mime=True)
        except Exception as e:
            print(str(e))
            # 通过文件后缀名来判断
            mime = mimetypes.guess_type(file)[0]
    elif buf:
        # 读取本地文件头来判断
        mime = magic.from_buffer(buf, mime=True)

    return mime if mime else 'application/empty'


class Aes:
    '''AES加密 pycrypto==2.6.1'''
    BLOCK_SIZE = 16  # AES.block_size
    PADDING = chr(20)  # 'ý' #未满16*n时，补齐字符chr(253)

    def __init__(self, key=AES_KEY):
        aes_key = (key * 6)[:16]
        self.cipher = AES.new(aes_key.encode(), mode=AES.MODE_ECB)

    def pad(self, s):
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * self.PADDING

    def Encode(self, text):
        p = self.pad(text).encode()
        a = self.cipher.encrypt(p)
        return base64.b64encode(a).decode()

    def Decode(self, text):
        try:
            b = base64.b64decode(text)
            return self.cipher.decrypt(b).decode().rstrip(self.PADDING)
        except Exception as e:
            print('Error: AES密码解密失败！！', e)
            return ''


class EncryptField(models.CharField):
    '''
    加密字段
    password = EncryptField("密码", max_length=80, write_only=True, default='')
    '''
    # DISPLAY_VALUE = '****'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.write_only = kwargs.pop('write_only', False)  # 禁读

    # def value_from_object(self, obj):
    #     '''obj.password - 解密'''
    #     value = getattr(obj, self.attname)
    #     return aes.Decode(value)

    def from_db_value(self, value, *args, **kwargs):
        '''从数据库取数据 - 解密'''
        if self.write_only:
            # return self.DISPLAY_VALUE
            return None  # 禁读
        return aes.Decode(value)

    def get_prep_value(self, value):
        '''保存到数据库 - 加密'''
        return aes.Encode(str(value)) if value else ''

    def save_form_data(self, instance, data):
        '''
        禁读或forms.PasswordInput, 未修改时data为空, 不保存字段值入库,
        比如提交表单只改了其它字段, 未修改密码, 则表数据原存储的密码保持不变.
        '''
        if data:
            setattr(instance, self.name, data)

    # def formfield(self, **kwargs):
    #     return super().formfield(**kwargs)


aes = Aes()
