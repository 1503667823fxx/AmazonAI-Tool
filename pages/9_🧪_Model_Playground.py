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

st.title("🧪 Gemini API 深度实验室 (Debug Mode)")
st.info("本页面用于强制测试 '图生图' 能力，并查看 API 返回的原始 JSON 数据。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数配置")
    
    # 手动输入模型名称，防止列表扫描不到隐藏模型
    model_name = st.text_input(
        "模型名称 (手动输入)", 
        value="models/gemini-3-pro-image-preview", 
        help="你可以试试 models/nano-banana-pro-preview 或 models/gemini-1.5-pro-latest"
    )
    
    uploaded_file = st.file_uploader("上传测试图片", type=["jpg", "png", "webp"])
    
    prompt = st.text_area(
        "提示词 (Prompt)", 
        value="Edit this image: Change the background to a snowy mountain. High quality.",
        height=100
    )
    
    # 关键参数控制
    st.markdown("#### 高级控制")
    force_image_modality = st.checkbox("强制指定 response_modalities=['IMAGE']", value=True)
    disable_safety = st.checkbox("关闭所有安全拦截 (BLOCK_NONE)", value=True)

with col2:
    st.subheader("2. 测试结果")
    
    if st.button("🚀 发送原始请求 (Raw Request)", type="primary"):
        if not uploaded_file:
            st.warning("请先上传图片")
        else:
            status = st.empty()
            debug_area = st.expander("🔍 查看 API 原始响应 (Raw Response)", expanded=True)
            
            try:
                status.info("正在构建请求...")
                
                # 1. 图片预处理 (转为最标准的 RGB JPEG)
                img = Image.open(uploaded_file).convert("RGB")
                
                # 2. 配置模型
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

                model = genai.GenerativeModel(model_name)
                
                status.info(f"正在调用 {model_name}...")
                
                # 3. 发送请求
                # 注意：我们将图片放在 Prompt 后面，这是官方推荐的多模态顺序
                response = model.generate_content(
                    [prompt, img],
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # 4. 深度解析响应 (打印所有细节)
                status.success("请求完成！开始解析...")
                
                # --- 在 Debug 区域显示原始数据 ---
                with debug_area:
                    st.markdown("### 🩺 诊断报告")
                    
                    # A. 检查 Prompt Feedback (是否被秒拦)
                    if response.prompt_feedback:
                        st.write("**Prompt Feedback:**")
                        st.json(str(response.prompt_feedback))
                    
                    # B. 检查 Candidates
                    if not response.candidates:
                        st.error("❌ 没有返回任何 Candidates (生成彻底失败)")
                    else:
                        candidate = response.candidates[0]
                        st.write(f"**Finish Reason:** {candidate.finish_reason}")
                        
                        # C. 遍历 Parts (关键！)
                        st.write(f"**Parts Count:** {len(candidate.content.parts)}")
                        
                        for i, part in enumerate(candidate.content.parts):
                            st.markdown(f"--- **Part {i}** ---")
                            
                            # 检查是否有文本
                            if part.text:
                                st.warning(f"📄 **发现文本内容:** \n\n{part.text}")
                                st.caption("如果 AI 返回了文本，说明它可能拒绝了生图，或者正在解释为什么不能生图。")
                            
                            # 检查是否有图片
                            if part.inline_data:
                                st.success(f"🖼️ **发现图片数据!** (MimeType: {part.inline_data.mime_type})")
                                try:
                                    img_data = base64.b64decode(part.inline_data.data)
                                    # 尝试显示
                                    st.image(img_data, caption=f"Part {i} 解码图片")
                                except Exception as e:
                                    st.error(f"图片解码失败: {e}")
                            
                            # 检查是否有函数调用 (Function Call)
                            if part.function_call:
                                st.info(f"🔧 **发现函数调用:** {part.function_call}")

            except Exception as e:
                status.error(f"💥 系统级报错: {str(e)}")
                st.exception(e)
