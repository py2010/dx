#!/bin/bash

# find ./ -name "*.pyc" -exec rm -f {} \;

# 宿主机有挂载项目到容器目录, 便于修改测试
DX_DIR=/opt/dx

if [ "$0" == ${DX_DIR}/docker-entrypoint.sh ];then
    echo 使用宿主机挂载目录: $DX_DIR
    cd $DX_DIR
    DEV=1

elif [ -x ${DX_DIR}/docker-entrypoint.sh ]; then
    exec ${DX_DIR}/docker-entrypoint.sh

fi


# 启动REDIS
nohup redis-server /etc/redis.conf >& logs/redis.log &
sleep 1

# 启动Django网站

if [ $DEV ]; then
    c/d ssh &
    c/d &  # runserver 开发测试
else
    # 生产运行
    c/d start
fi

sleep inf
