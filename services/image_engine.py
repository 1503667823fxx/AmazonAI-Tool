import streamlit as st
import google.generativeai as genai

class ImageGenEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def generate(self, prompt, model_name, ref_image=None, ratio_suffix="", negative_prompt=""):
        """
        支持负向提示词的生图接口。
        """
        # 1. 预处理 Prompt
        clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
        
        # 2. 拼接 Prompt (包含风格后缀、质量词、负向词)
        # 注意：对于很多模型，直接把 Negative prompt 写在后面是有效的
        final_prompt = f"{clean_prompt} {ratio_suffix}, high quality, 8k resolution, photorealistic"
        
        if negative_prompt and negative_prompt.strip():
            final_prompt += f" --no {negative_prompt.strip()}" 
            # 注：'--no' 是某些模型的通用语法，或者用 "Exclude: ..."
            # 如果是 Gemini 模型，我们可以尝试自然语言描述：
            # final_prompt += f". Do not include: {negative_prompt}."

        # 3. 准备输入
        inputs = [final_prompt]
        if ref_image:
            inputs.append(ref_image)

        # 4. 调用 API
        try:
            gen_model = genai.GenerativeModel(model_name)
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
