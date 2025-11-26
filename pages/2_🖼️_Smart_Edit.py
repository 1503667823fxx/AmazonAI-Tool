import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
# 移除 random 库，避免人为破坏同一性
from collections import deque 

# --- 0. 基础设置与门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# 执行安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 1. 鉴权配置 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 错误：未找到 GOOGLE_API_KEY")
    st.stop()

# --- 2. 样式优化 (CSS) ---
st.markdown("""
<style>
    .step-header {
        background: linear-gradient(90deg, #e3f2fd 0%, #ffffff 100%);
        padding: 12px 20px;
        border-radius: 8px;
        border-left: 6px solid #2196F3;
        margin-top: 25px;
        margin-bottom: 15px;
        font-weight: 600;
        color: #0D47A1;
        font-size: 1.1rem;
    }
    .stButton button {
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    /* 预览图容器优化 */
    .preview-container img {
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 常量定义 ---
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]

RATIO_MAP = {
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "4:3 (常规横向)": ", adjust composition to 4:3 landscape aspect ratio",
    "21:9 (电影感超宽)": ", cinematic 21:9 ultrawide aspect ratio"
}

# --- 4. 状态管理 ---
if "history_queue" not in st.session_state: st.session_state["history_queue"] = deque(maxlen=10)
# Tab 1 States
if "std_draft_prompt" not in st.session_state: st.session_state["std_draft_prompt"] = ""
if "std_images" not in st.session_state: st.session_state["std_images"] = []
# Tab 2 States
if "var_draft_prompt" not in st.session_state: st.session_state["var_draft_prompt"] = ""
if "batch_results" not in st.session_state: st.session_state["batch_results"] = []
# Tab 3 States
if "bg_draft_prompt" not in st.session_state: st.session_state["bg_draft_prompt"] = ""
if "bg_results" not in st.session_state: st.session_state["bg_results"] = []

# --- 5. 辅助函数 ---
def update_history(image_data, source="AI", prompt_summary=""):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state["history_queue"].appendleft({
        "image": image_data, "source": source, "time": timestamp, "desc": prompt_summary[:30] + "..."
    })

def convert_image_format(image_bytes, format="PNG"):
    """将图片字节流转换为指定格式"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        # JPEG 不支持透明通道，需转 RGB
        if format.upper() == "JPEG":
            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.save(buf, format=format, quality=95)
        return buf.getvalue(), f"image/{format.lower()}"
    except Exception as e:
        return image_bytes, "image/png"

def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    """封装 API 调用"""
    final_prompt = prompt + ratio_suffix + ", high quality, 8k resolution"
    gen_model = genai.GenerativeModel(model_name)
    try:
        response = gen_model.generate_content([final_prompt, image_input], stream=True)
        for chunk in response:
            if hasattr(chunk, "parts"):
                for part in chunk.parts:
                    if part.inline_data:
                        return part.inline_data.data
    except Exception as e:
        print(f"Error: {e}")
        return None
    return None

# ==========================================
# 🚀 侧边栏：历史记录
# ==========================================
with st.sidebar:
    st.title("🗂️ 工作区")
    # 全局格式选择
    download_format = st.radio("📥 下载格式偏好", ["PNG", "JPEG"], horizontal=True, help="JPEG 体积更小，PNG 画质无损")
    
    with st.expander("🕒 历史记录 (History)", expanded=False):
        if len(st.session_state["history_queue"]) == 0:
            st.caption("暂无生成记录")
        else:
            for item in st.session_state["history_queue"]:
                st.markdown(f"**{item['source']}**")
                st.caption(f"Time: {item['time']}")
                st.image(item['image'], width=150)
                st.divider()

# ==========================================
# 🚀 主界面
# ==========================================
st.title("🧬 Fashion AI Core V4.0")
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# ==========================================
# TAB 1: 标准工作流 (Standard)
# ==========================================
with tab_workflow:
    col_main, col_preview = st.columns([1.3, 1], gap="large")

    with col_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1: analysis_model = st.selectbox("1. 读图模型", ANALYSIS_MODELS, index=0)
        with c2: uploaded_file = st.file_uploader("2. 上传参考图", type=["jpg", "png", "webp"], key="std_upload")

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        user_idea = st.text_area("4. 你的创意", height=100, placeholder="例如：改为极简主义风格，白色背景...")

        if st.button("🧠 生成 Prompt", type="primary"):
            if not uploaded_file: st.warning("⚠️ 请先上传图片")
            else:
                with st.spinner("AI 正在思考..."):
                    try:
                        uploaded_file.seek(0)
                        img_obj = Image.open(uploaded_file)
                        model = genai.GenerativeModel(analysis_model)
                        prompt_req = f"Role: Art Director. Task: Create a prompt based on User Idea: '{user_idea}'. Type: {task_type}. Output: English Prompt Only."
                        response = model.generate_content([prompt_req, img_obj])
                        st.session_state["std_draft_prompt"] = response.text.strip()
                        st.rerun()
                    except Exception as e: st.error(f"分析失败: {e}")

        # Step 2
        if st.session_state.get("std_draft_prompt"):
            st.markdown('<div class="step-header">Step 2: 执行生成</div>', unsafe_allow_html=True)
            edited_prompt = st.text_area("Prompt", value=st.session_state["std_draft_prompt"], height=120)
            st.session_state["std_draft_prompt"] = edited_prompt

            cg1, cg2, cg3 = st.columns(3)
            with cg1: google_model = st.selectbox("模型", GOOGLE_IMG_MODELS)
            with cg2: selected_ratio_key = st.selectbox("比例", list(RATIO_MAP.keys()))
            with cg3: num_images = st.number_input("数量", 1, 4, 1)

            if "flash" in google_model and "1:1" not in selected_ratio_key:
                st.warning("⚠️ 注意：Gemini 2.5 Flash 模型通常强制 1:1 输出。如需 4:3 或 21:9，建议切换至 3.0 Pro 模型。")

            if st.button("🎨 开始生成", type="primary"):
                st.session_state["std_images"] = []
                bar = st.progress(0)
                for i in range(num_images):
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    img_data = generate_image_call(google_model, edited_prompt, img_pil, RATIO_MAP[selected_ratio_key])
                    if img_data:
                        st.session_state["std_images"].append(img_data)
                        update_history(img_data, source=f"Std {i+1}", prompt_summary=edited_prompt)
                    bar.progress((i+1)/num_images)
                    time.sleep(1)
                st.success("完成")

    # 右侧预览
    with col_preview:
        st.subheader("🖼️ 快速预览")
        if st.session_state["std_images"]:
            for idx, img_bytes in enumerate(st.session_state["std_images"]):
                st.image(img_bytes, caption=f"Result {idx+1}", width=350) # 预览宽度
                final_bytes, mime = convert_image_format(img_bytes, download_format)
                st.download_button(f"📥 下载 ({download_format})", final_bytes, file_name=f"std_{idx}.{download_format.lower()}", mime=mime)
        elif uploaded_file: st.image(uploaded_file, caption="原图", width=200)

# ==========================================
# TAB 2: ⚡ 变体改款 (Restyling - Logic Fix)
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 服装改款工厂 (Restyling)")
    st.info("💡 逻辑升级：AI 先读取产品特征，再结合改款指令，确保【产品同一性】。")
    
    cv_left, cv_right = st.columns([1, 1.5], gap="large")
    with cv_left:
        # Step 1: 分析
        st.markdown("#### Step 1: AI 读取产品特征")
        var_file = st.file_uploader("上传原版图片", type=["jpg", "png"], key="var_upload")
        var_analysis_model = st.selectbox("分析模型", ANALYSIS_MODELS, index=0, key="var_ana_model")
        
        if st.button("👁️ AI 读图提取特征", key="btn_var_ana"):
            if not var_file: st.warning("请先上传图片")
            else:
                with st.spinner("正在提取产品特征..."):
                    try:
                        var_file.seek(0)
                        v_img = Image.open(var_file)
                        model = genai.GenerativeModel(var_analysis_model)
                        # 强约束：只描述衣服本身特征
                        prompt = "Describe the main fashion product in detail: Silhouette, Fabric, Color, Pattern, Neckline, Sleeve style. Be precise."
                        resp = model.generate_content([prompt, v_img])
                        st.session_state["var_draft_prompt"] = resp.text.strip()
                        st.success("特征提取成功！")
                    except Exception as e: st.error(f"读取失败: {e}")

        # Step 2: 改款
        st.markdown("#### Step 2: 改款设置")
        # 显示/编辑 AI 提取的特征
        base_desc = st.text_area("产品基础特征 (AI提取)", value=st.session_state.get("var_draft_prompt", ""), height=100, disabled=False, help="这是AI看到的你产品的样子，你可以手动修正它。")
        
        CHANGE_LEVELS = {
            "🎨 微调 (纹理/面料)": "Keep the main silhouette and structure EXACTLY the same. Only modify fabric texture or material details.",
            "✂️ 中改 (领口/袖口)": "Keep the overall fit and shape. You can modify specific details like collar, sleeves, or pockets.",
            "🪄 大改 (版型重构)": "Redesign the fashion item based on the original vibe. Change silhouette and cut."
        }
        change_level = st.selectbox("改款幅度", list(CHANGE_LEVELS.keys()))
        user_mod = st.text_area("改款指令", height=80, placeholder="例如：改为丝绸材质，增加蕾丝花边...")
        
        batch_count = st.slider("生成数量", 1, 20, 4, key="var_batch")
        var_model = st.selectbox("生图模型", GOOGLE_IMG_MODELS, key="var_gen_model")
        start_batch = st.button("🚀 启动批量改款", type="primary")

    with cv_right:
        st.subheader("📦 方案池 (预览)")
        if start_batch and var_file and base_desc:
            st.session_state["batch_results"] = []
            grid = st.columns(3)
            sys_instruct = CHANGE_LEVELS[change_level]
            my_bar = st.progress(0)
            
            for i in range(batch_count):
                try:
                    var_file.seek(0)
                    v_img = Image.open(var_file)
                    # 核心逻辑修复：不使用 random seed 破坏同一性
                    # 而是结合“原特征描述” + “改款指令”
                    prompt = f"""
                    Task: Fashion Restyling.
                    Base Product Description: {base_desc}
                    Constraint: {sys_instruct}
                    User Modification Request: {user_mod}
                    Requirement: High quality, photorealistic, 8k.
                    Variant ID: {i}
                    """
                    img_data = generate_image_call(var_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["batch_results"].append(img_data)
                        with grid[i%3]:
                            st.image(img_data, use_container_width=True) # 预览模式
                except: pass
                my_bar.progress((i+1)/batch_count)
                time.sleep(1) # 稍微快一点
                
        # 结果展示与下载
        if st.session_state["batch_results"]:
            st.divider()
            st.markdown("#### 📥 结果下载")
            res_cols = st.columns(4)
            for idx, img_bytes in enumerate(st.session_state["batch_results"]):
                final_bytes, mime = convert_image_format(img_bytes, download_format)
                with res_cols[idx%4]:
                    st.image(img_bytes, caption=f"Var {idx+1}", use_container_width=True)
                    st.download_button(f"下载 ({download_format})", final_bytes, file_name=f"var_{idx}.{download_format.lower()}", mime=mime)

# ==========================================
# TAB 3: 🏞️ 场景置换 (Scene Swap - Logic Fix)
# ==========================================
with tab_background:
    st.markdown("### 🏞️ 场景批量置换")
    st.info("💡 逻辑升级：AI 锁定产品特征，仅重绘背景。")
    
    cb_left, cb_right = st.columns([1, 1.5], gap="large")
    with cb_left:
        # Step 1
        st.markdown("#### Step 1: AI 锁定产品")
        bg_file = st.file_uploader("上传产品图", type=["jpg", "png"], key="bg_upload")
        bg_ana_model = st.selectbox("分析模型", ANALYSIS_MODELS, index=0, key="bg_ana_model")
        
        if st.button("🔒 锁定产品主体特征", key="btn_bg_ana"):
            if not bg_file: st.warning("请先上传图片")
            else:
                with st.spinner("正在锁定主体..."):
                    try:
                        bg_file.seek(0)
                        v_img = Image.open(bg_file)
                        model = genai.GenerativeModel(bg_ana_model)
                        prompt = "Describe the FOREGROUND PRODUCT ONLY in extreme detail. Ignore the background. Focus on color, texture, brand logo, shape."
                        resp = model.generate_content([prompt, v_img])
                        st.session_state["bg_draft_prompt"] = resp.text.strip()
                        st.success("主体锁定成功！")
                    except Exception as e: st.error(f"读取失败: {e}")

        # Step 2
        st.markdown("#### Step 2: 换背景设置")
        product_desc = st.text_area("产品特征 (已锁定)", value=st.session_state.get("bg_draft_prompt", ""), height=100, disabled=True)
        
        bg_desc = st.text_area("新背景描述", height=80, placeholder="例如：放在木质纹理的桌面上，背景是模糊的咖啡厅...")
        bg_count = st.slider("生成数量", 1, 20, 4, key="bg_count")
        bg_model = st.selectbox("生图模型", GOOGLE_IMG_MODELS, index=1, key="bg_gen_model")
        start_bg = st.button("🚀 启动换背景", type="primary")

    with cb_right:
        st.subheader("📦 场景池 (预览)")
        if start_bg and bg_file and product_desc:
            st.session_state["bg_results"] = []
            bg_grid = st.columns(3)
            bg_bar = st.progress(0)
            
            for i in range(bg_count):
                try:
                    bg_file.seek(0)
                    v_img = Image.open(bg_file)
                    # 核心逻辑：Product Description + New Background + Keep Foreground Constraint
                    prompt = f"""
                    Task: Product Photography Background Replacement.
                    Product Description (KEEP EXACTLY SAME): {product_desc}
                    New Background Request: {bg_desc}
                    Constraint: DO NOT CHANGE THE PRODUCT. KEEP ORIGINAL ANGLE AND SHAPE. Only replace background.
                    Variant ID: {i}
                    """
                    img_data = generate_image_call(bg_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["bg_results"].append(img_data)
                        update_history(img_data, source=f"BG Swap {i+1}", prompt_summary=bg_desc)
                        with bg_grid[i%3]:
                            st.image(img_data, use_container_width=True)
                except Exception as e: st.error(f"Error: {e}")
                
                bg_bar.progress((i+1)/bg_count)
                time.sleep(1)
        
        # 结果展示与下载
        if st.session_state["bg_results"]:
            st.divider()
            st.markdown("#### 📥 结果下载")
            bg_res_cols = st.columns(4)
            for idx, img_bytes in enumerate(st.session_state["bg_results"]):
                final_bytes, mime = convert_image_format(img_bytes, download_format)
                with bg_res_cols[idx%4]:
                    st.image(img_bytes, caption=f"Scene {idx+1}", use_container_width=True)
                    st.download_button(f"下载 ({download_format})", final_bytes, file_name=f"scene_{idx}.{download_format.lower()}", mime=mime)
