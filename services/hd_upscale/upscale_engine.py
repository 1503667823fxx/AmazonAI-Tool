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

    def process_image(self, image_file):
        """
        使用SUPIR模型执行图片放大
        :param image_file: 上传的图片文件
        :return: 放大后的图片 URL (字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        try:
            # SUPIR模型的输入参数 (根据参考代码)
            input_params = {
                "image": image_file
            }
            
            # 调用SUPIR模型
            output = self.client.run(UpscaleConfig.MODEL_ID, input=input_params)
            
            # 处理输出结果
            if hasattr(output, 'url'):
                # 如果输出有url方法，调用它
                return str(output.url())
            elif isinstance(output, list) and len(output) > 0:
                # 如果是列表，取第一个元素
                result = output[0]
                if hasattr(result, 'url'):
                    return str(result.url())
                else:
                    return str(result)
            else:
                # 直接转换为字符串
                return str(output)

        except Exception as e:
            raise RuntimeError(f"SUPIR模型调用失败: {str(e)}")
