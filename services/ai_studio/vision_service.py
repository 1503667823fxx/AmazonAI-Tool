import streamlit as st
import io
import time
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class StudioVisionService:
    """
    [AI Studio 专属] 视觉服务
    包含生图引擎 + 视觉接力 (Visual Carry-over) 逻辑
    """
    def __init__(self, api_key):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def resolve_reference_image(self, current_msg, message_history):
        """
        [核心逻辑] 智能解析参考图
        1. 优先使用用户当前上传的图。
        2. 如果没传，自动寻找上一轮 AI 生成的图作为输入（视觉接力）。
        """
        # 情况 A: 用户本次上传了图
        if current_msg.get("ref_images"):
            return current_msg["ref_images"][0], "📸 使用本次上传的图片"
        
        # 情况 B: 视觉接力 (Visual Carry-over)
        # 检查历史记录倒数第二条（上一条是 User，再上一条是 AI）
        if len(message_history) >= 2:
            prev_ai_msg = message_history[-2] # 此时 history 已经包含 current_msg，所以是 -2
            
            # 检查是否为合法的 AI 图片消息
            if (prev_ai_msg["role"] == "model" and 
                prev_ai_msg.get("type") == "image_result" and 
                prev_ai_msg.get("hd_data")):
                
                try:
                    prev_bytes = prev_ai_msg["hd_data"]
                    img = Image.open(io.BytesIO(prev_bytes))
                    return img, "🔗 自动引用上一张生成图 (连续编辑)"
                except:
                    pass
        
        return None, None

    def generate_image(self, prompt, model_name, ref_image=None):
        """执行生图"""
        # 简单的重试与错误处理封装
        try:
            model = genai.GenerativeModel(model_name)
            inputs = [prompt]
            if ref_image:
                inputs.append(ref_image)
            
            config = genai.types.GenerationConfig(temperature=0.7)
            
            # 宽松的安全设置，防止创意被误杀
            safety = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }

            response = model.generate_content(inputs, generation_config=config, safety_settings=safety)
            
            if response.parts:
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        return part.inline_data.data
            return None
        except Exception as e:
            print(f"Vision Error: {e}")
            return None
