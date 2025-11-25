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
    """获取高级视觉模型 (用于生成Prompt)"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

def get_image_gen_model():
    """获取图像生成/编辑模型 (用于Step 1生图)"""
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
if "hybrid_recommendations" not in st.session_state:
    st.session_state["hybrid_recommendations"] = None

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
    **工作流程**：
    1. **构思**：AI 分析原图并提供 3 种方案，或者您输入想法，生成精确指令。
    2. **Step 1 (草图)**：Gemini 3.0 Pro 根据指令生成逻辑草图（修改动作/背景）。
    3. **Step 2 (精修)**：Flux 根据草图进行光影渲染。
    """)
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 构思与指令 (Brain)")
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
            
            # --- 智能推荐区域 ---
            if st.button("✨ AI 读图并推荐 3 种方案", type="secondary", key="btn_recommend"):
                with st.spinner("🧠 Gemini 3.0 Pro 正在深度分析产品并构思..."):
                    try:
                        img_obj = Image.open(ref_img)
                        rec_model = get_pro_vision_model()
                        
                        rec_prompt = """
                        你是一个亚马逊电商视觉专家。请分析这张图片。
                        构思 3 个具体的图像编辑指令 (Prompts)：
                        1. **场景图 (Lifestyle)**: 放入真实使用场景。
                        2. **展示图 (Creative Show)**: 干净高级的影棚背景。
                        3. **产品图 (Product Focus)**: 特写或功能展示。
                        
                        【输出格式】仅输出 JSON:
                        {
                            "lifestyle": "英文指令...",
                            "creative": "英文指令...",
                            "product": "英文指令..."
                        }
                        """
                        response = rec_model.generate_content([rec_prompt, img_obj])
                        clean_json = response.text.replace("```json", "").replace("```", "").strip()
                        st.session_state["hybrid_recommendations"] = json.loads(clean_json)
                        st.success("✅ 推荐已生成！")
                    except Exception as e:
                        st.error(f"推荐失败: {e}")

            # 显示推荐按钮
            recs = st.session_state.get("hybrid_recommendations")
            if recs:
                c1, c2, c3 = st.columns(3)
                if c1.button("🏡 场景图", help=recs.get('lifestyle')):
                    st.session_state["hybrid_instruction"] = recs.get('lifestyle')
                if c2.button("✨ 展示图", help=recs.get('creative')):
                    st.session_state["hybrid_instruction"] = recs.get('creative')
                if c3.button("🔍 产品图", help=recs.get('product')):
                    st.session_state["hybrid_instruction"] = recs.get('product')

            st.markdown("---")
            
            # 用户手动输入区
            user_idea = st.text_area(
                "或者：手动输入您的想法 (中文)", 
                height=60, 
                placeholder="例如：把背景改成极简的白色大理石，窗外有树影..."
            )
            
            if st.button("🧠 生成/更新 指令", type="secondary"):
                if not user_idea:
                    st.warning("请填写想法或选择上方推荐！")
                else:
                    with st.spinner("正在翻译并优化指令..."):
                        try:
                            img_obj = Image.open(ref_img)
                            model = get_pro_vision_model()
                            prompt = f"""
                            基于图片和用户需求："{user_idea}"。
                            写一段英文图像编辑指令。
                            格式："Edit this image to..."
                            直接输出指令。
                            """
                            response = model.generate_content([prompt, img_obj])
                            st.session_state["hybrid_instruction"] = response.text
                            st.success("指令已更新！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"生成失败: {e}")

            # 最终指令确认框
            edit_instruction = st.text_area(
                "最终编辑指令 (Step 1 用)", 
                value=st.session_state["hybrid_instruction"], 
                height=100
            )
            
            # --- 执行 Step 1 ---
            if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
                if not ref_img or not edit_instruction:
                    st.warning("请先生成或输入编辑指令！")
                else:
                    with st.spinner("🧠 Gemini 3.0 Pro Image 正在绘制..."):
                        try:
                            ref_img.seek(0)
                            img_obj = Image.open(ref_img)
                            model = get_image_gen_model()
                            
                            # 这里的 Prompt 很关键
                            response = model.generate_content(
                                [edit_instruction, img_obj],
                                generation_config={"response_modalities": ["IMAGE"]}
                            )
                            
                            # 【核心修复】解析逻辑增强
                            if not response.parts:
                                st.error("Gemini 未返回任何内容，可能是安全策略拦截。")
                            else:
                                part = response.parts[0]
                                if part.text:
                                    # 如果返回的是文本，说明生成失败（如拒绝编辑）
                                    st.error(f"Gemini 拒绝生成图片，原因: {part.text}")
                                    st.info("💡 建议：尝试修改指令，避免涉及人脸重绘或敏感内容。")
                                elif part.inline_data:
                                    # 如果是图片数据
                                    image_bytes = base64.b64decode(part.inline_data.data)
                                    try:
                                        # 验证图片有效性
                                        Image.open(io.BytesIO(image_bytes)).verify()
                                        st.session_state["step1_image"] = image_bytes
                                        st.success("✅ 草图生成成功！")
                                    except Exception:
                                        st.error("Gemini 返回的数据格式错误，无法解码为图片。")
                                else:
                                    st.error("未知响应格式。")
                                
                        except Exception as e:
                            st.error(f"API 调用失败: {e}")

    # === 右侧：预览与 Step 2 ===
    with col2:
        st.subheader("2. 预览与精修 (Hands)")
        
        if st.session_state["step1_image"]:
            image_stream = io.BytesIO(st.session_state["step1_image"])
            st.image(image_stream, caption="Step 1: Gemini 草图", use_column_width=True)
            
            st.divider()
            st.info("👇 Step 2: 使用 Flux 进行光影精修")
            
            flux_prompt = st.text_area(
                "精修风格指令", 
                value="Cinematic lighting, 8k resolution, photorealistic, commercial photography, highly detailed product shot, sharp focus",
                height=80
            )
            
            strength = st.slider("重绘幅度", 0.1, 1.0, 0.35, help="0.3-0.4最稳。")
            
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
                        st.error(f"Flux 失败: {e}")
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
