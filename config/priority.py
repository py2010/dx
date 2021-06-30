# -*- coding: utf-8 -*-
# exia@qq.com
import os
import sys
import json
from django.conf import settings

'''
用于设置各apps.conf配置的优先级, 未指定则使用默认优先级.
使各app业务程序只管从各自的conf.py取配置, 比如无需关注优先从环境变量取.
优先级由conf.py控制.

使用环境变量中的配置时, 要求配置名称(key/attr)必须全为大写, 否则忽略环境变量,
由于环境变量只支持字段串值, 会自动根据需要转为(str, int, float, bool)类型,
'''

# 默认优先级: 环境变量 > project.setting / YML > app.conf
DEFAULT_PRIORITY = [
    'env',  # 环境变量
    'settings',  # django.conf.settings / YML
    'conf',  # app.conf
]

# 环境变量值, 支持类型. (不支持的类型, env_convert=True时即使环境变量优先, 也会被忽略)
# 如果要增加其它类型支持, 请自定义EnvConvert对应函数功能, 比如dict为EnvConvert.dict()
ENV_DATA_TYPES = [
    str, int, float, bool,
    # list,
    # dict,
]


class EnvConvert:
    '''环境变量值只支持字段串, 自动转换类型'''

    types = ENV_DATA_TYPES

    def __call__(self, env_data, ref_data):
        data_type = type(ref_data)  # 参考值类型
        if data_type not in self.types:
            # 不在ENV_DATA_TYPES列表, 比如dict, py对象等..., 直接使用参考值, 高优先级的环境变量中的配置会被忽略!!
            return ref_data
        func = getattr(self, data_type.__name__, data_type)
        try:
            return func(env_data)  # 转换
        except Exception:
            return env_data

    def bool(self, env_data):
        if env_data.lower() in ('0', 'false', 'none', 'null'):
            return False
        return bool(env_data)

    def dict(self, env_data):
        # 环境变量字典类型的值, 格式为json.dumps处理后的格式
        return json.loads(env_data)

    # def list(self, env_data):
    #     # 环境变量列表类型的值, 格式为"值1,值2,值3..."
    #     return env_data.split(',')

    list = dict
    tuple = list


convert = EnvConvert()


def set_conf(conf_module_name, priority=DEFAULT_PRIORITY, env_convert=True):
    '''
    用于各app.conf根据配置优先级, 设置使用对应配置值
    参数说明:
        conf_module_name: app.conf模块名__name__,
        priority: 优先级/类型列表,
        env_convert: 环境变量值-是否自动转换. (字符串转为 ENV_DATA_TYPES 中的类型)
                 因环境变量的值只支持字符串, 当优先使用环境变量时, 是否自动转换为正确类型
    使用方法:
        # app/conf.py
        from config import priority
        priority.set_conf(__name__, priority=['env', 'conf'])
        ...配置项
        ...配置项
    '''
    conf = sys.modules[conf_module_name]

    class ConfValue:
        attr = None  # 配置名称
        kind = None  # 配置类型
        value = None  # 配置值
        error = None  # 取值出错
        has_val = False  # 是否有配置值

        def __repr__(self):
            return f'{self.attr} <kind: {self.kind}, value: {self.value}>'

        def __bool__(self):
            return self.has_val

        def __setattr__(self, attr, val):
            if attr == 'value':
                # 因配置值本身有可能为(False, None...), 所以使用has_val表示__bool__
                self.has_val = True  # 有配置值
            return super().__setattr__(attr, val)

        def __init__(self, attr=None, kind=None):
            self.attr = attr
            if kind and attr:
                self.kind = kind
                try:
                    getattr(self, f'from_{kind}')()
                except Exception as e:
                    self.error = e

        def from_env(self):
            if self.attr.isupper():
                self.value = os.environ[self.attr]
            raise KeyError  # 含小写字母则忽略环境变量

        def from_settings(self):
            self.value = getattr(settings, self.attr)

        def from_conf(self):
            self.value = getattr(conf, self.attr)

    class ConfObject:
        '''
        conf.py文件模块转py对象, 以支持__getattribute__, 根据优先级顺序, 进行取值.
        比如: 取 app.conf.attr 配置时, 优先从环境变量取值,
        其次取 settings.attr, 最后取 app.conf.attr
        只有高优先级的配置不存在时, 低优先级的才生效.
        '''

        def __repr__(self):
            return conf.__repr__()

        __str__ = __repr__

        def __getattribute__(self, attr):
            # print(attr, 1111111)
            if attr.startswith('__'):
                return getattr(conf, attr)
            result = ConfValue(attr)
            for kind in priority:
                val = ConfValue(attr, kind)
                if val:
                    if result:
                        # env_convert为True, 上次取得的环境变量字符串值, 需还原类型.
                        return convert(result.value, val.value)

                    else:
                        if env_convert and kind == 'env':
                            # 环境变量值都是字符串, 需还原类型, 会继续循环取参考值.
                            result.kind = kind
                            result.value = val.value
                        else:
                            # 按优先级, 成功取得配置值
                            # print(val.value, 2222222)
                            return val.value
                else:
                    if not result:
                        result.error = val.error
            if result:
                # 比如有环境变量, 但未取到参考值, 最终结果为环境变量值(字符串, 未转换类型)
                return result.value
            else:
                raise result.error

    sys.modules[conf_module_name] = ConfObject()


# def __getattr__(attr):
#     '''
#     conf.attr 不存在时, 从环境变量取值,
#     py版本最低要求python3.7 (PEP 562)
#     不支持__getattribute__, 也就是不支持环境变量优先于 conf.attr.
#     '''
#     # print(attr, 111111)
#     try:
#         return os.environ[attr.upper()]
#     except KeyError:
#         raise AttributeError
