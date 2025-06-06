#!/bin/bash

# 设置录音目录
RECORD_DIR="mic_test_records"
mkdir -p "$RECORD_DIR"

# 获取当前时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 检查是否安装了 soxi
if ! command -v soxi &> /dev/null; then
    echo "警告: soxi 未安装，将跳过音频文件信息显示"
    echo "可以通过 'sudo apt-get install sox' 安装"
fi

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
    
    # 尝试不同的采样率和通道配置
    SAMPLE_RATES=(48000 16000)
    CHANNELS=(2 1)
    
    SUCCESS=false
    
    for rate in "${SAMPLE_RATES[@]}"; do
        for ch in "${CHANNELS[@]}"; do
            echo "尝试采样率: ${rate}Hz, 通道数: ${ch}"
            
            # 录音5秒
            if arecord -D "hw:$CARD_NUM,0" -f S16_LE -r $rate -c $ch -d 5 "$FILENAME" 2>/dev/null; then
                SUCCESS=true
                echo "✓ 录音成功完成 (采样率: ${rate}Hz, 通道数: ${ch})"
                
                # 显示音频文件信息（如果安装了soxi）
                if command -v soxi &> /dev/null; then
                    echo "音频文件信息:"
                    soxi "$FILENAME"
                fi
                
                break 2  # 跳出两层循环
            fi
        done
    done
    
    if [ "$SUCCESS" = false ]; then
        echo "✗ 所有配置组合都失败"
        rm -f "$FILENAME"  # 删除失败的录音文件
    fi
    
    echo "----------------------------------------"
done

echo "所有麦克风测试完成！"
echo "录音文件保存在: $RECORD_DIR 目录下"

# 显示录音文件列表
echo -e "\n录音文件列表:"
ls -lh "$RECORD_DIR" 