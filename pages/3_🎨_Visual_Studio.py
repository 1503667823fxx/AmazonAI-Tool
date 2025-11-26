import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps
import io
import sys
import os
import requests

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="视觉基础工场", page_icon="🎨", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px;}
    .stImage {border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# --- 2. Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field"

def download_image(url, filename):
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_vision_model():
    return genai.GenerativeModel('gemini-1.5-flash')

# --- Top Nav ---
st.title("🎨 亚马逊 AI 视觉工场 (基础版)")
st.info("👉 想要高级图生图/换场景？请使用左侧菜单的 **「智能图生图」** 模块。")

tabs = st.tabs(["✨ 文生图", "🔍 高清放大"])

# Tab 1: 文生图
with tabs[0]:
    st.header("✨ 文生图 (海报)")
    col1, col2 = st.columns([4, 6])
    with col1:
        prompt_text = st.text_area("画面描述", height=100)
        if st.button("🪄 润色指令"):
            if prompt_text:
                with st.spinner("Gemini 构思..."):
                    model = get_vision_model()
                    resp = model.generate_content(f"转为Flux绘画提示词(英文): {prompt_text}")
                    st.session_state["t2i_prompt"] = resp.text
                    st.rerun()
        
        final_prompt = st.text_area("最终指令", value=st.session_state.get("t2i_prompt", ""))
        ar = st.selectbox("比例", ["1:1", "16:9", "9:16"], index=0)

    with col2:
        if st.button("🚀 生成", type="primary"):
            if final_prompt:
                with st.spinner("生成中..."):
                    try:
                        out = replicate.run("black-forest-labs/flux-1.1-pro", input={"prompt": final_prompt + UNIVERSAL_QUALITY_PROMPT, "aspect_ratio": ar})
                        st.image(str(out))
                    except Exception as e:
                        st.error(e)


# Tab 4: 高清放大
with tabs[3]:
    st.header("🔍 高清放大")
    img = st.file_uploader("低清图", key="up_img")
    if st.button("🚀 放大"):
        if img:
            with st.spinner("放大中..."):
                out = replicate.run("nightmareai/real-esrgan", input={"image": img, "scale": 4})
                st.image(str(out))

