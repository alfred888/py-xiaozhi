import os
import sys
import time

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.audio_processing.voice_to_text import VoiceToText
    from src.utils.logging_config import get_logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python 路径: {sys.path}")
    sys.exit(1)

logger = get_logger(__name__)

def on_text(text: str):
    """文本识别回调函数"""
    print(f"\n识别到文本: {text}")

def main():
    try:
        # 创建语音转文字实例
        vtt = VoiceToText()
        
        # 启动语音转文字
        print("开始语音识别，请说话...")
        print("按 Ctrl+C 退出程序")
        vtt.start(on_text_callback=on_text)
        
        # 运行一段时间
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序出错: {e}")
        logger.error(f"程序出错: {e}", exc_info=True)
    finally:
        # 停止语音转文字
        if 'vtt' in locals():
            vtt.stop()
        print("程序已退出")

if __name__ == "__main__":
    main() 