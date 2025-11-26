import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
st.set_page_config(page_title="Gemini 图生图测试", page_icon="🍌", layout="wide")

# --- 1. 鉴权配置 ---
# 必须先确保连上了 Google
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY，请检查 secrets.toml")
    st.stop()

# --- 2. 核心功能：获取账号下所有可用模型 ---
@st.cache_data(ttl=600)
def get_all_models():
    """
    不加任何过滤，直接拉取所有模型列表。
    方便你找到 gemini-2.5-flash-image 或 gemini-3-pro-image-preview
    """
    try:
        model_list = []
        for m in genai.list_models():
            # 只要名字里带 gemini 的都拿出来
            if "gemini" in m.name:
                model_list.append(m.name)
        
        # 按照新旧排序，把类似 1.5, 2.0, 3.0 的排前面
        return sorted(model_list, reverse=True)
    except Exception as e:
        st.error(f"获取模型列表失败: {e}")
        return ["models/gemini-1.5-pro", "models/gemini-1.5-flash"]

# --- 3. 界面布局 ---
st.title("🍌 Gemini 多模态图生图 (Img2Img) 测试台")
st.info("本模块用于测试 Google 最新模型的原生【图生图】能力。")

# 布局：左侧控制，右侧结果
col_ctrl, col_res = st.columns([1, 1.5], gap="medium")

with col_ctrl:
    st.subheader("1. 模型与输入")
    
    # 自动检索模型列表
    all_models = get_all_models()
    
    # --- 关键：在这里选择你截图里的模型 ---
    selected_model_name = st.selectbox(
        "🔍 选择模型 (请找 gemini-2.5 或 3.0-image)", 
        all_models,
        index=0
    )
    st.caption(f"当前选中: `{selected_model_name}`")

    # 上传原图
    uploaded_file = st.file_uploader("📤 上传参考图", type=["jpg", "png", "jpeg", "webp"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="原图预览", width=200)

    # 提示词
    prompt_text = st.text_area(
        "📝 修改指令 (Prompt)", 
        height=100, 
        placeholder="例如：Change the background to a snowy mountain, keep the product same...",
        help="告诉模型你想怎么修改这张图"
    )

    btn_run = st.button("🚀 开始图生图", type="primary")

# --- 4. 执行与解析 (解决文件报错的核心) ---
with col_res:
    st.subheader("2. 生成结果")
    
    if btn_run:
        if not uploaded_file or not prompt_text:
            st.warning("⚠️ 请确保图片和提示词都已就绪。")
        else:
            with st.spinner(f"正在请求 {selected_model_name} 进行图生图处理..."):
                try:
                    # 1. 准备数据
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    
                    # 2. 实例化模型
                    model = genai.GenerativeModel(selected_model_name)
                    
                    # 3. 发送请求 [提示词, 图片]
                    # 注意：Gemini 原生图生图通常直接返回 content
                    response = model.generate_content([prompt_text, img_pil], stream=True)
                    
                    # 4. 【核心修复】智能解析返回流
                    # Gemini 返回的可能是一段混合流，我们需要把里面的图片部分提取出来
                    
                    found_image = False
                    full_text = ""
                    
                    for chunk in response:
                        # 检查这个 chunk 里有没有 part 包含图片
                        if hasattr(chunk, "parts"):
                            for part in chunk.parts:
                                # 情况 A: 返回了文本 (说明模型可能拒绝画图，或者在解释)
                                if part.text:
                                    full_text += part.text
                                
                                # 情况 B: 返回了内联数据 (Base64图片)
                                if part.inline_data:
                                    image_data = part.inline_data.data
                                    image = Image.open(io.BytesIO(image_data))
                                    st.image(image, caption="Gemini 生成结果", use_column_width=True)
                                    found_image = True
                                
                                # 情况 C: 返回了函数调用或其他 (通常不处理)
                        
                        # 某些 SDK 版本可能直接把 image 放在 chunk.image
                        # 为了兼容性，我们做个深层检查
                        try:
                            # 某些特定的预览版模型返回格式比较特殊
                            if hasattr(chunk, "image") and chunk.image:
                                st.image(chunk.image, caption="Gemini 生成结果 (Preview)", use_column_width=True)
                                found_image = True
                        except:
                            pass

                    # 5. 结果反馈
                    if found_image:
                        st.success("✅ 图片生成成功！")
                        if full_text:
                            with st.expander("模型还说了什么？"):
                                st.write(full_text)
                    else:
                        st.error("❌ 模型没有返回图片。")
                        st.markdown("### 可能的原因：")
                        st.write("1. **模型选错了**：你选的模型可能不支持画图 (如标准的 gemini-1.5-pro 只能看图不能画图)。请确保选的是带有 `image` 后缀的预览模型。")
                        st.write("2. **被拒绝**：Prompt 可能触发了安全过滤。")
                        if full_text:
                            st.warning("模型返回的文本内容如下：")
                            st.info(full_text)

                except Exception as e:
                    st.error(f"❌ 调用报错: {str(e)}")
                    st.markdown("---")
                    st.caption("调试信息：请确认你的 API Key 是否有权访问该预览版模型。")
