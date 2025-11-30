import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import io
from PIL import Image
import time

# 初始化 API
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def _get_safety_settings():
    """使用宽松的安全设置，避免误杀电商图"""
    return {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

def fill_image(image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    """
    使用 Gemini 3 Pro 的多模态能力进行'图生图'扩充。
    注意：这里其实是把 Padded 过的原图喂给模型，让它重绘整张图。
    """
    try:
        # 1. 模型选择 (你验证过可用的模型)
        model_name = "models/gemini-3-pro-image-preview" 
        print(f"正在调用模型: {model_name}")

        # 2. 构建输入
        # 这里的 image 已经是 image_tools 处理过带灰色边框的图
        # 我们需要明确告诉 Gemini：中间是产品，边框是空的，请填满
        final_prompt = f"""
        Function: Image Expansion / Outpainting.
        Input: The provided image contains a product in the center surrounded by gray/empty padding.
        Task: {prompt}
        Requirement: 
        1. Keep the central product EXACTLY as it is. 
        2. Fill the gray padding area with a background that matches the product's lighting and perspective seamlessly.
        3. Do NOT add any new objects, people, or text.
        4. High fidelity, photorealistic, 8k resolution.
         --no people, text, watermark, distortion, mutation
        """
        
        # 3. 配置生成参数
        gen_config = genai.types.GenerationConfig(
            temperature=0.4, # 稍微降低创造性，求稳
            candidate_count=1
        )

        model = genai.GenerativeModel(model_name)
        
        # 4. 发送请求 (重试机制)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # 传入 Prompt 和 参考底图
                response = model.generate_content(
                    [final_prompt, image], 
                    generation_config=gen_config,
                    safety_settings=_get_safety_settings()
                )
                
                # 5. 解析结果
                if response.parts:
                    for part in response.parts:
                        # 检查是否包含图片数据 (inline_data)
                        if hasattr(part, "inline_data") and part.inline_data:
                            img_data = part.inline_data.data
                            return Image.open(io.BytesIO(img_data))
                
                print(f"尝试 {attempt+1}: 未返回图片数据。")
                
            except Exception as e:
                print(f"Gemini Gen Error (Attempt {attempt}): {e}")
                if "429" in str(e): # 资源耗尽
                    time.sleep(2)
                    continue
                if attempt == max_retries:
                    raise e
                    
        raise Exception("多次重试后未能生成图片")

    except Exception as e:
        st.error(f"绘图失败: {str(e)}")
        # 返回原图作为兜底，防止程序崩溃
        return image
