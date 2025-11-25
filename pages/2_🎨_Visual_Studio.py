import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps
import io
import sys
import os
import requests
import time
import base64 
import json

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
    .step-card {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #0068c9;
        margin-bottom: 15px;
    }
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
UNIVERSAL_NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly, pixelated, watermark, text, signature, bad anatomy, deformed, lowres, bad hands, mutation"

# --- 4. 辅助函数 ---
def download_image(url, filename):
    """提供下载链接"""
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_vision_model():
    """获取视觉模型 (用于读图) - 使用 1.5 Flash 保证速度"""
    return genai.GenerativeModel('gemini-1.5-flash')

def get_pro_vision_model():
    """获取高级视觉模型 (用于复杂构思) - 使用 3.0 Pro"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

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
st.caption("集成 FLUX.1 Pro (绘图) + Gemini 3.0 Pro (构思)")

# 初始化 Session State
if "t2i_final_prompt" not in st.session_state:
    st.session_state["t2i_final_prompt"] = ""
if "scene_gen_prompt" not in st.session_state:
    st.session_state["scene_gen_prompt"] = ""
if "hybrid_instruction" not in st.session_state:
    st.session_state["hybrid_instruction"] = ""
if "generated_image_url" not in st.session_state:
    st.session_state["generated_image_url"] = None

# 创建功能分区
tabs = st.tabs([
    "🖼️ 智能场景变换 (Flux)", 
    "✨ 文生图 (海报)", 
    "🖌️ 局部重绘", 
    "↔️ 画幅扩展", 
    "🔍 高清放大", 
    "🧩 A+ 助手"
])

# ==================================================
# Tab 1: 智能场景变换 (原双模图生图 - 逻辑重构)
# ==================================================
with tabs[0]:
    st.header("🖼️ 智能场景变换 (Smart Scene Swap)")
    st.info("工作流：Gemini 读取原图特征 + 用户需求 -> 生成精准指令 -> Flux 参照原图结构生成新场景。")
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：构思与指令 ===
    with col1:
        st.markdown('<div class="step-card">Step 1: 上传与构思 (Gemini Brain)</div>', unsafe_allow_html=True)
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
            
            # 1. 任务类型
            task_type = st.radio(
                "想要变成什么图？", 
                ["🏡 场景图 (Lifestyle - 放入真实场景)", 
                 "✨ 展示图 (Creative - 纯净高级背景)", 
                 "🔍 创意变体 (Creative Variation - 风格化)"], 
                horizontal=True
            )
            
            # 2. 用户想法
            user_idea = st.text_area(
                "您的具体想法 (支持中文)", 
                height=80, 
                placeholder="例如：把背景改成温馨的圣诞节客厅，壁炉在燃烧，给产品打暖色光..."
            )
            
            # 3. 按钮：生成指令
            if st.button("🧠 让 Gemini 编写绘画指令", type="secondary"):
                if not user_idea:
                    st.warning("请先写下您的想法！")
                else:
                    with st.spinner("Gemini 3.0 Pro 正在深度分析原图细节..."):
                        try:
                            img_obj = Image.open(ref_img)
                            # 为了加快速度，缩图
                            img_small = img_obj.copy()
                            img_small.thumbnail((1024, 1024))
                            
                            model = get_pro_vision_model()
                            
                            prompt = f"""
                            你是一个世界顶级的商业摄影提示词(Prompt)专家。
                            请仔细观察这张图片，提取主体的核心视觉特征（形状、颜色、材质、结构）。
                            
                            【任务】
                            基于图片主体，结合用户的需求："{user_idea}"，以及任务类型："{task_type}"，
                            写一段用于 FLUX AI 绘画模型的英文提示词。
                            
                            【提示词结构要求】
                            1. **Subject**: 详细描述产品主体（确保 AI 知道要画什么）。
                            2. **Environment**: 详细描述用户想要的背景环境。
                            3. **Lighting/Style**: 商业摄影光影、8k分辨率、超写实。
                            
                            【输出】
                            直接输出一段完整的英文 Prompt，不要包含 Markdown 标记或解释。
                            """
                            
                            response = model.generate_content([prompt, img_small])
                            st.session_state["hybrid_instruction"] = response.text
                            st.success("✅ 指令已生成！请在右侧确认。")
                            # 强制刷新让右侧显示
                            time.sleep(0.1) 
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Gemini 分析失败: {e}")

    # === 右侧：确认与生成 ===
    with col2:
        st.markdown('<div class="step-card">Step 2: 确认指令与生成 (Flux Hands)</div>', unsafe_allow_html=True)
        
        # 4. 指令确认框
        final_prompt = st.text_area(
            "最终绘画指令 (英文 - 可手动修改)", 
            value=st.session_state["hybrid_instruction"], 
            height=150,
            help="Flux 将根据这段话进行绘制。"
        )
        
        # 5. 参数控制
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            # 图生图的灵魂参数：Strength
            # 0.0 = 完全原图，1.0 = 完全不看原图
            # 换背景通常推荐 0.6 - 0.8
            strength = st.slider("重绘幅度 (Strength)", 0.1, 1.0, 0.75, help="数值越大，背景变化越大，但主体可能微变。数值越小，越像原图。推荐 0.75。")
        with col_p2:
            num_outputs = st.number_input("生成数量", 1, 4, 1)

        # 6. 生成按钮
        if st.button("🚀 开始生成 (Run Flux)", type="primary"):
            if not ref_img or not final_prompt:
                st.warning("请先在左侧上传图片并生成指令！")
            else:
                with st.spinner("🎨 Flux 正在根据您的指令重绘..."):
                    try:
                        # 准备图片
                        ref_img.seek(0)
                        
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={
                                "prompt": final_prompt + UNIVERSAL_QUALITY_PROMPT,
                                "image": ref_img,
                                "prompt_strength": 1 - strength, # Replicate参数逻辑: strength越高保留越少
                                "go_fast": True,
                                "num_outputs": num_outputs,
                                "output_format": "jpg",
                                "output_quality": 100,
                                "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT
                            }
                        )
                        
                        # 处理结果
                        if isinstance(output, list):
                            st.session_state["generated_image_url"] = output
                        else:
                            st.session_state["generated_image_url"] = [output]
                            
                        st.success("✅ 生成完成！")
                        
                    except Exception as e:
                        st.error(f"Flux 生成失败: {e}")

        # 7. 结果展示
        if st.session_state["generated_image_url"]:
            st.divider()
            st.markdown("#### 🎉 生成结果")
            for i, url in enumerate(st.session_state["generated_image_url"]):
                st.image(url, caption=f"结果 {i+1}", use_column_width=True)
                download_image(url, f"flux_result_{i+1}.jpg")

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
