import argparse
import io
import logging
import signal
import sys
import time

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

def parse_args():
    """解析命令行参数"""
    # 确保sys.stdout和sys.stderr不为None
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    parser = argparse.ArgumentParser(description="小智Ai客户端 - 无界面版")

    # 添加协议选择参数
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="通信协议：mqtt 或 websocket",
    )

    # 添加日志级别参数
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="日志级别",
    )

    return parser.parse_args()

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    logger.info("接收到中断信号，正在关闭...")
    app = Application.get_instance()
    app.shutdown()
    sys.exit(0)

def main():
    """程序入口点"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    # 解析命令行参数
    args = parse_args()

    try:
        # 日志
        setup_logging()
        logger.info("正在启动无界面版小智Ai客户端...")

        # 创建并运行应用程序
        app = Application.get_instance()
        
        # 启动应用，使用CLI模式
        app.run(mode="cli", protocol=args.protocol)
        
        logger.info("应用程序已启动，按Ctrl+C退出")
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到键盘中断，正在关闭...")
            app.shutdown()
            
    except Exception as e:
        logger.error(f"程序发生错误: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main()) 