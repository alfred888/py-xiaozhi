import json
import threading
import time
from typing import Callable, Optional

import pyaudio
from vosk import KaldiRecognizer, Model, SetLogLevel

from ..constants.constants import AudioConfig
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

class VoiceToText:
    """实时语音转文字类"""

    def __init__(self):
        """初始化语音转文字功能"""
        # 初始化基本属性
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recognizer = None
        self.running = False
        self.thread = None
        self.on_text_callback = None
        
        # 初始化语音识别模型
        self._init_model()
        
    def _init_model(self):
        """初始化语音识别模型"""
        try:
            # 设置Vosk日志级别
            SetLogLevel(-1)
            
            # 加载模型
            model_path = "models/vosk-model-small-cn-0.22"
            logger.info(f"加载语音识别模型: {model_path}")
            self.model = Model(model_path=model_path)
            
            # 创建识别器
            self.recognizer = KaldiRecognizer(self.model, AudioConfig.INPUT_SAMPLE_RATE)
            self.recognizer.SetWords(True)
            logger.info("语音识别模型加载完成")
            
        except Exception as e:
            logger.error(f"初始化语音识别模型失败: {e}")
            raise
            
    def _find_input_device(self):
        """查找输入设备"""
        device_index = None
        device_info = None
        
        # 遍历所有设备
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            logger.debug(f"设备 {i}: {info['name']} (输入通道: {info['maxInputChannels']}, 输出通道: {info['maxOutputChannels']})")
            
            # 检查是否是输入设备
            if info["maxInputChannels"] > 0:
                # 优先选择讯飞麦克风设备
                if "XFM-DP" in info["name"] or "ACM" in info["name"]:
                    device_index = i
                    device_info = info
                    logger.info(f"找到讯飞麦克风设备: {info['name']} (索引: {i})")
                    break
        
        # 如果找不到讯飞麦克风设备，使用默认输入设备
        if device_index is None:
            logger.warning("未找到讯飞麦克风设备，使用默认输入设备")
            device_index = self.audio.get_default_input_device_info()["index"]
            device_info = self.audio.get_device_info_by_index(device_index)
            logger.info(f"使用默认输入设备: {device_info['name']} (索引: {device_index})")
            
        return device_index, device_info
            
    def start(self, on_text_callback: Optional[Callable[[str], None]] = None):
        """启动语音转文字
        
        Args:
            on_text_callback: 文本识别回调函数，接收识别到的文本作为参数
        """
        if self.running:
            logger.warning("语音转文字已经在运行")
            return
            
        self.on_text_callback = on_text_callback
        self.running = True
        
        # 创建并启动识别线程
        self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.thread.start()
        logger.info("语音转文字已启动")
        
    def stop(self):
        """停止语音转文字"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
            
        # 关闭音频流
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        logger.info("语音转文字已停止")
        
    def _recognition_loop(self):
        """语音识别主循环"""
        try:
            # 查找输入设备
            device_index, device_info = self._find_input_device()
            
            # 获取设备支持的采样率
            default_rate = int(device_info.get('defaultSampleRate', 16000))
            supported_rates = device_info.get('supportedSampleRates', [])
            logger.info(f"设备默认采样率: {default_rate}Hz")
            if supported_rates:
                logger.info(f"设备支持的采样率: {supported_rates}")
            
            # 检查设备是否支持目标采样率
            target_rate = AudioConfig.INPUT_SAMPLE_RATE
            if supported_rates and target_rate not in supported_rates:
                logger.warning(f"设备不支持{target_rate}Hz采样率，使用设备默认采样率{default_rate}Hz")
                sample_rate = default_rate
            else:
                sample_rate = target_rate
                logger.info(f"使用目标采样率: {sample_rate}Hz")
            
            # 创建音频流
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=AudioConfig.CHANNELS,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=AudioConfig.INPUT_FRAME_SIZE
            )
            
            logger.info("开始语音识别循环")
            
            while self.running:
                try:
                    # 读取音频数据
                    data = self.stream.read(AudioConfig.INPUT_FRAME_SIZE, exception_on_overflow=False)
                    
                    # 处理音频数据
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        
                        if text:
                            logger.info(f"识别到文本: {text}")
                            if self.on_text_callback:
                                self.on_text_callback(text)
                                
                except Exception as e:
                    logger.error(f"处理音频数据时出错: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"语音识别循环出错: {e}")
        finally:
            # 确保资源被正确释放
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running
