#!/bin/bash

project=dx
# python=/kf/python/venv/$project/bin/python3
log_level=${LOG_LEVEL:-DEBUG}

port=${DJANGO_PORT:-8066}  #默认端口
host=[::]  # 可支持ip6的监听地址

if [ "$IPV6" == "0" ];then
    # 只监听IPv4地址
    host=0.0.0.0
fi


# 选择python路径
pys=($python $PYTHON `which python3` `which python`)
# echo ${pys[*]}
for python in ${pys[*]}; do
    # echo $python
    if [ -x ${python} ]; then
        echo 使用python路径: $python
        break
    fi
    # echo 路径不存在或无执行权限: $python
done


# 日志级别
if [ -z $log_level ]; then
    log_level=DEBUG
fi

f=`basename $0` #当前文件名d
p="$( cd "$( dirname "$0"  )" && pwd  )" #脚本目录c路径

base=`dirname "$p"` #项目根目录

cd $base #项目根目录
pwd

run() {
    #用于生产环境启动停止django网站进程
    arg1=$1
    # echo $arg1
    # alpine容器shell(busybox)中 ps命令PID在第一列, 为统一, 第一列不能为user
    proc="$(ps ax | grep -Ei '(c/d runworker|uvicorn|runserver[[:space:]].*:'$port'|proxy_sshd|'$python' -u manage.py)' | grep -v 'grep')"
    # echo -e "$proc"

    if [ "$arg1" == "stop" ];then
        ifs=$IFS; IFS="\n";
        if [ -z "$2" ];then
            echo "Stopping....."
            echo -e "$proc" | grep -Ei '('$port'|[[:space:]]proxy_sshd)' | awk '{print $1}' | xargs kill -9 2>/dev/null
        else
            echo "结束端口 <$2> 进程..."
            netstat -tnlp|grep :$2|awk '{print $7}' |awk -F '/' '{print $1}' | xargs kill -9 2>/dev/null
            #${s%/*}
        fi
        IFS=$ifs
    elif [ "$arg1" == "start" ];then
        pid=`echo -e "$proc" | grep $port | awk '{print $2}'`
        if [ -z "$pid" ];then

            nohup $p/$f proxy_sshd >& logs/sshd.log &
            # echo \
            nohup $python -u /usr/local/bin/gunicorn \
                --workers=4 \
                --log-level $log_level \
                -b $host:$port \
                --threads 40 \
                --max-requests 4096 \
                --max-requests-jitter 512 \
                --forwarded-allow-ips "*" \
                -k uvicorn.workers.UvicornWorker \
                $project.asgi:application \
                >& logs/web.log &

            echo "Starting....."
            sleep 1
            ps aux | grep -Ei '(c/d runworker|uvicorn|runserver 0.0.0.0:'$port'|c/d cert|'$python' -u manage.py)' | grep -v 'grep'
        else
            echo -e "$proc"
            echo "已有相关进程运行中，忽略处理"
        fi

    elif [ "$arg1" == "state" ];then
        if [ -z "$proc" ];then
            echo "No running.."
        else
            echo -e "$proc"
        fi

    fi
}


arg1=$1
arg2=$2


if ([ "$arg1" -gt 0 ] 2>/dev/null && [ -z "$arg2" ]) ;then
    arg2=$host':'${arg1}
    arg1='runserver --noreload'
    # $p/$f proxy_sshd >& sshd.log &

elif [ "$arg1" == "ssh" ];then
    arg1='proxy_sshd'

elif [ "$arg1" == "m1" ];then
    arg1='makemigrations'
elif [ "$arg1" == "m2" ];then
	arg1='migrate'

elif [ "$arg1" == "u" ];then
    arg1='createsuperuser'

elif [ "$arg1" == "h" ];then
    arg1='help'
elif [ "$arg1" == "s" ];then
    arg1='shell'

elif [ -z "$arg1" ];then
    arg1='runserver'
    arg2=$host':'$port

    # echo $arg2 444444444

    # $p/$f proxy_sshd &
    # trap 'onCtrlC' SIGHUP SIGINT SIGQUIT SIGKILL
    # function onCtrlC () {
    #     echo -e '\n退出ssh服务端...'
    #     pkill -f proxy_sshd
    # }

elif [ "$arg1" == "stop" ];then
    run $arg1 $2
    exit
elif [ "$arg1" == "start" ];then
    run $arg1
    exit
elif [ "$arg1" == "state" ];then
    run $arg1
    exit
elif [ "$arg1" == "restart" ];then
    run "stop"
    sleep 1
    run "start"
    exit


fi


#echo $arg1
#echo $arg2

# 不fork子进程, 解决py子进程被kill后, 终端回车不换行问题
exec $python -u manage.py $arg1 $arg2 $3 $4



