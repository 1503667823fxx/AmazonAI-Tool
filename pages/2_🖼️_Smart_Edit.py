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
    # 引入UI组件
    from app_utils.history_manager import HistoryManager
    from app_utils.ui_components import render_history_sidebar, show_image_modal
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

# --- 2. 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# 初始化 Session State (防止刷新丢失数据)
if "services_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未找到 GOOGLE_API_KEY")
        st.stop()
    st.session_state.llm = LLMEngine(api_key)
    st.session_state.img_gen = ImageGenEngine(api_key)
    st.session_state.history = HistoryManager()
    
    # 数据容器
    st.session_state.std_prompts = []  # 存储生成的 Prompt 列表
    st.session_state.std_results = []  # 存储生成的图片结果
    st.session_state.prompt_ver = 0    # 版本控制，强制刷新 UI
    st.session_state.services_ready = True

llm = st.session_state.llm
img_gen = st.session_state.img_gen
history = st.session_state.history

# --- 3. 常量定义 ---
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (Square)": ", crop to 1:1 aspect ratio",
    "4:3 (Landscape)": ", 4:3 landscape aspect ratio",
    "21:9 (Cinematic)": ", cinematic 21:9 ultrawide"
}

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 工作区")
    # 复用历史记录组件
    render_history_sidebar(history) 

# --- 5. 主逻辑区 (双栏布局) ---
st.title("🧬 Fashion AI Core (Smart Edit)")

# 布局划分：左侧配置(1.2)，右侧预览(1)
c_config, c_view = st.columns([1.2, 1], gap="large")

with c_config:
    st.subheader("🛠️ 需求配置")
    
    # === A. 图片上传 (保留多图逻辑) ===
    uploaded_files = st.file_uploader("上传参考图", type=["jpg","png","webp"], accept_multiple_files=True)
    
    # 核心变量初始化
    active_img_input = None     # 传给 LLM 读图
    active_ref_for_gen = None   # 传给生图做参考
    
    if uploaded_files:
        file_count = len(uploaded_files)
        # 缩略图展示区
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
            active_ref_for_gen = img_list[0] # 单图：作为生图参考
        else:
            st.info(f"🧩 检测到 {file_count} 张图片，启用**多图融合模式** (仅作为灵感参考)。")
            active_img_input = img_list      # 多图：列表传给 LLM
            active_ref_for_gen = None        # 多图：不传具体参考图，全靠 Prompt

    # === B. 创意输入 ===
    col_t1, col_t2 = st.columns(2)
    task_type = col_t1.selectbox("任务类型", ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"])
    selected_style = col_t2.selectbox("🎨 风格预设", list(PRESETS.keys()), index=0)

    user_idea = st.text_area(
        "你的创意 Prompt", 
        height=80, 
        placeholder="简述修改需求即可（例如：换成外国女模特、放在沙滩背景）。",
        help="输入最核心的需求，AI会自动补全画质词。"
    )

    # === C. AI 思考按钮 ===
    if st.button("🧠 AI 思考并生成 Prompt", type="primary"):
        if not uploaded_files: 
            st.toast("⚠️ 请先上传图片", icon="🚨")
        else:
            with st.status("🤖 AI 正在优化提示词...", expanded=True) as status:
                try:
                    # 准备图片指针
                    if isinstance(active_img_input, list):
                        for img in active_img_input: 
                            if hasattr(img, 'seek'): img.seek(0)
                    elif hasattr(active_img_input, 'seek'):
                        active_img_input.seek(0)

                    time.sleep(0.5)
                    
                    # 调用 LLM (移除UI上的权重/拆分，使用默认值)
                    # 默认: weight=0.7, enable_split=False (根据你的减负要求)
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, 0.7, selected_style, active_img_input, False
                    )
                    
                    # 更新 Session State
                    st.session_state.std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.std_prompts.append({"en": p_en, "zh": p_zh})
                    
                    st.session_state.prompt_ver += 1
                    status.update(label="✅ Prompt 优化完毕！", state="complete", expanded=False)
                    st.rerun() # 强制刷新以显示下方的 Prompt 编辑器
                except Exception as e:
                    st.error(f"LLM 调用失败: {e}")

    # === D. Prompt 编辑器 (保留你要求的逻辑) ===
    if st.session_state.std_prompts:
        st.markdown("---")
        st.caption("📝 **任务列表 (Prompt Editor)**")
        
        for i, p_data in enumerate(st.session_state.std_prompts):
            with st.container(border=True):
                st.markdown(f"**Task {i+1}**")
                # 保留原有的 Tab 结构
                tab_zh, tab_en = st.tabs(["🇨🇳 中文编辑", "🇺🇸 English Source"])
                
                with tab_zh:
                    current_key = f"p_zh_{i}_v{st.session_state.prompt_ver}"
                    new_zh = st.text_area("中文指令", p_data["zh"], key=current_key, height=100)
                    
                    # 同步逻辑：中文变动 -> 翻译 -> 更新英文
                    if new_zh != p_data["zh"]: 
                        st.session_state.std_prompts[i]["zh"] = new_zh
                        try:
                            translated_en = llm.translate(new_zh, "English")
                            st.session_state.std_prompts[i]["en"] = translated_en
                            st.rerun()
                        except Exception as e:
                            st.warning("翻译服务暂时不可用，请直接编辑英文")

                with tab_en:
                    # 英文部分通常作为 Source，如果需要也可以开放编辑
                    st.text_area("English Prompt", st.session_state.std_prompts[i]["en"], disabled=True, height=100)

        # === E. 高级参数与执行 (折叠) ===
        with st.expander("⚙️ 生成参数设置", expanded=False):
            r1_c1, r1_c2 = st.columns(2)
            model_name = r1_c1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS)
            ratio_key = r1_c2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
            
            r2_c1, r2_c2 = st.columns(2)
            num_images = r2_c1.slider("🖼️ 生成数量", 1, 4, 1)
            # 对应 _get_safety_settings 参数
            safety_level = r2_c2.selectbox("🛡️ 安全过滤", ["Standard (标准)", "Permissive (宽松)", "Strict (严格)"])
            
            seed_input = st.number_input("🎲 Seed (-1为随机)", value=-1, step=1)
            real_seed = None if seed_input == -1 else int(seed_input)

        # 执行按钮
        if st.button("🚀 开始生成图片", type="primary", use_container_width=True):
            st.session_state.std_results = [] # 清空旧结果
            
            # 准备参考图
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
                            # 调用生成接口
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
                                st.error(f"任务 {idx+1} 生成失败 (可能因安全策略拦截)")
                        
                        except Exception as e:
                            st.error(f"API 异常: {e}")
                        
                        current_op += 1
                        bar.progress(current_op / total_ops)
                
                status.update(label="🎉 全部完成！", state="complete", expanded=False)
                st.toast("图片生成完成！", icon="🖼️")

# --- 右侧：结果预览区 ---
with c_view:
    st.subheader("🖼️ 结果预览")
    if not st.session_state.std_results:
        st.info("👈 在左侧完成配置后，结果将在此显示。")
        # 占位图
        st.markdown(
            '<div style="border: 2px dashed #ddd; height: 300px; display: flex; align-items: center; justify-content: center; color: #888;">Waiting for results...</div>', 
            unsafe_allow_html=True
        )
    else:
        # 结果渲染循环
        for idx, img_bytes in enumerate(st.session_state.std_results):
            with st.container(border=True):
                # 创建缩略图防止卡顿
                thumb = create_preview_thumbnail(img_bytes, 400)
                st.image(thumb, use_container_width=True, caption=f"Result {idx+1}")
                
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    # 弹窗组件
                    if st.button("🔍 放大", key=f"v_zoom_{idx}", use_container_width=True):
                        show_image_modal(img_bytes, f"Result {idx+1}")
                with b_col2:
                    # 下载组件
                    final_bytes, mime = process_image_for_download(img_bytes, format="JPEG")
                    st.download_button(
                        "📥 下载", 
                        data=final_bytes, 
                        file_name=f"res_{idx}.jpg", 
                        mime=mime, 
                        key=f"v_dl_{idx}", 
                        use_container_width=True
                    )
