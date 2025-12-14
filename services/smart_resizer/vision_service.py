import streamlit as st
import google.generativeai as genai
from PIL import Image

API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    让 Gemini 分析原图，生成用于背景扩展的精确指令。
    """
    try:
        model = genai.GenerativeModel('models/gemini-flash-latest')
        
        prompt = """
        请分析这张产品图片的背景环境，为图像扩展提供指导。

        分析要点：
        1. 背景材质和纹理（如：纯白背景、木纹、大理石、布料等）
        2. 光照方向和强度（如：顶光、侧光、柔光、硬光）
        3. 整体色调和氛围（如：暖色调、冷色调、高对比度等）
        4. 背景风格（如：简约、工业风、自然风等）

        输出格式：
        "扩展背景：[材质描述]，[光照描述]，[色调描述]，保持[风格描述]，确保与产品无缝融合"

        注意：
        - 只描述背景环境，不要描述产品本身
        - 用中文回答
        - 保持描述简洁准确
        """
        
        response = model.generate_content([prompt, image])
        analysis = response.text.strip()
        
        # 如果分析结果太长，截取关键部分
        if len(analysis) > 200:
            analysis = analysis[:200] + "..."
            
        return analysis
        
    except Exception as e:
        print(f"背景分析错误: {e}")
        return "扩展背景：纯净白色背景，柔和均匀光照，简约现代风格，确保与产品无缝融合"
