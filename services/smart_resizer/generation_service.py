import streamlit as st
import replicate
import io
import base64

# 初始化配置
# 确保 secrets.toml 中配置: [replicate] api_token = "..." 或 REPLICATE_API_TOKEN
# Replicate 客户端会自动读取环境变量或 st.secrets (如果有设置环境变量的话)
# 显式获取以防万一
REPLICATE_API_TOKEN = st.secrets.get("REPLICATE_API_TOKEN") or st.secrets["replicate"]["api_token"]

def image_to_bytes(img):
    """辅助函数：PIL转Bytes"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def fill_image(image, mask, prompt):
    """
    调用 Flux Fill 模型进行扩画
    """
    # 准备 API 客户端
    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    
    # 将 PIL 图片转换为文件对象供 API 上传
    image_bytes = image_to_bytes(image)
    mask_bytes = image_to_bytes(mask)
    
    # 模型选择: flux-fill-pro (质量最高) 或 flux-fill-dev (开发用)
    # 注意：Flux Fill API 接收原图和mask
    model_id = "black-forest-labs/flux-fill-pro" 
    
    output = client.run(
        model_id,
        input={
            "image": image_bytes,
            "mask": mask_bytes,
            "prompt": prompt,
            "guidance_scale": 30, # Flux Fill 通常需要较高的引导值以保持一致性
            "steps": 20,
            "output_format": "jpg",
            "safety_tolerance": 5
        }
    )
    
    # Replicate 返回的是 URL 或者是 URL 列表
    if isinstance(output, list):
        return output[0]
    return output
