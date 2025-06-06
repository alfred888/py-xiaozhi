#!/bin/bash

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此脚本"
    exit 1
fi

# 复制规则文件到udev目录
cp 99-xunfei-mic.rules /etc/udev/rules.d/

# 重新加载udev规则
udevadm control --reload-rules
udevadm trigger

echo "讯飞麦克风设备规则已安装"
echo "请重新插拔麦克风设备，然后可以通过 /dev/xunfei_mic 访问设备" 