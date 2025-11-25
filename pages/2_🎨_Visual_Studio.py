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
    【核心修复】智能遍历所有 parts，寻找图片数据，忽略文本废话
    返回: (image_bytes, error_message)
    """
    try:
        # 检查是否有 candidates
        if not response_obj.candidates:
            return None, f"{model_name} 未返回任何内容 (Block Reason: {response_obj.prompt_feedback})"

        # 获取第一个 candidate 的所有 parts
        parts = response_obj.candidates[0].content.parts
        if not parts:
            return None, f"{model_name} 返回了空的内容部分。"

        image_bytes = None
        text_feedback = []

        # --- 遍历搜寻图片 ---
        for part in parts:
            # 1. 检查是否有图片数据
            if part.inline_data and part.inline_data.data:
                try:
                    decoded = base64.b64decode(part.inline_data.data)
                    # 严格安检：用 PIL 试着打开
                    Image.open(io.BytesIO(decoded)).verify()
                    image_bytes = decoded
                    break # 找到了就立刻退出循环，不再找了
                except Exception as e:
                    print(f"跳过无效图片数据: {e}")
                    continue
            
            # 2. 如果是文本，记录下来（可能是拒绝理由）
            if part.text:
                text_feedback.append(part.text)

        # --- 结果判定 ---
        if image_bytes:
            return image_bytes, None # 成功！
        
        # 如果没找到图片，返回收集到的文本信息作为错误提示
        error_msg = f"{model_name} 未生成图片。"
        if text_feedback:
            error_msg += f"\nAI 回复了文本: {' '.join(text_feedback)[:200]}..."
        
        return None, error_msg

    except Exception as e:
        return None, f"解析响应时发生严重系统错误: {str(e)}"

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
    
    col1, col2 = st.columns([5, 5])
    
    # === 左侧：输入与构思 ===
    with col1:
        st.subheader("1. 构思与指令 (Brain)")
        ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="hybrid_up")
        
        if ref_img:
            st.image(ref_img, width=200, caption="原图")
            
            # 1. 选择任务类型
            task_type = st.radio(
                "生成方向：", 
                ["🏡 场景图 (Lifestyle)", "✨ 展示图 (Creative)", "🔍 产品图 (Focus)"], 
                horizontal=True
            )
            
            # 2. 用户输入想法
            user_idea = st.text_area("具体想法 (可选)", height=60, placeholder="例如：背景改成极简的白色大理石...")
            
            # 3. 生成指令按钮
            if st.button("🧠 Gemini 读图并生成指令", type="secondary"):
                with st.spinner("Gemini 3.0 Pro 正在分析..."):
                    try:
                        img_obj = Image.open(ref_img)
                        # 使用 3.0 Pro Preview (只读图写字)
                        model = get_pro_vision_model()
                        
                        prompt = f"""
                        你是一个亚马逊电商视觉专家。
                        【任务】分析图片并基于用户需求写一段 AI 图像编辑指令。
                        【类型】{task_type}
                        【需求】{user_idea}
                        【输出】直接输出一段英文指令，格式："Edit this image to..."。
                        """
                        response = model.generate_content([prompt, img_obj])
                        st.session_state["hybrid_instruction"] = response.text
                        st.success("✅ 指令已生成！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"分析失败: {e}")

            # 4. 确认指令
            st.markdown("---")
            edit_instruction = st.text_area("最终编辑指令 (Step 1 用)", value=st.session_state["hybrid_instruction"], height=100)
            
            # 5. 执行 Step 1
            if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
                if not ref_img or not edit_instruction:
                    st.warning("请先生成指令！")
                else:
                    st.session_state["step1_image"] = None # 清空旧图
                    
                    with st.spinner("🧠 正在绘制草图... (优先尝试 3.0 Pro)"):
                        try:
                            ref_img.seek(0)
                            original_img = Image.open(ref_img).convert("RGB")
                            
                            # --- 尝试 A: 3.0 Pro ---
                            model_v3 = get_image_gen_model_v3()
                            success = False
                            
                            try:
                                response = model_v3.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                # 智能遍历解析
                                img_bytes, err_msg = validate_and_process_image(response, "Gemini 3.0 Pro")
                                
                                if img_bytes:
                                    st.session_state["step1_image"] = img_bytes
                                    st.success("✅ 3.0 Pro 生成成功！")
                                    success = True
                                else:
                                    print(f"V3 验证未通过: {err_msg}") 
                                    # 这里不报错，默默切到 V2.5
                                    
                            except Exception as e_v3:
                                print(f"V3 异常: {e_v3}")
                            
                            # --- 尝试 B: 2.5 Flash (保底) ---
                            if not success:
                                st.warning("3.0 Pro 暂不可用或返回文本，正在切换至 2.5 Flash Image 重试...")
                                model_v25 = get_image_gen_model_v25()
                                
                                response_v25 = model_v25.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                img_bytes, err_msg = validate_and_process_image(response_v25, "Gemini 2.5 Flash")
                                
                                if img_bytes:
                                    st.session_state["step1_image"] = img_bytes
                                    st.success("✅ 2.5 Flash 生成成功！")
                                else:
                                    st.error(f"❌ 所有模型均尝试失败。\n最后一次错误: {err_msg}")
                                    
                        except Exception as e:
                            st.error(f"系统错误: {e}")

    # === 右侧：Step 2 ===
    with col2:
        st.subheader("2. 预览与精修 (Hands)")
        
        if st.session_state["step1_image"]:
            try:
                image_stream = io.BytesIO(st.session_state["step1_image"])
                st.image(image_stream, caption="Step 1: Gemini 草图", use_column_width=True)
                download_image(st.session_state["step1_image"], "step1_draft.jpg", is_bytes=True)
                
                st.divider()
                st.info("👇 Step 2: 使用 Flux 精修光影")
                
                flux_prompt = st.text_area(
                    "精修风格指令", 
                    value="Cinematic lighting, 8k resolution, photorealistic, commercial photography, highly detailed product shot, sharp focus",
                    height=80
                )
                
                strength = st.slider("重绘幅度", 0.1, 1.0, 0.35)
                
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
                                    "output_quality": 100
                                }
                            )
                            final_url = str(output[0])
                            st.image(final_url, caption="Step 2: Flux 精修成品", use_column_width=True)
                            download_image(final_url, "final_product.jpg")
                        except Exception as e:
                            st.error(f"Flux 失败: {e}")
            except Exception:
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

# --- 调试工具 (仅在需要时使用) ---
with st.expander("🔍 开发者调试工具 (查看可用模型)"):
    if st.button("列出当前 Key 支持的所有 Gemini 模型"):
        try:
            st.write("正在查询 Google API...")
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            st.success("查询成功！")
            st.write(available_models)
        except Exception as e:
            st.error(f"查询失败: {e}")
