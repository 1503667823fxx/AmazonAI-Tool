import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
st.set_page_config(page_title="Google Native Studio", page_icon="🍌", layout="wide")

# --- 1. 鉴权配置 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY")
    st.stop()

# --- 2. 常量定义 ---
# 🔒 锁定你指定的两个核心模型
TARGET_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3-pro-image-preview"
]

# 📐 亚马逊/电商常用比例提示词后缀
# 注意：Gemini 图生图更多是基于指令编辑，我们通过 Prompt 强化来引导构图
RATIO_PROMPTS = {
    "保持原图比例 (Original)": "",
    "1:1 正方形 (Amazon 主图)": ", crop and center composition to 1:1 square aspect ratio",
    "3:4 纵向 (手机端展示)": ", adjust composition to 3:4 portrait aspect ratio",
    "4:3 横向 (PC端展示)": ", adjust composition to 4:3 landscape aspect ratio",
    "16:9 宽屏 (Banner海报)": ", cinematic 16:9 wide aspect ratio"
}

# --- 3. 界面布局 ---
st.title("🍌 Google 原生图生图 (Native Studio)")
st.caption("基于 Gemini 2.5/3.0 多模态原生绘图能力")

col_left, col_right = st.columns([1, 1.5], gap="large")

# === 左侧：控制台 ===
with col_left:
    st.subheader("🛠️ 工作台")
    
    # 1. 模型选择 (已锁定)
    selected_model_name = st.selectbox(
        "🧠 选择核心模型", 
        TARGET_MODELS,
        index=0,
        help="2.5 Flash 速度快，3.0 Pro 细节更强"
    )

    # 2. 上传图片
    uploaded_file = st.file_uploader("📤 上传产品原图", type=["jpg", "png", "jpeg", "webp"])
    if uploaded_file:
        st.image(uploaded_file, caption="原图预览", width=250)

    # 3. 比例选择 (新增)
    ratio_selection = st.selectbox(
        "📐 输出比例 (电商标准)",
        options=list(RATIO_PROMPTS.keys()),
        index=0
    )

    # 4. 提示词输入
    user_prompt = st.text_area(
        "📝 修改指令", 
        height=100, 
        placeholder="例如：Change background to a modern living room, soft morning light...",
        value="Keep the product unchanged, change background to a clean white studio setting with soft shadows."
    )

    # 5. 素材库框架 (预留接口)
    with st.expander("📂 场景与光影素材库 (Coming Soon)", expanded=False):
        st.info("🚧 开发中：未来这里将提供可视化素材选择")
        # 模拟未来的 UI
        tab1, tab2 = st.tabs(["光影预设", "场景贴图"])
        with tab1:
            st.markdown("🔴 伦勃朗光 (未激活)")
            st.markdown("🔵 蝴蝶光 (未激活)")
        with tab2:
            st.markdown("🏞️ 森林 (未激活)")
            st.markdown("🏙️ 街道 (未激活)")
        st.caption("目前请在上方指令框中直接描述场景。")

    # 6. 运行按钮
    btn_run = st.button("🚀 执行生成", type="primary")

# === 右侧：结果展示 ===
with col_right:
    st.subheader("🖼️ 生成结果")
    
    if btn_run:
        if not uploaded_file or not user_prompt:
            st.warning("⚠️ 请先上传图片并输入指令")
        else:
            with st.spinner(f"正在调用 {selected_model_name} 进行处理..."):
                try:
                    # 准备数据
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    
                    # 组合最终 Prompt = 用户指令 + 比例后缀
                    final_prompt = user_prompt + RATIO_PROMPTS[ratio_selection] + ", high quality, 8k resolution, commercial photography"
                    
                    # 实例化模型
                    model = genai.GenerativeModel(selected_model_name)
                    
                    # 发送请求
                    # Gemini 的图生图通常不需要复杂的 config，它主要听 prompt 的话
                    response = model.generate_content([final_prompt, img_pil], stream=True)
                    
                    # --- 核心解析逻辑 (保持你测试成功的版本) ---
                    found_image = False
                    full_text = ""
                    
                    # 创建占位符，实现流式输出的感觉
                    msg_placeholder = st.empty()
                    
                    for chunk in response:
                        if hasattr(chunk, "parts"):
                            for part in chunk.parts:
                                if part.text:
                                    full_text += part.text
                                    msg_placeholder.info(f"模型思考中: {full_text}")
                                
                                if part.inline_data:
                                    image_data = part.inline_data.data
                                    image = Image.open(io.BytesIO(image_data))
                                    
                                    # 显示结果
                                    st.success("✅ 生成成功！")
                                    st.image(image, caption=f"Gemini 生成 | {ratio_selection}", use_column_width=True)
                                    
                                    # 下载按钮
                                    buf = io.BytesIO()
                                    image.save(buf, format="PNG")
                                    st.download_button(
                                        label="📥 下载高清原图",
                                        data=buf.getvalue(),
                                        file_name="gemini_result.png",
                                        mime="image/png"
                                    )
                                    found_image = True
                                    msg_placeholder.empty() # 清除文字提示

                    if not found_image:
                        st.error("❌ 未生成图片")
                        if full_text:
                            with st.expander("查看模型反馈"):
                                st.write(full_text)

                except Exception as e:
                    st.error(f"❌ 运行报错: {str(e)}")
                    st.caption("提示：请确保你的 API Key 拥有这两个预览版模型的使用权限。")
