
import os

guacd_hostname = '127.0.0.1'
guacd_port = '4822'
# guacd_ssl = 'true'  # 默认不加密, 客户端启用加密时, 需guacd本身也支持


'''
guacamole 连接参数

https://guacamole.apache.org/doc/gug/configuring-guacamole.html#connection-configuration

GuacamoleClient.read_instruction()
'''

base_path = os.environ.get("DOCKER_GUACD_DIR", '/guacamole')  # 用于网盘/存放录像, guacd 4822服务器上的路径
'''
guacd为容器时, base_path 为容器中的路径, 不是宿主机路径.
使用docker-compose.yml构建容器时, services.guacd.volumes挂载路径,
宿主机.../dx/media/guacamole目录:容器目录, (容器目录必须与base_path一致)

为播放录像, 需挂载宿主机路径 <settings.MEDIA_ROOT>/guacamole 到容器 "base_path".
如果guacd在不同机器上, 播放录像需自行创建nginx配置录像文件静态资源,
比如 http://xxx/MEDIA_URL/REPLAY_PATH/录像文件

'''
REPLAY_PATH = 'guacamole/replay'  # 用于前端网页访问, 存放RDP/VNC录像文件夹，MEDIA_ROOT/REPLAY_PATH

GUACD = {
    # 连接参数, guacd参数名连接符为"-", 由于python变量名不能含中杠"-", key名改为下杠"_"

    # 显示
    'width': 800,
    'height': 600,
    # 'dpi': 96,  # 分辨率(DPI)
    # 'color_depth': '16',  # 色彩深度 8 16 24 32位色
    'resize_method': 'display-update',  # 缩放方法, display-update / reconnect, 未设置则窗口变化时不处理
    # 'read_only': 'true'

    # # 设备重定向
    # 'disable_audio': 'true',  # 禁用音频
    # 'enable_audio_input': 'true',  # 启用麦克风
    # 'enable_printing': 'true',  # 启用打印
    # 'printer_name': 'dx printer',  # 打印机设备的名称
    # 'static_channels': 'aa,bb,cc',  # 静态通道, 音频声道?

    'enable_drive': 'true',  # 启用虚拟盘 GUAC FS
    'drive_path': os.path.join(base_path, 'guacfs'),  # guacd 4822服务器路径
    # drive_path所在上级目录不存在时, 无法下载文件, 也不支持自动创建.
    'create_drive_path': 'true',  # guacd 服务器drive_path目录不存在则自动创建(只支持创建最后一级目录)
    # 'drive_name': 'tsclient',
    # 'disable_download': 'true',
    # 'disable_upload': 'true',

    # # 剪切板
    # 'disable_copy': 'true',  # 禁止RDP中复制
    # 'disable_paste': 'true',

    # # 屏幕录像
    # 'recording_name': '',
    'recording_path': os.path.join(base_path, 'replay'),  # 录像保存位置, guacd 4822服务器路径
    'create_recording_path': 'true',  # (只支持创建最后一级目录)
    # 'recording_exclude_output': 'true',  # 排除图像/数据流
    # 'recording_exclude_mouse': 'true',  # 排除鼠标
    # 'recording_include_keys': 'true',  # 包含按键事件

    # 性能
    'enable_wallpaper': 'true',  # 墙纸
    # 'enable_theming': 'true',  # 主题
    # 'enable_font_smoothing': 'true',  # 字体平滑
    # 'enable_full_window_drag': 'true',  # 全窗口拖拽 (拖动窗口显示内容)
    # 'enable_desktop_composition': 'true',  # 桌面合成效果(Aero) (透明窗口和阴影)
    # 'enable_menu_animations': 'true',  # 菜单动画
    # 'disable_bitmap_caching': 'true',  # 禁用位图缓存
    # 'disable_offscreen_caching': 'true',  # 禁用离屏缓存
    # 'disable_glyph_caching': 'true',  # 禁用字形缓存

    # 会话设置
    # 'console': 'true',  # windows控制台 id: 0
    # 'console_audio': 'true',  # 远程服务器物理位置的音频/功放

}

