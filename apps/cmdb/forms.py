# coding=utf-8
from django import forms

from . import models
# from django.forms.widgets import CheckboxSelectMultiple


class HostForm(forms.ModelForm):
    # 前端主机添加页面

    class Meta:
        model = models.Host
        fields = '__all__'
        # exclude = ("name",)

        widgets = {
            # 'user': CheckboxSelectMultiple,
            # 'usergroup': CheckboxSelectMultiple,
            # 'host_user': CheckboxSelectMultiple,
        }

        # error_messages = {
        #     'model':{
        #         'max_length': ('太短了'),
        #     }
        # }

    # model_field = Meta.model._meta.get_field('user')
    # user = forms.ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=User.objects.filter(is_superuser=False), label=model_field.verbose_name, required=False, help_text=model_field.help_text)


class HostUserForm(forms.ModelForm):

    class Meta:
        model = models.HostUser
        fields = '__all__'
        # exclude = ("id",)

        widgets = {
            'password': forms.PasswordInput(),
        }

        labels = {
        }

        help_texts = {
        }
        error_messages = {

        }


class PermForm(forms.ModelForm):

    class Meta:
        model = models.Perm
        fields = '__all__'
        # exclude = ('web_usergroup',)

        widgets = {
            # 'host': forms.SelectMultiple(attrs={
            #     'class': 'dual_select',
            # }),
        }

        labels = {
        }

        help_texts = {
        }
        error_messages = {

        }

