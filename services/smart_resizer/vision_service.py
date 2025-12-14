import streamlit as st
import google.generativeai as genai
from PIL import Image
from .config import get_model_name

API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_background(image: Image.Image) -> str:
    """
    让 Gemini 分析原图，生成用于背景扩展的精确指令。
    """
    try:
        # 使用配置文件中指定的模型进行分析
        model_name = get_model_name("vision_analysis")
        model = genai.GenerativeModel(model_name)
        
        prompt = """
        请仔细分析这张产品图片的背景特征，为智能画幅扩展提供准确指导。

        重点分析：
        1. 背景类型：纯色背景/渐变背景/纹理背景/场景背景
        2. 主要颜色：具体的颜色值或色调描述
        3. 纹理特征：光滑/粗糙/有图案/无图案
        4. 光照特点：均匀光照/有阴影/光照方向
        5. 整体风格：简约/复古/现代/自然等

        请用简洁的中文回答，格式如下：
        "背景类型，主要颜色，纹理特征，光照特点，整体风格"

        例如："纯白背景，白色，光滑无纹理，均匀柔光，简约现代"

        注意：
        - 只分析背景，忽略产品本身
        - 描述要具体准确，避免模糊词汇
        - 控制在50字以内
        """
        
        response = model.generate_content([prompt, image])
        analysis = response.text.strip()
        
        # 清理和标准化分析结果
        analysis = analysis.replace('"', '').replace('"', '').replace('"', '')
        if analysis.startswith('背景类型'):
            analysis = analysis[4:]  # 移除重复的"背景类型"
        
        # 如果分析结果太长，截取关键部分
        if len(analysis) > 100:
            analysis = analysis[:100] + "..."
            
        return analysis
        
    except Exception as e:
        print(f"背景分析错误: {e}")
        # 提供更智能的兜底分析
        return _fallback_analysis(image)

def _fallback_analysis(image: Image.Image) -> str:
    """
    当Gemini不可用时的兜底分析方法
    """
    try:
        # 简单的颜色分析
        import numpy as np
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 分析边缘区域的颜色（假设边缘是背景）
        h, w = img_array.shape[:2]
        edge_pixels = []
        
        # 采样边缘像素
        for i in range(0, w, 10):
            edge_pixels.append(img_array[0, i])  # 顶边
            edge_pixels.append(img_array[h-1, i])  # 底边
        for i in range(0, h, 10):
            edge_pixels.append(img_array[i, 0])  # 左边
            edge_pixels.append(img_array[i, w-1])  # 右边
        
        edge_pixels = np.array(edge_pixels)
        avg_color = np.mean(edge_pixels, axis=0)
        
        # 判断背景类型
        if np.all(avg_color > 240):
            return "纯白背景，白色，光滑无纹理，均匀光照，简约风格"
        elif np.all(avg_color < 50):
            return "纯黑背景，黑色，光滑无纹理，均匀光照，简约风格"
        else:
            r, g, b = avg_color.astype(int)
            return f"纯色背景，RGB({r},{g},{b})，光滑纹理，均匀光照，简约风格"
            
    except Exception:
        return "纯白背景，白色，光滑无纹理，均匀光照，简约风格"
