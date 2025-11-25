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
    【终极诊断版】解析 Gemini 响应，增加详细 Debug 信息
    """
    try:
        # 0. 检查 Prompt Feedback
        if response_obj.prompt_feedback:
            if response_obj.prompt_feedback.block_reason:
                return None, f"🚫 {model_name} 请求被拦截 (Blocked)，原因: {response_obj.prompt_feedback.block_reason}"

        # 1. 检查 Candidates
        if not response_obj.candidates:
            return None, f"⚠️ {model_name} 未返回任何 Candidate。可能服务器繁忙或 Prompt 被完全过滤。"

        candidate = response_obj.candidates[0]
        
        # 2. 检查 Finish Reason
        finish_reason_map = {1: "STOP (正常)", 2: "MAX_TOKENS", 3: "SAFETY (安全拦截)", 4: "RECITATION", 5: "OTHER"}
        finish_code = candidate.finish_reason
        finish_str = finish_reason_map.get(finish_code, str(finish_code))
        
        if finish_code == 3:
            return None, f"🛡️ {model_name} 触发安全拦截 (SAFETY)。请修改指令。"

        # 3. 遍历 Parts 寻找图片
        if not candidate.content.parts:
            return None, f"⚠️ {model_name} 返回内容为空 (Finish Reason: {finish_str})。这通常意味着模型不知道如何处理输入。"

        image_bytes = None
        text_feedback = []

        for i, part in enumerate(candidate.content.parts):
            # 优先找图片
            if part.inline_data and part.inline_data.data:
                try:
                    decoded = base64.b64decode(part.inline_data.data)
                    Image.open(io.BytesIO(decoded)).verify()
                    image_bytes = decoded
                    break 
                except Exception as e:
                    print(f"Part {i} 图片校验失败: {e}")
                    continue
            
            if part.text:
                text_feedback.append(part.text)

        # 4. 最终判定
        if image_bytes:
            return image_bytes, None
        
        # 错误组装
        error_msg = f"❌ {model_name} 未生成有效图片。"
        if text_feedback:
            error_msg += f"\n🤖 AI 回复了文本: {' '.join(text_feedback)}"
        else:
            error_msg += f"\n(调试信息: Finish Reason={finish_str}, Parts Count={len(candidate.content.parts)})"
            
        return None, error_msg

    except Exception as e:
        return None, f"💥 系统解析错误: {str(e)}"

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
            
            st.markdown("#### 第一步：告诉 AI 你想要什么")
            
            task_type = st.radio(
                "生成方向：", 
                ["🏡 场景图 (Lifestyle)", "✨ 展示图 (Creative)", "🔍 产品图 (Focus)"], 
                horizontal=True
            )
            
            user_idea = st.text_area(
                "您的具体想法 (中文/英文)", 
                height=80, 
                placeholder="例如：我想要一个温馨的圣诞节氛围..."
            )
            
            if st.button("🧠 Gemini 读图并生成指令", type="secondary"):
                with st.spinner("Gemini 3.0 Pro 正在分析..."):
                    try:
                        img_obj = Image.open(ref_img)
                        model = get_pro_vision_model()
                        
                        prompt = f"""
                        你是一个亚马逊电商视觉专家。请基于这张图片的内容，结合用户的需求，写一段用于 AI 图像编辑的精确指令 (Prompt)。
                        
                        【任务类型】{task_type}
                        【用户想法】{user_idea}
                        
                        【输出要求】
                        请输出一段 **英文** 指令，格式为：
                        "Create an image of [product description] with [background description]. Lighting should be [lighting description]."
                        注意：请使用"Create an image of..."而不是"Edit this image..."，以确保模型能生成新图。
                        """
                        
                        response = model.generate_content([prompt, img_obj])
                        st.session_state["hybrid_instruction"] = response.text
                        st.success("✅ 指令已生成！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"分析失败: {e}")

            # 4. 确认指令
            st.markdown("#### 第二步：确认指令")
            edit_instruction = st.text_area(
                "最终编辑指令 (英文 - Step 1 用)", 
                value=st.session_state["hybrid_instruction"], 
                height=120
            )
            
            # 5. 执行 Step 1
            st.markdown("#### 第三步：生成草图")
            if st.button("✨ Step 1: Gemini 生成草图", type="primary"):
                if not ref_img or not edit_instruction:
                    st.warning("请先生成指令！")
                else:
                    st.session_state["step1_image"] = None 
                    
                    with st.spinner("🧠 正在绘制草图..."):
                        try:
                            # 准备图片
                            ref_img.seek(0)
                            original_img = Image.open(ref_img).convert("RGB")
                            original_img.thumbnail((1024, 1024)) 
                            
                            # --- 尝试 A: 3.0 Pro (带图) ---
                            model_v3 = get_image_gen_model_v3()
                            success = False
                            error_report = ""
                            
                            try:
                                # 尝试 Img2Img (如果支持)
                                response = model_v3.generate_content(
                                    [edit_instruction, original_img],
                                    generation_config={"response_modalities": ["IMAGE"]}
                                )
                                img_bytes, err_msg = validate_and_process_image(response, "Gemini 3.0 Pro (Img2Img)")
                                
                                if img_bytes:
                                    st.session_state["step1_image"] = img_bytes
                                    st.success("✅ 3.0 Pro 生成成功！")
                                    success = True
                                else:
                                    error_report = err_msg
                                    print(f"V3 Img2Img 失败: {err_msg}")
                                    
                            except Exception as e:
                                error_report = str(e)
                                print(f"V3 Img2Img 异常: {e}")
                            
                            # --- 尝试 B: 3.0 Pro (不带图 - Text-to-Image) ---
                            # 如果带图失败，说明模型可能不支持 Image Input for Generation，尝试纯文生图
                            if not success:
                                st.warning(f"3.0 Pro 图生图模式未成功 ({error_report})，尝试纯文本生成模式...")
                                
                                try:
                                    response_txt = model_v3.generate_content(
                                        [edit_instruction], # 只传文本
                                        generation_config={"response_modalities": ["IMAGE"]}
                                    )
                                    img_bytes, err_msg = validate_and_process_image(response_txt, "Gemini 3.0 Pro (Text2Img)")
                                    
                                    if img_bytes:
                                        st.session_state["step1_image"] = img_bytes
                                        st.success("✅ 3.0 Pro (纯文本模式) 生成成功！")
                                        success = True
                                    else:
                                        error_report = err_msg
                                except Exception as e:
                                    error_report = str(e)

                            # --- 尝试 C: 2.5 Flash (保底) ---
                            if not success:
                                st.warning(f"3.0 Pro 全面失败，切换至 2.5 Flash Image 重试...")
                                model_v25 = get_image_gen_model_v25()
                                
                                try:
                                    # 2.5 Flash 也是优先尝试 Text2Img，因为它对 Img2Img 支持一般
                                    response_v25 = model_v25.generate_content(
                                        [edit_instruction],
                                        generation_config={"response_modalities": ["IMAGE"]}
                                    )
                                    img_bytes, err_msg = validate_and_process_image(response_v25, "Gemini 2.5 Flash")
                                    
                                    if img_bytes:
                                        st.session_state["step1_image"] = img_bytes
                                        st.success("✅ 2.5 Flash 生成成功！")
                                    else:
                                        st.error(f"❌ 最终失败。\n最后报错: {err_msg}")
                                except Exception as e:
                                    st.error(f"❌ 系统错误: {str(e)}")
                                    
                        except Exception as e:
                            st.error(f"严重错误: {e}")

    # === 右侧：预览与 Step 2 ===
    with col2:
        st.subheader("2. 预览与精修 (Hands)")
        
        if st.session_state["step1_image"]:
            try:
                image_stream = io.BytesIO(st.session_state["step1_image"])
                st.image(image_stream, caption="Step 1: Gemini 草图", use_column_width=True)
                download_image(st.session_state["step1_image"], "step1_draft.jpg", is_bytes=True)
                
                st.divider()
                st.info("👇 Step 2: Flux 精修")
                
                flux_prompt = st.text_area("精修指令", value="Cinematic lighting, 8k resolution, photorealistic, product photography", height=80)
                strength = st.slider("重绘幅度", 0.1, 1.0, 0.35)
                
                if st.button("🚀 Flux 精修", type="primary"):
                    with st.spinner("Flux 渲染中..."):
                        step1_file = io.BytesIO(st.session_state["step1_image"])
                        output = replicate.run(
                            "black-forest-labs/flux-dev", 
                            input={"prompt": flux_prompt + UNIVERSAL_QUALITY_PROMPT, "image": step1_file, "prompt_strength": 1 - strength, "go_fast": False, "output_quality": 100}
                        )
                        st.image(str(output[0]), use_column_width=True)
                        download_image(str(output[0]), "final.jpg")
            except Exception:
                st.session_state["step1_image"] = None
        else:
            st.info("👈 请先在左侧完成 Step 1。")

# ==================================================
# Tab 2-6: 其他功能区 (保持不变)
# ==================================================
with tabs[1]:
    st.header("✨ 文生图")
    # ... (文生图代码保持一致) ...
    col1, col2 = st.columns([4, 6])
    with col1:
        prompt_text = st.text_area("画面描述", height=150)
        if st.button("润色"): pass
    with col2:
        if st.button("生成"): pass

with tabs[2]:
    st.header("🖌️ 局部重绘")
    # ... (局部重绘代码) ...

with tabs[3]:
    st.header("↔️ 画幅扩展")
    # ... (扩展代码) ...

with tabs[4]:
    st.header("🔍 高清放大")
    # ... (放大代码) ...

with tabs[5]:
    st.header("🧩 A+ 助手")
    # ... (助手代码) ...

# --- 底部：模型自检工具 (必用！) ---
st.markdown("---")
with st.expander("🔍 模型体检工具 (点此排查问题)"):
    st.caption("点击下方按钮，查看您的 API Key 到底支持哪些 Gemini 模型。")
    if st.button("运行模型诊断"):
        try:
            st.write("正在连接 Google API...")
            models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name)
            
            st.success(f"查询成功！共找到 {len(models)} 个可用模型：")
            st.code("\n".join(models))
            
            # 自动检测是否包含我们用到的模型
            required = ['gemini-3-pro-preview', 'gemini-3-pro-image-preview', 'gemini-2.5-flash-image-preview']
            missing = [r for r in required if f"models/{r}" not in models]
            
            if missing:
                st.error(f"⚠️ 警告：您的账号缺少以下模型权限，可能会导致报错：\n{missing}")
            else:
                st.success("✅ 完美！您的账号拥有所有顶级模型的权限。")
                
        except Exception as e:
            st.error(f"诊断失败: {e}")
