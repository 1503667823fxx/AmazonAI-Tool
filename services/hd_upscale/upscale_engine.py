# services/hd_upscale/upscale_engine.py
import replicate
import streamlit as st
from .config import UpscaleConfig

class UpscaleEngine:
    def __init__(self):
        try:
            self.api_token = st.secrets["REPLICATE_API_TOKEN"]
            self.client = replicate.Client(api_token=self.api_token)
        except Exception:
            self.client = None

    def process_image(self, image_file, scale=4, face_enhance=False):
        """
        执行图片放大
        :return: 放大后的图片 URL (绝对纯净的字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            input_params = {
                "image": image_file,
                "scale": scale,
                "face_enhance": face_enhance,
            }

            output = self.client.run(
                UpscaleConfig.MODEL_ID,
                input=input_params
            )
            
            # --- [核心修复开始] ---
            # 1. 如果是列表，取第一个元素
            if isinstance(output, list):
                if len(output) > 0:
                    output = output[0]
                else:
                    return None
            
            # 2. [关键] 无论它是 FileOutput 对象还是什么，强制转为普通字符串
            # Replicate 的 FileOutput 对象只要 str() 一下就会变回 URL
            return str(output)
            # --- [核心修复结束] ---

        except Exception as e:
            raise RuntimeError(f"放大服务调用失败: {str(e)}")
