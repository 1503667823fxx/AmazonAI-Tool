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
# Replicate
if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 错误：未找到 REPLICATE_API_TOKEN")
    st.stop()

# Google
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
    .history-img {border: 2px solid #ddd; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# 【Step 1】用的读图模型列表 (你指定的)
ANALYSIS_MODELS = [
    "models/gemini-flash-latest",  # 推荐：性价比最高的 2.5 版本
    "models/gemini-2.5-pro",        # 备用：经典强力模型
    "models/gemini-3-pro-preview"       # 备用：顶尖模型
]

# 【Step 2】用的生图模型列表 (之前测试通过的)
GOOGLE_IMG_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3-pro-image-preview"
]

# --- 3. 状态管理 ---
if "history_queue" not in st.session_state:
    st.session_state["history_queue"] = deque(maxlen=5)
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 1
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

# 侧边栏
with st.sidebar:
    st.header("🕒 历史记录 (Latest 5)")
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
st.caption("Flow: 理解与构思 -> Google 原型生成 -> Flux 精细化重绘")

col_main, col_preview = st.columns([1.2, 1], gap="large")

with col_main:
    # ==========================================
    # Step 1: 输入与构思 (The Brain)
    # ==========================================
    st.markdown('<div class="step-header">Step 1: 需求分析与构思</div>', unsafe_allow_html=True)
    
    # 【修改点 1】让用户选择读图模型，解决 404 问题
    analysis_model = st.selectbox(
        "0. 选择读图模型 (Brain)", 
        ANALYSIS_MODELS, 
        index=0,
        help="如果报错 404，请切换其他模型尝试。"
    )

    uploaded_file = st.file_uploader("1. 上传图片", type=["jpg", "png", "webp"])
    
    task_type = st.radio(
        "2. 选择生成类型", 
        ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"], 
        horizontal=True,
        help="产品图模式会自动尝试去除模特，将衣物/商品平铺展示。"
    )
    
    user_idea = st.text_area("3. 你的想法 (简单描述即可)", height=70, placeholder="例如：在海边的夕阳下，光线温暖...")

    if st.button("🧠 生成设计方案 (Draft Prompt)"):
        if not uploaded_file:
            st.warning("请先上传图片")
        else:
            with st.spinner(f"正在使用 {analysis_model} 读图并设计方案..."):
                try:
                    uploaded_file.seek(0)
                    img_obj = Image.open(uploaded_file)
                    
                    # 【修改点 2】使用用户选择的模型，而不是写死的 gemini-1.5-flash
                    model = genai.GenerativeModel(analysis_model)
                    
                    special_instruction = ""
                    if "产品图" in task_type:
                        special_instruction = "IMPORTANT: User wants a 'Product Only' shot. Remove any human models, body parts, or mannequins. Lay the clothing/product flat or hang it invisibly. Focus purely on the item itself on a clean background."

                    prompt_req = f"""
                    Role: Expert Commercial Art Director.
                    Task: Analyze the image and user idea to write a perfect prompt for AI Image Generation.
                    
                    Input Image: A fashion product/scene.
                    User Goal: {task_type}
                    User Idea: "{user_idea}"
                    
                    {special_instruction}
                    
                    Requirements:
                    1. Describe the Subject (Product) in detail (keep it faithful).
                    2. Describe the Environment/Background based on User Idea.
                    3. Lighting & Style: Commercial photography, 8k, masterpiece.
                    
                    Output: ONLY the English Prompt text. No explanations.
                    """
                    
                    response = model.generate_content([prompt_req, img_obj])
                    
                    if response.text:
                        st.session_state["draft_prompt"] = response.text.strip()
                        st.session_state["current_step"] = 2
                        st.rerun()
                    else:
                        st.error("模型返回了空内容，请重试。")
                        
                except Exception as e:
                    st.error(f"分析失败: {e}")
                    st.info("💡 提示：报错 404 说明你选的模型名称不对，请在上方下拉菜单换一个模型。")

    # ==========================================
    # Step 2: Google 原型验证 (The Skeleton)
    # ==========================================
    if st.session_state.get("draft_prompt"):
        st.markdown('<div class="step-header">Step 2: Google 原型生成</div>', unsafe_allow_html=True)
        
        edited_prompt = st.text_area("4. 确认/修改 提示词方案", value=st.session_state["draft_prompt"], height=120)
        st.session_state["draft_prompt"] = edited_prompt 

        # 这里的模型列表是你之前测试通过的
        google_model = st.selectbox("5. 选择多模态生图 AI", GOOGLE_IMG_MODELS)

        if st.button("🎨 运行 Google 生成 (原型验证)"):
            with st.spinner(f"正在调用 {google_model} ..."):
                try:
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    
                    gen_model = genai.GenerativeModel(google_model)
                    
                    # Google 图生图逻辑
                    response = gen_model.generate_content([edited_prompt, img_pil], stream=True)
                    
                    found_img = False
                    for chunk in response:
                        if hasattr(chunk, "parts"):
                            for part in chunk.parts:
                                if part.inline_data:
                                    img_data = part.inline_data.data
                                    st.session_state["google_image_bytes"] = img_data 
                                    found_img = True
                                    update_history(img_data, source="Google", prompt_summary=edited_prompt)
                    
                    if found_img:
                        st.success("Google 生成完成！请在右侧查看。")
                        st.session_state["current_step"] = 3
                    else:
                        st.error("Google 未返回图片，可能是被安全策略拦截或 Prompt 违规。")
                except Exception as e:
                    st.error(f"Google 生成出错: {e}")

    # ==========================================
    # Step 3: Flux 精修 (The Final Polish)
    # ==========================================
    if st.session_state.get("google_image_bytes"):
        st.markdown('<div class="step-header">Step 3: Flux 质感精修</div>', unsafe_allow_html=True)
        
        st.info("是否对 Google 的结果满意？如果不满意，可以用 Flux 进行更强力的重绘。")
        
        flux_feedback = st.text_input("6. (可选) 填写修改建议", placeholder="例如：增加皮肤质感，光线再柔和一点，背景虚化...")
        
        if st.button("✨ 优化 Flux 指令并生成"):
            with st.spinner("正在优化指令并调用 Flux Pro..."):
                try:
                    # 【修改点 3】这里也使用 Step 1 选中的模型来做文本优化，保证一致性
                    optimizer_model = genai.GenerativeModel(analysis_model)
                    
                    opt_req = f"""
                    Base Prompt: {st.session_state["draft_prompt"]}
                    User Feedback: {flux_feedback}
                    
                    Task: Rewrite the Base Prompt to incorporate User Feedback. 
                    Ensure keywords for Flux model are added: "hyper-realistic, 8k, film grain, ray tracing".
                    Output: ONLY the optimized English Prompt.
                    """
                    opt_res = optimizer_model.generate_content(opt_req)
                    final_flux_prompt = opt_res.text.strip()
                    st.session_state["flux_prompt"] = final_flux_prompt 
                    
                    uploaded_file.seek(0)
                    
                    output = replicate.run(
                        "black-forest-labs/flux-dev",
                        input={
                            "prompt": final_flux_prompt,
                            "image": uploaded_file, 
                            "prompt_strength": 0.75, 
                            "go_fast": True,
                            "num_outputs": 1,
                            "output_format": "jpg",
                            "output_quality": 100,
                            "negative_prompt": "blurry, low quality, illustration, painting, cartoon"
                        }
                    )
                    
                    flux_url = str(output[0]) if isinstance(output, list) else str(output)
                    
                    update_history(flux_url, source="Flux", prompt_summary=final_flux_prompt)
                    st.success("Flux 精修完成！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Flux 处理失败: {e}")

# ==========================================
# 右侧预览区
# ==========================================
with col_preview:
    st.header("🖼️ 实时画布")
    
    if st.session_state.get("google_image_bytes"):
        st.subheader("Google Prototype")
        g_img = Image.open(io.BytesIO(st.session_state["google_image_bytes"]))
        st.image(g_img, caption="Google Result", use_column_width=True)
        st.download_button("📥 下载 Google 图", st.session_state["google_image_bytes"], file_name="google_draft.png")
    
    latest_flux = None
    for item in st.session_state["history_queue"]:
        if item["source"] == "Flux":
            latest_flux = item
            break
            
    if latest_flux:
        st.divider()
        st.subheader("Flux Final Result")
        st.image(latest_flux["image"], caption="Flux Result", use_column_width=True)
        st.info(f"使用的 Prompt: {latest_flux.get('desc', '')}")
    
    if not st.session_state.get("google_image_bytes") and not latest_flux:
        st.info("等待操作... 请在左侧上传图片并开始。")
        if uploaded_file:
            st.image(uploaded_file, caption="原始图片", width=200)
        for i, url in enumerate(st.session_state["generated_image_urls"]):
            st.image(url, caption=f"Result {i+1}", use_column_width=True)
            st.markdown(f"[📥 点击下载大图]({url})")
