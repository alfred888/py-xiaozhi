#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RULES_FILE="$SCRIPT_DIR/99-xunfei-mic.rules"

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 检查规则文件是否存在
if [ ! -f "$RULES_FILE" ]; then
    echo "错误：找不到规则文件 $RULES_FILE"
    exit 1
fi

# 显示当前连接的设备
echo "当前连接的设备："
ls -l /dev/tty* | grep -E "USB|ACM"

# 复制规则文件到udev目录
cp "$RULES_FILE" /etc/udev/rules.d/

# 重新加载udev规则
udevadm control --reload-rules
udevadm trigger

echo "讯飞麦克风设备规则已安装"
echo "请重新插拔麦克风设备，然后可以通过 /dev/xunfei_mic 访问设备"

# 检查设备权限
echo "检查设备权限："
ls -l /dev/ttyACM*

# 提示用户可能需要添加dialout组
echo "如果遇到权限问题，请运行："
echo "sudo usermod -a -G dialout $USER"
echo "然后重新登录系统" 