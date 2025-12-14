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
            
            # 更详细的outpainting提示词
            simple_prompt = f"""Outpaint this image to {ratio_w}:{ratio_h} aspect ratio.
            
Task: Image outpainting (canvas expansion)
- Keep the original image content exactly as is
- Expand the canvas to fit {ratio_w}:{ratio_h} ratio
- Fill new areas with seamless background extension
- Do NOT crop or remove any part of the original image
- Only ADD background content to achieve the target aspect ratio"""
            
            response = model.generate_content([simple_prompt, image])
            
            if response.parts:
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        img_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(img_data))
                        
                        # 检查是否真的扩展了（而不是裁剪）
                        orig_w, orig_h = image.size
                        gen_w, gen_h = result_image.size
                        gen_ratio = gen_w / gen_h
                        target_ratio_val = ratio_w / ratio_h
                        
                        # 判断是扩展还是裁剪
                        if gen_w >= orig_w or gen_h >= orig_h:
                            st.success(f"✅ 扩展成功！原尺寸: {orig_w}×{orig_h} → 新尺寸: {gen_w}×{gen_h}, 比例: {gen_ratio:.2f}")
                        else:
                            st.warning(f"⚠️ 检测到裁剪而非扩展。原尺寸: {orig_w}×{orig_h} → 新尺寸: {gen_w}×{gen_h}")
                        
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
