import streamlit as st
import replicate
import io
import base64

# 获取 Replicate API Token
REPLICATE_API_TOKEN = st.secrets.get("REPLICATE_API_TOKEN") or st.secrets["replicate"]["api_token"]

def image_to_bytes(img):
    """辅助函数：PIL转Bytes"""
    buf = io.BytesIO()
    # 强制转为PNG格式发送给API，避免格式兼容问题
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def fill_image(image, mask, prompt):
    """
    调用 Flux Fill 模型进行扩画
    """
    try:
        # 准备 API 客户端
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        
        # 将 PIL 图片转换为文件对象供 API 上传
        image_bytes = image_to_bytes(image)
        mask_bytes = image_to_bytes(mask)
        
        # 模型选择: 使用 Pro 版本以获得最佳商业效果
        model_id = "black-forest-labs/flux-fill-pro" 
        
        output = client.run(
            model_id,
            input={
                "image": image_bytes,
                "mask": mask_bytes, # 白色区域会被重绘(扩充区)，黑色区域保留(原图)
                "prompt": prompt,
                "guidance_scale": 50, # 提高引导值，让它更听从Prompt的描述
                "steps": 25,          # 步数适中，平衡速度和质量
                "output_format": "jpg",
                "safety_tolerance": 5
            }
        )
        
        # --- 核心修复部分 ---
        # Replicate SDK 可能返回 URL 字符串，也可能返回 FileOutput 对象
        
        # 1. 如果是列表（Flux有时返回列表），取第一个
        if isinstance(output, list):
            output = output[0]

        # 2. 如果是 FileOutput 对象（即没有 read 方法但有 url 属性，或者是生成器），
        # 最稳妥的方法是：如果它有 read 方法，就 read() 成 bytes；
        # 如果它是 URL 字符串，直接返回；
        # Replicate 的 FileOutput 对象通常可以像文件一样 read()
        
        if hasattr(output, "read"):
            return output.read()  # 返回二进制数据，st.image 可以直接显示
        
        # 3. 如果是 URL 字符串，也直接返回
        return output

    except Exception as e:
        # 捕获并打印详细错误，方便调试
        print(f"Replicate Error Details: {e}")
        raise e
