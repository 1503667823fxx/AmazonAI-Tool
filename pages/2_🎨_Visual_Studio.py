import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps
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
def download_image(url, filename):
    """提供下载链接"""
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_vision_model():
    """获取视觉模型 (2.5-flash)"""
    return genai.GenerativeModel('gemini-2.5-flash')

def process_rembg_mask(image_file):
    """Rembg 抠图并生成反向蒙版 (用于Flux Fill)"""
    try:
        output_url = replicate.run("cjwbw/rembg:1.4", input={"image": image_file})
        response = requests.get(str(output_url))
        no_bg_image = Image.open(io.BytesIO(response.content))
        
        if no_bg_image.mode == 'RGBA':
            alpha = no_bg_image.split()[-1]
        else:
            alpha = Image.new("L", no_bg_image.size, 255)
            
        # Flux Fill 需要: 白色=重绘(背景), 黑色=保留(主体)
        # Rembg Alpha: 白色=主体, 黑色=背景
        # 所以要反转
        mask = ImageOps.invert(alpha)
        return no_bg_image, mask
    except Exception as e:
        st.error(f"抠图失败: {e}")
        return None, None

# --- 5. 顶部导航 ---
st.title("🎨 亚马逊 AI 视觉工场 (Pro)")
st.caption("集成 FLUX.1 Pro, IDM-VTON, FaceSwap, Real-ESRGAN 等顶级模型")

# 初始化 Session State
if "t2i_final_prompt" not in st.session_state:
    st.session_state["t2i_final_prompt"] = ""
if "scene_gen_prompt" not in st.session_state:
    st.session_state["scene_gen_prompt"] = ""

# 创建功能分区
tabs = st.tabs([
    "💃 模特/产品工场 (核心)", 
    "✨ 文生图 (海报)", 
    "🖌️ 局部重绘", 
    "↔️ 画幅扩展", 
    "🔍 高清放大", 
    "🧩 A+ 助手"
])

# ==================================================
# Tab 1: 模特/产品工场 (重构核心)
# ==================================================
with tabs[0]:
    st.header("💃 模特与服饰工场 (Model Studio)")
    st.markdown("""
    针对竞品图换模特、换动作、换场景的复杂需求，我们提供三种精准模式：
    """)
    
    # 子模式选择
    mode = st.radio(
        "请选择操作模式：",
        ["🎭 智能换脸 (最保真/换人)", "👗 虚拟试穿 (换动作/换人)", "🌆 场景置换 (保留人/换背景)"],
        horizontal=True
    )
    
    st.divider()

    # --- 模式 A: 智能换脸 ---
    if "智能换脸" in mode:
        col1, col2 = st.columns([5, 5])
        with col1:
            st.info("📝 **逻辑**：保留竞品图的**姿势、衣服、光影**，只替换面部。\n**适用**：竞品图拍得很好，但模特是外国人想换成亚洲人，或者避免肖像侵权。")
            target_img = st.file_uploader("1. 上传底图 (竞品图/原图)", type=["jpg", "png", "webp"], key="face_target")
            source_img = st.file_uploader("2. 上传目标人脸 (你想换上去的脸)", type=["jpg", "png", "webp"], key="face_source", help="只需一张清晰的脸部照片即可。")
            
        with col2:
            if st.button("🚀 开始换脸", type="primary"):
                if not target_img or not source_img:
                    st.warning("请上传两张图片！")
                else:
                    with st.spinner("🎭 正在进行面部融合..."):
                        try:
                            output = replicate.run(
                                "lucataco/faceswap:9a4298548422074c3f57258c5d544497314ae4112df80d116f0d2109bd65a8e2",
                                input={
                                    "target_image": target_img,
                                    "swap_image": source_img
                                }
                            )
                            st.image(str(output), caption="换脸结果", use_column_width=True)
                            download_image(str(output), "faceswap_result.jpg")
                        except Exception as e:
                            st.error(f"换脸失败: {e}")

    # --- 模式 B: 虚拟试穿 (VTON) ---
    elif "虚拟试穿" in mode:
        col1, col2 = st.columns([5, 5])
        with col1:
            st.info("📝 **逻辑**：将衣服从原图中提取出来，穿到另一个模特身上。\n**适用**：**彻底改变动作**。你需要先生成一张想要动作的模特图（可以用文生图生成），然后把衣服穿上去。")
            
            human_img = st.file_uploader("1. 上传模特图 (目标动作/人)", type=["jpg", "png", "webp"], key="vton_human", help="你想让衣服穿在谁身上？可以是AI生成的模特图。")
            garm_img = st.file_uploader("2. 上传衣服图 (平铺/挂拍/竞品裁切)", type=["jpg", "png", "webp"], key="vton_garm", help="只包含衣服的图片效果最好。")
            category = st.selectbox("衣服类型", ["upper_body (上衣)", "lower_body (下装)", "dresses (连衣裙)"])
            
        with col2:
            if st.button("🚀 开始试穿", type="primary"):
                if not human_img or not garm_img:
                    st.warning("请上传模特和衣服！")
                else:
                    with st.spinner("👗 AI 正在进行虚拟试穿... (耗时约 30-60s)"):
                        try:
                            # IDM-VTON 模型
                            output = replicate.run(
                                "cuuupid/idm-vton:c871bb9b0466074280c2a9a73e196398b0865801cd6825bc88f20713653c5afc",
                                input={
                                    "garm_img": garm_img,
                                    "human_img": human_img,
                                    "garment_des": category.split(" ")[0],
                                    "crop": False, # 保持原图构图
                                    "steps": 30
                                }
                            )
                            st.image(str(output), caption="试穿结果", use_column_width=True)
                            download_image(str(output), "tryon_result.jpg")
                        except Exception as e:
                            st.error(f"试穿失败: {e}")
                            st.info("💡 提示：如果效果不好，请尝试裁剪衣服图片，只保留衣服主体。")

    # --- 模式 C: 场景置换 ---
    elif "场景置换" in mode:
        col1, col2 = st.columns([5, 5])
        with col1:
            st.info("📝 **逻辑**：**像素级保留**模特和衣服，只重绘背景。\n**适用**：模特图很完美，但想换个圣诞节/户外/家居背景。")
            
            scene_img = st.file_uploader("1. 上传原图", type=["jpg", "png", "webp"], key="scene_up")
            scene_desc = st.text_area("2. 新场景描述", height=100, placeholder="例如：Luxury living room, warm lighting...")
            
            if st.button("✨ 帮我写场景 Prompt", type="secondary"):
                if not scene_img:
                    st.warning("请先上传图片")
                else:
                    with st.spinner("Gemini 正在构思..."):
                        try:
                            img_small = Image.open(scene_img).copy()
                            img_small.thumbnail((512, 512))
                            model = get_vision_model()
                            prompt = f"基于这张图的主体，设计一个'{scene_desc}'的背景Prompt，强调光影融合，直接输出英文。"
                            resp = model.generate_content([prompt, img_small])
                            st.session_state["scene_gen_prompt"] = resp.text
                            st.success("生成成功！")
                            time.sleep(0.1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gemini 错误: {e}")

        with col2:
            final_scene_prompt = st.text_area("最终指令", value=st.session_state["scene_gen_prompt"], height=100)
            
            if st.button("🚀 替换背景 (Flux Fill)", type="primary"):
                if not scene_img or not final_scene_prompt:
                    st.warning("请完善信息")
                else:
                    with st.spinner("✂️ 自动抠图 + 🎨 背景重绘..."):
                        try:
                            # 1. 自动抠图流程
                            scene_img.seek(0)
                            _, mask = process_rembg_mask(scene_img)
                            
                            if mask:
                                # 准备上传数据
                                img_bytes = io.BytesIO()
                                scene_img.seek(0)
                                Image.open(scene_img).convert("RGB").save(img_bytes, format="PNG")
                                
                                mask_bytes = io.BytesIO()
                                mask.save(mask_bytes, format="PNG")
                                
                                # 2. Flux Fill
                                output = replicate.run(
                                    "black-forest-labs/flux-fill-pro",
                                    input={
                                        "image": img_bytes,
                                        "mask": mask_bytes,
                                        "prompt": final_scene_prompt + UNIVERSAL_QUALITY_PROMPT,
                                        "output_format": "jpg",
                                        "output_quality": 100
                                    }
                                )
                                st.image(str(output), caption="场景置换结果", use_column_width=True)
                                download_image(str(output), "scene_swap.jpg")
                            else:
                                st.error("抠图失败")
                        except Exception as e:
                            st.error(f"生成失败: {e}")

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
    st.header("🔍 高清放大")
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
