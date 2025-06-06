#!/usr/bin/env python3
import serial
import time
import sys

def send_message(ser, message):
	"""发送消息并等待响应"""
	print(f"发送: {' '.join([f'{b:02x}' for b in message])}")
	ser.write(message)
	time.sleep(0.5)  # 增加等待时间
	
	# 读取完整响应
	response = bytearray()
	while ser.in_waiting:
		response.extend(ser.read(ser.in_waiting))
		time.sleep(0.1)
	
	if response:
		print(f"接收: {' '.join([f'{b:02x}' for b in response])}")
	else:
		print("未收到响应")
	
	return response

def parse_response(response):
	"""解析设备响应"""
	if not response:
		return False, "未收到响应"
	
	# 检查命令确认部分
	if len(response) < 7:
		return False, "响应数据不完整"
	
	# 检查命令确认
	if response[0:7] != bytearray([0xA5, 0x01, 0x01, 0x04, 0x00, 0x00, 0x00]):
		return False, "命令确认失败"
	
	# 检查状态响应
	if len(response) >= 12 and response[7:11] == bytearray([0xA5, 0x00, 0x00, 0x00]):
		return True, "设备状态正常"
	
	return True, "命令已发送，但状态响应异常"

def changehuan():
	"""生成修改唤醒词的消息"""
	# 消息格式：A5 01 01 04 0000 [校验和]
	message = bytearray([0xA5, 0x01, 0x01, 0x04, 0x00, 0x00])
	
	# 计算校验和（只取低8位）
	checksum = sum(message) & 0xFF
	message.append(checksum)
	
	return message

def main():
	try:
		# 打开串口（使用新的设备别名）
		ser = serial.Serial('/dev/xunfei_mic', 115200, timeout=1)
		print("已连接到讯飞麦克风设备")
		
		# 清空缓冲区
		ser.reset_input_buffer()
		ser.reset_output_buffer()
		
		# 发送修改唤醒词命令
		response = send_message(ser, changehuan())
		
		# 解析响应
		success, message = parse_response(response)
		print(message)
		
		if success:
			print("请重新上电设备以应用更改")
		
		# 关闭串口
		ser.close()
		
	except serial.SerialException as e:
		print(f"串口错误: {e}")
		print("请确保已运行 install_mic_rules.sh 并重新插拔设备")
	except Exception as e:
		print(f"发生错误: {e}")

if __name__ == "__main__":
	main()
