import streamlit as st
import google.generativeai as genai
from PIL import Image

# 初始化配置 (确保 secrets 里有 google_api_key)
# 建议在 secrets.toml 中配置: [google] api_key = "..." 或直接在根级配置
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    使用 Gemini Flash 1.5 快速分析图片背景特征，用于指导 Outpainting。
    """
    try:
        model = genai.GenerativeModel('models/gemini-flash-latest')
        
        # 专门针对 Outpainting 优化的 Prompt
        prompt = """
        Analyze the background texture, lighting direction, and overall style of this product image.
        Describe what the surroundings should look like if the image were extended outwards.
        Focus on:
        1. Texture (e.g., wooden table, marble, blurry nature, studio white).
        2. Lighting (e.g., soft natural light from left, hard studio lighting).
        3. Color Palette.
        
        Output a single concise English prompt for an image generation model to extend this background seamlessly. 
        Do NOT describe the product itself. Start with: "A high quality background featuring..."
        """
        
        response = model.generate_content([prompt, image])
        return response.text.strip()
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # 降级方案：如果分析失败，返回通用提示词
        return "High quality, seamless background extension, cinematic lighting, 8k resolution."
