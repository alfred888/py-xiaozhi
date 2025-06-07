import json
import os
import threading
import time
from typing import Callable, Optional

import pyaudio
from vosk import KaldiRecognizer, Model, SetLogLevel

class VoiceToText:
    """实时语音转文字类"""

    def __init__(self):
        os.environ['PULSE_LATENCY_MSEC'] = '30'
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recognizer = None
        self.running = False
        self.thread = None
        self.on_text_callback = None
        self.stream_lock = threading.Lock()
        self._init_model()

    def _init_model(self):
        SetLogLevel(-1)
        model_path = "models/vosk-model-small-cn-0.22"
        self.model = Model(model_path=model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

    def _find_input_device(self):
        """强制使用含XFM名称的设备，否则抛出异常"""
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if "XFM" in info["name"]:
                    print(f"[Audio] 选用麦克风: {info['name']} (索引 {i})")
                    return i, info
            except Exception:
                continue
        raise Exception("未找到包含 'XFM' 的麦克风")

    def _create_audio_stream(self, device_index, sample_rate):
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
                start=True
            )
            return stream
        except Exception as e:
            print(f"[ERROR] 创建音频流失败: {e}")
            return None

    def _check_microphone_status(self):
        if not self.stream or not self.stream.is_active():
            return False
        try:
            with self.stream_lock:
                test_data = self.stream.read(1024, exception_on_overflow=False)
                return len(test_data) > 0
        except:
            return False

    def _reset_stream(self):
        try:
            if self.stream:
                with self.stream_lock:
                    self.stream.stop_stream()
                    self.stream.close()
            device_index, device_info = self._find_input_device()
            self.stream = self._create_audio_stream(device_index, 16000)
            return self.stream is not None
        except:
            return False

    def start(self, on_text_callback: Optional[Callable[[str], None]] = None):
        if self.running:
            return
        self.on_text_callback = on_text_callback
        self.running = True
        self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def _recognition_loop(self):
        try:
            device_index, device_info = self._find_input_device()
            self.stream = self._create_audio_stream(device_index, 16000)
            if not self.stream:
                print("[ERROR] 音频流创建失败")
                return

            print("🎙️ 开始语音识别，请说话...")

            while self.running:
                try:
                    with self.stream_lock:
                        data = self.stream.read(1024, exception_on_overflow=False)
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            print(f"[识别结果] {text}")
                            if self.on_text_callback:
                                self.on_text_callback(text)
                except Exception as e:
                    print(f"[识别错误] {e}")
                    time.sleep(0.5)
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

    def is_running(self) -> bool:
        return self.running
