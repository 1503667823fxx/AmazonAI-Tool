import streamlit as st
import requests
import json
import base64
from PIL import Image
import io
import sys
import os

# --- 0. 引入门禁 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    if not auth.check_password(): st.stop()
except ImportError:
    pass 

st.set_page_config(page_title="API 终极实验室", page_icon="🧪", layout="wide")

st.title("🧪 Gemini API 终极实验室 (Raw HTTP 版)")
st.info("本页面绕过 Python SDK，直接使用 HTTP 请求轰炸谷歌服务器，以复刻 TS 代码的成功逻辑。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

API_KEY = st.secrets["GOOGLE_API_KEY"]

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数复刻")
    
    # 这里的默认值改成了你 TS 代码里成功的模型
    model_name = st.text_input(
        "模型名称", 
        value="gemini-2.5-flash-image", 
        help="TS代码中使用的是 'gemini-2.5-flash-image'。这是关键！"
    )
    
    uploaded_file = st.file_uploader("上传测试图片", type=["jpg", "png", "webp"])
    
    # 复刻 TS 代码中的 Prompt 结构
    default_prompt = """Task: High-Fidelity Image Generation.
Input 1: Source Image.
Instructions:
1. Modify the image according to the user request.
2. Maintain photorealism and texture consistency.
User Request: Change the background to a luxury office."""
    
    prompt = st.text_area("提示词 (模仿 TS 结构)", value=default_prompt, height=200)

with col2:
    st.subheader("2. 原始响应诊断")
    
    if st.button("🚀 发送 Raw HTTP 请求", type="primary"):
        if not uploaded_file:
            st.warning("请先上传图片")
        else:
            status = st.empty()
            debug_expander = st.expander("🔍 查看完整的 JSON 响应包", expanded=True)
            
            try:
                status.info("正在构建 Payload (模拟 TS 格式)...")
                
                # 1. 图片转 Base64 (不带头)
                img_bytes = uploaded_file.getvalue()
                b64_img = base64.b64encode(img_bytes).decode('utf-8')
                
                # 2. 构建原生 JSON Payload
                # 这是谷歌 API 最底层的格式，绝对不会错
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png", # 即使上传的是jpg，告诉API这是png有时更稳，或者老实填
                                    "data": b64_img
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "response_modalities": ["IMAGE"], # 关键参数
                        "temperature": 0.4
                    }
                }
                
                # 3. 发起请求
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
                
                status.info(f"正在 POST: {url} ...")
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload)
                )
                
                # 4. 诊断结果
                if response.status_code == 200:
                    status.success(f"HTTP 200 OK! 请求成功！")
                    res_json = response.json()
                    
                    # 在折叠框里显示原始 JSON
                    with debug_expander:
                        st.json(res_json)
                    
                    # 尝试提取图片
                    try:
                        candidates = res_json.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            found_img = False
                            for part in parts:
                                if "inline_data" in part:
                                    b64_data = part["inline_data"]["data"]
                                    mime_type = part["inline_data"].get("mime_type", "image/png")
                                    
                                    img_data = base64.b64decode(b64_data)
                                    st.image(img_data, caption=f"API 返回的图片 ({mime_type})")
                                    
                                    # 下载按钮
                                    st.download_button(
                                        "📥 下载生成的图片",
                                        data=img_data,
                                        file_name="generated.png",
                                        mime=mime_type
                                    )
                                    found_img = True
                            
                            if not found_img:
                                st.error("⚠️ JSON 里没有找到 'inline_data' 字段，可能返回了文本或被拦截。")
                        else:
                            st.error("⚠️ JSON 里没有 'candidates' 字段。")
                            
                    except Exception as parse_e:
                        st.error(f"解析 JSON 图片失败: {parse_e}")
                        
                else:
                    status.error(f"HTTP {response.status_code} - 请求失败")
                    st.error(response.text) # 打印报错详情
                    
            except Exception as e:
                st.error(f"系统错误: {e}")
