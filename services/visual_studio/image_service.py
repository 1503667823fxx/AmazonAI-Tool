import streamlit as st
import replicate
import os

# 确保环境变量中有 Token，供 replicate SDK 使用
if "replicate_api_token" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["replicate_api_token"]

def generate_image_replicate(prompt: str, aspect_ratio: str, output_format: str = "png", safety_tolerance: int = 2) -> str:
    """
    调用 Replicate 上的 Flux 模型生成图片。
    
    Args:
        prompt: 英文提示词
        aspect_ratio: 图片比例 (例如 "16:9")
        output_format: "png", "jpg", "webp"
        safety_tolerance: 安全等级 (1-5)
        
    Returns:
        str: 生成图片的 URL 地址
    """
    
    # 1. 确定模型版本 ID
    # Flux-Schnell (快速版) vs Flux-Dev (开发版/高质量)
    # 这里我们默认用 black-forest-labs 官方版本
    # 如果您想支持切换，可以通过参数传入 model_type
    
    # 示例中使用black-forest-labs/flux-2-pro因为它生成极致画质

    model_id = "black-forest-labs/flux-2-pro, prunaai/flux-fast" 
    
    input_params = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,  # Flux 支持直接传 "16:9", "1:1" 等字符串
        "output_format": output_format,
        "disable_safety_checker": False,
        "safety_tolerance": safety_tolerance
    }
    
    try:
        # 2. 调用 Replicate API
        # output 通常是一个列表，包含图片 URL
        output = replicate.run(
            model_id,
            input=input_params
        )
        
        # 3. 解析结果
        if output and isinstance(output, list) and len(output) > 0:
            # output[0] 是一个 FileOutput 对象或 URL 字符串
            return str(output[0])
        else:
            raise ValueError("Replicate API 返回结果为空")
            
    except Exception as e:
        raise RuntimeError(f"Replicate 生图失败: {str(e)}")
