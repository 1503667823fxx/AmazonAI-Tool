import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
from collections import deque 

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
st.set_page_config(page_title="Fashion AI Pro Workflow", page_icon="🧬", layout="wide")

# --- 1. 鉴权配置 ---
if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 错误：未找到 REPLICATE_API_TOKEN")
    st.stop()

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 错误：未找到 GOOGLE_API_KEY")
    st.stop()

# --- 2. 常量与样式 ---
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

# 读图模型
ANALYSIS_MODELS = [
    "models/gemini-2.0-flash-exp", 
    "models/gemini-1.5-pro",
    "models/gemini-1.5-flash"
]

# 生图模型
GOOGLE_IMG_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3-pro-image-preview"
]

# 📐 【新增】比例控制
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
if "flux_prompt" not in st.session_state:
    st.session_state["flux_prompt"] = ""

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

with st.sidebar:
    st.header("🕒 历史记录")
    if len(st.session_state["history_queue"]) == 0:
        st.caption("暂无生成记录")
    else:
        for item in st.session_state["history_queue"]:
            st.markdown(f"**{item['source']}** - {item['time']}")
            if isinstance(item['image'], bytes):
                st.image(item['image'], use_column_width=True)
            else:
                st.image(item['image'], use_column_width=True)
            st.divider()

st.title("🧬 Fashion AI 全流程工作流")
st.caption("Flow: 理解与构思 -> Google 原型 -> Flux 精修")

col_main, col_preview = st.columns([1.2, 1], gap="large")

with col_main:
    # ==========================================
    # Step 1: 需求分析 (The Brain)
    # ==========================================
    st.markdown('<div class="step-header">Step 1: 需求分析与构思</div>', unsafe_allow_html=True)
    
    analysis_model = st.selectbox("0. 选择读图模型", ANALYSIS_MODELS, index=0)
    uploaded_file = st.file_uploader("1. 上传图片", type=["jpg", "png", "webp"])
    
    task_type = st.radio(
        "2. 选择生成类型", 
        ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"], 
        horizontal=True
    )
    
    user_idea = st.text_area("3. 你的想法", height=70, placeholder="例如：给模特加上黑色腿环，鞋子换成灰色，背景保持不变...")

    if st.button("🧠 生成设计方案"):
        if not uploaded_file:
            st.warning("请先上传图片")
        else:
            with st.spinner(f"正在使用 {analysis_model} 分析..."):
                try:
                    uploaded_file.seek(0)
                    img_obj = Image.open(uploaded_file)
                    model = genai.GenerativeModel(analysis_model)
                    
                    special_instruction = ""
                    if "产品图" in task_type:
                        special_instruction = "IMPORTANT: Remove models/body parts. Flat lay product."

                    prompt_req = f"""
                    Role: Expert Commercial Art Director.
                    Task: Write a prompt based on User Idea.
                    User Idea: "{user_idea}"
                    Type: {task_type}
                    {special_instruction}
                    
                    CRITICAL: If user asks for small edits (e.g. change color, add item), emphasize maintaining the original subject identity and pose.
                    Output: English Prompt Only.
                    """
                    
                    response = model.generate_content([prompt_req, img_obj])
                    if response.text:
                        st.session_state["draft_prompt"] = response.text.strip()
                        st.success("方案已生成，请进入下一步")
                        time.sleep(0.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"分析失败: {e}")

    # ==========================================
    # Step 2: Google 原型 (The Skeleton)
    # ==========================================
    if st.session_state.get("draft_prompt"):
        st.markdown('<div class="step-header">Step 2: Google 原型生成</div>', unsafe_allow_html=True)
        
        edited_prompt = st.text_area("4. 确认提示词", value=st.session_state["draft_prompt"], height=100)
        st.session_state["draft_prompt"] = edited_prompt 

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            google_model = st.selectbox("5. 选择生图模型", GOOGLE_IMG_MODELS)
        with col_g2:
            # 【修复 1】补回比例选择
            selected_ratio = st.selectbox("6. 图片比例", list(RATIO_PROMPTS.keys()))

        if st.button("🎨 运行 Google 生成"):
            with st.spinner(f"正在调用 {google_model} ..."):
                try:
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    gen_model = genai.GenerativeModel(google_model)
                    
                    # 拼接比例后缀
                    final_g_prompt = edited_prompt + RATIO_PROMPTS[selected_ratio]
                    
                    response = gen_model.generate_content([final_g_prompt, img_pil], stream=True)
                    
                    found_img = False
                    for chunk in response:
                        if hasattr(chunk, "parts"):
                            for part in chunk.parts:
                                if part.inline_data:
                                    img_data = part.inline_data.data
                                    st.session_state["google_image_bytes"] = img_data 
                                    found_img = True
                                    update_history(img_data, source=f"Google ({selected_ratio})", prompt_summary=edited_prompt)
                    
                    if found_img:
                        st.success("Google 生成完成！")
                        st.rerun()
                    else:
                        st.error("Google 未返回图片")
                except Exception as e:
                    st.error(f"Google 生成出错: {e}")

    # ==========================================
    # Step 3: Flux 精修 (The Final Polish)
    # ==========================================
    # 只要有 Google 结果 或者 已经有草稿，就可以尝试用 Flux
    if st.session_state.get("draft_prompt"):
        st.markdown('<div class="step-header">Step 3: Flux 质感精修</div>', unsafe_allow_html=True)
        
        st.info("💡 提示：Flux 改细节(如加腿环)请尝试调整「重绘幅度」。幅度过大会导致人物变脸。")
        
        flux_feedback = st.text_input("7. (可选) 修改建议", placeholder="例如：Leg band should be leather texture...")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            # 【修复 2】底图来源选择
            base_image_source = st.selectbox(
                "8. 底图来源", 
                ["使用原始上传图片 (推荐保真)", "使用 Google 生成图 (推荐构图)"],
                help="想保留原模特长相？选「原始图片」。想保留 Google 的新背景？选「Google 生成图」。"
            )
        with col_f2:
            # 【修复 2】重绘幅度滑块
            strength_val = st.slider(
                "9. 重绘幅度 (Strength)", 
                0.1, 1.0, 0.55, 
                help="🔴 0.3-0.5: 微调/加细节(不易变脸) \n🔴 0.6-0.8: 换背景/换姿势(容易变脸) \n🔴 0.9-1.0: 重新画"
            )

        if st.button("✨ 优化 Flux 指令并生成"):
            with st.spinner("Flux 正在重绘..."):
                try:
                    # 确定底图
                    if "原始" in base_image_source:
                        uploaded_file.seek(0)
                        input_image_obj = uploaded_file
                    else:
                        # 使用 Google 的图
                        if st.session_state.get("google_image_bytes"):
                            input_image_obj = io.BytesIO(st.session_state["google_image_bytes"])
                        else:
                            st.warning("还没有 Google 生成图，自动切换回原图。")
                            uploaded_file.seek(0)
                            input_image_obj = uploaded_file

                    # 优化 Prompt
                    optimizer_model = genai.GenerativeModel(analysis_model)
                    opt_req = f"""
                    Original Prompt: {st.session_state["draft_prompt"]}
                    User Feedback: {flux_feedback}
                    
                    Task: Rewrite for Flux.1-Dev.
                    IMPORTANT: User wants to modify specific details (like adding items or changing colors) while keeping the main subject consistent.
                    Add keywords: "photorealistic, 8k, detailed texture".
                    Output: English Prompt Only.
                    """
                    opt_res = optimizer_model.generate_content(opt_req)
                    final_flux_prompt = opt_res.text.strip()
                    st.session_state["flux_prompt"] = final_flux_prompt 
                    
                    # 调用 Replicate
                    output = replicate.run(
                        "black-forest-labs/flux-dev",
                        input={
                            "prompt": final_flux_prompt,
                            "image": input_image_obj, 
                            "prompt_strength": strength_val, # 使用用户设定的值
                            "go_fast": True,
                            "num_outputs": 1,
                            "output_format": "jpg",
                            "output_quality": 100,
                            "negative_prompt": "blurry, low quality, distorted face, bad anatomy"
                        }
                    )
                    
                    flux_url = str(output[0]) if isinstance(output, list) else str(output)
                    update_history(flux_url, source=f"Flux (Str:{strength_val})", prompt_summary=final_flux_prompt)
                    st.success("Flux 精修完成！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Flux 处理失败: {e}")

# ==========================================
# 右侧预览区
# ==========================================
with col_preview:
    st.header("🖼️ 实时画布")
    
    # 显示 Google 结果
    if st.session_state.get("google_image_bytes"):
        st.subheader("Google Prototype")
        g_img = Image.open(io.BytesIO(st.session_state["google_image_bytes"]))
        st.image(g_img, caption="Google Result", use_column_width=True)
        st.download_button("📥 下载 Google 图", st.session_state["google_image_bytes"], file_name="google_draft.png")
    
    # 显示 Flux 结果 (从历史中找最新的)
    latest_flux = None
    for item in st.session_state["history_queue"]:
        if "Flux" in item["source"]:
            latest_flux = item
            break
            
    if latest_flux:
        st.divider()
        st.subheader("Flux Final Result")
        st.image(latest_flux["image"], caption=f"Flux Result ({latest_flux['time']})", use_column_width=True)
        st.info(f"使用的 Prompt: {latest_flux.get('desc', '')}")
    
    if not st.session_state.get("google_image_bytes") and not latest_flux:
        st.info("等待操作... 请在左侧上传图片并开始。")
        if uploaded_file:
            st.image(uploaded_file, caption="原始图片", width=200)
