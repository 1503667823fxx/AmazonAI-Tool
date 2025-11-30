import streamlit as st
import requests
import json
import base64
import io
from PIL import Image

# 获取 Google API Key
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]

def image_to_base64(img: Image.Image) -> str:
    """辅助函数：将 PIL 图片转为 Base64 字符串（不带头）"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')

def fill_image(image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    """
    直接使用 HTTP 请求调用 Google Imagen 3 API (REST 方式)。
    这种方法不依赖 google-generativeai 库的版本，避免 'AttributeError'。
    """
    
    # --- 1. 准备 API 端点 ---
    # 使用 Google 官方 Imagen 3 的 REST 端点
    # 注意：模型名称通常是 'imagen-3.0-generate-001' 或 'imagen-3.0-capability-001'
    # 如果你的账号支持 gemini-3-pro-image-preview，也可以尝试，但在 API 路径中通常是通用名称
    model_name = "models/gemini-3-pro-image-preview" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:editImage?key={API_KEY}"
    
    # --- 2. 准备 Payload (请求体) ---
    payload = {
        "requests": [{
            "image": {
                "imageBytes": image_to_base64(image)
            },
            "mask": {
                "imageBytes": image_to_base64(mask) # 这里的 Mask 白色代表编辑区
            },
            "prompt": prompt,
            "parameters": {
                "sampleCount": 1,
                # 【关键】强制禁止生成人物，防止影分身
                "personGeneration": "DONT_ALLOW", 
                # 指定正方形，或者让模型自动保持原图比例
                # "aspectRatio": "1:1" 
            }
        }]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # --- 3. 发送请求 ---
        print(f"正在通过 REST API 调用模型: {model_name} ...")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # --- 4. 处理响应 ---
        if response.status_code != 200:
            # 打印详细错误信息
            error_msg = f"API Error {response.status_code}: {response.text}"
            print(error_msg)
            raise Exception(f"Google API 请求失败: {response.text}")
            
        result = response.json()
        
        # 提取图片数据
        # 结构通常是: result['image']['imageBytes'] 或 result['predictions'][0]['bytesBase64Encoded']
        # Imagen API 的返回结构可能略有不同，我们需要做兼容判断
        
        img_data = None
        
        # 尝试路径 A (常见路径)
        if 'image' in result and 'imageBytes' in result['image']:
            img_data = result['image']['imageBytes']
        # 尝试路径 B (列表路径)
        elif 'images' in result and len(result['images']) > 0:
            img_data = result['images'][0].get('imageBytes')
        else:
            # 打印返回结构以便调试
            print(f"API 返回结构未知: {result.keys()}")
            raise Exception("无法从 API 响应中提取图片数据")

        if img_data:
            # 解码 Base64 并转为 PIL
            image_bytes = base64.b64decode(img_data)
            return Image.open(io.BytesIO(image_bytes))
            
    except Exception as e:
        st.error(f"绘图服务出错: {str(e)}")
        # 可以在这里打印 response.text 查看具体是权限问题还是参数问题
        raise e
