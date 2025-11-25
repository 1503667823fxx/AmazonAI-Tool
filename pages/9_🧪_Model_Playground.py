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

st.title("🧪 Gemini API 深度实验室 (法医版)")
st.info("本页面用于对 API 返回的 '损坏数据' 进行尸检，查明它到底是什么。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数配置")
    
    model_name = st.text_input(
        "模型名称 (手动输入)", 
        value="models/gemini-3-pro-image-preview", 
        help="尝试 models/gemini-3-pro-image-preview 或 models/imagen-3"
    )
    
    uploaded_file = st.file_uploader("上传测试图片", type=["jpg", "png", "webp"])
    
    prompt = st.text_area(
        "提示词 (Prompt)", 
        value="Edit this image: Change the background to a snowy mountain. High quality.",
        height=100
    )
    
    st.markdown("#### 高级控制")
    force_image_modality = st.checkbox("强制指定 response_modalities=['IMAGE']", value=True)
    disable_safety = st.checkbox("关闭所有安全拦截 (BLOCK_NONE)", value=True)

with col2:
    st.subheader("2. 尸检报告")
    
    if st.button("🚀 发送请求并解剖数据", type="primary"):
        if not uploaded_file:
            st.warning("请先上传图片")
        else:
            status = st.empty()
            try:
                status.info("正在构建请求...")
                img = Image.open(uploaded_file).convert("RGB")
                
                generation_config = {"response_mime_type": "application/json"} if not force_image_modality else {"response_modalities": ["IMAGE"]}
                
                safety_settings = {}
                if disable_safety:
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }

                model = genai.GenerativeModel(model_name)
                status.info(f"正在调用 {model_name}...")
                
                response = model.generate_content(
                    [prompt, img],
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                status.success("请求完成！开始尸检...")
                
                # === 深度诊断区 ===
                with st.expander("🔍 数据流解剖结果 (必看)", expanded=True):
                    # 1. 检查结束原因
                    if not response.candidates:
                        st.error("❌ 无 Candidate 返回。")
                        if response.prompt_feedback:
                            st.write(f"Feedback: {response.prompt_feedback}")
                        st.stop()
                        
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason
                    st.metric("Finish Reason", f"{finish_reason} (1=Success, 3=Safety)")
                    
                    if not candidate.content.parts:
                        st.error("❌ Parts 为空。")
                        st.stop()

                    for i, part in enumerate(candidate.content.parts):
                        st.markdown(f"--- **Part {i} 分析** ---")
                        
                        # A. 文本部分
                        if part.text:
                            st.info(f"📝 **发现文本:** {part.text}")
                        
                        # B. 图片部分 (重点分析)
                        if part.inline_data:
                            mime = part.inline_data.mime_type
                            raw_b64 = part.inline_data.data
                            
                            st.write(f"🏷️ **声明格式:** {mime}")
                            st.write(f"📦 **Base64 长度:** {len(raw_b64)} 字符")
                            
                            try:
                                # 解码二进制
                                img_bytes = base64.b64decode(raw_b64)
                                size_bytes = len(img_bytes)
                                st.write(f"💾 **解码后大小:** {size_bytes} bytes ({size_bytes/1024:.2f} KB)")
                                
                                # 1. 获取文件头 (Hex)
                                hex_head = img_bytes[:16].hex().upper()
                                st.code(f"文件头 (Hex): {hex_head}", language="text")
                                
                                # 2. 智能判断真实格式
                                file_type = "未知/损坏"
                                if hex_head.startswith("FFD8"): file_type = "JPEG (正常)"
                                elif hex_head.startswith("89504E47"): file_type = "PNG (正常)"
                                elif hex_head.startswith("52494646"): file_type = "WEBP (正常)"
                                elif hex_head.startswith("7B"): file_type = "JSON 文本 (异常!)"
                                elif hex_head.startswith("3C"): file_type = "XML/HTML 文本 (异常!)"
                                elif size_bytes == 0: file_type = "空文件"
                                
                                if "异常" in file_type or "空" in file_type:
                                    st.error(f"💀 **尸检结论: 这是一个 {file_type}**")
                                    # 尝试把坏数据当文本读出来
                                    try:
                                        text_content = img_bytes.decode('utf-8')
                                        st.warning(f"🕵️ **潜藏的文本内容:**\n{text_content}")
                                    except:
                                        st.write("无法作为文本读取。")
                                else:
                                    st.success(f"✅ **尸检结论: 这是一个有效的 {file_type}**")
                                    # 尝试显示
                                    try:
                                        st.image(img_bytes, caption="成功渲染")
                                    except Exception as e:
                                        st.error(f"Streamlit 渲染失败: {e}")
                                
                                # 3. 提供原始垃圾数据下载 (供进一步分析)
                                st.download_button(
                                    label="📥 下载此原始数据 (bin)",
                                    data=img_bytes,
                                    file_name="debug_data.bin",
                                    mime="application/octet-stream"
                                )
                                
                            except Exception as e:
                                st.error(f"Base64 解码崩溃: {e}")

            except Exception as e:
                st.error(f"💥 系统崩溃: {str(e)}")
                st.exception(e)
