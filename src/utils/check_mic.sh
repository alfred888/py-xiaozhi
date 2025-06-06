#!/bin/bash

# 设置录音目录
RECORD_DIR="mic_test_records"
mkdir -p "$RECORD_DIR"

# 获取当前时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 获取所有录音设备
echo "正在检测可用的麦克风设备..."
arecord -l | grep "card" | while read -r line; do
    # 提取设备信息
    CARD_NUM=$(echo "$line" | grep -o "card [0-9]" | cut -d' ' -f2)
    DEVICE_NAME=$(echo "$line" | grep -o "\[.*\]" | tr -d '[]')
    
    # 生成文件名
    FILENAME="${RECORD_DIR}/mic_${CARD_NUM}_${DEVICE_NAME}_${TIMESTAMP}.wav"
    
    echo "正在测试麦克风: Card $CARD_NUM - $DEVICE_NAME"
    echo "录音将保存到: $FILENAME"
    
    # 录音5秒
    arecord -D "hw:$CARD_NUM,0" -f S16_LE -r 16000 -c 1 -d 5 "$FILENAME"
    
    if [ $? -eq 0 ]; then
        echo "✓ 录音成功完成"
        # 显示音频文件信息
        echo "音频文件信息:"
        soxi "$FILENAME"
    else
        echo "✗ 录音失败"
    fi
    echo "----------------------------------------"
done

echo "所有麦克风测试完成！"
echo "录音文件保存在: $RECORD_DIR 目录下" 