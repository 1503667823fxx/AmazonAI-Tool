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
    
    # [修改点 1] 引入专属的工具包
    from app_utils.smart_edit.tools import (
        SmartEditHistory, 
        render_history_sidebar, 
        create_preview_thumbnail, 
        process_image_for_download,
        show_image_modal
    )
    
    # [修改点 2] 引入专属的服务包 (包含 PRESETS)
    from services.smart_edit.prompt_service import SmartEditPrompter, PRESETS
    from services.smart_edit.image_service import SmartEditGenerator
    
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="图生图AI工作台", page_icon="🧬", layout="wide")

# --- CSS 注入 ---
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(2) {
        position: sticky;
        top: 60px; 
        height: calc(100vh - 80px); 
        overflow-y: auto; 
        padding-top: 10px;
    }
    .streamlit-expanderHeader {
        background-color: #f0f2f6;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# [修改点 3] 初始化专属 Session State，防止与其他模块冲突
if "se_services_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未找到 GOOGLE_API_KEY")
        st.stop()
    
    # 实例化专属类
    st.session_state.se_prompter = SmartEditPrompter(api_key)
    st.session_state.se_generator = SmartEditGenerator(api_key)
    st.session_state.se_history = SmartEditHistory() # 默认key='smart_edit_history'
    
    st.session_state.se_std_prompts = []  
    st.session_state.se_std_results = []  
    st.session_state.se_prompt_ver = 0    
    st.session_state.se_services_ready = True

# 快捷引用
llm = st.session_state.se_prompter
img_gen = st.session_state.se_generator
history = st.session_state.se_history

# --- 3. 常量定义 ---
GOOGLE_IMG_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3-pro-image-preview", 
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
c_config, c_view = st.columns([1.2, 1], gap="large")

# ================= 左侧：配置区 =================
with c_config:
    st.subheader("🛠️ 需求配置")
    
    # === A. 图片上传 ===
    uploaded_files = st.file_uploader(
        "上传参考图", 
        type=["jpg","png","webp"], 
        accept_multiple_files=True,
        help="支持上传单张或多张图片。"
    )
    
    active_img_input = None     
    active_ref_for_gen = None   
    
    if uploaded_files:
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
    task_type = col_t1.selectbox("任务类型", ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"])
    
    # 直接使用引入的 PRESETS
    selected_style = col_t2.selectbox("🎨 风格预设", list(PRESETS.keys()), index=0)

    user_idea = st.text_area("你的创意 Prompt", height=80, placeholder="例如：换个外国女模特，背景改成巴黎街头，保留衣服细节。")

    # === C. AI 思考按钮 ===
    if st.button("🧠 AI 思考并生成 Prompt", type="primary"):
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
                    
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, 0.7, selected_style, active_img_input, False
                    )
                    
                    st.session_state.se_std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.se_std_prompts.append({"en": p_en, "zh": p_zh})
                    
                    st.session_state.se_prompt_ver += 1
                    status.update(label="✅ Prompt 优化完毕！", state="complete", expanded=False)
                    st.rerun() 
                except Exception as e:
                    st.error(f"LLM 调用失败: {e}")

    # === D. Prompt 编辑器 ===
    if st.session_state.se_std_prompts:
        st.markdown("---")
        st.caption("📝 **指令编辑器 (Prompt Editor)**")
        
        for i, p_data in enumerate(st.session_state.se_std_prompts):
            with st.container(border=True):
                st.markdown(f"**Task {i+1}**")
                tab_zh, tab_en = st.tabs(["🇨🇳 中文编辑 (推荐)", "🇺🇸 英文原文"])
                
                with tab_zh:
                    current_key = f"p_zh_{i}_v{st.session_state.se_prompt_ver}"
                    new_zh = st.text_area("中文指令", p_data["zh"], key=current_key, height=100)
                    
                    if new_zh != p_data["zh"]: 
                        st.session_state.se_std_prompts[i]["zh"] = new_zh
                        try:
                            translated_en = llm.translate(new_zh, "English")
                            st.session_state.se_std_prompts[i]["en"] = translated_en
                            st.rerun()
                        except Exception as e:
                            st.warning("翻译服务暂时不可用")

                with tab_en:
                    st.text_area("English Prompt", st.session_state.se_std_prompts[i]["en"], disabled=True, height=100)

        # === E. 高级参数与执行 ===
        with st.expander("⚙️ 生成参数设置", expanded=False):
            r1_c1, r1_c2 = st.columns(2)
            model_name = r1_c1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS)
            ratio_key = r1_c2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
            
            r2_c1, r2_c2 = st.columns(2)
            num_images = r2_c1.slider("🖼️ 生成数量", 1, 4, 1)
            safety_level = r2_c2.selectbox("🛡️ 安全过滤", ["Standard (标准)", "Permissive (宽松)", "Strict (严格)"])
            
            seed_input = st.number_input("🎲 Seed (-1为随机)", value=-1, step=1)
            real_seed = None if seed_input == -1 else int(seed_input)

        # 执行按钮
        if st.button("🚀 开始生成图片", type="primary", use_container_width=True):
            st.session_state.se_std_results = [] 
            
            ref_img_to_pass = None
            if active_ref_for_gen:
                if hasattr(active_ref_for_gen, 'seek'): active_ref_for_gen.seek(0)
                ref_img_to_pass = active_ref_for_gen

            total_ops = len(st.session_state.se_std_prompts) * num_images
            bar = st.progress(0)
            current_op = 0
            
            with st.status("🎨 正在绘制中...", expanded=True) as status:
                for idx, task in enumerate(st.session_state.se_std_prompts):
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
                                st.session_state.se_std_results.append(res_bytes)
                                history.add(res_bytes, f"Task {idx+1}-{n+1}", task["zh"])
                            else:
                                st.error(f"任务 {idx+1} 生成失败")
                        
                        except Exception as e:
                            st.error(f"API 异常: {e}")
                        
                        current_op += 1
                        bar.progress(current_op / total_ops)
                
                status.update(label="🎉 全部完成！", state="complete", expanded=False)
                st.toast("图片生成完成！", icon="🖼️")

# ================= 右侧：结果预览区 (Sticky) =================
with c_view:
    st.subheader("🖼️ 结果预览")
    
    if not st.session_state.se_std_results:
        st.info("👈 在左侧完成配置后，结果将在此显示。")
        st.markdown(
            '<div style="border: 2px dashed #ddd; height: 300px; display: flex; align-items: center; justify-content: center; color: #888;">Waiting for results...</div>', 
            unsafe_allow_html=True
        )
    else:
        for idx, img_bytes in enumerate(st.session_state.se_std_results):
            with st.container(border=True):
                thumb = create_preview_thumbnail(img_bytes, 800)
                st.image(thumb, use_container_width=True, caption=f"Result {idx+1} (点击图片可放大)")
                
                final_bytes, mime = process_image_for_download(img_bytes, format="JPEG")
                st.download_button(
                    "📥 下载高清原图", 
                    data=final_bytes, 
                    file_name=f"smart_edit_res_{idx}_{int(time.time())}.jpg", 
                    mime=mime, 
                    key=f"se_v_dl_{idx}", 
                    use_container_width=True
                )
