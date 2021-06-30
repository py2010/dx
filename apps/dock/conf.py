# -*- coding: utf-8 -*-
import os


DOCKER_CERT_PATH = '/etc/docker'  # docker客户端(cmdb本机)TSL证书目录，默认在cmdb运行用户的~/.docker/目录
# 三个TSL证书文件名，必需为默认的cert.pem、ca.pem、key.pem，如果不默认，需在cmdb程序中指定
if not os.path.isdir(DOCKER_CERT_PATH) or not os.path.exists(os.path.join(DOCKER_CERT_PATH, 'cert.pem')):
    DOCKER_CERT_PATH = None

YmlDir = '/data/app/yml/'  # yml文件根目录
ImgDir = '/data/app/img/'  # 镜像包文件根目录

DOCKER_LOGS_LINES = 500  # 查看容器日志，显示最后XX行，默认为'all'所有日志
