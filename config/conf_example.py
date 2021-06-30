from config import priority

'''
根据配置优先级, 设置各配置值.
未指定优先级时, 默认优先级:
环境变量 > project.setting / YML > app.conf

示例:
priority.set_conf(__name__, priority=['env', 'conf'], env_convert=False)
'''
priority.set_conf(__name__)


PATH = 'test'
PWD = {1: 1}  # 当env_convert=True, 环境变量不支持配置字典, 虽优先但会忽略
STATIC_URL = 333

'''
In [1]: from config import conf_example

In [2]: conf_example.PATH
Out[2]: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/bin'

In [3]: conf_example.PWD
Out[3]: {1: 1}

In [4]: conf_example.STATIC_URL
Out[4]: '/static/'

'''


# from config import confile
# yml = confile.YML('docker-compose.yml')  # ***/project/docker-compose.yml
# locals().update(yml)  # 将YML配置加载到当前conf
# print(services, 111)

# yml._deep_update_({'services': {'test': {1: 2}}})
# print(yml.services, 222)

# # DEBUG
# import ipdb; ipdb.set_trace()  # breakpoint 7e9cd84c //

