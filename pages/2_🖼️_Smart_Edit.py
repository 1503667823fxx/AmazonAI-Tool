import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
from collections import deque 

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# --- 1. 鉴权配置 (只保留 Google) ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 错误：未找到 GOOGLE_API_KEY，请检查 .streamlit/secrets.toml")
    st.stop()

# --- 2. 常量定义 ---
st.markdown("""
<style>
    .step-header {
        background: linear-gradient(90deg, #f0f2f6 0%, #ffffff 100%);
        padding: 10px 20px;
        border-radius: 8px;
        border-left: 5px solid #4F8BF9;
        margin-top: 20px;
        margin-bottom: 10px;
        font-weight: bold;
        color: #31333F;
    }
    .stButton button {border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# 读图分析模型 (Brain)
ANALYSIS_MODELS = [
    "models/gemini-flash-latest", 
    "models/gemini-2.5-pro",
    "models/gemini-3-pro-preview"
]

# 生图模型 (Painter)
GOOGLE_IMG_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3-pro-image-preview"
]

# 比例控制
RATIO_PROMPTS = {
    "保持原图比例 (Original)": "",
    "1:1 正方形 (Amazon 主图)": ", crop and center composition to 1:1 square aspect ratio",
    "3:4 纵向 (手机端展示)": ", adjust composition to 3:4 portrait aspect ratio",
    "4:3 横向 (PC端展示)": ", adjust composition to 4:3 landscape aspect ratio",
    "16:9 宽屏 (Banner海报)": ", cinematic 16:9 wide aspect ratio"
}

# --- 3. 状态管理 ---
if "history_queue" not in st.session_state:
    st.session_state["history_queue"] = deque(maxlen=5)
if "draft_prompt" not in st.session_state:
    st.session_state["draft_prompt"] = ""
if "google_image_bytes" not in st.session_state:
    st.session_state["google_image_bytes"] = None 

# --- 4. 辅助函数 ---
def update_history(image_data, source="AI", prompt_summary=""):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state["history_queue"].appendleft({
        "image": image_data,
        "source": source,
        "time": timestamp,
        "desc": prompt_summary[:20] + "..."
    })

# ==========================================
# 🚀 主界面布局
# ==========================================

# 侧边栏：历史记录
with st.sidebar:
    st.header("🕒 历史记录")
    if len(st.session_state["history_queue"]) == 0:
        st.caption("暂无生成记录")
    else:
        for item in st.session_state["history_queue"]:
            st.markdown(f"**{item['source']}** - {item['time']}")
            st.image(item['image'], use_column_width=True)
            st.divider()

st.title("🧬 Fashion AI Core (Google Native)")
st.caption("Flow: 智能读图分析 -> 提示词设计 -> Google 原生图生图")

col_main, col_preview = st.columns([1.2, 1], gap="large")

with col_main:
    # ==========================================
    # Step 1: 需求分析 (The Brain)
    # ==========================================
    st.markdown('<div class="step-header">Step 1: 需求分析与提示词设计</div>', unsafe_allow_html=True)
    
    # 1. 选择大脑
    analysis_model = st.selectbox("1. 选择读图模型 (Brain)", ANALYSIS_MODELS, index=0)
    
    # 2. 上传素材
    uploaded_file = st.file_uploader("2. 上传原始图片", type=["jpg", "png", "webp"])
    
    # 3. 任务配置
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        task_type = st.selectbox(
            "3. 生成类型", 
            ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"]
        )
    with col_t2:
        user_idea = st.text_input("4. 你的想法 (可选)", placeholder="例如：放在白色大理石桌面上，自然光...")

    # 4. 生成按钮
    if st.button("🧠 生成设计方案 (Draft Prompt)", type="primary"):
        if not uploaded_file:
            st.warning("⚠️ 请先上传图片")
        else:
            with st.spinner(f"正在使用 {analysis_model} 阅读图片并构思..."):
                try:
                    uploaded_file.seek(0)
                    img_obj = Image.open(uploaded_file)
                    model = genai.GenerativeModel(analysis_model)
                    
                    # 针对产品图的特殊指令
                    special_instruction = ""
                    if "产品图" in task_type:
                        special_instruction = "IMPORTANT: Remove any human models, body parts, or mannequins. Lay the clothing/product flat or hang it invisibly. Focus purely on the item itself on a clean background."

                    prompt_req = f"""
                    Role: Expert Commercial Art Director.
                    Task: Write a precise Prompt for AI Image Generation based on the input image.
                    
                    Input Context:
                    - User Goal: {task_type}
                    - User Idea: "{user_idea}"
                    
                    {special_instruction}
                    
                    Requirements:
                    1. Describe the Subject (Product) faithfully (color, texture, shape).
                    2. Describe the Lighting & Environment clearly.
                    3. Style keywords: Commercial photography, 8k resolution, photorealistic.
                    
                    Output: Return ONLY the English prompt text. No markdown, no explanations.
                    """
                    
                    response = model.generate_content([prompt_req, img_obj])
                    if response.text:
                        st.session_state["draft_prompt"] = response.text.strip()
                        st.success("✅ 方案已生成！")
                        time.sleep(0.2)
                        st.rerun()
                except Exception as e:
                    st.error(f"分析失败: {e}")
                    st.info("提示：如果报错 404，请切换 gemini-2.5-pro 试试。")

    # ==========================================
    # Step 2: Google 原生生成 (The Painter)
    # ==========================================
    if st.session_state.get("draft_prompt"):
        st.markdown('<div class="step-header">Step 2: 执行图生图</div>', unsafe_allow_html=True)
        
        # 5. 编辑 Prompt
        edited_prompt = st.text_area("5. 确认/编辑 提示词", value=st.session_state["draft_prompt"], height=120)
        st.session_state["draft_prompt"] = edited_prompt 

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            google_model = st.selectbox("6. 选择生图模型", GOOGLE_IMG_MODELS)
        with col_g2:
            selected_ratio = st.selectbox("7. 图片比例", list(RATIO_PROMPTS.keys()))

        if st.button("🎨 立即生成 (Generate)", type="primary"):
            with st.spinner(f"正在调用 {google_model} 绘图..."):
                try:
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    gen_model = genai.GenerativeModel(google_model)
                    
                    # 组合最终指令
                    final_g_prompt = edited_prompt + RATIO_PROMPTS[selected_ratio]
                    
                    # 调用 API
                    response = gen_model.generate_content([final_g_prompt, img_pil], stream=True)
                    
                    found_img = False
                    # 解析流式返回
                    for chunk in response:
                        if hasattr(chunk, "parts"):
                            for part in chunk.parts:
                                if part.inline_data:
                                    img_data = part.inline_data.data
                                    st.session_state["google_image_bytes"] = img_data 
                                    found_img = True
                                    # 更新历史
                                    update_history(img_data, source=f"Google ({selected_ratio})", prompt_summary=edited_prompt)
                    
                    if found_img:
                        st.success("🎉 生成成功！")
                        st.rerun()
                    else:
                        st.error("❌ 未生成图片。可能是 Prompt 触发了安全过滤。")
                except Exception as e:
                    st.error(f"生成出错: {e}")

# ==========================================
# 右侧预览区
# ==========================================
with col_preview:
    st.header("🖼️ 结果预览")
    
    # 1. 结果图
    if st.session_state.get("google_image_bytes"):
        st.image(st.session_state["google_image_bytes"], caption="Google 生成结果", use_column_width=True)
        
        # 下载按钮
        st.download_button(
            label="📥 下载高清大图",
            data=st.session_state["google_image_bytes"],
            file_name="fashion_ai_result.png",
            mime="image/png"
        )
    
    # 2. 原图对照
    if uploaded_file:
        with st.expander("查看原图对照", expanded=False):
            st.image(uploaded_file, caption="原始输入图", width=200)

    # 3. 初始状态提示
    if not st.session_state.get("google_image_bytes") and not uploaded_file:
        st.info("👈 请在左侧开始操作流程")
