import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps, UnidentifiedImageError
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
    return genai.GenerativeModel('gemini-2.5-flash')

def get_pro_vision_model():
    """获取高级视觉模型 (用于生成Prompt，不生图)"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

def get_image_gen_model_v3():
    """获取图像生成模型 V3 (优先尝试)"""
    return genai.GenerativeModel('gemini-3-pro-image-preview')

def get_image_gen_model_v25():
    """获取图像生成模型 V2.5 (保底备用)"""
    return genai.GenerativeModel('gemini-2.5-flash-image-preview')

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
st.caption("集成 FLUX.1 Pro, Gemini 3.0 Pro, FaceSwap 等顶级模型")

# 初始化 Session State
if "t2i_final_prompt" not in st.session_state:
    st.session_state["t2i_final_prompt"] = ""
if "scene_gen_prompt" not in st.session_state:
    st.session_state["scene_gen_prompt"] = ""
if "step1_image" not in st.session_state:
    st.session_state["step1_image"] = None
if "hybrid_instruction" not in st.session_state:
    st.session_state["hybrid_instruction"] = ""

# 创建功能分区
tabs = st.tabs([
    "🖼️ 双模图生图 (混合)", 
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
    **严谨工作流**：
    1. **构思**：选择类型 -> 填写想法 -> Gemini 3.0 Pro 读图并综合生成指令。
    2. **Step 1 (草图)**：Gemini 图像模型执行逻辑修改。
    3. **Step 2 (精修)**：Flux 进行光影渲染。
    """)
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 构思与指令 (Brain)")
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
            
            st.markdown("#### 第一步：告诉 AI 你想要什么")
            
            # 1. 选择任务类型
            task_type = st.radio(
                "请选择生成方向：", 
                ["🏡 场景图 (Lifestyle - 放入真实场景)", 
                 "✨ 展示图 (Creative Show - 纯净高级背景)", 
                 "🔍 产品图 (Product Focus - 特写/状态改变)"], 
                horizontal=True
            )
            
            # 2. 用户输入想法
            user_idea = st.text_area(
                "您的具体想法 (可选，支持中文)", 
                height=80, 
                placeholder="例如：我想要一个温馨的圣诞节氛围，背景有壁炉和雪花..."
            )
            
            # 3. 生成指令按钮
            if st.button("🧠 Gemini 读图并生成指令", type="secondary"):
                with st.spinner("Gemini 3.0 Pro 正在分析图片并融合您的想法..."):
                    try:
                        img_obj = Image.open(ref_img)
                        
                        # 使用 3.0 Pro Preview (只读图写字，不画图)
                        model = get_pro_vision_model()
                        
                        prompt = f"""
                        你是一个亚马逊电商视觉专家。请基于这张图片的内容，结合用户的需求，写一段用于 AI 图像编辑的精确指令 (Prompt)。
                        
                        【任务类型】{task_type}
                        【用户想法】{user_idea}
                        
                        【图片分析】
                        请先快速识别图片中的主体产品是什么，保留其核心特征。
                        
                        【输出要求】
                        请输出一段 **英文** 指令，格式为：
                        "Edit this image to [change description]. Keep the product [product features] unchanged. Set the background to [background description]. Lighting should be [lighting description]."
                        
                        请直接输出指令内容，不要包含Markdown或其他废话。
                        """
                        
                        response = model.generate_content([prompt, img_obj])
                        st.session_state["hybrid_instruction"] = response.text
                        st.success("✅ 指令已生成，请在下方确认！")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"分析失败: {e}")

            # 4. 显示并确认指令
            st.markdown("#### 第二步：确认指令")
            edit_instruction = st.text_area(
                "最终编辑指令 (英文 - 可手动修改)", 
                value=st.session_state["hybrid_instruction"], 
                height=120,
                help="这是发给 AI 画师的最终命令。"
            )
            
            # 5. 执行 Step 1
            st.markdown("#### 第三步：生成草图")
            if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
                if not ref_img or not edit_instruction:
                    st.warning("请先生成或输入编辑指令！")
                else:
                    with st.spinner("🧠 Gemini 图像模型正在绘制... (尝试使用 3.0 Pro)"):
                        try:
                            # 准备图片：转换为 RGB JPEG 格式，防止格式兼容性问题
                            ref_img.seek(0)
                            original_img = Image.open(ref_img).convert("RGB")
                            
                            # 尝试优先使用 3.0 Pro Image
                            model = get_image_gen_model_v3()
                            
                            try:
                                response = model.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                # 解析
                                image_data = response.candidates[0].content.parts[0].inline_data.data
                                image_bytes = base64.b64decode(image_data)
                                # 验证
                                Image.open(io.BytesIO(image_bytes)).verify()
                                st.session_state["step1_image"] = image_bytes
                                st.success("✅ 3.0 Pro 生成成功！")
                                
                            except Exception as e_v3:
                                print(f"V3 失败: {e_v3}")
                                st.warning("Gemini 3.0 Pro 暂未响应或不支持此图片编辑，正在切换至 2.5 Flash Image (更稳) 进行重试...")
                                
                                # 保底方案：切换到 2.5 Flash Image Preview
                                model_fallback = get_image_gen_model_v25()
                                response = model_fallback.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                image_data = response.candidates[0].content.parts[0].inline_data.data
                                image_bytes = base64.b64decode(image_data)
                                st.session_state["step1_image"] = image_bytes
                                st.success("✅ 2.5 Flash 生成成功！")

                        except Exception as e:
                            st.error(f"生成失败: {e}")
                            st.info("💡 可能原因：指令涉及敏感内容，或者原图格式 AI 无法识别。建议换一张简单的指令重试。")

    # === 右侧：预览与 Step 2 ===
    with col2:
        st.subheader("2. 预览与精修 (Hands)")
        
        if st.session_state["step1_image"]:
            image_stream = io.BytesIO(st.session_state["step1_image"])
            st.image(image_stream, caption="Step 1: Gemini 草图 (逻辑已修改)", use_column_width=True)
            
            st.divider()
            st.info("👇 对草图满意吗？使用 Flux 进行光影精修！")
            
            flux_prompt = st.text_area(
                "精修风格指令", 
                value="Cinematic lighting, 8k resolution, photorealistic, commercial photography, highly detailed product shot, sharp focus",
                height=80
            )
            
            strength = st.slider("重绘幅度 (Denoising)", 0.1, 1.0, 0.35, help="0.3-0.4最稳。")
            
            if st.button("🚀 Step 2: Flux 极致精修", type="primary"):
                with st.spinner("🎨 Flux 正在注入灵魂..."):
                    try:
                        step1_file = io.BytesIO(st.session_state["step1_image"])
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={
                                "prompt": flux_prompt + UNIVERSAL_QUALITY_PROMPT,
                                "image": step1_file,
                                "prompt_strength": 1 - strength, 
                                "go_fast": False, 
                                "output_quality": 100, 
                                "num_inference_steps": 30
                            }
                        )
                        final_url = str(output[0])
                        st.image(final_url, caption="Step 2: Flux 精修成品", use_column_width=True)
                        download_image(final_url, "final_product.jpg")
                    except Exception as e:
                        st.error(f"Flux 精修失败: {e}")
        else:
            st.info("👈 请先在左侧完成 Step 1 的生成。")

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
