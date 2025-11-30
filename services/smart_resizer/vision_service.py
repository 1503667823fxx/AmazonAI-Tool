import streamlit as st
import google.generativeai as genai
from PIL import Image

# 初始化配置
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    使用 Gemini 快速分析图片背景特征。
    【关键修复】：强制 Gemini 忽略主体，只输出极简的环境纹理描述。
    """
    try:
        # 使用最新的 Flash 模型
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        # --- 核心修改：极简主义 Prompt ---
        # 我们不需要 Gemini 写小作文，只需要几个关键词。
        prompt = """
        Task: You are an AI visual analyst assisting an image outpainting model.
        The center subject of this image will be masked and protected. Your ONLY job is to describe the empty surrounding environment to fill the canvas seamlessly.

        Rules:
        1. CRITICAL: DO NOT mention any person, product, object, costume, or subject in the image.
        2. Describe ONLY background texture, lighting, and color.
        3. Keep it extremely concise (under 15 words).
        4. If the background is plain studio, just say "seamless studio background".

        Example good output: "soft diffused studio lighting, clean white seamless wall, minimal texture"
        Example BAD output: "A person standing on a white floor" (Do not do this).

        Analyze the provided image and output the prompt now:
        """
        
        response = model.generate_content([prompt, image])
        cleaned_prompt = response.text.strip()
        # 兜底，如果 Gemini 还是废话太多，截断它
        if len(cleaned_prompt) > 100:
             cleaned_prompt = cleaned_prompt[:100]
             
        print(f"Generated Prompt: {cleaned_prompt}") # 在控制台打印出来看看
        return cleaned_prompt
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # 降级方案：对于电商白底图，最稳妥的通用提示
        return "seamless clean studio background, soft uniform lighting, high quality."
