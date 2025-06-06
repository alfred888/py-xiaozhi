#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyaudio
import wave
import time
import os
from datetime import datetime

class AudioDeviceTester:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.record_dir = "mic_test_records"
        os.makedirs(self.record_dir, exist_ok=True)
        
    def find_device_by_name(self, target_name):
        """查找指定名称的设备"""
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if target_name in device_info['name']:
                return {
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': 48000  # 强制使用 48000Hz 采样率
                }
        return None

    def record_audio(self, device_index, duration=5):
        """录制音频"""
        device_info = self.p.get_device_info_by_index(device_index)
        sample_rate = 48000  # 强制使用 48000Hz 采样率
        channels = 1  # 强制使用单声道
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mic_{device_index}_{device_info['name']}_{timestamp}.wav"
        filename = os.path.join(self.record_dir, filename)
        
        print(f"\n正在使用设备 {device_info['name']} 录音...")
        print(f"采样率: {sample_rate}Hz, 通道数: {channels}")
        
        # 打开音频流
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        print("开始录音...")
        frames = []
        
        # 录制音频
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)
        
        print("录音完成")
        
        # 停止并关闭流
        stream.stop_stream()
        stream.close()
        
        # 保存音频文件
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"音频已保存到: {filename}")
        return filename

    def play_audio(self, filename):
        """播放音频文件"""
        print(f"\n正在播放: {filename}")
        
        # 打开音频文件
        wf = wave.open(filename, 'rb')
        
        # 打开音频流
        stream = self.p.open(
            format=self.p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        # 播放音频
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        
        # 停止并关闭流
        stream.stop_stream()
        stream.close()
        wf.close()
        
        print("播放完成")

    def test_usb_camera(self):
        """测试 USB Camera 音频设备"""
        # 查找 USB Camera 设备
        device = self.find_device_by_name("USB Camera")
        if not device:
            print("未找到 USB Camera 音频设备")
            return
        
        print(f"找到 USB Camera 音频设备: {device['name']}")
        
        try:
            # 录音
            filename = self.record_audio(device['index'])
            
            # 播放
            self.play_audio(filename)
            
        except Exception as e:
            print(f"测试失败: {e}")
        
        print("\n测试完成！")

    def close(self):
        """关闭 PyAudio"""
        self.p.terminate()

def main():
    tester = AudioDeviceTester()
    try:
        tester.test_usb_camera()
    finally:
        tester.close()

if __name__ == "__main__":
    main() 