#!/bin/bash

# 设置录音目录
RECORD_DIR="mic_test_records"

# 检查目录是否存在
if [ ! -d "$RECORD_DIR" ]; then
    echo "错误: 录音目录 $RECORD_DIR 不存在"
    exit 1
fi

# 获取最新的录音文件（使用数组来正确处理文件名）
mapfile -t LATEST_FILES < <(ls -t "$RECORD_DIR"/*.wav 2>/dev/null | head -n 4)

if [ ${#LATEST_FILES[@]} -eq 0 ]; then
    echo "错误: 没有找到录音文件"
    exit 1
fi

echo "开始播放最新的录音文件..."
echo "----------------------------------------"

# 播放每个文件
for file in "${LATEST_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "警告: 文件不存在: $file"
        continue
    fi
    
    filename=$(basename "$file")
    echo "正在播放: $filename"
    
    # 使用 aplay 播放音频
    aplay "$file"
    
    if [ $? -eq 0 ]; then
        echo "✓ 播放完成"
    else
        echo "✗ 播放失败"
    fi
    
    echo "----------------------------------------"
    # 等待用户确认是否继续
    read -p "按回车键继续播放下一个文件，或按 Ctrl+C 退出..."
done

echo "所有文件播放完成！" 