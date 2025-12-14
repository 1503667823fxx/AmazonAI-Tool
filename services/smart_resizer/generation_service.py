import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 初始化 API
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def fill_image(image: Image.Image, mask: Image.Image, prompt: str, use_gemini: bool = True, target_ratio: tuple = None, test_mode: bool = False) -> Image.Image:
    """
    简单的Gemini画幅重构
    """
    try:
        if target_ratio:
            ratio_w, ratio_h = target_ratio
            
            # 使用Gemini进行画幅重构
            model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
            
            # 简单直接的提示词
            simple_prompt = f"请将这张图片改为 {ratio_w}:{ratio_h} 的画幅比例。"
            
            response = model.generate_content([simple_prompt, image])
            
            if response.parts:
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        img_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(img_data))
                        
                        # 显示结果信息
                        gen_w, gen_h = result_image.size
                        gen_ratio = gen_w / gen_h
                        target_ratio_val = ratio_w / ratio_h
                        st.success(f"✅ 生成成功！尺寸: {gen_w}×{gen_h}, 比例: {gen_ratio:.2f} (目标: {target_ratio_val:.2f})")
                        
                        return result_image
            
            # 检查文本响应
            if response.text:
                st.warning(f"Gemini返回文本: {response.text}")
        
        # 如果失败，返回原图
        st.error("Gemini处理失败，返回原图")
        return image
        
    except Exception as e:
        st.error(f"处理失败: {str(e)}")
        return image
