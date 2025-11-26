import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import io
import sys
import os

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download
except ImportError:
    pass 

st.set_page_config(page_title="Visual Studio", page_icon="🎨", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# API Check
if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

st.title("🎨 视觉工场 (Visual Studio)")
st.caption("Flux Pro 商业级文生图 & 4K 画质增强中心")

tab_txt2img, tab_upscale = st.tabs(["✨ 文生图 (Text-to-Image)", "🔍 画质增强 (Upscale)"])

# ==========================================
# Tab 1: 文生图 (Flux Pro)
# ==========================================
with tab_txt2img:
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        st.subheader("1. 创意描述")
        prompt_text = st.text_area("画面描述 (中文)", height=120, placeholder="例如：一只穿着宇航服的猫，站在火星表面，电影质感，4k分辨率...")
        
        # 辅助润色
        if st.button("🪄 AI 润色指令 (Magic Prompt)"):
            if prompt_text:
                with st.spinner("Gemini 正在优化提示词..."):
                    try:
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
                        resp = model.generate_content(f"Translate and optimize this for Flux.1 image generation model (English only, highly detailed): {prompt_text}")
                        st.session_state["flux_prompt"] = resp.text.strip()
                        st.rerun()
                    except Exception as e:
                        st.error(f"润色失败: {e}")
        
        final_prompt = st.text_area("最终指令 (英文)", value=st.session_state.get("flux_prompt", ""), height=120, help="Flux 模型直接读取此内容")
        
        ar = st.selectbox("画幅比例", ["1:1", "16:9", "9:16", "4:3", "3:2"], index=0)
        
        if st.button("🚀 生成图片 (Flux 1.1 Pro)", type="primary"):
            if final_prompt:
                with st.spinner("Flux 正在绘图 (约 10-15秒)..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-1.1-pro",
                            input={
                                "prompt": final_prompt,
                                "aspect_ratio": ar,
                                "output_format": "jpg",
                                "output_quality": 95,
                                "safety_tolerance": 2
                            }
                        )
                        st.session_state["flux_result"] = str(output)
                    except Exception as e:
                        st.error(f"生成失败: {e}")

    with col2:
        st.subheader("2. 生成结果")
        if "flux_result" in st.session_state:
            st.image(st.session_state["flux_result"], caption="Flux 生成结果", use_container_width=True)
            st.markdown(f"**Prompt:** _{final_prompt}_")
        else:
            st.info("等待生成...")

# ==========================================
# Tab 2: 画质增强 (Upscale)
# ==========================================
with tab_upscale:
    st.subheader("🔍 4K/8K 超清修复")
    st.info("使用 Real-ESRGAN 算法将低清图片无损放大 4 倍。")
    
    u_col1, u_col2 = st.columns([1, 1])
    
    with u_col1:
        up_img = st.file_uploader("上传低清图片", type=["jpg", "png", "webp"])
        if up_img:
            st.image(up_img, caption="原图", use_container_width=True)
            
        if st.button("🚀 开始放大 (4x)"):
            if up_img:
                with st.spinner("正在进行超分辨率处理..."):
                    try:
                        output = replicate.run(
                            "nightmareai/real-esrgan",
                            input={
                                "image": up_img,
                                "scale": 4,
                                "face_enhance": True
                            }
                        )
                        st.session_state["up_result"] = str(output)
                    except Exception as e:
                        st.error(f"放大失败: {e}")
    
    with u_col2:
        if "up_result" in st.session_state:
            st.image(st.session_state["up_result"], caption="4K 增强结果", use_container_width=True)
