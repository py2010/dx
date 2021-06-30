
'''
django配置管理与工具

1. confile, 支持将各配置文件转py对象, 支持conf.key方式递归取值
2. 使简化各app的配置读取, 只管从自身app.conf.py中读取配置,
至于配置是使用环境变量/settings, 优先级相关设置等, 都在conf中简单定义即可.
'''
