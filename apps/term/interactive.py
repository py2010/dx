# -*- coding: utf-8 -*-

from django.utils import timezone
from django.db import connection, OperationalError
from django.conf import settings

try:
    import simplejson as json
except ImportError:
    import json

# import threading
import time
import re
import os
import traceback

import logging
from .conf import REPLAY_PATH

from channels.layers import get_channel_layer

import django_redis
redis = django_redis.get_redis_connection("default")

channel_layer = get_channel_layer()

logger = logging.getLogger('sshd_cmd')


class CustomeFloatEncoder(json.JSONEncoder):

    def encode(self, obj):
        if isinstance(obj, float):
            return format(obj, '.6f')
        return json.JSONEncoder.encode(self, obj)


def savelog(session, times, stdouts, stdins):

    # 终端日志设置结束时间、命令记录
    session.cmds = get_cmds(stdins)  # 命令记录
    session.end_time = timezone.now()
    n = 3
    while n:
        n -= 1
        try:
            try:
                session.save()
                print('session.end_time', session.end_time)
                break
            except Exception as e:
                """
                极端情况，终端连接闲置长久不退，比如10小时，超出mysql连接闲置中断超时时间，
                django已无任何数据库连接，正常情况下重新访问网页程序时django会自动重连，
                但是特殊情况下，尤其是后端程序自动处理，因无任何网址访问重新触发，导致出错。
                django Bug，需connection.close()后，django的程序才会自动重连mysql
                """
                print(e)
                connection.close()
                print('---connection.close()---')
                time.sleep(5)
        except Exception as e:
            print(e)

    # 记录终端回放日志文件
    attrs = {
        "version": 1,
        "width": 90,
        "height": 32,
        "duration": times,
        "command": os.environ.get('SHELL', None),
        'title': None,
        "env": {
            "TERM": os.environ.get('TERM'),
            "SHELL": os.environ.get('SHELL', 'sh')
        },
        'stdout': list(map(lambda frame: [frame[0], frame[1]], stdouts))
    }
    # print(attrs)
    logfile = os.path.join(settings.MEDIA_ROOT, REPLAY_PATH, session.log)
    print(logfile)
    logfile_dir = os.path.dirname(logfile)
    if not os.path.exists(logfile_dir):
        # 目录不存在时创建
        os.makedirs(logfile_dir)
    with open(logfile, "w+") as f:
        try:
            f.write(json.dumps(attrs, ensure_ascii=0, indent=2))
            # f.write(json.dumps(attrs, indent=2))
        except Exception:
            traceback.print_exc()
            print(attrs, 77777)

    # print('-----------------------------')
    # print(stdouts)
    # print('-----------------------------')


def get_cmds(stdins=[]):
    # 解析输入输出按键信息，生成用户执行的命令
    # return ''
    # texts = []
    # for stdin in stdins:
    #     text = stdin[1]
    #     if text.startswith('^C\r\n'):
    #         text = '^C'
    #     elif text.startswith('\r\n') or (u'\u001b]0;' in text and u'\u0007' in text):
    #         # u'\u001b]0;' u'\u0007'， 命令输入所在行，开头的类似[root@dev ~]#
    #         text = '\r\n'
    #     # elif len(text) > 888:
    #     #     continue

    #     texts.append(text)

    # 开始将texts按元素'\r\n'、'^C'间隔，进行分割成多个子列表
    cmds = []
    cmd = []
    for stdin in stdins:
        cmd.append(stdin)
        if stdin == '\r\n':
            # 结尾，分隔命令
            cmds.append(cmd)
            cmd = []
        elif stdin == '^C':
            # ctrl+c取消的命令
            cmd = []
        else:
            if stdin.startswith(u'\r\u001b[C\u001b[C\u001b[C\u001b[C'):
                # 上下方向键，终端输出为\r“回车”+右移显示原有[root@dev ~]# ，然后+新命令(或短命令+光标清行)
                # 这种情况下，如果新命令和之前老命令开头有部分相同，将导致新命令开头部分缺失
                new_cmd = stdin[1:].replace(u'\x1b[K', '')
                while new_cmd.startswith(u'\x1b[C'):
                    new_cmd = new_cmd[3:]
                new_cmd = replace_xP(new_cmd.replace(u'\u001b[1@', ''))  # 去除上下键产生的 u'\u001b[数字P'、u'\u001b[1@'
                if new_cmd.endswith(u'\x1b[C'):
                    # 当前命令和前一个命令，后面部分相同，终端输出时直接在原有基础上处理显示
                    # cmd[-2]: "vi /data/shell/hf_cup_ftp.sh"
                    # cmd[-1]: "cat /data/shell/hf_cup_ftp.sh"
                    # "\r\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[1@cat\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C"
                    new_cmd = new_cmd[:-3]
                    n = 1  # 后面部分相同字符长度
                    while new_cmd.endswith(u'\x1b[C'):
                        new_cmd = new_cmd[:-3]
                        n += 1  # 每去除一个尾部右移，相同字符位数+1
                    new_cmd = '%s%s' % (new_cmd, cmd[-2][-n:])  # cat + 后面26位相同字符“ /data/shell/hf_cup_ftp.sh”
                cmd = [new_cmd]
            elif stdin.endswith(u'\u001b[C\u001b[C\u001b[C\u001b[C') and u'\r\u001b[C\u001b[C\u001b[C\u001b[C' in stdin:
                # 左右、home、end光标偏移输入
                # u"v /data/shell/hf_cup_ftp.sh\r\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C\u001b[C"
                cmd[-1] = stdin[0]  # 更新stdin
            elif stdin.endswith(u'\x1b[K') or stdin.startswith(u'\b'):
                # u'\b\b\b\b\b\b\b\bll\u001b[K'
                # u'\b\b\b\b\u001b[2Pll'
                # ！cmd = [u'crontab -l', u'\x08e', '\r\n'] 向上键历史命令，当前面有部分内容相同时
                new_cmd = stdin.lstrip(u'\b').replace(u'\x1b[K', '')
                new_cmd = replace_xP(new_cmd)  # 去除上下键产生的 u'\u001b[数字P'
                cmd = [new_cmd]
            else:
                while stdin.startswith(u'\x1b[C') and stdin.endswith(u'\b'):
                    # 在快速按键输入并同时狂按左移键时，终端输出有延时，
                    # 会输出右移+字符+“\b左移”，左右抵消后结果仍一致
                    stdin = stdin[3:-1]
                cmd[-1] = stdin  # 更新stdin

    logger.info('cmds: %s 0000' % cmds)
    logger.info(stdins)

    # import ipdb;ipdb.set_trace()
    cmds_1 = []
    for cmd in cmds:
        # 处理 退格、删除，上下、左右方向键+输入 产生的"\u001b[1@按键字符"，(命令字符串空格左边的输入)
        if cmd == ['\r\n']:
            continue
        cmd_1 = ''  # cmd列表按键转为字符输入
        enum = enumerate(cmd)
        i = 0  # 光标位置
        for (index, key) in enum:
            # index列表索引， key 按键输入，一般为单个字符，因实时websocket人工输入慢而计算机快
            logger.debug('%s %s %s' % (i, index, [key]))
            # i += 1
            if key == u'\x1b[D':
                # 左
                i -= 1  # 光标位置左移一位
            elif key == u'\x1b[C':
                # 右
                i += 1  # 光标位置右移一位
            elif key == u'\x1b[F':
                # End
                i = len(cmd_1)
            elif key == u'\x1b[H':
                # Home
                i = 0
            elif key == u'\x7f':
                # 退格
                cmd_1 = '%s%s' % (cmd_1[:i - 1], cmd_1[i:])  # 删除光标前一个按键字符
                i -= 1
            elif key == u'\x1b[3~':
                # 删除
                cmd_1 = '%s%s' % (cmd_1[:i], cmd_1[i + 1:])  # 删除光标所在位一个按键字符
            elif key.startswith(u'\u001b[1@'):
                # 光标有偏移时，在字符串空格左边，按键输入
                stdin_key = key.replace(u'\u001b[1@', '')
                cmd_1 = '%s%s%s' % (cmd_1[:i], stdin_key, cmd_1[i:])
                i += len(stdin_key)  # 按键字符输入后，光标自动右移一位
            elif key.endswith('\b'):
                # 上下方向键
                # 或光标有偏移时，在字符串最后一个空格分隔的右边，按键输入
                # key: 输入字符+光标后面的字符+\b数个
                stdin_key = del_str(key)
                cmd_1 = '%s%s%s' % (cmd_1[:i], stdin_key, cmd_1[i:])
                i += len(stdin_key)  # 按键字符输入后，光标自动右移一位
            elif key == u'\r\n':
                # 回车执行命令，忽略光标偏移，放到命令末尾
                cmd_1 = '%s%s' % (cmd_1, key)
            else:
                #  正常按键字符输入
                cmd_1 = '%s%s%s' % (cmd_1[:i], key, cmd_1[i:])
                i += len(key)
            # logger.debug('cmd_1: %s ************' % cmd_1)
        cmds_1.append(cmd_1)

    logger.info('cmds_1: %s 1111' % cmds_1)
    return ''.join(cmds_1).strip()


def replace_xP(s):
    p = '(\x1b\[\d+P)'
    new_s = re.sub(re.compile(p, re.S), '', s)  # 去除上下键产生的 u'\u001b[数字P'
    return new_s


def del_str(s):
    # u'd65\x08\x08f65\x08\x08'
    # 上下键、左右键后光标偏移输入
    cs = [c for c in s]
    indexs = [i for (i, j) in enumerate(cs) if j == '\b']  # 存储退格符所在索引位置
    del_indexs = indexs[:]  # 将要删除的元素(含退格本身)所在列表位置
    # print('indexs', indexs)
    for index in indexs:
        del_index = index - 1
        while (del_index in del_indexs):
            # 若元素已被之前退格删，删除前移一位元素。
            del_index -= 1
        del_indexs.append(del_index)
    print('del_indexs', del_indexs)
    cs2 = [j for (i, j) in enumerate(cs) if i not in del_indexs]
    key = ''.join(cs2).strip()
    if not key and s[0] == ' ':
        # 用户输入的就是空格
        key = ' '
    return key

    """
    cs_1 = []  # 去除界面信息、(tab、向下键空)
    # import ipdb;ipdb.set_trace()
    for cmd in cmds:
        # if cmd[-1] == '\r\n':
        add = 1  # 是否将cmd收集到cs_1中
        for i in cmd:
                # print(i, len(i), 555)
            if len(i) > 222:
                    # 命令长度不会很长
                add = 0
                break
            elif len(i) > 20:
                for u in [
                    # 命令行窗口
                    u'\u001b[0m',
                    u'\u001b[01',
                    # vi窗口
                    u'\u001b[m',
                    # u'\u001b[?',
                    u'\u001bP+',
                ]:
                    if u in i:
                            # 命令不含\u001b[0m这类终端界面表格字符
                        add = 0
                        break
            elif i.startswith(u'\u001b['):
                if not (i.startswith(u'\u001b[C') or i.startswith(u'\u001b[1@')):
                    # 除右方向键符及输入，人工输入不会以它开头，包括退格、tab、方向键。
                    add = 0
                    break
        if add:
            cs_1.append(cmd)
    logger.info('cs_1: %s 1111' % cs_1)

    cs_2 = []  # 处理tab键等空效果字符\x07，tab导致了回车分割，重新拼接成一个命令
    for cmd in cs_1:
        try:
            last_cmd = cs_2[-1]  # 上一个cmd
            if last_cmd[-2] == u'\u0007' or cmd[0] == u'\u0007':
                # 上一个cmd 最后按键是tab等空效果字符或当前命令第一个为tab，二个命令合成一个
                last_cmd.pop(-2)  # '\x07'
                last_cmd.pop(-1)  # '\r\n'
                if cmd[-1] != '^C':
                    last_cmd.extend(cmd)
                else:
                    # 当前命令以ctrl+C结尾，放弃，并将和当前命令为同一条的上条不全命令删除
                    cs_2.pop(-1)
            else:
                raise IndexError
        except IndexError:
            if cmd[-1] != '^C':
                cs_2.append(cmd)
        except Exception:
            print(traceback.print_exc())
    logger.info('cs_2: %s 2222' % cs_2)

    cs_3 = []  # 处理方向键退格键等
    for cmd in cs_2:
        c_3 = []
        for i in cmd:
            # 上下左右方向键、Home、End
            if i.strip('\b') == '':
                # 去除左方向键效果，因退格键为“\b光标符”，无输入字符
                continue
            elif i.strip('\u001b[C') == '':
                # 去除右方向键效果
                continue
            elif i.startswith(u'\u001b[C' * 4) and i.endswith(u'\u001b[K'):
                # 上下方向键产生的字符变化，一般为很长字符变化为短字符，
                # 删除很长字符时终端输出不是用大量\b\b光标去删。而是回车从头开始，右移光标[root@dev ~]#末
                c_3 = [i.replace(u'\u001b[C', '')]  # 将之前历史元素清空，复位
                continue
            else:
                c_3.append(i)

        c_3_2 = ''  # 收录列表字符按键
        for i in c_3:
            # 左右移动光标，并且有输入
            pass
            if i.endswith('\b'):
                # 右移光标，然后输入
                # i: 输入字符+光标后面的字符+\b数个
                s = i.rstrip('\b')
                # stdin_str = s[len(i) - len(s):]  # 输入，一般为单个字符，因实时websocket人工输入慢而计算机快
                right_str = s[len(s) - len(i):]  # 光标后面的字符串，长度和\b数len(i)-len(s)一致
                if c_3_2.endswith(right_str):
                    c_3_2 = '%s%s' % (c_3_2[:len(right_str)], s)  # 光标左字符串+输入单字符+光标右字符串
                    continue
                else:
                    print('???????????????????????????????????')
                    print('未知异常，c_3_2: %s, right_str: %s' % (c_3_2, right_str))
                    print('???????????????????????????????????')
            c_3_2 = '%s%s' % (c_3_2, i)

        cmd = [i for i in c_3_2.replace(u'\x08\x1b[K', '\b').strip() if i != u'\u0007']  # 使元素全为单字符，去掉退格光标指示符、tab产生的响铃字符，便于退格键处理
        # print(cmd, 44444444)
        indexs = [i for (i, j) in enumerate(cmd) if j == '\b']  # 存储退格键所在索引位置
        del_indexs = indexs[:]  # 将要删除的元素(含退格键本身)所在列表位置
        # print('indexs', indexs)
        for index in indexs:
            del_index = index - 1
            while (del_index in del_indexs):
                # 若元素已被之前退格删，删除前移一位元素。
                del_index -= 1
            del_indexs.append(del_index)
        print('del_indexs', del_indexs)
        c_3 = [j for (i, j) in enumerate(cmd) if i not in del_indexs]
        cmd = ''.join(c_3).strip()
        if cmd:
            cs_3.append(''.join(c_3))
    logger.info('cs_3: %s 3333' % cs_3)

    # 2.stdins，带回车的粘贴输入
    if stdins:
        logger.info('stdins: %s 4444' % stdins)
    cs_3.extend(stdins)
    p = "(\x1b\[[0-9]*[;0-9]*[;0-9]*[mHABCDJsuLMP])"  # 终端控制字符
    cmds = re.sub(re.compile(p, re.S), '', '\r\n'.join(cs_3))
    logger.info('cmds: %s 5555' % cmds)
    return cmds
    """

