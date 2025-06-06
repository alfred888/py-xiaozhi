#!/usr/bin/env python3
import serial
import time
import sys

def send_message(ser, message):
	"""发送消息并等待响应"""
	print(f"发送: {' '.join([f'{b:02x}' for b in message])}")
	ser.write(message)
	time.sleep(0.1)
	response = ser.read(4)
	print(f"接收: {' '.join([f'{b:02x}' for b in response])}")
	return response

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
		# 打开串口
		ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
		print("已连接到串口设备")
		
		# 发送修改唤醒词命令
		response = send_message(ser, changehuan())
		
		# 检查响应
		if response and response[0] == 0xA5 and response[1] == 0x00:
			print("唤醒词修改命令已发送")
		else:
			print("命令发送失败")
		
		# 关闭串口
		ser.close()
		
	except serial.SerialException as e:
		print(f"串口错误: {e}")
	except Exception as e:
		print(f"发生错误: {e}")

if __name__ == "__main__":
	main()
