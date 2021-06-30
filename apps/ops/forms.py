# coding=utf-8
from django import forms
import sys

from . import models


class UserProfileForm(forms.ModelForm):
    # 未设required值, fields_for_model只从model字段中取, 覆盖widget实例.is_required
    pwd = forms.CharField(label='密码', required=False, strip=True,
                          widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'})
                          )

    class Meta:
        model = models.UserProfile
        fields = [
            'username', 'pwd', 'name',
            'is_superuser', 'is_active', 'groups', 'user_permissions',
            'email', 'phone', 'weixin', 'otp', 'show_otp',
            'userdays', 'pwddays',
        ]

        widgets = {
            # 'password': forms.PasswordInput,
        }

        labels = {
        }

        help_texts = {
        }
        error_messages = {
            # 'username': {'unique': '3333333'}
        }

    # def clean(self):
    #     return self.cleaned_data

    # def clean_pwd(self):
    #     pwd = self.cleaned_data['pwd']
    #     if not pwd:
    #         if not self.instance.id:
    #             raise forms.ValidationError('新用户密码不能为空')
    #     return pwd

    def clean_none_field(self):
        # 将字段None值改为''
        field_name = sys._getframe().f_back.f_locals.get('name')
        return self.cleaned_data.get(field_name) or ''

    clean_name = clean_none_field
    clean_phone = clean_none_field
    clean_weixin = clean_none_field

# import ipdb; ipdb.set_trace()
