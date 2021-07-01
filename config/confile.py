# -*- coding: utf-8 -*-
# https://gitee.com/py2010
import os
import sys
import json

'''
读取各种类型的配置文件,
转换对象, 便捷使用各配置值
支持python2和3
'''


class MyDict(dict):
    '''
    使支持 mydict.key 取值/赋值, 且支持递归
    示例:
        d = {'a': {'aa': 8}, 'b': [1, 2]}
        d = MyDict(d)
        print(d.a.aa)  # 取值
        d.a.aa = 1000  # 赋值
        print(d, 111111)
        d._deep_update_({'a': {'ab': 3}})
        print(d, 222222)

    如果key名称和dict内置属性相同, 比如dict['keys'],
    只能dict[key]迭代取值, 因为dict.keys为内置方法.
    赋值不受dict内置类属性影响, 可支持点赋值.
    '''

    def __getattr__(self, attr):
        if attr in self:
            # mydict.key
            val = self[attr]
            if isinstance(val, dict):
                # 使支持递归, mydict.key.子key
                val = self[attr] = MyDict(val)
            return val
        # else:
        #     raise KeyError(attr)
        # AttributeError
        return super(MyDict, self).__getattribute__(attr)

    def __setattr__(self, attr, val):
        # print(attr, val, 444444)
        if hasattr(self, attr):
            return super(MyDict, self).__setattr__(attr, val)
        else:
            self[attr] = val

    def _deep_update_(self, d={}):
        '''
        (dict.update不支持"深拷贝"), 用于实现深层更新(递归更新多层字典)
        主要用于含默认配置且为多层字典时,
        default_dict._deep_update_(conf_dict)
        '''
        for k, v in d.items():
            if isinstance(v, dict):
                try:
                    getattr(self, k)._deep_update_(v)
                    continue
                except AttributeError:
                    pass
            self[k] = v

    def copy(self):
        '''重写dict.copy, 浅拷贝后的dict转MyDict类型'''
        new_dict = super(MyDict, self).copy()
        return MyDict(new_dict)


class Conf(MyDict):
    SETATTR = True  # 是否开启.赋值
    NOERROR = True  # 配置项不存在时, True表示不报错

    def __getattr__(self, attr):
        '''
        NOERROR = True, 配置键值不存在时, 不报错, 返回None
        '''
        try:
            return super(self.__class__, self).__getattr__(attr)
        except (KeyError, AttributeError) as e:
            if self.NOERROR:
                return  # 不存在的键返回None值
            raise e

    def __setattr__(self, attr, val):
        if attr != 'SETATTR' and self.SETATTR:
            self[attr] = val
            return
        return super(self.__class__, self).__setattr__(attr, val)


class File(object):
    '''
    读取配置转py字典, 使支持 dict.key.子key 取值
    default: 默认配置, 支持多层字典结构默认值
    set_attr: 是否开启.赋值, 开启后支持递归.赋值
    '''
    _default_conf_file_ = ''

    def __new__(cls, conf_file='', default={}, set_attr=False, no_error=True, *args, **kwargs):

        conf_file = cls._check_(conf_file)
        data = cls._python_(conf_file)

        # conf = super(cls.__bases__[0], cls).__new__(data, *args, **kwargs)
        conf = Conf(default, *args, **kwargs)  # 加载默认配置
        conf._deep_update_(data)  # 递归深拷贝更新配置
        conf.SETATTR = set_attr
        conf.NOERROR = no_error
        return conf

    @classmethod
    def _check_(cls, conf_file=''):
        # 检查/获取配置文件
        if not conf_file:
            # try:
            #     conf_file = sys.argv[1]
            # except Exception:
                conf_file = cls._default_conf_file_
        if not os.path.isfile(conf_file):
            raise IOError('配置文件路径不存在(%s)' % conf_file)

        return conf_file

    @classmethod
    def _python_(cls, conf_file):
        # 读取文件转python字典
        raise NotImplementedError('请根据配置文件类型, 在子类实现功能')


class JSON(File):
    _default_conf_file_ = 'conf.json'

    @classmethod
    def _python_(cls, conf_file):
        # 读取文本转python字典
        with open(conf_file) as f:
            return json.loads(f.read())


class YML(File):
    '''
    读取yml配置转py对象, 使支持 dict.key.子key 取值
    '''
    _default_conf_file_ = 'conf.yml'

    @classmethod
    def _python_(cls, conf_file):
        # 读取文本转python字典
        with open(conf_file) as f:
            import yaml
            return yaml.safe_load(f.read())


# data = YML('docker-compose.yml')
# data.services.test = {1: 1}
# print(data.services, 111)
# data._deep_update_({'services': {'test': {1: 2}}})
# print(data.services, 222)
# import ipdb; ipdb.set_trace()


class INI(File):
    '''
    读取ini/文件配置, 二层字典结构, 转py对象
    自动去除配置值前后所带引号/空格
    '''
    _default_conf_file_ = 'conf.ini'

    @classmethod
    def _python_(cls, conf_file):
        # 读取文本转python字典
        if sys.version < '3.0':
            import ConfigParser as configparser
        else:
            import configparser

        conf = configparser.ConfigParser()
        conf.read(conf_file)
        data = {}
        for section, option in conf._sections.items():
            if option:
                data[section] = {}
                for k, v in option.items():
                    if k != '__name__':
                        # 去掉值前后空格/引号 (引号内带空格有效)
                        data[section][k] = v.strip(' ').strip('"\'')
        return data

