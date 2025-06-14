import queue
import threading
import time
import platform

import numpy as np
import pyaudio
import scipy.signal

# 在导入opuslib之前先设置opus库
from src.utils.opus_loader import setup_opus
setup_opus()
import opuslib

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """音频编解码器类，处理音频的录制和播放（严格兼容版）"""

    def __init__(self):
        self.audio = None
        self.input_stream = None
        self.output_stream = None
        self.opus_encoder = None
        self.opus_decoder = None
        # 设置队列最大大小，防止内存溢出（约10秒音频缓冲）
        max_queue_size = int(10 * 1000 / AudioConfig.FRAME_DURATION)
        self.audio_decode_queue = queue.Queue(maxsize=max_queue_size)

        # 状态管理（保留原始变量名）
        self._is_closing = False
        self._is_input_paused = False
        self._input_paused_lock = threading.Lock()
        self._stream_lock = threading.Lock()

        # 音频重采样相关
        self.actual_input_sample_rate = AudioConfig.INPUT_SAMPLE_RATE
        self.need_resample = False
        self.resample_ratio = 1.0
        self.resample_buffer = np.array([], dtype=np.float32)

        self._initialize_audio()

    def _initialize_audio(self):
        try:
            self.audio = pyaudio.PyAudio()

            # 初始化流（优化实现）
            self.input_stream = self._create_stream(is_input=True)
            self.output_stream = self._create_stream(is_input=False)

            # 编解码器初始化（保持原始参数）
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                AudioConfig.OPUS_APPLICATION,
            )
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS
            )

            logger.info("音频设备和编解码器初始化成功")
        except Exception as e:
            logger.error(f"初始化音频设备失败: {e}")
            self.close()
            raise

    def _create_stream(self, is_input=True):
        """流创建逻辑"""
        try:
            device_index = None
            device_info = None
            logger.info("开始扫描音频设备...")
            
            if is_input:
                # macOS优先检测策略
                if platform.system() == "Darwin":
                    # 优先查找MacBook内置麦克风
                    preferred_devices = ["MacBook Pro麦克风", "MacBook Air麦克风", "Built-in Microphone"]
                    for i in range(self.audio.get_device_count()):
                        info = self.audio.get_device_info_by_index(i)
                        logger.debug(f"设备 {i}: {info['name']} (输入通道: {info['maxInputChannels']}, 输出通道: {info['maxOutputChannels']})")
                        if info["maxInputChannels"] > 0:
                            for preferred in preferred_devices:
                                if preferred in info["name"]:
                                    device_index = i
                                    device_info = info
                                    logger.info(f"找到macOS优先设备: {info['name']} (索引: {i})")
                                    break
                        if device_index is not None:
                            break
                    
                    # 如果没找到优先设备，再查找讯飞设备
                    if device_index is None:
                        for i in range(self.audio.get_device_count()):
                            info = self.audio.get_device_info_by_index(i)
                            if info["maxInputChannels"] > 0 and "XFM-DP-V0.0.18" in info["name"]:
                                device_index = i
                                device_info = info
                                logger.info(f"找到讯飞麦克风设备: {info['name']} (索引: {i})")
                                break
                else:
                    # 非macOS系统，优先查找讯飞设备
                    for i in range(self.audio.get_device_count()):
                        info = self.audio.get_device_info_by_index(i)
                        logger.debug(f"设备 {i}: {info['name']} (输入通道: {info['maxInputChannels']}, 输出通道: {info['maxOutputChannels']})")
                        if info["maxInputChannels"] > 0 and "XFM-DP-V0.0.18" in info["name"]:
                            device_index = i
                            device_info = info
                            logger.info(f"找到讯飞麦克风设备: {info['name']} (索引: {i})")
                            break
                
                # 如果都没找到，使用默认设备
                if device_index is None:
                    logger.warning("未找到特定麦克风设备，使用默认输入设备")
                    device_index = self.audio.get_default_input_device_info()["index"]
                    device_info = self.audio.get_device_info_by_index(device_index)
                    logger.info(f"使用默认输入设备: {device_info['name']} (索引: {device_index})")

            # 获取设备支持的采样率并设置重采样
            if device_info and is_input:
                default_rate = int(device_info.get('defaultSampleRate', 16000))
                logger.info(f"设备默认采样率: {default_rate}Hz")
                
                # 检测是否需要重采样
                if default_rate != AudioConfig.INPUT_SAMPLE_RATE:
                    logger.info(f"设备采样率{default_rate}Hz与目标采样率{AudioConfig.INPUT_SAMPLE_RATE}Hz不匹配，启用重采样")
                    self.actual_input_sample_rate = default_rate
                    self.need_resample = True
                    self.resample_ratio = AudioConfig.INPUT_SAMPLE_RATE / default_rate
                    logger.info(f"重采样比例: {self.resample_ratio:.4f}")
                    sample_rate = default_rate
                else:
                    self.actual_input_sample_rate = AudioConfig.INPUT_SAMPLE_RATE
                    self.need_resample = False
                    sample_rate = AudioConfig.INPUT_SAMPLE_RATE
            elif is_input:
                sample_rate = AudioConfig.INPUT_SAMPLE_RATE
            else:
                sample_rate = AudioConfig.OUTPUT_SAMPLE_RATE

            # 根据实际采样率调整帧大小
            if is_input and self.need_resample:
                frame_size = int(AudioConfig.INPUT_FRAME_SIZE * (self.actual_input_sample_rate / AudioConfig.INPUT_SAMPLE_RATE))
            else:
                frame_size = AudioConfig.INPUT_FRAME_SIZE if is_input else AudioConfig.OUTPUT_FRAME_SIZE

            params = {
                "format": pyaudio.paInt16,
                "channels": AudioConfig.CHANNELS,
                "rate": sample_rate,
                "input": is_input,
                "output": not is_input,
                "frames_per_buffer": frame_size,
                "stream_callback": None,
            }

            # 添加设备索引
            if is_input and device_index is not None:
                params["input_device_index"] = device_index
                logger.info(f"使用设备索引: {device_index}")

            stream = self.audio.open(**params)
            logger.info(f"音频流创建成功: {'输入' if is_input else '输出'} (采样率: {sample_rate}Hz)")
            return stream
        except Exception as e:
            logger.error(f"创建音频流失败: {e}")
            raise

    def _reinitialize_stream(self, is_input=True):
        """通用流重建方法"""
        if self._is_closing:
            return False if is_input else None

        try:
            stream_attr = "input_stream" if is_input else "output_stream"
            current_stream = getattr(self, stream_attr)

            if current_stream:
                try:
                    current_stream.stop_stream()
                    current_stream.close()
                except Exception:
                    pass

            new_stream = self._create_stream(is_input=is_input)
            setattr(self, stream_attr, new_stream)
            new_stream.start_stream()

            stream_type = "输入" if is_input else "输出"
            logger.info(f"音频{stream_type}流重新初始化成功")
            return True if is_input else None
        except Exception as e:
            stream_type = "输入" if is_input else "输出"
            logger.error(f"{stream_type}流重建失败: {e}")
            if is_input:
                return False
            else:
                raise

    def pause_input(self):
        with self._input_paused_lock:
            self._is_input_paused = True
        logger.info("音频输入已暂停")

    def resume_input(self):
        with self._input_paused_lock:
            self._is_input_paused = False
        logger.info("音频输入已恢复")

    def is_input_paused(self):
        with self._input_paused_lock:
            return self._is_input_paused

    def read_audio(self):
        """读取音频数据，支持重采样"""
        if self.is_input_paused():
            return None

        try:
            with self._stream_lock:
                # 流状态检查优化
                if not self.input_stream or not self.input_stream.is_active():
                    if not self._reinitialize_stream(is_input=True):
                        return None

                # 计算实际需要读取的帧大小
                if self.need_resample:
                    actual_frame_size = int(AudioConfig.INPUT_FRAME_SIZE * (self.actual_input_sample_rate / AudioConfig.INPUT_SAMPLE_RATE))
                else:
                    actual_frame_size = AudioConfig.INPUT_FRAME_SIZE

                # 动态缓冲区调整
                available = self.input_stream.get_read_available()
                if available > actual_frame_size * 2:
                    skip_samples = available - (actual_frame_size * 1.5)
                    if skip_samples > 0:
                        self.input_stream.read(
                            int(skip_samples), exception_on_overflow=False
                        )
                        logger.debug(f"跳过{skip_samples}个样本减少延迟")

                # 读取数据
                data = self.input_stream.read(
                    actual_frame_size, exception_on_overflow=False
                )

                # 数据验证
                expected_bytes = actual_frame_size * 2  # 16-bit = 2 bytes per sample
                if len(data) != expected_bytes:
                    logger.warning(f"音频数据长度异常，期望{expected_bytes}字节，实际{len(data)}字节")
                    self._reinitialize_stream(is_input=True)
                    return None

                # 重采样处理
                if self.need_resample:
                    data = self._resample_audio(data)
                    if data is None:
                        return None

                return self.opus_encoder.encode(data, AudioConfig.INPUT_FRAME_SIZE)

        except Exception as e:
            logger.error(f"音频读取失败: {e}")
            self._reinitialize_stream(is_input=True)
            return None

    def play_audio(self):
        """播放音频（简化版本，解码失败直接丢弃）"""
        try:
            if self.audio_decode_queue.empty():
                return

            # 逐个处理音频数据，失败直接丢弃
            processed_count = 0
            max_process_per_call = 5  # 限制单次处理数量，避免阻塞

            while (
                not self.audio_decode_queue.empty()
                and processed_count < max_process_per_call
            ):
                try:
                    opus_data = self.audio_decode_queue.get_nowait()

                    # 解码音频数据，失败直接跳过
                    try:
                        pcm = self.opus_decoder.decode(
                            opus_data, AudioConfig.OUTPUT_FRAME_SIZE
                        )
                    except opuslib.OpusError as e:
                        logger.warning(f"音频解码失败，丢弃此帧: {e}")
                        processed_count += 1
                        continue

                    # 播放音频数据，失败直接丢弃
                    try:
                        with self._stream_lock:
                            if self.output_stream and self.output_stream.is_active():
                                self.output_stream.write(
                                    np.frombuffer(pcm, dtype=np.int16).tobytes()
                                )
                            else:
                                logger.warning("输出流未激活，丢弃此帧")
                    except OSError as e:
                        logger.warning(f"音频播放失败，丢弃此帧: {e}")
                        if "Stream closed" in str(e):
                            self._reinitialize_stream(is_input=False)

                    processed_count += 1

                except queue.Empty:
                    break

        except Exception as e:
            logger.error(f"播放音频时发生未预期错误: {e}")

    def close(self):
        """（优化资源释放顺序和线程安全性）"""
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("开始关闭音频编解码器...")

        try:
            # 清空队列先行处理
            self.clear_audio_queue()

            # 安全停止和关闭流
            with self._stream_lock:
                # 先关闭输入流
                if self.input_stream:
                    try:
                        if (
                            hasattr(self.input_stream, "is_active")
                            and self.input_stream.is_active()
                        ):
                            self.input_stream.stop_stream()
                        self.input_stream.close()
                    except Exception as e:
                        logger.warning(f"关闭输入流失败: {e}")
                    finally:
                        self.input_stream = None

                # 再关闭输出流
                if self.output_stream:
                    try:
                        if (
                            hasattr(self.output_stream, "is_active")
                            and self.output_stream.is_active()
                        ):
                            self.output_stream.stop_stream()
                        self.output_stream.close()
                    except Exception as e:
                        logger.warning(f"关闭输出流失败: {e}")
                    finally:
                        self.output_stream = None

                # 最后释放PyAudio
                if self.audio:
                    try:
                        self.audio.terminate()
                    except Exception as e:
                        logger.warning(f"释放PyAudio失败: {e}")
                    finally:
                        self.audio = None

            # 清理编解码器
            self.opus_encoder = None
            self.opus_decoder = None

            logger.info("音频资源已完全释放")
        except Exception as e:
            logger.error(f"关闭音频编解码器过程中发生错误: {e}")
        # 移除冗余的状态重置

    def write_audio(self, opus_data):
        """将Opus数据写入播放队列，处理队列满的情况"""
        try:
            # 非阻塞方式放入队列
            self.audio_decode_queue.put_nowait(opus_data)
        except queue.Full:
            # 队列满时，移除最旧的数据，添加新数据
            logger.warning("音频播放队列已满，丢弃最旧的音频帧")
            try:
                self.audio_decode_queue.get_nowait()  # 移除最旧的
                self.audio_decode_queue.put_nowait(opus_data)  # 添加新的
            except queue.Empty:
                # 如果队列突然变空，直接添加
                self.audio_decode_queue.put_nowait(opus_data)

    # has_pending_audio 方法已移除（可直接使用 not audio_decode_queue.empty()）

    def get_queue_status(self):
        """获取队列状态信息（简化版）"""
        queue_size = self.audio_decode_queue.qsize()
        max_size = self.audio_decode_queue.maxsize
        return {
            "current_size": queue_size,
            "max_size": max_size,
            "is_empty": queue_size == 0,
        }

    def wait_for_audio_complete(self, timeout=5.0):
        """等待音频播放完成（简化版）"""
        start = time.time()
        while not self.audio_decode_queue.empty() and time.time() - start < timeout:
            time.sleep(0.1)

        if not self.audio_decode_queue.empty():
            remaining = self.audio_decode_queue.qsize()
            logger.warning(f"音频播放超时，剩余队列: {remaining} 帧")

    def clear_audio_queue(self):
        with self._stream_lock:
            cleared_count = 0
            while not self.audio_decode_queue.empty():
                try:
                    self.audio_decode_queue.get_nowait()
                    cleared_count += 1
                except queue.Empty:
                    break
            if cleared_count > 0:
                logger.info(f"清空音频队列，丢弃 {cleared_count} 帧音频数据")

    # start_streams 方法已移除（功能冗余，可直接调用各流的 start_stream）

    def stop_streams(self):
        """安全停止流（优化错误处理）"""
        with self._stream_lock:
            for name, stream in [
                ("输入", self.input_stream),
                ("输出", self.output_stream),
            ]:
                if stream:
                    try:
                        # 使用hasattr避免在流已关闭情况下调用is_active
                        if hasattr(stream, "is_active") and stream.is_active():
                            stream.stop_stream()
                    except Exception as e:
                        # 使用warning级别，因为这不是严重错误
                        logger.warning(f"停止{name}流失败: {e}")

    def _resample_audio(self, audio_data):
        """音频重采样处理"""
        try:
            # 将字节数据转换为numpy数组
            audio_samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # 添加到重采样缓冲区
            self.resample_buffer = np.concatenate([self.resample_buffer, audio_samples])
            
            # 计算需要的输入样本数以产生目标输出样本数
            input_samples_needed = int(AudioConfig.INPUT_FRAME_SIZE / self.resample_ratio)
            
            if len(self.resample_buffer) < input_samples_needed:
                # 缓冲区样本不足，返回None等待更多数据
                return None
            
            # 提取需要的样本进行重采样
            samples_to_process = self.resample_buffer[:input_samples_needed]
            self.resample_buffer = self.resample_buffer[input_samples_needed:]
            
            # 使用scipy进行重采样
            resampled = scipy.signal.resample(samples_to_process, AudioConfig.INPUT_FRAME_SIZE)
            
            # 转换回int16并返回字节数据
            resampled_int16 = np.clip(resampled, -32768, 32767).astype(np.int16)
            return resampled_int16.tobytes()
            
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return None

    def __del__(self):
        self.close()
