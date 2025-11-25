import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import base64

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="模型试驾场", page_icon="🧪", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

st.title("🧪 Gemini 模型试驾场 (Model Playground)")
st.caption("这里是纯净的测试环境，用于排查 API 权限和模型能力。")

# --- 2. 验证 API Key ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ 未找到 Google API Key，请在 secrets.toml 中配置。")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 侧边栏：模型探测器 ---
with st.sidebar:
    st.header("📡 模型探测雷达")
    
    if st.button("🔄 扫描可用模型"):
        try:
            with st.spinner("正在连接 Google 服务器..."):
                all_models = []
                # 列出所有模型
                for m in genai.list_models():
                    all_models.append(m)
                
                st.session_state["all_models_list"] = all_models
                st.success(f"扫描成功！共发现 {len(all_models)} 个模型。")
        except Exception as e:
            st.error(f"扫描失败: {e}")

    # 筛选逻辑
    all_models = st.session_state.get("all_models_list", [])
    
    # 提取支持 generateContent 的模型 (用于对话/识图)
    chat_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
    # 提取可能支持生图的模型 (通过名字猜测，通常包含 image)
    image_models = [m.name for m in all_models if 'image' in m.name.lower() or 'vision' in m.name.lower()]
    
    st.markdown("---")
    st.markdown(f"**🔍 发现 {len(chat_models)} 个生成模型**")
    
    # 选择当前测试的模型
    selected_model_name = st.selectbox(
        "选择要测试的模型:", 
        options=chat_models if chat_models else ["models/gemini-1.5-flash"], # 默认值
        index=0 if chat_models else 0
    )

# --- 4. 主界面：多功能测试台 ---
tab1, tab2, tab3 = st.tabs(["💬 纯文本对话", "👁️ 多模态识图", "🎨 图像生成测试"])

# === Tab 1: 纯文本对话 ===
with tab1:
    st.subheader(f"正在测试: `{selected_model_name}`")
    user_input = st.text_input("输入测试文本", "Hello, who are you?")
    
    if st.button("发送 (Text Chat)", key="btn_chat"):
        try:
            model = genai.GenerativeModel(selected_model_name)
            response = model.generate_content(user_input)
            st.success("✅ 响应成功:")
            st.write(response.text)
        except Exception as e:
            st.error(f"❌ 失败: {e}")

# === Tab 2: 多模态识图 ===
with tab2:
    st.subheader(f"正在测试: `{selected_model_name}`")
    st.info("测试该模型是否具备 Vision (视觉) 能力。")
    
    uploaded_img = st.file_uploader("上传测试图片", type=["jpg", "png", "webp"], key="vision_up")
    vision_prompt = st.text_input("输入指令", "Describe this image in detail.")
    
    if uploaded_img and st.button("发送 (Vision)", key="btn_vision"):
        try:
            image = Image.open(uploaded_img)
            st.image(image, width=200)
            
            model = genai.GenerativeModel(selected_model_name)
            response = model.generate_content([vision_prompt, image])
            st.success("✅ 响应成功:")
            st.write(response.text)
        except Exception as e:
            st.error(f"❌ 失败: {e}")
            st.warning("提示：如果报错，说明该模型可能不支持多模态输入（只能读字，不能看图）。")

# === Tab 3: 图像生成测试 (关键战场) ===
with tab3:
    st.subheader(f"正在测试: `{selected_model_name}`")
    st.warning("⚠️ 注意：只有特定模型（如 imagen 或 gemini-image）才支持生图。用普通模型测试必然报错。")
    
    col_gen1, col_gen2 = st.columns(2)
    
    with col_gen1:
        st.markdown("#### A. 文生图 (Text to Image)")
        t2i_prompt = st.text_input("生图提示词", "A cute robot holding a Streamlit logo, 3d render")
        
        if st.button("🎨 测试文生图", key="btn_t2i"):
            try:
                model = genai.GenerativeModel(selected_model_name)
                # 强制要求返回图片
                response = model.generate_content(
                    t2i_prompt,
                    generation_config={"response_modalities": ["IMAGE"]}
                )
                
                # 解析
                try:
                    if not response.parts:
                        st.error("未返回 Parts。")
                    else:
                        part = response.parts[0]
                        if part.text:
                            st.warning(f"AI 返回了文本而不是图片: {part.text}")
                        elif part.inline_data:
                            img_data = base64.b64decode(part.inline_data.data)
                            st.image(img_data, caption="生成结果")
                            st.success("🎉 成功！该模型支持文生图！")
                except Exception as parse_err:
                    st.error(f"解析失败: {parse_err}")
                    
            except Exception as e:
                st.error(f"❌ 请求失败: {e}")

    with col_gen2:
        st.markdown("#### B. 图生图 (Image to Image)")
        ref_img_gen = st.file_uploader("上传参考图", type=["jpg", "png"], key="gen_up")
        i2i_prompt = st.text_input("编辑指令", "Change the background to a beach")
        
        if ref_img_gen and st.button("🎨 测试图生图", key="btn_i2i"):
            try:
                img_obj = Image.open(ref_img_gen)
                st.image(img_obj, width=150, caption="输入图")
                
                model = genai.GenerativeModel(selected_model_name)
                
                # 尝试发送 [prompt, image]
                response = model.generate_content(
                    [i2i_prompt, img_obj],
                    generation_config={"response_modalities": ["IMAGE"]}
                )
                
                # 解析
                try:
                    if not response.parts:
                        st.error("未返回 Parts。")
                    else:
                        part = response.parts[0]
                        if part.text:
                            st.warning(f"AI 返回了文本: {part.text}")
                        elif part.inline_data:
                            img_data = base64.b64decode(part.inline_data.data)
                            st.image(img_data, caption="生成结果")
                            st.success("🎉 成功！该模型支持图生图！")
                except Exception as parse_err:
                    st.error(f"解析失败: {parse_err}")
                    
            except Exception as e:
                st.error(f"❌ 请求失败: {e}")
                st.info("如果报错 '400 Bad Request' 或 'multimodal input not supported'，说明该模型不支持接收图片作为输入来生成新图片。")

# --- 底部：原始数据查看 ---
with st.expander("🔍 查看所有模型原始数据 (JSON)"):
    if st.button("获取 Raw Data"):
        raw_info = []
        for m in genai.list_models():
            raw_info.append({
                "name": m.name,
                "methods": m.supported_generation_methods,
                "input_limit": m.input_token_limit,
                "output_limit": m.output_token_limit
            })
        st.json(raw_info)
