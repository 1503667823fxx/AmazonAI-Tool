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

    def process_image(self, image_file, scale=4, face_enhance=False, model_type="real_esrgan", preserve_structure=False):
        """
        执行图片放大
        :param model_type: 模型类型选择
        :param preserve_structure: 是否启用结构保护模式
        :return: 放大后的图片 URL (绝对纯净的字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            # 根据模型类型选择对应的模型ID
            model_id = UpscaleConfig.MODELS.get(model_type, UpscaleConfig.MODELS["real_esrgan"])
            
            # 基础参数
            input_params = {
                "image": image_file,
            }
            
            # 根据不同模型调整参数
            if model_type == "real_esrgan":
                input_params["scale"] = scale
                input_params["face_enhance"] = face_enhance
                
            elif model_type == "real_esrgan_v2":
                # Real-ESRGAN V2 - 可能有更好的结构保持
                input_params["scale"] = scale
                input_params["face_enhance"] = face_enhance
                
            else:
                # 默认参数
                input_params["scale"] = scale
                input_params["face_enhance"] = face_enhance
            
            output = self.client.run(model_id, input=input_params)
            
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
