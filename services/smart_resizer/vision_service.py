import streamlit as st
import google.generativeai as genai
from PIL import Image

API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    使用 Gemini 分析图片，为 Imagen 生成提示词。
    """
    try:
        # 使用最新的 Flash 模型进行快速分析
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        # 针对 Google Imagen 优化的 Prompt
        prompt = """
        Task: Describe the BACKGROUND texture and lighting of this image for an outpainting task.
        
        CRITICAL RULES:
        1. DO NOT describe the person, product, or central subject. IGNORE THEM.
        2. Focus ONLY on the empty space.
        3. Use keywords like "seamless", "clean", "studio lighting".
        4. Output format: A comma-separated list of visual qualities.
        
        Example Output: "pure white studio background, soft shadows, seamless extension, high key lighting"
        """
        
        response = model.generate_content([prompt, image])
        analysis = response.text.strip()
        
        # 强制加上这句 Magic Prompt，Imagen 对此非常受用
        final_prompt = f"{analysis}, empty background, high quality, photorealistic, 8k"
        
        print(f"Google Prompt: {final_prompt}")
        return final_prompt
        
    except Exception as e:
        print(f"Vision Error: {e}")
        return "pure white studio background, seamless, empty, high quality"
