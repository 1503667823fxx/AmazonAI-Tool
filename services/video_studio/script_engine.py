import json
import re
import google.generativeai as genai
import streamlit as st

def _clean_json_string(json_str):
    """
    内部工具：清洗 LLM 返回的字符串，提取有效的 JSON 部分。
    防止 LLM 返回 "Here is your JSON code: ```json ... ```" 导致解析失败。
    """
    try:
        # 尝试直接解析
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 1. 移除 Markdown 代码块标记
        pattern = r"```json(.*?)```"
        match = re.search(pattern, json_str, re.DOTALL)
        if match:
            clean_str = match.group(1).strip()
            return json.loads(clean_str)
        
        # 2. 如果没有代码块，尝试寻找第一个 { 和最后一个 }
        start_idx = json_str.find('{')
        end_idx = json_str.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_str = json_str[start_idx:end_idx+1]
            return json.loads(clean_str)
            
        raise ValueError("无法从模型返回中提取有效的 JSON 数据")

def generate_video_script(api_key, product_info, video_duration=15, style="Amazon Minimalist"):
    """
    核心功能：根据商品信息生成分镜脚本。
    
    Args:
        api_key (str): 从 st.secrets 获取的 Google API 密钥
        product_info (str): 商品标题、卖点或 ASIN 信息
        video_duration (int): 目标时长（秒）
        style (str): 视频风格
    
    Returns:
        dict: 包含场景列表的结构化数据
    """
    
    # 配置 Gemini API
    genai.configure(api_key=api_key)

    # 亚马逊视频专用 Prompt：强调视觉冲击和卖点
    system_prompt = f"""
    You are an expert Video Director specialized in Amazon E-commerce videos.
    Your goal is to create a high-conversion video script for a product.
    
    TARGET AUDIENCE: Amazon shoppers (high intent, short attention span).
    TOTAL DURATION: Approx {video_duration} seconds.
    STYLE: {style}.
    
    OUTPUT FORMAT:
    You must output ONLY a valid JSON object. Do not add any conversational text.
    The JSON structure must be:
    {{
        "title": "Video Title",
        "scenes": [
            {{
                "scene_id": 1,
                "visual_prompt": "Detailed prompt for AI video generator (e.g., Runway/Pika). Describe camera movement, lighting, and subject action.",
                "audio_text": "Voiceover script for this scene. Keep it punchy.",
                "duration": 3,
                "text_overlay": "Short text to show on screen (2-5 words)"
            }},
            ...
        ]
    }}
    """

    user_prompt = f"""
    Create a video script for the following product:
    {product_info}
    
    Requirements:
    1. Start with a "Hook" to grab attention immediately.
    2. Focus on the main problem the product solves.
    3. Show the product in use (Lifestyle context).
    4. End with a Call to Action.
    """

    try:
        # 使用 Gemini 3.0 Flash Preview 模型
        model = genai.GenerativeModel('gemini-3.0-flash-preview')
        
        # 组合完整的提示词
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # 生成内容
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        raw_content = response.text
        script_data = _clean_json_string(raw_content)
        return script_data

    except Exception as e:
        # 返回错误信息结构，方便前端捕获
        return {"error": str(e)}
