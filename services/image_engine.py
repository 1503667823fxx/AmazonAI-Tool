import streamlit as st
import google.generativeai as genai

class ImageGenEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def generate(self, prompt, model_name, ref_image=None, ratio_suffix=""):
        """
        统一的生图接口。
        Args:
            prompt (str): 提示词
            model_name (str): 模型名称 (e.g., gemini-2.5-flash-image)
            ref_image (PIL.Image): 参考图 (可选)
            ratio_suffix (str): 比例后缀字符串 (e.g., ", crop 1:1")
        Returns:
            bytes: 图片字节流 或 None
        """
        # 1. 预处理 Prompt
        clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
        final_prompt = f"{clean_prompt} {ratio_suffix}, high quality, 8k resolution, photorealistic"

        # 2. 准备输入
        inputs = [final_prompt]
        if ref_image:
            inputs.append(ref_image)

        # 3. 调用 API
        try:
            gen_model = genai.GenerativeModel(model_name)
            # 使用 stream=True 模式获取 inline_data
            response = gen_model.generate_content(inputs, stream=True)
            
            for chunk in response:
                if hasattr(chunk, "parts"):
                    for part in chunk.parts:
                        if part.inline_data:
                            return part.inline_data.data
        except Exception as e:
            st.error(f"Image Gen Error ({model_name}): {e}")
            return None
        return None
