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
    使用 Gemini 的多模态能力进行图像扩充。
    注意：由于Gemini不支持直接的inpainting，这里使用图像理解+重新生成的方式。
    """
    try:
        # 1. 使用可用的Gemini模型
        model_name = "models/gemini-3-pro-image-preview"  # 使用稳定可用的模型
        print(f"正在调用模型: {model_name}")

        # 2. 构建更精确的提示词
        final_prompt = f"""
        你是一个专业的图像扩展AI。请分析这张图片：

        任务：图像画幅扩展 (Outpainting)
        输入：图片中心是产品主体，周围灰色区域需要填充背景
        
        要求：
        1. 保持中心产品完全不变，位置、大小、颜色、细节都不能改动
        2. 只填充灰色区域，生成与产品风格一致的背景
        3. 背景要求：{prompt}
        4. 确保光照、透视、色调与原产品完美融合
        5. 不要添加任何新的物体、文字或水印
        6. 输出高质量、无缝衔接的完整图像
        
        请生成扩展后的完整图像。
        """
        
        # 3. 配置生成参数 - 更保守的设置
        gen_config = genai.types.GenerationConfig(
            temperature=0.3,  # 降低随机性
            candidate_count=1,
            max_output_tokens=4096
        )

        model = genai.GenerativeModel(model_name)
        
        # 4. 发送请求 (重试机制)
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                # 传入 Prompt 和 参考底图
                response = model.generate_content(
                    [final_prompt, image], 
                    generation_config=gen_config,
                    safety_settings=_get_safety_settings()
                )
                
                # 5. 检查响应
                if response.parts:
                    for part in response.parts:
                        # 检查是否包含图片数据
                        if hasattr(part, "inline_data") and part.inline_data:
                            img_data = part.inline_data.data
                            return Image.open(io.BytesIO(img_data))
                
                # 如果没有图片数据，检查文本响应
                if response.text:
                    print(f"模型响应文本: {response.text}")
                    
                print(f"尝试 {attempt+1}: 未返回图片数据")
                
            except Exception as e:
                print(f"Gemini调用错误 (尝试 {attempt+1}): {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    time.sleep(3 * (attempt + 1))  # 递增等待时间
                    continue
                elif "safety" in str(e).lower():
                    # 安全过滤问题，尝试更温和的提示词
                    final_prompt = f"请扩展这张产品图片的背景，保持产品不变。背景风格：{prompt}"
                    continue
                if attempt == max_retries:
                    raise e
                    
        raise Exception("多次重试后未能生成图片")

    except Exception as e:
        st.error(f"AI绘图失败: {str(e)}")
        print(f"详细错误信息: {e}")
        # 返回原图作为兜底
        return image
