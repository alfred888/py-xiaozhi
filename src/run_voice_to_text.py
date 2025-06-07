import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.audio_processing.voice_to_text import VoiceToText
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def on_text(text: str):
    """文本识别回调函数"""
    print(f"\n识别到文本: {text}")

def main():
    # 创建语音转文字实例
    vtt = VoiceToText()
    
    try:
        # 启动语音转文字
        print("开始语音识别，请说话...")
        vtt.start(on_text_callback=on_text)
        
        # 运行一段时间
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        # 停止语音转文字
        vtt.stop()
        print("程序已退出")

if __name__ == "__main__":
    main() 