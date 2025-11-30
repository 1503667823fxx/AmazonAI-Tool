import streamlit as st
import replicate
import io

# 获取 Replicate API Token
REPLICATE_API_TOKEN = st.secrets.get("REPLICATE_API_TOKEN") or st.secrets["replicate"]["api_token"]

def image_to_bytes(img):
    """辅助函数：PIL转Bytes"""
    buf = io.BytesIO()
    # 强制转为PNG格式发送给API
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def fill_image(image, mask, prompt):
    """
    调用 Flux Fill 模型进行扩画
    【关键修复】：增加负向提示词，防止影分身。
    """
    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        
        image_bytes = image_to_bytes(image)
        mask_bytes = image_to_bytes(mask)
        
        model_id = "black-forest-labs/flux-fill-pro" 
        
        # --- 核心修改：添加强力的负向提示词 ---
        # 告诉模型：不要有人，不要重复，不要乱加东西，不要文字，不要模糊
        negative_prompt = "people, person, humans, duplicated subjects, extra objects, text, watermark, blurry, distorted, low quality, ugly"

        output = client.run(
            model_id,
            input={
                "image": image_bytes,
                "mask": mask_bytes,
                "prompt": prompt,
                # 【新增】负向提示词
                "negative_prompt": negative_prompt, 
                # 适当降低引导值，让模型更关注原图融合而不是过度听从prompt
                "guidance_scale": 25, 
                "steps": 25,
                "output_format": "jpg",
                "safety_tolerance": 5
            }
        )
        
        # 处理返回结果 (流对象转Bytes)
        if isinstance(output, list):
            output = output[0]

        if hasattr(output, "read"):
            return output.read()
        
        return output

    except Exception as e:
        print(f"Replicate Error Details: {e}")
        raise e
