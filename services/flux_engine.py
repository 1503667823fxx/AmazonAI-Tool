import streamlit as st
import replicate
import io
import base64
from PIL import Image

class FluxInpaintEngine:
    def __init__(self):
        # 尝试从 Secrets 获取 Token
        self.api_token = st.secrets.get("REPLICATE_API_TOKEN")
        if not self.api_token:
            # 兼容性处理：如果没有配置 Replicate，这个模块将不可用
            self.client = None
        else:
            try:
                self.client = replicate.Client(api_token=self.api_token)
            except Exception as e:
                print(f"Replicate Init Error: {e}")
                self.client = None

    def is_ready(self):
        return self.client is not None

    def _image_to_bytes(self, image: Image.Image, format="PNG"):
        """辅助函数：PIL 转 Bytes"""
        buf = io.BytesIO()
        image.save(buf, format=format)
        buf.seek(0)
        return buf

    def generate_fill(self, image_input, mask_input, prompt, guidance_scale=30, strength=1.0, seed=None):
        """
        调用 Flux-Fill 模型进行局部重绘
        """
        if not self.client:
            raise ValueError("Replicate API Token not configured.")

        # 1. 准备输入文件流
        # Replicate python client 接受 file-like object
        img_bytes = self._image_to_bytes(image_input)
        mask_bytes = self._image_to_bytes(mask_input)

        # 2. 构造输入参数
        # 模型：black-forest-labs/flux-fill-dev (效果极好且速度尚可)
        model_id = "black-forest-labs/flux-fill-dev"
        
        input_payload = {
            "image": img_bytes,
            "mask": mask_bytes,
            "prompt": prompt,
            "guidance_scale": guidance_scale, # Flux 对 Prompt 的遵循度
            "output_format": "jpg",
            "safety_tolerance": 2 # 允许一定程度的宽松
        }
        
        if seed is not None and seed != -1:
            input_payload["seed"] = seed

        # 3. 调用 API
        try:
            # Flux Fill 通常返回一个 URL 列表
            output = self.client.run(
                model_id,
                input=input_payload
            )
            
            # 4. 下载结果图片
            if output and isinstance(output, list):
                result_url = output[0] # 获取第一张图的 URL
                # 将 URL 读回为 Bytes，方便前端处理
                import requests
                resp = requests.get(str(result_url))
                if resp.status_code == 200:
                    return resp.content
            
            return None

        except Exception as e:
            # 错误透传给前端展示
            raise e
