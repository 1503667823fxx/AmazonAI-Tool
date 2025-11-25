import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps
import io
import sys
import os
import requests
import time
import base64 # 新增：用于处理 Gemini 生成的图片数据

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
    /* 优化 Tab 样式 */
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {
        height: 50px; 
        background-color: #f8f9fa; 
        border-radius: 5px 5px 0 0;
        border: 1px solid #e0e0e0;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff; 
        border-top: 3px solid #ff9900;
        font-weight: bold;
    }
    .stTextArea textarea {font-family: 'Consolas', monospace; font-size: 14px;}
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 底层常量 ---
UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field, masterpiece, sharp focus"

# --- 4. 辅助函数 ---
def download_image(url_or_data, filename, is_bytes=False):
    """提供下载链接 (支持 URL 和 Bytes)"""
    if is_bytes:
        b64 = base64.b64encode(url_or_data).decode()
        href = f'<a href="data:image/jpeg;base64,{b64}" download="{filename}">📥 点击下载 {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.markdown(f"### [📥 点击下载 {filename}]({url_or_data})")

def get_vision_model():
    """获取视觉模型 (用于读图)"""
    # 用于分析图片的普通视觉模型，保持速度
    return genai.GenerativeModel('gemini-2.5-flash')

def get_image_gen_model():
    """获取图像生成/编辑模型 (用于Step 1)"""
    # 【核心修改】切换至您指定的最高级 Pro 模型
    return genai.GenerativeModel('gemini-3-pro-image-preview')

def process_rembg_mask(image_file):
    """Rembg 抠图并生成反向蒙版"""
    try:
        output_url = replicate.run("cjwbw/rembg:1.4", input={"image": image_file})
        response = requests.get(str(output_url))
        no_bg_image = Image.open(io.BytesIO(response.content))
        
        if no_bg_image.mode == 'RGBA':
            alpha = no_bg_image.split()[-1]
        else:
            alpha = Image.new("L", no_bg_image.size, 255)
            
        mask = ImageOps.invert(alpha)
        return no_bg_image, mask
    except Exception as e:
        st.error(f"抠图失败: {e}")
        return None, None

# --- 5. 顶部导航 ---
st.title("🎨 亚马逊 AI 视觉工场 (Pro)")
st.caption("集成 FLUX.1 Pro, Gemini 3.0 Pro Image, FaceSwap 等顶级模型")

# 初始化 Session State
if "t2i_final_prompt" not in st.session_state:
    st.session_state["t2i_final_prompt"] = ""
if "scene_gen_prompt" not in st.session_state:
    st.session_state["scene_gen_prompt"] = ""
if "step1_image" not in st.session_state:
    st.session_state["step1_image"] = None # 存储第一步生成的图片对象

# 创建功能分区
tabs = st.tabs([
    "🖼️ 双模图生图 (混合)", # 原 模特/产品工场
    "✨ 文生图 (海报)", 
    "🖌️ 局部重绘", 
    "↔️ 画幅扩展", 
    "🔍 高清放大", 
    "🧩 A+ 助手"
])

# ==================================================
# Tab 1: 双模图生图 (Gemini -> Flux)
# ==================================================
with tabs[0]:
    st.header("🖼️ 双模混合图生图 (Hybrid Workflow)")
    st.markdown("""
    **工作原理**：
    1. **Step 1 (大脑)**：使用 **Gemini 3.0 Pro Image** 进行“逻辑编辑”（如：换个动作、增加道具），它听得懂人话。
    2. **Step 2 (双手)**：将 Gemini 生成的“草图”传给 Flux 进行“光影精修”，实现商业级画质。
    """)
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与 Step 1 ===
    with col1:
        st.subheader("1. 逻辑编辑 (Gemini 驱动)")
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
        
        edit_instruction = st.text_area(
            "编辑指令 (告诉 Gemini 怎么改)", 
            height=100, 
            placeholder="例如：把背景改成温馨的圣诞节客厅，给模特戴上一顶红色帽子，保持产品不变。"
        )
        
        if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
            if not ref_img or not edit_instruction:
                st.warning("请上传图片并输入指令！")
            else:
                with st.spinner("🧠 Gemini 3.0 Pro 正在进行深度逻辑修改..."):
                    try:
                        # 准备图片
                        img_obj = Image.open(ref_img)
                        
                        # 调用 Gemini 图像编辑模型
                        model = get_image_gen_model()
                        
                        # 构造 Prompt
                        prompt = f"Edit this image: {edit_instruction}. Make it look realistic."
                        
                        response = model.generate_content(
                            [prompt, img_obj],
                            generation_config={"response_modalities": ["IMAGE"]}
                        )
                        
                        # 解析返回的图片数据
                        try:
                            image_data = response.candidates[0].content.parts[0].inline_data.data
                            image_bytes = base64.b64decode(image_data)
                            
                            # 存入 Session State
                            st.session_state["step1_image"] = image_bytes
                            st.success("✅ 第一步完成！请在下方预览，满意后进行第二步精修。")
                            
                        except Exception as parse_err:
                            st.error("无法解析 Gemini 返回的图片，可能触发了安全拦截或模型未返回图片。")
                            st.text(str(parse_err))
                            
                    except Exception as e:
                        st.error(f"Gemini 生成失败: {e}")

        # 显示第一步结果
        if st.session_state["step1_image"]:
            st.markdown("---")
            st.image(st.session_state["step1_image"], caption="Step 1: Gemini 生成结果 (逻辑已修改)", use_column_width=True)
            download_image(st.session_state["step1_image"], "step1_draft.jpg", is_bytes=True)

    # === 右侧：Step 2 ===
    with col2:
        st.subheader("2. 光影精修 (Flux 驱动)")
        st.info("将左侧生成的图片作为底图，通过 Flux 提升画质和细节。")
        
        flux_prompt = st.text_area(
            "风格指令 (告诉 Flux 怎么渲染)", 
            value="Cinematic lighting, 8k resolution, photorealistic, commercial photography, highly detailed product shot",
            height=100
        )
        
        strength = st.slider("重绘幅度 (Denoising Strength)", 0.1, 1.0, 0.35, help="数值越小越像左侧的草图，数值越大画质越好但可能改变形状。建议 0.3-0.5。")
        
        if st.button("🚀 Step 2: Flux 极致精修", type="primary"):
            if not st.session_state["step1_image"]:
                st.warning("请先完成第一步生成！")
            else:
                with st.spinner("🎨 Flux 正在进行像素级精修..."):
                    try:
                        # 将 bytes 转为 file-like object
                        step1_file = io.BytesIO(st.session_state["step1_image"])
                        
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={
                                "prompt": flux_prompt + UNIVERSAL_QUALITY_PROMPT,
                                "image": step1_file,
                                "prompt_strength": 1 - strength, # Replicate 逻辑: strength 越高保留越多，这里转换一下逻辑方便理解
                                "go_fast": False, # 追求质量，关掉快速模式
                                "output_quality": 100,
                                "num_inference_steps": 30
                            }
                        )
                        # Flux dev 返回 list
                        final_url = str(output[0])
                        st.image(final_url, caption="Step 2: Flux 精修结果 (最终成品)", use_column_width=True)
                        download_image(final_url, "final_product.jpg")
                        
                    except Exception as e:
                        st.error(f"Flux 精修失败: {e}")

# ==================================================
# Tab 2: 文生图 (Text-to-Image)
# ==================================================
with tabs[1]:
    st.header("✨ 文生图 (创意海报)")
    col1, col2 = st.columns([4, 6])
    
    with col1:
        st.info("适用于：从零创造创意海报、抽象背景、营销素材。")
        prompt_text = st.text_area("画面描述", height=150, placeholder="例如：一个极其精美的圣诞节礼品盒...")
        
        if st.button("🪄 润色指令", key="t2i_optimize"):
            if not prompt_text:
                st.warning("请先输入描述")
            else:
                with st.spinner("Gemini 构思中..."):
                    try:
                        model = get_vision_model()
                        p = f"你是一个商业插画师。将此描述转换为FLUX模型的英文Prompt，直接输出英文：{prompt_text}"
                        resp = model.generate_content(p)
                        st.session_state["t2i_final_prompt"] = resp.text
                        st.success("完成！")
                        time.sleep(0.1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"错误: {e}")

        final_prompt_t2i = st.text_area("最终指令", value=st.session_state["t2i_final_prompt"], height=100)
        ar_t2i = st.selectbox("比例", ["1:1", "16:9", "9:16", "4:5"], key="t2i_ar")

    with col2:
        if st.button("🚀 生成海报", type="primary", key="t2i_run"):
            if not final_prompt_t2i:
                st.warning("指令不能为空")
            else:
                with st.spinner("FLUX 绘画中..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-1.1-pro",
                            input={"prompt": final_prompt_t2i + UNIVERSAL_QUALITY_PROMPT, "aspect_ratio": ar_t2i}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "poster.jpg")
                    except Exception as e:
                        st.error(f"生成失败: {e}")

# ==================================================
# Tab 3: 局部重绘
# ==================================================
with tabs[2]:
    st.header("🖌️ 局部重绘 (Inpainting)")
    st.info("手动上传蒙版，指定修改区域。")
    col1, col2 = st.columns([4, 6])
    with col1:
        inp_img = st.file_uploader("原图", type=["jpg", "png"], key="inp_up")
        inp_mask = st.file_uploader("蒙版 (白色为修改区)", type=["jpg", "png"], key="inp_mask")
        inp_prompt = st.text_area("修改描述", key="inp_prompt")
    with col2:
        if st.button("🚀 重绘", type="primary", key="inp_run"):
            if inp_img and inp_mask and inp_prompt:
                with st.spinner("处理中..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={"image": inp_img, "mask": inp_mask, "prompt": inp_prompt + UNIVERSAL_QUALITY_PROMPT}
                        )
                        st.image(str(output), use_column_width=True)
                    except Exception as e:
                        st.error(f"失败: {e}")

# ==================================================
# Tab 4: 画幅扩展
# ==================================================
with tabs[3]:
    st.header("↔️ 画幅扩展 (Outpainting)")
    col1, col2 = st.columns([4, 6])
    with col1:
        out_img = st.file_uploader("原图", type=["jpg", "png"], key="out_up")
        target_ar = st.selectbox("目标比例", ["16:9", "9:16", "4:3"], key="out_ar")
        out_prompt = st.text_input("背景描述", key="out_prompt")
    with col2:
        if st.button("🚀 扩展", type="primary", key="out_run"):
            if out_img and out_prompt:
                with st.spinner("扩展中..."):
                    try:
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={"image": out_img, "prompt": out_prompt + UNIVERSAL_QUALITY_PROMPT, "aspect_ratio": target_ar.split(" ")[0]}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "expanded.jpg")
                    except Exception as e:
                        st.error(f"失败: {e}")

# ==================================================
# Tab 5: 高清放大
# ==================================================
with tabs[4]:
    st.header("🔍 图片高清放大")
    col1, col2 = st.columns([4, 6])
    with col1:
        upscale_img = st.file_uploader("低清图", type=["jpg", "png"], key="up_up")
        scale = st.slider("倍数", 2, 4, 4)
    with col2:
        if st.button("🚀 放大", type="primary", key="up_run"):
            if upscale_img:
                with st.spinner("修复中..."):
                    try:
                        output = replicate.run(
                            "nightmareai/real-esrgan",
                            input={"image": upscale_img, "scale": scale}
                        )
                        st.image(str(output), use_column_width=True)
                        download_image(str(output), "upscaled.jpg")
                    except Exception as e:
                        st.error(f"失败: {e}")

# ==================================================
# Tab 6: A+ 助手
# ==================================================
with tabs[5]:
    st.header("🧩 A+ 助手")
    files = st.file_uploader("多图上传", type=['jpg','png'], accept_multiple_files=True, key="aplus")
    if files:
        for f in files:
            st.image(Image.open(f), use_column_width=True)
    if files:
        for f in files:
            st.image(Image.open(f), use_column_width=True)

