import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import requests
import time

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="视觉工场", page_icon="🎨", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 自定义 CSS ---
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px;}
    .stImage {border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .stTabs [data-baseweb="tab-list"] {gap: 20px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0;}
    .stTabs [aria-selected="true"] {background-color: #ffffff; border-top: 3px solid #ff9900;}
    /* 优化文本域字体 */
    .stTextArea textarea {font-family: 'Consolas', monospace; font-size: 14px;}
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 底层提示词常量 (Base Prompts) ---
UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field, masterpiece, sharp focus"
UNIVERSAL_NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly, pixelated, watermark, text, signature, bad anatomy, deformed, lowres, bad hands"

# --- 4. 辅助函数 ---
def download_image(url, filename):
    """提供下载链接"""
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_vision_model():
    """获取视觉模型，使用 2.5-flash (对应你的账号权限)"""
    return genai.GenerativeModel('gemini-2.5-flash')

# --- 5. 顶部导航 ---
st.title("🎨 亚马逊 AI 视觉工场 (All-in-One)")
st.caption("集成 FLUX.1 Pro, FLUX-Fill, Real-ESRGAN 等顶级模型")

# 初始化 Session State
if "i2i_final_prompt" not in st.session_state:
    st.session_state["i2i_final_prompt"] = ""
if "t2i_final_prompt" not in st.session_state:
    st.session_state["t2i_final_prompt"] = ""

# 创建 6 个功能分区
tabs = st.tabs([
    "✨ 文生图 (海报)", 
    "🖼️ 图生图 (智能变体)", 
    "🖌️ 局部重绘 (换背景)", 
    "↔️ 画幅调整 (扩展)", 
    "🔍 高清放大", 
    "🧩 A+ 拼接助手"
])

# ==================================================
# Tab 1: 文生图 (创意海报/Banner)
# ==================================================
with tabs[0]:
    st.header("✨ 文生图 (Text-to-Image)")
    col1, col2 = st.columns([4, 6])
    
    with col1:
        st.info("适用于：从零创造创意海报、抽象背景、营销素材。")
        prompt_text = st.text_area("画面描述 (支持中文)", height=150, placeholder="例如：一个极其精美的圣诞节礼品盒，放在雪地上，背景是模糊的圣诞树，暖光，8k分辨率...")
        
        # Gemini 润色
        if st.button("🪄 Gemini 润色指令 (快速版)", key="t2i_optimize"):
            if not prompt_text:
                st.warning("请先输入描述")
            else:
                with st.spinner("Gemini 2.5 Flash 正在构思..."):
                    try:
                        model = get_vision_model()
                        p = f"你是一个商业插画师。将此描述转换为FLUX模型的英文Prompt，强调光影和质感，直接输出英文，不要解释：{prompt_text}"
                        resp = model.generate_content(p)
                        
                        # 【修复点】强制更新文本框的 Key
                        st.session_state["t2i_final_prompt"] = resp.text
                        st.session_state["t2i_final"] = resp.text  # 强制覆盖 Widget Key
                        
                        st.success("润色完成！")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gemini 调用失败: {e}")

        final_prompt_t2i = st.text_area("最终指令 (英文)", value=st.session_state.get("t2i_final_prompt", ""), height=100, key="t2i_final")
        ar_t2i = st.selectbox("比例", ["1:1", "16:9", "9:16", "4:5"], key="t2i_ar")

    with col2:
        if st.button("🚀 生成海报", type="primary", key="t2i_run"):
            if not final_prompt_t2i:
                st.warning("指令不能为空")
            else:
                with st.spinner("FLUX 正在绘画..."):
                    try:
                        full_prompt = final_prompt_t2i + UNIVERSAL_QUALITY_PROMPT
                        output = replicate.run(
                            "black-forest-labs/flux-1.1-pro",
                            input={"prompt": full_prompt, "aspect_ratio": ar_t2i, "output_quality": 100}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "poster.jpg")
                    except Exception as e:
                        st.error(f"生成失败: {e}")

# ==================================================
# Tab 2: 图生图 (智能变体 - 重点修复版)
# ==================================================
with tabs[1]:
    st.header("🖼️ 图生图 (Image-to-Image 3.0)")
    st.caption("Gemini 2.5 Flash (极速版) + FLUX 绘图引擎")
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 素材与构思")
        ref_img = st.file_uploader("上传参考图 (Gemini将读取产品特征)", type=["jpg", "png", "webp"], key="i2i_up")
        if ref_img:
            img_obj = Image.open(ref_img)
            st.image(img_obj, width=200, caption="参考原图")
        
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            user_modifications = st.text_area("修改要求", height=100, placeholder="例如：改成素描风格，或者让产品看起来更亮...")
        with col_in2:
            scene_context = st.text_area("植入场景", height=100, placeholder="例如：放在高档大理石桌面上，背景是温馨的客厅...")

        strength = st.slider("重绘幅度 (Image Strength)", 0.1, 1.0, 0.75, help="数值越大，AI发挥空间越大（越不像原图）。")

        # 智能合成按钮
        if st.button("✨ 生成 Prompt (快速响应)", type="secondary", key="i2i_magic_new"):
            if not ref_img:
                st.warning("请先上传参考图！")
            else:
                # 进度显示条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("⏳ 1/3: 正在压缩图片以加速传输...")
                    progress_bar.progress(30)
                    
                    # 1. 强力压缩图片 (防止大图卡死)
                    img_small = img_obj.copy()
                    img_small.thumbnail((512, 512)) 
                    
                    status_text.text("⏳ 2/3: Gemini 2.5 Flash 正在极速分析...")
                    progress_bar.progress(60)
                    
                    # 2. 调用 Gemini 2.5 Flash
                    model = get_vision_model()
                    
                    synthesis_prompt = f"""
                    你是一个精通 FLUX 绘画模型的提示词专家。
                    请基于图片内容，结合用户要求："{user_modifications}" 和场景："{scene_context}"，
                    写一段高质量英文 Prompt。
                    要求：提取产品核心特征，自然融入新场景。
                    直接输出英文，不要解释。
                    """
                    
                    response = model.generate_content([synthesis_prompt, img_small])
                    generated_text = response.text
                    
                    status_text.text("✅ 3/3: 完成！正在刷新界面...")
                    progress_bar.progress(100)
                    
                    # 3. 更新并刷新 - 【关键修复点】
                    # 不仅更新 session 变量，还强制更新 widget key
                    st.session_state["i2i_final_prompt"] = generated_text
                    st.session_state["i2i_final_text"] = generated_text 
                    
                    time.sleep(0.2) 
                    st.rerun()
                    
                except Exception as e:
                    status_text.empty()
                    st.error(f"Gemini 报错: {e}")

    # === 右侧：生成与结果 ===
    with col2:
        st.subheader("2. 生成控制")
        
        final_prompt_display = st.text_area(
            "最终指令 (自动追加画质词)", 
            value=st.session_state["i2i_final_prompt"], 
            height=150,
            key="i2i_final_text"
        )
        
        with st.expander("查看底层预设", expanded=False):
            st.markdown(f"**自动正向词:** `{UNIVERSAL_QUALITY_PROMPT}`")

        if st.button("🚀 生成变体 (Run FLUX)", type="primary", key="i2i_run_flux"):
            if not ref_img or not final_prompt_display:
                st.warning("请完善信息")
            else:
                with st.spinner("🎨 FLUX 正在重绘..."):
                    try:
                        full_prompt = final_prompt_display + UNIVERSAL_QUALITY_PROMPT
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={
                                "prompt": full_prompt, 
                                "image": ref_img,
                                "prompt_strength": 1 - strength,
                                "go_fast": True,
                                "megapixels": "1",
                                "num_outputs": 1,
                                "output_format": "jpg",
                                "output_quality": 100,
                                "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT 
                            }
                        )
                        image_url = str(output[0])
                        st.image(image_url, caption="FLUX 生成结果", use_column_width=True)
                        download_image(image_url, "variant_gen.jpg")
                    except Exception as e:
                        st.error(f"生成失败: {e}")

# ==================================================
# Tab 3: 局部重绘
# ==================================================
with tabs[2]:
    st.header("🖌️ 局部重绘 & 换背景")
    st.info("基于 FLUX-Fill 模型。")
    col1, col2 = st.columns([4, 6])
    with col1:
        inp_img = st.file_uploader("上传原图", type=["jpg", "png"], key="inp_up")
        inp_mask = st.file_uploader("上传蒙版 (白色为重绘区)", type=["jpg", "png"], key="inp_mask")
        inp_prompt = st.text_area("重绘描述", placeholder="例如：A luxury marble table...", key="inp_prompt")
    with col2:
        if st.button("🚀 开始重绘", type="primary", key="inp_run"):
            if not inp_img or not inp_mask or not inp_prompt:
                st.warning("请上传图片和蒙版")
            else:
                with st.spinner("FLUX-Fill 正在填补..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={"image": inp_img, "mask": inp_mask, "prompt": inp_prompt + UNIVERSAL_QUALITY_PROMPT, "output_format": "jpg"}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "inpainted.jpg")
                    except Exception as e:
                        st.error(f"重绘失败: {e}")

# ==================================================
# Tab 4: 画幅调整
# ==================================================
with tabs[3]:
    st.header("↔️ 画幅调整 (Outpainting)")
    st.info("把 1:1 扩展成 16:9 Banner。")
    col1, col2 = st.columns([4, 6])
    with col1:
        out_img = st.file_uploader("上传原图", type=["jpg", "png"], key="out_up")
        target_ar = st.selectbox("目标比例", ["16:9", "9:16", "4:3", "3:2"], key="out_ar")
        out_prompt = st.text_input("背景描述", placeholder="例如：extended blurred living room background")
    with col2:
        if st.button("🚀 智能扩展", type="primary", key="out_run"):
            if not out_img or not out_prompt:
                st.warning("请上传图片")
            else:
                with st.spinner("FLUX-Fill 扩展中..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={"image": out_img, "prompt": out_prompt + UNIVERSAL_QUALITY_PROMPT, "aspect_ratio": target_ar.split(" ")[0], "output_format": "jpg"}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "expanded.jpg")
                    except Exception as e:
                        st.error(f"扩展失败: {e}")

# ==================================================
# Tab 5: 高清放大
# ==================================================
with tabs[4]:
    st.header("🔍 图片高清放大")
    col1, col2 = st.columns([4, 6])
    with col1:
        upscale_img = st.file_uploader("上传低清图", type=["jpg", "png"], key="up_up")
        scale = st.slider("放大倍数", 2, 10, 4)
        face_enhance = st.checkbox("人脸增强", value=False)
    with col2:
        if st.button("🚀 开始放大", type="primary", key="up_run"):
            if not upscale_img:
                st.warning("请上传图片")
            else:
                with st.spinner("像素修复中..."):
                    try:
                        output = replicate.run(
                            "nightmareai/real-esrgan",
                            input={"image": upscale_img, "scale": scale, "face_enhance": face_enhance}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "upscaled_hd.jpg")
                    except Exception as e:
                        st.error(f"放大失败: {e}")

# ==================================================
# Tab 6: A+ 拼接助手
# ==================================================
with tabs[5]:
    st.header("🧩 A+ 拼接预览")
    uploaded_files = st.file_uploader("上传多张图片", type=['jpg','png'], accept_multiple_files=True, key="aplus_up")
    if uploaded_files:
        for img_file in uploaded_files:
            st.image(Image.open(img_file), use_column_width=True)
