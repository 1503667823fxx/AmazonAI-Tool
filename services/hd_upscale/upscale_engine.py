# services/hd_upscale/upscale_engine.py
import replicate
import streamlit as st
from .config import UpscaleConfig

class UpscaleEngine:
    def __init__(self):
        # 尝试从 secrets 获取 key，实现开箱即用
        try:
            self.api_token = st.secrets["REPLICATE_API_TOKEN"]
            self.client = replicate.Client(api_token=self.api_token)
        except Exception:
            self.client = None
            st.error("❌ 未检测到 REPLICATE_API_TOKEN，请检查 Streamlit Secrets 配置。")

    def process_image(self, image_file, scale=4, face_enhance=False):
        """
        执行图片放大
        :param image_file: Streamlit UploadedFile 对象
        :param scale: 放大倍数 (2 或 4)
        :param face_enhance: 是否开启面部修复
        :return: 放大后的图片 URL
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            # Replicate Python Client 可以直接处理文件流
            input_params = {
                "image": image_file,
                "scale": scale,
                "face_enhance": face_enhance,
            }

            output = self.client.run(
                UpscaleConfig.MODEL_ID,
                input=input_params
            )
            
            # Real-ESRGAN 通常返回一个 URL 字符串
            return output

        except Exception as e:
            raise RuntimeError(f"放大服务调用失败: {str(e)}")
