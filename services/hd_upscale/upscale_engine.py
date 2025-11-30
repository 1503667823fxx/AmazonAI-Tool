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
            # 注意：初始化时不报错，留到点击按钮时再报错，体验更好

    def process_image(self, image_file, scale=4, face_enhance=False):
        """
        执行图片放大
        :param image_file: Streamlit UploadedFile 对象
        :param scale: 放大倍数 (2 或 4)
        :param face_enhance: 是否开启面部修复
        :return: 放大后的图片 URL (字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化，请检查 Secrets 配置")

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
            
            # --- [修复核心] ---
            # Replicate 的 Real-ESRGAN 模型返回的是一个列表: ["https://..."]
            # 我们需要提取出里面的字符串
            if isinstance(output, list) and len(output) > 0:
                return output[0]  # 提取列表里的第一个元素
            
            # 如果它本身就是字符串（部分模型版本差异），直接返回
            return output

        except Exception as e:
            raise RuntimeError(f"放大服务调用失败: {str(e)}")
