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
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 辅助函数 ---
def upload_to_replicate(image_file):
    """将上传的图片文件转换为 Replicate 可读的格式"""
    return image_file

def download_image(url, filename):
    """提供下载链接"""
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

# --- 4. 顶部导航 ---
st.title("🎨 亚马逊 AI 视觉工场 (All-in-One)")
st.caption("集成 FLUX.1 Pro, FLUX-Fill, Real-ESRGAN 等顶级模型")

# 创建 6 个功能分区
tabs = st.tabs([
    "✨ 文生图 (海报)", 
    "🖼️ 图生图 (变体)", 
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
        if st.button("🪄 Gemini 润色指令", key="t2i_optimize"):
            if not prompt_text:
                st.warning("请先输入描述")
            else:
                with st.spinner("Gemini 正在构思..."):
                    try:
                        model = genai.GenerativeModel('gemini-3-pro-preview')
                        p = f"你是一个商业插画师。将此描述转换为FLUX模型的英文Prompt，强调光影和质感：{prompt_text}"
                        resp = model.generate_content(p)
                        st.session_state["t2i_final_prompt"] = resp.text
                        st.success("润色完成！")
                        st.rerun()
                    except:
                        st.error("Gemini 调用失败")

        final_prompt_t2i = st.text_area("最终指令 (英文)", value=st.session_state.get("t2i_final_prompt", ""), height=100, key="t2i_final")
        
        ar_t2i = st.selectbox("比例", ["1:1", "16:9", "9:16", "4:5"], key="t2i_ar")

    with col2:
        if st.button("🚀 生成海报", type="primary", key="t2i_run"):
            if not final_prompt_t2i:
                st.warning("指令不能为空")
            else:
                with st.spinner("FLUX 正在绘画..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-1.1-pro",
                            input={"prompt": final_prompt_t2i, "aspect_ratio": ar_t2i, "output_quality": 100}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "poster.jpg")
                    except Exception as e:
                        st.error(f"生成失败: {e}")

# ==================================================
# Tab 2: 图生图 (风格迁移/参考生成)
# ==================================================
with tabs[1]:
    st.header("🖼️ 图生图 (Image-to-Image)")
    col1, col2 = st.columns([4, 6])
    
    with col1:
        st.info("适用于：保持产品大概轮廓，改变风格或背景。")
        ref_img = st.file_uploader("上传参考图", type=["jpg", "png", "webp"], key="i2i_up")
        if ref_img:
            st.image(ref_img, width=200)
        
        prompt_i2i = st.text_area("新画面描述", height=100, placeholder="例如：变成赛博朋克风格，霓虹灯光...")
        strength = st.slider("重绘幅度 (Image Strength)", 0.1, 1.0, 0.75, help="数值越小越像原图，数值越大越像提示词。")

    with col2:
        if st.button("🚀 生成变体", type="primary", key="i2i_run"):
            if not ref_img or not prompt_i2i:
                st.warning("请上传图片并输入描述")
            else:
                with st.spinner("正在重绘..."):
                    try:
                        # 使用 Flux Dev 的 img2img 模式
                        output = replicate.run(
                            "black-forest-labs/flux-dev", # Dev版支持img2img参数较好
                            input={
                                "prompt": prompt_i2i, 
                                "image": ref_img,
                                "prompt_strength": 1 - strength, # Replicate参数逻辑有时相反，视具体模型
                                "go_fast": True
                            }
                        )
                        # Flux dev 返回的是 list
                        st.image(output[0], use_column_width=True)
                        download_image(str(output[0]), "variant.jpg")
                    except Exception as e:
                        st.error(f"生成失败: {e}")

# ==================================================
# Tab 3: 局部重绘 (Inpainting & Background)
# ==================================================
with tabs[2]:
    st.header("🖌️ 局部重绘 & 换背景")
    st.info("基于 FLUX-Fill 模型，这是目前最强的重绘模型。")
    
    col1, col2 = st.columns([4, 6])
    
    with col1:
        inp_img = st.file_uploader("上传原图", type=["jpg", "png"], key="inp_up")
        inp_mask = st.file_uploader("上传蒙版 (黑白图，白色为重绘区)", type=["jpg", "png"], key="inp_mask", help="如果没有蒙版，可以使用PS简单做一个，白色区域会被AI重新画。")
        
        inp_prompt = st.text_area("重绘区域描述", placeholder="例如：(如果是换背景) A luxury marble table in a bright kitchen...", key="inp_prompt")
        
    with col2:
        if st.button("🚀 开始重绘", type="primary", key="inp_run"):
            if not inp_img or not inp_mask or not inp_prompt:
                st.warning("需要：原图 + 蒙版 + 描述")
            else:
                with st.spinner("FLUX-Fill 正在填补..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": inp_img,
                                "mask": inp_mask,
                                "prompt": inp_prompt,
                                "output_format": "jpg"
                            }
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "inpainted.jpg")
                    except Exception as e:
                        st.error(f"重绘失败: {e}")

# ==================================================
# Tab 4: 画幅调整 (Outpainting/扩展)
# ==================================================
with tabs[3]:
    st.header("↔️ 画幅调整 (Outpainting)")
    st.info("神器！把 1:1 的图扩展成 16:9 的 Banner，自动补全缺失的背景。")
    
    col1, col2 = st.columns([4, 6])
    
    with col1:
        out_img = st.file_uploader("上传原图 (例如产品图)", type=["jpg", "png"], key="out_up")
        if out_img:
            st.image(out_img, width=200)
            
        target_ar = st.selectbox("目标比例", ["16:9 (电脑Banner)", "9:16 (手机全屏)", "4:3", "3:2"], key="out_ar")
        
        # 简单的Prompt辅助
        out_prompt = st.text_input("背景描述 (AI需要知道补什么)", placeholder="例如：extended blurred living room background, high quality")

    with col2:
        if st.button("🚀 智能扩展画幅", type="primary", key="out_run"):
            if not out_img or not out_prompt:
                st.warning("请上传图片并填写背景描述")
            else:
                with st.spinner("FLUX-Fill 正在脑补画面... (约20秒)"):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt,
                                "aspect_ratio": target_ar.split(" ")[0],
                                "output_format": "jpg"
                            }
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "expanded.jpg")
                    except Exception as e:
                        st.error(f"扩展失败: {e}")

# ==================================================
# Tab 5: 高清放大 (Upscaling)
# ==================================================
with tabs[4]:
    st.header("🔍 图片高清放大")
    st.info("使用 Real-ESRGAN 模型，将模糊的小图无损放大 4 倍。")
    
    col1, col2 = st.columns([4, 6])
    
    with col1:
        upscale_img = st.file_uploader("上传低清图/小图", type=["jpg", "png"], key="up_up")
        scale = st.slider("放大倍数", 2, 10, 4)
        face_enhance = st.checkbox("人脸增强 (如果有模特)", value=False)

    with col2:
        if st.button("🚀 开始放大", type="primary", key="up_run"):
            if not upscale_img:
                st.warning("请上传图片")
            else:
                with st.spinner("正在进行像素级修复..."):
                    try:
                        output = replicate.run(
                            "nightmareai/real-esrgan",
                            input={
                                "image": upscale_img,
                                "scale": scale,
                                "face_enhance": face_enhance
                            }
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "upscaled_hd.jpg")
                    except Exception as e:
                        st.error(f"放大失败: {e}")

# ==================================================
# Tab 6: A+ 拼接助手 (Tools)
# ==================================================
with tabs[5]:
    st.header("🧩 A+ 页面拼接助手")
    st.info("这是一个简单的工具，帮你把几张生成的图拼在一起预览效果。")
    
    uploaded_files = st.file_uploader("上传多张图片", type=['jpg','png'], accept_multiple_files=True, key="aplus_up")
    
    if uploaded_files:
        # 简单的竖向拼接预览
        st.write("### 竖向拼接预览 (模拟移动端)")
        for img_file in uploaded_files:
            image = Image.open(img_file)
            st.image(image, use_column_width=True)
            
        st.success(f"共预览 {len(uploaded_files)} 张图片。建议生成后下载，使用 PS 进行精细排版。")
