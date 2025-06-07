import json
import os
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
        # 设置环境变量，强制使用PulseAudio
        os.environ['PULSE_LATENCY_MSEC'] = '30'
        
        # 初始化基本属性
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recognizer = None
        self.running = False
        self.thread = None
        self.on_text_callback = None
        self.stream_lock = threading.Lock()
        
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
            try:
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
            except Exception as e:
                logger.warning(f"获取设备 {i} 信息时出错: {e}")
                continue
        
        # 如果找不到讯飞麦克风设备，使用默认输入设备
        if device_index is None:
            try:
                logger.warning("未找到讯飞麦克风设备，使用默认输入设备")
                device_index = self.audio.get_default_input_device_info()["index"]
                device_info = self.audio.get_device_info_by_index(device_index)
                logger.info(f"使用默认输入设备: {device_info['name']} (索引: {device_index})")
            except Exception as e:
                logger.error(f"获取默认输入设备失败: {e}")
                # 尝试使用第一个可用的输入设备
                for i in range(self.audio.get_device_count()):
                    try:
                        info = self.audio.get_device_info_by_index(i)
                        if info["maxInputChannels"] > 0:
                            device_index = i
                            device_info = info
                            logger.info(f"使用备用输入设备: {info['name']} (索引: {i})")
                            break
                    except Exception as e:
                        continue
                
                if device_index is None:
                    raise Exception("找不到可用的输入设备")
            
        return device_index, device_info
            
    def _create_audio_stream(self, device_index, sample_rate):
        """创建音频流"""
        try:
            # 尝试使用PulseAudio
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=AudioConfig.CHANNELS,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=AudioConfig.INPUT_FRAME_SIZE,
                stream_callback=None,
                start=True  # 直接启动流
            )
            
            # 等待流启动
            time.sleep(0.1)
            
            # 测试流是否可用
            try:
                test_data = stream.read(1024, exception_on_overflow=False)
                if not test_data:
                    raise Exception("无法从音频流读取数据")
                return stream
            except Exception as e:
                logger.error(f"测试音频流失败: {e}")
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except:
                        pass
                return None
            
        except Exception as e:
            logger.error(f"创建音频流失败: {e}")
            if 'stream' in locals() and stream:
                try:
                    stream.close()
                except:
                    pass
            return None
            
    def _check_microphone_status(self):
        """检查麦克风状态"""
        try:
            if not self.stream:
                return False
                
            if not self.stream.is_active():
                return False
                
            # 尝试读取一小段数据
            with self.stream_lock:
                test_data = self.stream.read(1024, exception_on_overflow=False)
                return len(test_data) > 0
                
        except Exception as e:
            logger.error(f"检查麦克风状态失败: {e}")
            return False
            
    def _reset_stream(self):
        """重置音频流"""
        try:
            if self.stream:
                with self.stream_lock:
                    try:
                        self.stream.stop_stream()
                        self.stream.close()
                    except Exception as e:
                        logger.error(f"关闭旧音频流失败: {e}")
                    finally:
                        self.stream = None
                        
            # 重新创建流
            device_index, device_info = self._find_input_device()
            sample_rate = int(device_info.get('defaultSampleRate', 16000))
            self.stream = self._create_audio_stream(device_index, sample_rate)
            
            if not self.stream:
                raise Exception("无法重新创建音频流")
                
            logger.info("音频流重置成功")
            return True
            
        except Exception as e:
            logger.error(f"重置音频流失败: {e}")
            return False
        
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
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"关闭音频流时出错: {e}")
            finally:
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
            
            # 尝试不同的采样率
            sample_rates_to_try = [
                16000,                          # 常用采样率
                44100,                          # 标准采样率
                48000,                          # 高采样率
                default_rate,                   # 设备默认采样率
                AudioConfig.INPUT_SAMPLE_RATE   # 配置的采样率
            ]
            
            # 如果设备支持特定采样率，优先使用
            if supported_rates:
                sample_rates_to_try = [rate for rate in supported_rates if rate in sample_rates_to_try]
            
            # 尝试不同的采样率
            stream = None
            for rate in sample_rates_to_try:
                logger.info(f"尝试使用采样率: {rate}Hz")
                stream = self._create_audio_stream(device_index, rate)
                if stream:
                    logger.info(f"成功使用采样率: {rate}Hz")
                    break
                time.sleep(0.1)  # 短暂延迟后重试
            
            if not stream:
                raise Exception("无法创建有效的音频流")
            
            self.stream = stream
            logger.info("开始语音识别循环")
            
            error_count = 0
            MAX_ERRORS = 5
            RETRY_DELAY = 0.5
            last_stream_check = 0
            STREAM_CHECK_INTERVAL = 1.0  # 每秒检查一次流状态
            
            while self.running:
                try:
                    # 定期检查流状态
                    current_time = time.time()
                    if current_time - last_stream_check >= STREAM_CHECK_INTERVAL:
                        last_stream_check = current_time
                        if not self._check_microphone_status():
                            logger.warning("麦克风状态异常，尝试重新初始化")
                            if not self._reset_stream():
                                error_count += 1
                                if error_count >= MAX_ERRORS:
                                    logger.error("达到最大错误次数，退出循环")
                                    break
                            time.sleep(RETRY_DELAY)
                            continue
                    
                    # 读取音频数据
                    with self.stream_lock:
                        data = self.stream.read(AudioConfig.INPUT_FRAME_SIZE, exception_on_overflow=False)
                    
                    # 处理音频数据
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        
                        if text:
                            logger.info(f"识别到文本: {text}")
                            if self.on_text_callback:
                                self.on_text_callback(text)
                                
                    error_count = 0  # 成功时清零
                                
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理音频数据时出错: {e}")
                    if error_count >= MAX_ERRORS:
                        logger.error("达到最大错误次数，尝试重新初始化")
                        if not self._reset_stream():
                            logger.error("重新初始化失败，退出循环")
                            break
                        error_count = 0
                    time.sleep(RETRY_DELAY)
                    
        except Exception as e:
            logger.error(f"语音识别循环出错: {e}")
        finally:
            # 确保资源被正确释放
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.error(f"关闭音频流时出错: {e}")
                finally:
                    self.stream = None
                
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running
