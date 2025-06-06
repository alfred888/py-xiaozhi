#!/bin/bash

# 设置录音目录
RECORD_DIR="mic_test_records"
mkdir -p "$RECORD_DIR"

# 获取当前时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 查找 USB Camera 设备
echo "正在查找 USB Camera 音频设备..."
CAMERA_DEVICE=$(arecord -l | grep "USB Camera" | head -n 1)

if [ -z "$CAMERA_DEVICE" ]; then
    echo "错误: 未找到 USB Camera 音频设备"
    exit 1
fi

# 提取设备信息
CARD_NUM=$(echo "$CAMERA_DEVICE" | grep -o "card [0-9]" | cut -d' ' -f2)
DEVICE_NAME=$(echo "$CAMERA_DEVICE" | grep -o "\[.*\]" | tr -d '[]')

echo "找到 USB Camera 音频设备: Card $CARD_NUM - $DEVICE_NAME"

# 生成文件名
FILENAME="${RECORD_DIR}/mic_${CARD_NUM}_${DEVICE_NAME}_${TIMESTAMP}.wav"

echo "正在录音..."
echo "采样率: 48000Hz, 通道数: 1"

# 录音5秒
arecord -D "hw:$CARD_NUM,0" \
    -f S16_LE \
    -r 48000 \
    -c 1 \
    -d 5 \
    "$FILENAME"

if [ $? -eq 0 ]; then
    echo "✓ 录音成功完成"
    echo "音频已保存到: $FILENAME"
    
    # 显示音频文件信息（如果安装了 soxi）
    if command -v soxi &> /dev/null; then
        echo "音频文件信息:"
        soxi "$FILENAME"
    fi
    
    # 播放录音
    echo -e "\n正在播放录音..."
    aplay "$FILENAME"
    
    if [ $? -eq 0 ]; then
        echo "✓ 播放完成"
    else
        echo "✗ 播放失败"
    fi
else
    echo "✗ 录音失败"
    rm -f "$FILENAME"  # 删除失败的录音文件
fi

echo -e "\n测试完成！" 