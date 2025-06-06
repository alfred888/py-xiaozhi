#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RULES_FILE="$SCRIPT_DIR/99-xunfei-mic.rules"
AUDIO_RULES_FILE="$SCRIPT_DIR/99-xunfei-audio.rules"

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 检查规则文件是否存在
if [ ! -f "$RULES_FILE" ]; then
    echo "错误：找不到串口规则文件 $RULES_FILE"
    exit 1
fi

if [ ! -f "$AUDIO_RULES_FILE" ]; then
    echo "错误：找不到音频规则文件 $AUDIO_RULES_FILE"
    exit 1
fi

# 显示当前连接的设备
echo "当前连接的设备："
echo "=== 串口设备 ==="
ls -l /dev/tty* | grep -E "USB|ACM"
echo -e "\n=== 音频设备 ==="
arecord -l

# 复制规则文件到udev目录
cp "$RULES_FILE" /etc/udev/rules.d/
cp "$AUDIO_RULES_FILE" /etc/udev/rules.d/

# 重新加载udev规则
udevadm control --reload-rules
udevadm trigger

echo "讯飞设备规则已安装"
echo "请重新插拔设备，然后可以通过以下路径访问设备："
echo "- 串口设备: /dev/xunfei_mic"
echo "- 音频设备: /dev/xunfei_audio"

# 检查设备权限
echo -e "\n检查设备权限："
ls -l /dev/ttyACM* 2>/dev/null
ls -l /dev/snd/* 2>/dev/null

# 提示用户可能需要添加dialout组
echo -e "\n如果遇到权限问题，请运行："
echo "sudo usermod -a -G dialout,audio $USER"
echo "然后重新登录系统" 