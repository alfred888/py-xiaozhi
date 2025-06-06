import base64
import os
import threading
import urllib.parse

from openai import OpenAI
import httpx

class ImageAnalyzer:
    _instance = None
    _lock = threading.Lock()
    client = None

    def __init__(self):
        self.model = None

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(
        self,
        api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        models="qwen-omni-turbo",
    ):
        # 确保 api_key 被正确编码
        encoded_api_key = urllib.parse.quote(api_key)
        http_client = httpx.Client(
            base_url=base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {encoded_api_key}",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=30.0
        )
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client
        )
        self.models = models

    @classmethod
    def get_instance(cls):
        """获取摄像头管理器实例（线程安全）"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def analyze_image(
        self, base64_image, prompt="图中描绘的是什么景象,请详细描述，因为用户可能是盲人"
    ) -> str:
        """分析图片并返回结果"""
        completion = self.client.chat.completions.create(
            model=self.models,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",  # 直接使用字符串，而不是列表
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            modalities=["text"],
            stream=True,
            stream_options={"include_usage": True},
        )
        mesag = ""
        for chunk in completion:
            if chunk.choices:
                mesag += chunk.choices[0].delta.content
            else:
                pass
        return mesag
