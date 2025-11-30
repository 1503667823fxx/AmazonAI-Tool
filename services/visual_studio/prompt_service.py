import streamlit as st
import google.generativeai as genai

def _get_gemini_client():
    """配置并获取 Gemini 客户端"""
    try:
        api_key = st.secrets["google_api_key"]
        genai.configure(api_key=api_key)
        # 使用最新的 Flash 模型，速度快且免费额度高
        model = genai.GenerativeModel('models/gemini-flash-latest')
        return model
    except Exception as e:
        raise ValueError(f"Google API Key 配置错误或缺失: {str(e)}")

def optimize_prompt(user_input: str, style_preset: str) -> str:
    """
    使用 Gemini 优化提示词。
    
    Args:
        user_input: 用户原始输入 (中文/英文)
        style_preset: 选定的风格 (如 "Cinematic")
        
    Returns:
        str: 优化后的英文提示词
    """
    model = _get_gemini_client()
    
    # 构建系统指令 (System Instruction)
    # 告诉 Gemini 它是一个专业的 Midjourney/Flux 提示词工程师
    system_prompt = f"""
    You are an expert AI art prompt engineer for Flux/Midjourney models.
    
    YOUR TASK:
    1. Translate the user's input into English if it's not already.
    2. Expand it into a highly detailed visual description suitable for image generation.
    3. Incorporate the artistic style: "{style_preset}".
    4. Include keywords for lighting, composition, texture, and mood.
    5. Output ONLY the final English prompt text. Do not add explanations like "Here is the prompt:".
    
    User Input: "{user_input}"
    """
    
    try:
        # 调用生成
        response = model.generate_content(system_prompt)
        return response.text.strip()
    except Exception as e:
        # 如果出错，优雅降级：直接返回用户输入（翻译成英文最好，这里简单返回）
        print(f"Gemini Optimization Error: {e}")
        return f"{style_preset} style, {user_input}"
