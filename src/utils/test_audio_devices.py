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
        
    def get_audio_devices(self):
        """获取所有音频设备信息"""
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # 只获取输入设备
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        return devices

    def record_audio(self, device_index, duration=5):
        """录制音频"""
        device_info = self.p.get_device_info_by_index(device_index)
        sample_rate = int(device_info['defaultSampleRate'])
        channels = int(device_info['maxInputChannels'])
        
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

    def test_all_devices(self):
        """测试所有音频设备"""
        devices = self.get_audio_devices()
        if not devices:
            print("未找到音频输入设备")
            return
        
        print(f"找到 {len(devices)} 个音频输入设备:")
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device['name']}")
        
        recorded_files = []
        
        # 测试每个设备
        for device in devices:
            try:
                filename = self.record_audio(device['index'])
                recorded_files.append(filename)
            except Exception as e:
                print(f"设备 {device['name']} 录音失败: {e}")
        
        # 播放所有录音
        if recorded_files:
            print("\n开始播放所有录音...")
            for filename in recorded_files:
                try:
                    self.play_audio(filename)
                    input("按回车键继续播放下一个文件...")
                except Exception as e:
                    print(f"播放 {filename} 失败: {e}")
        
        print("\n测试完成！")

    def close(self):
        """关闭 PyAudio"""
        self.p.terminate()

def main():
    tester = AudioDeviceTester()
    try:
        tester.test_all_devices()
    finally:
        tester.close()

if __name__ == "__main__":
    main() 