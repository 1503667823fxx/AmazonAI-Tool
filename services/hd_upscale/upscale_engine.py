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
        使用Real-ESRGAN模型执行图片放大
        :param image_file: 上传的图片文件
        :param scale: 放大倍数 (2 或 4)
        :param face_enhance: 是否启用面部增强
        :return: 放大后的图片 URL (字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            # Real-ESRGAN模型的输入参数
            input_params = {
                "image": image_file,
                "scale": scale,
                "face_enhance": face_enhance
            }
            
            # 调用Real-ESRGAN模型
            output = self.client.run(UpscaleConfig.MODEL_ID, input=input_params)
            
            # 处理输出结果
            if isinstance(output, list) and len(output) > 0:
                # 如果是列表，取第一个元素
                result = output[0]
                return str(result)
            else:
                # 直接转换为字符串
                return str(output)

        except Exception as e:
            raise RuntimeError(f"图片放大失败: {str(e)}")
