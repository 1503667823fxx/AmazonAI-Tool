import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import base64
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 0. 引入门禁 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    if not auth.check_password(): st.stop()
except ImportError:
    pass 

st.set_page_config(page_title="API 深度实验室", page_icon="🧪", layout="wide")

st.title("🧪 Gemini API 深度实验室 (TS代码复刻版)")
st.info("本页面基于您提供的 geminiService.ts 逻辑进行了参数对齐，用于终极排查。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数配置")
    
    # 【关键修改】默认值改为 TS 代码中成功的模型名
    model_name = st.text_input(
        "模型名称", 
        value="gemini-2.5-flash-image", 
        help="TS代码中使用的是 'gemini-2.5-flash-image'。也可以尝试加上 'models/' 前缀。"
    )
    
    # 模拟 TS 代码的多图输入逻辑
    img1 = st.file_uploader("Input 1 (原图/Source)", type=["jpg", "png", "webp"])
    img2 = st.file_uploader("Input 2 (参考图/Mask - 可选)", type=["jpg", "png", "webp"])
    
    # 模拟 TS 代码的 Prompt 结构
    default_prompt = """Task: High-Fidelity Image Generation.
Input 1: Source Image.
Instructions:
1. Modify the image according to the user request.
2. Maintain photorealism and texture consistency.
User Request: Change the background to a luxury office."""
    
    prompt = st.text_area("提示词 (Prompt)", value=default_prompt, height=150)
    
    st.markdown("#### 高级控制")
    # TS 代码中使用了 responseModalities: [Modality.IMAGE]
    force_image_modality = st.checkbox("强制指定 response_modalities=['IMAGE']", value=True)
    disable_safety = st.checkbox("关闭所有安全拦截 (BLOCK_NONE)", value=True)

with col2:
    st.subheader("2. 响应诊断")
    
    if st.button("🚀 发送请求 (复刻 TS 逻辑)", type="primary"):
        if not img1:
            st.warning("请至少上传 Input 1")
        else:
            status = st.empty()
            try:
                status.info("正在预处理图片 (模仿 TS 转 PNG)...")
                
                inputs = [prompt]
                
                # 处理 Input 1
                pil_img1 = Image.open(img1).convert("RGB")
                # 模仿 TS: canvasToBase64(canvas, 'image/png') -> 转为 PNG 字节流
                b_img1 = io.BytesIO()
                pil_img1.save(b_img1, format="PNG")
                # Python SDK 可以直接接受 PIL Image 或 Blob，这里我们用 PIL Image 以便 SDK 自动处理
                # 但为了完全模仿，我们也可以构造 Blob，不过 Python SDK 的 Image 对象最稳
                inputs.append(pil_img1)
                
                # 处理 Input 2
                if img2:
                    pil_img2 = Image.open(img2).convert("RGB")
                    inputs.append(pil_img2)
                    status.info("已添加 Input 2 (参考图)")

                # 配置
                generation_config = {}
                if force_image_modality:
                    generation_config["response_modalities"] = ["IMAGE"]
                
                safety_settings = {}
                if disable_safety:
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }

                status.info(f"正在调用 {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                # 发送请求
                response = model.generate_content(
                    inputs,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                status.success("请求完成！开始解析...")
                
                # === 深度诊断 ===
                with st.expander("🔍 原始数据解剖", expanded=True):
                    if not response.candidates:
                        st.error("❌ 无 Candidate 返回。")
                        if response.prompt_feedback:
                            st.write(f"Feedback: {response.prompt_feedback}")
                        st.stop()
                        
                    candidate = response.candidates[0]
                    st.write(f"**Finish Reason:** {candidate.finish_reason}")
                    
                    if not candidate.content.parts:
                        st.error("❌ Parts 为空。")
                        st.stop()

                    found_image = False
                    for i, part in enumerate(candidate.content.parts):
                        st.markdown(f"--- **Part {i}** ---")
                        
                        if part.text:
                            st.warning(f"📄 **文本:** {part.text}")
                        
                        if part.inline_data:
                            st.success(f"🖼️ **图片数据!** ({part.inline_data.mime_type})")
                            try:
                                img_data = base64.b64decode(part.inline_data.data)
                                st.write(f"数据大小: {len(img_data)} bytes")
                                
                                # 检查文件头
                                hex_head = img_data[:16].hex().upper()
                                st.code(f"Hex Header: {hex_head}")
                                
                                if hex_head.startswith("FFD8"):
                                    st.caption("检测到 JPEG 头")
                                elif hex_head.startswith("89504E47"):
                                    st.caption("检测到 PNG 头")
                                else:
                                    st.error(f"⚠️ 未知或损坏的文件头！看起来不像图片。")
                                    # 尝试解码为文本看看是不是报错信息
                                    try:
                                        st.text(f"尝试文本解码: {img_data.decode('utf-8')}")
                                    except:
                                        pass

                                # 尝试渲染
                                st.image(img_data, caption="成功解码并渲染")
                                found_image = True
                                
                                st.download_button("下载图片", img_data, "gemini_gen.png", "image/png")
                                
                            except Exception as e:
                                st.error(f"解码/渲染失败: {e}")

                    if not found_image:
                        st.error("❌ 未在响应中找到有效的图片数据。")

            except Exception as e:
                st.error(f"💥 错误: {str(e)}")
                st.exception(e)
