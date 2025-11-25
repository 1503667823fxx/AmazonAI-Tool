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
# 这些词会自动追加到 Prompt 中，无需用户输入
UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field, masterpiece, sharp focus"
UNIVERSAL_NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly, pixelated, watermark, text, signature, bad anatomy, deformed, lowres, bad hands"

# --- 4. 辅助函数 ---
def download_image(url, filename):
    """提供下载链接"""
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

# --- 5. 顶部导航 ---
st.title("🎨 亚马逊 AI 视觉工场 (All-in-One)")
st.caption("集成 FLUX.1 Pro, FLUX-Fill, Real-ESRGAN 等顶级模型")

# 初始化 Session State
if "i2i_final_prompt" not in st.session_state:
    st.session_state["i2i_final_prompt"] = ""

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
                        # 自动追加底层高质量词
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
# Tab 2: 图生图 (智能变体 - 已修复)
# ==================================================
with tabs[1]:
    st.header("🖼️ 图生图 (Image-to-Image 3.0)")
    st.caption("Gemini 3.0 Pro 视觉引擎 + FLUX 绘图引擎")
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 素材与构思")
        ref_img = st.file_uploader("上传参考图 (Gemini将读取产品特征)", type=["jpg", "png", "webp"], key="i2i_up")
        if ref_img:
            # 加载并显示原图
            img_obj = Image.open(ref_img)
            st.image(img_obj, width=200, caption="参考原图")
        
        # 分离的输入框
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            user_modifications = st.text_area("修改要求 (User Instruction)", height=100, placeholder="例如：改成素描风格，或者让产品看起来更亮...")
        with col_in2:
            scene_context = st.text_area("植入场景 (Scene Context)", height=100, placeholder="例如：放在高档大理石桌面上，背景是温馨的客厅，晨光...")

        strength = st.slider("重绘幅度 (Image Strength)", 0.1, 1.0, 0.75, help="数值越大，AI发挥空间越大（越不像原图）。推荐 0.6-0.8。")

        # 智能合成按钮
        if st.button("✨ Gemini 智能分析并生成 Prompt", type="secondary", key="i2i_magic"):
            if not ref_img:
                st.warning("请先上传参考图！")
            else:
                # 创建占位符，显示进度
                status_box = st.empty()
                status_box.info("🧠 1/3 正在压缩图片以便快速分析...")
                
                try:
                    # 1. 图片预处理：压缩图片以加快 API 传输速度 (关键修复)
                    # Gemini 识别特征不需要 4K 原图，1024px 足够了，速度快 10 倍
                    img_small = img_obj.copy()
                    img_small.thumbnail((1024, 1024))
                    
                    status_box.info("🧠 2/3 Gemini 正在观察图片特征并融合要求...")
                    
                    # 2. 调用 Gemini
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    
                    # 强大的合成 Prompt
                    synthesis_prompt = f"""
                    你是一个精通 FLUX 绘画模型的提示词专家。
                    
                    【任务】
                    请基于这张图片的内容，结合用户的修改要求和场景植入需求，写一段高质量的英文 Prompt。
                    
                    【输入信息】
                    1. **图片内容**: 请仔细观察图片，提取主体的核心特征（颜色、材质、结构、形状），确保重绘时主体不崩。
                    2. **用户修改要求**: {user_modifications}
                    3. **植入场景**: {scene_context}
                    
                    【输出要求】
                    - 将产品特征与新场景自然融合。
                    - 保持描述的准确性和画面的美感。
                    - 直接输出一段英文 Prompt，不要包含任何解释性文字。
                    """
                    
                    # 传入处理后的小图
                    response = model.generate_content([synthesis_prompt, img_small])
                    
                    # 3. 更新 Session State
                    st.session_state["i2i_final_prompt"] = response.text
                    status_box.success("✅ 3/3 生成完成！正在刷新...")
                    
                    # 4. 强制刷新以显示结果
                    time.sleep(0.5) # 给一点点时间让用户看到成功提示
                    st.rerun()
                    
                except Exception as e:
                    status_box.empty()
                    st.error(f"Gemini 分析失败: {e}")

    # === 右侧：生成与结果 ===
    with col2:
        st.subheader("2. 生成控制")
        
        # 显示合成后的 Prompt
        final_prompt_display = st.text_area(
            "最终指令 (自动追加了底层画质词)", 
            value=st.session_state["i2i_final_prompt"], 
            height=150,
            key="i2i_final_text"
        )
        
        # 展示底层规则 (只读，让用户知道不用自己写)
        with st.expander("查看底层预设 (已自动生效)", expanded=False):
            st.markdown(f"**✅ 自动追加的正向词:**\n`{UNIVERSAL_QUALITY_PROMPT}`")
            st.markdown(f"**🚫 自动启用的负向词:**\n`{UNIVERSAL_NEGATIVE_PROMPT}`")

        if st.button("🚀 生成变体 (Run FLUX)", type="primary", key="i2i_run_flux"):
            if not ref_img or not final_prompt_display:
                st.warning("请完善左侧信息并生成 Prompt")
            else:
                with st.spinner("🎨 正在重绘中..."):
                    try:
                        # 组合最终 Prompt
                        full_prompt = final_prompt_display + UNIVERSAL_QUALITY_PROMPT
                        
                        # 调用 Flux Dev (支持 img2img)
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={
                                "prompt": full_prompt, 
                                "image": ref_img,
                                "prompt_strength": 1 - strength, # Replicate参数: 0保留原图, 1完全重绘
                                "go_fast": True,
                                "megapixels": "1",
                                "num_outputs": 1,
                                "aspect_ratio": "1:1",
                                "output_format": "jpg",
                                "output_quality": 100,
                                # 虽然 Flux 不强依赖 negative_prompt，但为了保险我们加上
                                "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT 
                            }
                        )
                        
                        # Flux dev output 是 list
                        image_url = str(output[0])
                        st.image(image_url, caption="FLUX 生成结果", use_column_width=True)
                        download_image(image_url, "variant_gen.jpg")
                        
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
                                "prompt": inp_prompt + UNIVERSAL_QUALITY_PROMPT,
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
        out_prompt = st.text_input("背景描述 (AI需要知道补什么)", placeholder="例如：extended blurred living room background")

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
                                "prompt": out_prompt + UNIVERSAL_QUALITY_PROMPT,
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
