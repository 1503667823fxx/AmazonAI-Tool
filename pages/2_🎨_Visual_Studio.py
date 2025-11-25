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
    .stTextArea textarea {font-family: 'Consolas', monospace; font-size: 14px;}
    /* 步骤指示器 */
    .step-indicator {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #0068c9;
        margin-bottom: 15px;
        font-weight: bold;
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

# --- 4. 辅助函数 ---
def download_image(url_or_data, filename, is_bytes=False):
    """提供下载链接 (支持 URL 和 Bytes)"""
    if is_bytes:
        b64 = base64.b64encode(url_or_data).decode()
        href = f'<a href="data:image/jpeg;base64,{b64}" download="{filename}">📥 点击下载 {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.markdown(f"### [📥 点击下载 {filename}]({url_or_data})")

def get_pro_vision_model():
    """获取高级视觉模型 (用于读图写指令，不生图)"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

def get_image_gen_model_v3():
    """获取图像生成模型 V3 (优先)"""
    return genai.GenerativeModel('gemini-3-pro-image-preview')

def get_image_gen_model_v25():
    """获取图像生成模型 V2.5 (保底)"""
    return genai.GenerativeModel('gemini-2.5-flash-image-preview')

def validate_and_process_image(response_obj, model_name):
    """
    通用图像验证函数：检查 API 返回的是不是真的图片
    返回: (image_bytes, error_message)
    """
    try:
        if not response_obj.parts:
            return None, f"{model_name} 未返回任何内容。"
            
        # 检查是否被拦截返回了文本
        if response_obj.parts[0].text:
            return None, f"{model_name} 拒绝生成图像，原因: {response_obj.parts[0].text}"
            
        if not response_obj.parts[0].inline_data:
            return None, f"{model_name} 返回了未知格式的数据。"

        # 解码 Base64
        image_data = response_obj.parts[0].inline_data.data
        image_bytes = base64.b64decode(image_data)
        
        # 关键步骤：使用 PIL 尝试打开，验证完整性
        try:
            img_test = Image.open(io.BytesIO(image_bytes))
            img_test.verify() # 验证文件头和尾
            return image_bytes, None # 验证通过
        except Exception as img_err:
            return None, f"{model_name} 返回了损坏的图像数据 (PIL校验失败): {str(img_err)}"

    except Exception as e:
        return None, f"解析响应时发生严重错误: {str(e)}"

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
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 构思与指令 (Brain)")
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
            
            st.markdown('<div class="step-indicator">第 1 步：告诉 AI 你想要什么</div>', unsafe_allow_html=True)
            
            # 1. 选择任务类型
            task_type = st.radio(
                "生成方向：", 
                ["🏡 场景图 (Lifestyle - 放入真实场景)", 
                 "✨ 展示图 (Creative Show - 纯净高级背景)", 
                 "🔍 产品图 (Product Focus - 特写/状态改变)"], 
                horizontal=True
            )
            
            # 2. 用户输入想法
            user_idea = st.text_area(
                "具体想法 (中文/英文)", 
                height=80, 
                placeholder="例如：我想要一个温馨的圣诞节氛围，背景有壁炉和雪花，给产品打暖色光..."
            )
            
            # 3. 生成指令按钮
            if st.button("🧠 Gemini 分析并写指令", type="secondary"):
                if not user_idea:
                    st.warning("请先告诉 AI 你的具体想法！")
                else:
                    with st.spinner("Gemini 3.0 Pro 正在读图并构思..."):
                        try:
                            img_obj = Image.open(ref_img)
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
            st.markdown('<div class="step-indicator">第 2 步：确认 AI 的指令</div>', unsafe_allow_html=True)
            edit_instruction = st.text_area(
                "最终编辑指令 (英文 - Step 1 用)", 
                value=st.session_state["hybrid_instruction"], 
                height=120,
                help="Gemini 将根据这段话生成草图。"
            )
            
            # 5. 执行 Step 1
            st.markdown('<div class="step-indicator">第 3 步：生成逻辑草图</div>', unsafe_allow_html=True)
            if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
                if not ref_img or not edit_instruction:
                    st.warning("请先生成或输入编辑指令！")
                else:
                    # 清空旧图，防止误会
                    st.session_state["step1_image"] = None
                    
                    with st.spinner("🧠 正在绘制草图... (尝试使用 3.0 Pro)"):
                        try:
                            # 准备图片：转换为 RGB JPEG 格式
                            ref_img.seek(0)
                            original_img = Image.open(ref_img).convert("RGB")
                            
                            # --- 尝试方案 A: 3.0 Pro ---
                            model_v3 = get_image_gen_model_v3()
                            success = False
                            
                            try:
                                response = model_v3.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                # 严格验证
                                img_bytes, err_msg = validate_and_process_image(response, "Gemini 3.0 Pro")
                                
                                if img_bytes:
                                    st.session_state["step1_image"] = img_bytes
                                    st.success("✅ 3.0 Pro 生成成功！")
                                    success = True
                                else:
                                    print(f"V3 验证失败: {err_msg}") # 后台打印
                                    # 不报错给用户，直接走 Fallback
                                    
                            except Exception as e_v3:
                                print(f"V3 调用异常: {e_v3}")
                            
                            # --- 尝试方案 B: 2.5 Flash (保底) ---
                            if not success:
                                st.warning("Gemini 3.0 Pro 暂未响应或数据异常，正在切换至 2.5 Flash Image (更稳) 进行重试...")
                                model_v25 = get_image_gen_model_v25()
                                
                                response_v25 = model_v25.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                # 再次严格验证
                                img_bytes, err_msg = validate_and_process_image(response_v25, "Gemini 2.5 Flash")
                                
                                if img_bytes:
                                    st.session_state["step1_image"] = img_bytes
                                    st.success("✅ 2.5 Flash 生成成功！")
                                else:
                                    st.error(f"❌ 所有模型均尝试失败。\n最后一次错误信息: {err_msg}")
                                    
                        except Exception as e:
                            st.error(f"系统错误: {e}")

    # === 右侧：预览与 Step 2 ===
    with col2:
        st.subheader("2. 预览与精修 (Hands)")
        
        if st.session_state["step1_image"]:
            # 使用 io.BytesIO 包装
            try:
                image_stream = io.BytesIO(st.session_state["step1_image"])
                st.image(image_stream, caption="Step 1: Gemini 草图 (逻辑已修改)", use_column_width=True)
                download_image(st.session_state["step1_image"], "step1_draft.jpg", is_bytes=True)
                
                st.divider()
                st.markdown('<div class="step-indicator">第 4 步：Flux 光影精修</div>', unsafe_allow_html=True)
                
                flux_prompt = st.text_area(
                    "精修风格指令", 
                    value="Cinematic lighting, 8k resolution, photorealistic, commercial photography, highly detailed product shot, sharp focus",
                    height=80
                )
                
                strength = st.slider("重绘幅度 (Denoising)", 0.1, 1.0, 0.35, help="0.3-0.4最稳。")
                
                if st.button("🚀 Step 2: Flux 极致精修", type="primary"):
                    with st.spinner("🎨 Flux 正在注入灵魂..."):
                        try:
                            # 再次包装 stream，因为 Flux 需要文件对象
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
            except Exception as display_err:
                st.error(f"图片显示失败，数据可能损坏: {display_err}")
                st.session_state["step1_image"] = None # 清除坏数据
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
