import streamlit as st
import google.generativeai as genai
from PIL import Image

API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    让 Gemini 分析原图，生成用于'填补背景'的指令。
    """
    try:
        model = genai.GenerativeModel('models/gemini-flash-latest')
        
        prompt = """
        You are an AI Art Director.
        Look at this product image.
        Write a concise prompt to EXTEND the background outwards.
        
        1. Identify the texture (e.g., marble, wood, pure white studio).
        2. Identify the lighting direction.
        3. Output a command like: "Extend the background with [Texture], using [Lighting], keeping the style clean and seamless."
        
        CRITICAL: DO NOT describe the product itself. Only describe the environment to be generated.
        """
        
        response = model.generate_content([prompt, image])
        analysis = response.text.strip()
        
        return analysis
        
    except Exception as e:
        print(f"Vision Error: {e}")
        return "Extend the background with a clean, high-quality studio setting, soft lighting, seamless integration."
