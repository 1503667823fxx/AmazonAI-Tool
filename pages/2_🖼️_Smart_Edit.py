import streamlit as st
from PIL import Image
import sys
import os
import time

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    # 引入UI组件 (移除了 show_image_modal)
    from app_utils.history_manager import HistoryManager
    from app_utils.ui_components import render_history_sidebar
    from app_utils.image_processing import create_preview_thumbnail, process_image_for_download
    
    # 引入服务引擎
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
    from services.styles import PRESETS
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# --- CSS 注入：实现右侧栏悬浮跟随 ---
st.markdown("""
    <style>
    /* 针对宽屏模式下的第二列 (结果预览区) 设置 Sticky */
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(2) {
        position: sticky;
        top: 60px; /* 距离顶部的距离 */
        height: calc(100vh - 80px); /* 视口高度减去头部 */
        overflow-y: auto; /* 允许内部滚动 */
        padding-top: 10px;
    }
    /* 优化 Expander 的样式 */
    .streamlit-expanderHeader {
        background-color: #f0f2f6;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# 初始化 Session State
if "services_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未找到 GOOGLE_API_KEY")
        st.stop()
    st.session_state.llm = LLMEngine(api_key)
    st.session_state.img_gen = ImageGenEngine(api_key)
    st.session_state.history = HistoryManager()
    
    st.session_state.std_prompts = []  
    st.session_state.std_results = []  
    st.session_state.prompt_ver = 0    
    st.session_state.services_ready = True

llm = st.session_state.llm
img_gen = st.session_state.img_gen
history = st.session_state.history

# --- 3. 常量定义 (已更新为您指定的模型) ---
GOOGLE_IMG_MODELS = [
    "models/gemini-3-pro-image-preview", 
    "models/gemini-3-pro-preview",
    "models/gemini-flash-latest",
    "models/gemini-flash-lite-latest"
]
RATIO_MAP = {
    "1:1 (Square)": ", crop to 1:1 aspect ratio",
    "4:3 (Landscape)": ", 4:3 landscape aspect ratio",
    "21:9 (Cinematic)": ", cinematic 21:9 ultrawide"
}

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 工作区")
    st.info("💡 **提示**：生成的图片会自动保存在这里，刷新页面也不会丢失。")
    render_history_sidebar(history) 

# --- 5. 主逻辑区 (双栏布局) ---
st.title("🧬 Fashion AI Core (Smart Edit)")

# 布局划分：左侧配置(1.2)，右侧预览(1)
c_config, c_view = st.columns([1.2, 1], gap="large")

# ================= 左侧：配置区 =================
with c_config:
    st.subheader("🛠️ 需求配置")
    
    # === A. 图片上传 (可折叠) ===
    uploaded_files = st.file_uploader(
        "上传参考图", 
        type=["jpg","png","webp"], 
        accept_multiple_files=True,
        help="支持上传单张或多张图片。\n- 单图：作为生图的直接参考（权重高）。\n- 多图：作为灵感参考，AI会分析多张图的共同特征。"
    )
    
    active_img_input = None     
    active_ref_for_gen = None   
    
    if uploaded_files:
        # 使用 Expander 包裹预览，节省空间
        with st.expander(f"📸 原图预览 ({len(uploaded_files)} 张) - 点击收起", expanded=True):
            file_count = len(uploaded_files)
            cols = st.columns(min(file_count, 4))
            img_list = []
            
            for idx, f in enumerate(uploaded_files):
                img = Image.open(f)
                img_list.append(img)
                if idx < 4:
                    with cols[idx]:
                        st.image(img, use_container_width=True)
            
            if file_count == 1:
                active_img_input = img_list[0]
                active_ref_for_gen = img_list[0]
            else:
                st.info(f"🧩 已启用多图融合模式。")
                active_img_input = img_list      
                active_ref_for_gen = None 

    # === B. 创意输入 ===
    st.markdown("#### 💡 创意指令")
    col_t1, col_t2 = st.columns(2)
    task_type = col_t1.selectbox(
        "任务类型", 
        ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"],
        help="选择生成的目的，会影响 AI 对背景和光影的默认处理方式。"
    )
    selected_style = col_t2.selectbox(
        "🎨 风格预设", 
        list(PRESETS.keys()), 
        index=0,
        help="选择一种视觉风格，这会覆盖在您的 Prompt 之上。"
    )

    user_idea = st.text_area(
        "你的创意 Prompt", 
        height=80, 
        placeholder="例如：换个外国女模特，背景改成巴黎街头，保留衣服细节。",
        help="👉 **重要**：如果您想换模特，请明确输入“换个模特”、“换成外国人”等指令，AI 会自动处理。"
    )

    # === C. AI 思考按钮 ===
    if st.button("🧠 AI 思考并生成 Prompt", type="primary", help="点击后，AI 会结合原图和您的文字，生成专业的英文绘画指令。"):
        if not uploaded_files: 
            st.toast("⚠️ 请先上传图片", icon="🚨")
        else:
            with st.status("🤖 AI 正在拆解需求...", expanded=True) as status:
                try:
                    if isinstance(active_img_input, list):
                        for img in active_img_input: 
                            if hasattr(img, 'seek'): img.seek(0)
                    elif hasattr(active_img_input, 'seek'):
                        active_img_input.seek(0)

                    time.sleep(0.5)
                    
                    # 这里的 prompt 优化逻辑已经包含了您要求的“换人”增强
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, 0.7, selected_style, active_img_input, False
                    )
                    
                    st.session_state.std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.std_prompts.append({"en": p_en, "zh": p_zh})
                    
                    st.session_state.prompt_ver += 1
                    status.update(label="✅ Prompt 优化完毕！", state="complete", expanded=False)
                    st.rerun() 
                except Exception as e:
                    st.error(f"LLM 调用失败: {e}")

    # === D. Prompt 编辑器 ===
    if st.session_state.std_prompts:
        st.markdown("---")
        # 将编辑器也放入 Expander (可选，这里我默认展开，但标题清晰)
        st.caption("📝 **指令编辑器 (Prompt Editor)**")
        
        for i, p_data in enumerate(st.session_state.std_prompts):
            with st.container(border=True):
                st.markdown(f"**Task {i+1}**")
                tab_zh, tab_en = st.tabs(["🇨🇳 中文编辑 (推荐)", "🇺🇸 英文原文"])
                
                with tab_zh:
                    current_key = f"p_zh_{i}_v{st.session_state.prompt_ver}"
                    new_zh = st.text_area(
                        "中文指令", 
                        p_data["zh"], 
                        key=current_key, 
                        height=100,
                        help="您可以修改这里的中文，系统会自动翻译回英文供生图使用。"
                    )
                    
                    if new_zh != p_data["zh"]: 
                        st.session_state.std_prompts[i]["zh"] = new_zh
                        try:
                            translated_en = llm.translate(new_zh, "English")
                            st.session_state.std_prompts[i]["en"] = translated_en
                            st.rerun()
                        except Exception as e:
                            st.warning("翻译服务暂时不可用")

                with tab_en:
                    st.text_area("English Prompt", st.session_state.std_prompts[i]["en"], disabled=True, height=100)

        # === E. 高级参数与执行 ===
        with st.expander("⚙️ 生成参数设置", expanded=False):
            r1_c1, r1_c2 = st.columns(2)
            model_name = r1_c1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS, help="Gemini 3 Pro Image Preview 是目前效果最好的选择。")
            ratio_key = r1_c2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
            
            r2_c1, r2_c2 = st.columns(2)
            num_images = r2_c1.slider("🖼️ 生成数量", 1, 4, 1, help="一次生成的图片数量，数量越多等待时间越长。")
            safety_level = r2_c2.selectbox(
                "🛡️ 安全过滤", 
                ["Standard (标准)", "Permissive (宽松)", "Strict (严格)"],
                help="如果生成内衣或泳装模特失败，请尝试切换到 'Permissive'。"
            )
            
            seed_input = st.number_input("🎲 Seed (-1为随机)", value=-1, step=1, help="固定种子可以复现之前的生成结果。")
            real_seed = None if seed_input == -1 else int(seed_input)

        # 执行按钮
        if st.button("🚀 开始生成图片", type="primary", use_container_width=True):
            st.session_state.std_results = [] 
            
            ref_img_to_pass = None
            if active_ref_for_gen:
                if hasattr(active_ref_for_gen, 'seek'): active_ref_for_gen.seek(0)
                ref_img_to_pass = active_ref_for_gen

            total_ops = len(st.session_state.std_prompts) * num_images
            bar = st.progress(0)
            current_op = 0
            
            with st.status("🎨 正在绘制中...", expanded=True) as status:
                for idx, task in enumerate(st.session_state.std_prompts):
                    for n in range(num_images):
                        st.write(f"任务 {idx+1}: 正在生成第 {n+1}/{num_images} 张...")
                        try:
                            res_bytes = img_gen.generate(
                                task["en"], 
                                model_name, 
                                ref_img_to_pass, 
                                RATIO_MAP[ratio_key], 
                                seed=real_seed, 
                                creativity=0.5, 
                                safety_level=safety_level.split()[0]
                            )
                            
                            if res_bytes:
                                st.session_state.std_results.append(res_bytes)
                                history.add(res_bytes, f"Task {idx+1}-{n+1}", task["zh"])
                            else:
                                st.error(f"任务 {idx+1} 生成失败 (可能因安全策略拦截，请尝试调节安全等级)")
                        
                        except Exception as e:
                            st.error(f"API 异常: {e}")
                        
                        current_op += 1
                        bar.progress(current_op / total_ops)
                
                status.update(label="🎉 全部完成！", state="complete", expanded=False)
                st.toast("图片生成完成！", icon="🖼️")

# ================= 右侧：结果预览区 (Sticky) =================
with c_view:
    st.subheader("🖼️ 结果预览")
    
    if not st.session_state.std_results:
        st.info("👈 在左侧完成配置后，结果将在此显示。")
        st.markdown(
            '<div style="border: 2px dashed #ddd; height: 300px; display: flex; align-items: center; justify-content: center; color: #888;">Waiting for results...</div>', 
            unsafe_allow_html=True
        )
    else:
        # 结果渲染循环
        for idx, img_bytes in enumerate(st.session_state.std_results):
            with st.container(border=True):
                # 1. 创建缩略图
                thumb = create_preview_thumbnail(img_bytes, 800) # 提高一点清晰度
                
                # 2. 直接展示 (Streamlit 原生支持点击全屏查看)
                st.image(thumb, use_container_width=True, caption=f"Result {idx+1} (点击图片可放大)")
                
                # 3. 下载按钮
                final_bytes, mime = process_image_for_download(img_bytes, format="JPEG")
                st.download_button(
                    "📥 下载高清原图", 
                    data=final_bytes, 
                    file_name=f"smart_edit_res_{idx}_{int(time.time())}.jpg", 
                    mime=mime, 
                    key=f"v_dl_{idx}", 
                    use_container_width=True,
                    help="以高质量 JPEG 格式下载此图片"
                )
