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

    def process_image(self, image_file, scale_factor=2):
        """
        使用Crystal Upscaler模型执行图片放大
        根据你提供的正确代码实现
        :param image_file: 上传的图片文件
        :param scale_factor: 放大倍数 (默认2倍)
        :return: 放大后的图片 URL (字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            # 根据你提供的正确代码，Crystal Upscaler需要image和scale_factor参数
            input_params = {
                "image": image_file,
                "scale_factor": scale_factor
            }
            
            # 调用Crystal Upscaler模型
            output = self.client.run(UpscaleConfig.MODEL_ID, input=input_params)
            
            # 根据你的参考代码处理输出
            if hasattr(output, 'url'):
                # 使用 output.url 属性 (不是方法)
                return str(output.url)
            elif hasattr(output, 'read'):
                # 如果有read方法，说明是文件对象，需要获取URL
                return str(output)
            else:
                # 直接转换为字符串
                return str(output)

        except Exception as e:
            raise RuntimeError(f"Crystal Upscaler模型调用失败: {str(e)}")
