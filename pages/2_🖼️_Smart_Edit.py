import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
from collections import deque 

# --- 0. 基础设置与门禁系统 (修复版) ---
# 1. 确保能找到根目录下的 auth.py
sys.path.append(os.path.abspath('.'))

# 2. 尝试引入 auth，如果还没有 auth.py 就跳过 (防止本地调试报错)
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# 3. 执行安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()  # 验证失败则停止往下运行


# --- 2. 样式优化 ---
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
    /* 优化文本框显示 */
    .stTextArea textarea {
        font-size: 16px;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# 模型列表
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]

# 比例控制
RATIO_PROMPTS = {
    "Original (原图比例)": "",
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "3:4 (社交媒体纵向)": ", adjust composition to 3:4 portrait aspect ratio",
    "16:9 (电影感横屏)": ", cinematic 16:9 wide aspect ratio"
}

# --- 3. 状态管理 ---
if "history_queue" not in st.session_state:
    st.session_state["history_queue"] = deque(maxlen=10) # 历史记录增加到10条
if "draft_prompt" not in st.session_state:
    st.session_state["draft_prompt"] = ""
if "last_generated_images" not in st.session_state:
    st.session_state["last_generated_images"] = [] # 存储最新一次生成的一组图

# --- 4. 辅助函数 ---
def update_history(image_data, source="AI", prompt_summary=""):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state["history_queue"].appendleft({
        "image": image_data,
        "source": source,
        "time": timestamp,
        "desc": prompt_summary[:30] + "..."
    })

def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    """封装单次 API 调用逻辑"""
    final_prompt = prompt + ratio_suffix
    gen_model = genai.GenerativeModel(model_name)
    response = gen_model.generate_content([final_prompt, image_input], stream=True)
    
    for chunk in response:
        if hasattr(chunk, "parts"):
            for part in chunk.parts:
                if part.inline_data:
                    return part.inline_data.data
    return None

# ==========================================
# 🚀 侧边栏：历史记录 (已优化折叠)
# ==========================================
with st.sidebar:
    st.title("🗂️ 工作区")
    
    # 【改动 1】可收起/展开的历史记录
    with st.expander("🕒 历史记录 (History)", expanded=False):
        if len(st.session_state["history_queue"]) == 0:
            st.caption("暂无生成记录")
        else:
            for item in st.session_state["history_queue"]:
                st.markdown(f"**{item['source']}**")
                st.caption(f"Time: {item['time']}")
                st.image(item['image'], use_column_width=True)
                st.divider()

# ==========================================
# 🚀 主界面：多标签页架构
# ==========================================
st.title("🧬 Fashion AI Core")

# 【架构升级】分为两个主要功能区
tab_workflow, tab_variants = st.tabs(["✨ 标准精修工作流", "⚡ 变体批量工厂"])

# ==========================================
# TAB 1: 标准工作流 (原功能增强版)
# ==========================================
with tab_workflow:
    col_main, col_preview = st.columns([1.3, 1], gap="large")

    with col_main:
        # --- Step 1: 构思 ---
        st.markdown('<div class="step-header">Step 1: 需求分析与素材设定</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            analysis_model = st.selectbox("1. 读图模型", ANALYSIS_MODELS, index=0)
        with c2:
            uploaded_file = st.file_uploader("2. 上传参考图", type=["jpg", "png", "webp"], key="std_upload")

        # 【改动 2】预留的素材风格功能区
        with st.expander("🎨 场景/画质/光影素材库 (预留功能区)", expanded=True):
            st.caption("🚧 此区域未来将提供可视化点击选择，当前仅作 UI 占位")
            m1, m2, m3 = st.columns(3)
            with m1: st.selectbox("🎥 镜头语言", ["默认", "85mm 人像", "35mm 广角", "微距特写"], disabled=True)
            with m2: st.selectbox("💡 影棚光效", ["默认", "伦勃朗光", "柔光箱", "自然窗光"], disabled=True)
            with m3: st.selectbox("✨ 艺术画风", ["写实摄影", "胶片颗粒", "极简棚拍", "赛博朋克"], disabled=True)

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        
        # 【改动 4】加大的文本框
        user_idea = st.text_area(
            "4. 你的创意想法 (支持详细描述)", 
            height=120, 
            placeholder="例如：背景改为北欧风格的客厅，阳光从左侧窗户射入，画面色调偏暖..."
        )

        if st.button("🧠 生成 Prompt 方案", type="primary"):
            if not uploaded_file:
                st.warning("⚠️ 请先上传图片")
            else:
                with st.spinner("AI 正在解析图片与创意..."):
                    try:
                        uploaded_file.seek(0)
                        img_obj = Image.open(uploaded_file)
                        model = genai.GenerativeModel(analysis_model)
                        
                        prompt_req = f"""
                        Role: Art Director.
                        Task: Create a prompt based on Image + User Idea: "{user_idea}"
                        Type: {task_type}
                        Requirement: Commercial Photography, 8k.
                        Output: English Prompt Only.
                        """
                        response = model.generate_content([prompt_req, img_obj])
                        st.session_state["draft_prompt"] = response.text.strip()
                        st.success("✅ 方案已生成")
                        st.rerun()
                    except Exception as e:
                        st.error(f"分析失败: {e}")

        # --- Step 2: 生成 ---
        if st.session_state.get("draft_prompt"):
            st.markdown('<div class="step-header">Step 2: 执行生成</div>', unsafe_allow_html=True)
            
            edited_prompt = st.text_area("5. 确认/编辑 Prompt", value=st.session_state["draft_prompt"], height=150)
            st.session_state["draft_prompt"] = edited_prompt

            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1: google_model = st.selectbox("6. 生图模型", GOOGLE_IMG_MODELS)
            with col_g2: selected_ratio = st.selectbox("7. 比例", list(RATIO_PROMPTS.keys()))
            # 【改动 3】图片数量选择
            with col_g3: num_images = st.number_input("8. 生成数量", min_value=1, max_value=4, value=1)

            if st.button("🎨 立即生成 (Standard Run)", type="primary"):
                if not uploaded_file: st.error("图片丢失，请重新上传")
                else:
                    st.session_state["last_generated_images"] = [] # 清空上次结果
                    progress_bar = st.progress(0)
                    
                    for i in range(num_images):
                        with st.spinner(f"正在生成第 {i+1}/{num_images} 张..."):
                            try:
                                uploaded_file.seek(0)
                                img_pil = Image.open(uploaded_file)
                                
                                img_data = generate_image_call(
                                    google_model, 
                                    edited_prompt, 
                                    img_pil, 
                                    RATIO_PROMPTS[selected_ratio]
                                )
                                
                                if img_data:
                                    st.session_state["last_generated_images"].append(img_data)
                                    update_history(img_data, source=f"Std-Gen {i+1}", prompt_summary=edited_prompt)
                            except Exception as e:
                                st.error(f"第 {i+1} 张生成失败: {e}")
                            
                            # 更新进度条
                            progress_bar.progress((i + 1) / num_images)
                            time.sleep(1) # 避免触发速率限制

                    if st.session_state["last_generated_images"]:
                        st.success(f"🎉 全部完成！共生成 {len(st.session_state['last_generated_images'])} 张")

    # --- 右侧预览 (Tab 1) ---
    with col_preview:
        st.subheader("🖼️ 结果预览")
        if st.session_state["last_generated_images"]:
            for idx, img_bytes in enumerate(st.session_state["last_generated_images"]):
                st.image(img_bytes, caption=f"Result {idx+1}", use_column_width=True)
                st.download_button(f"📥 下载 Result {idx+1}", img_bytes, file_name=f"std_res_{idx}.png")
        elif uploaded_file:
             st.image(uploaded_file, caption="原图参考", width=200)

# ==========================================
# TAB 2: ⚡ 变体批量工厂 (全新功能)
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 变体批量制作 (Variant Factory)")
    st.info("💡 此模式用于大批量生成同一产品的不同变体。系统将循环执行指令，适合寻找灵感。")
    
    col_v_left, col_v_right = st.columns([1, 2], gap="large")
    
    with col_v_left:
        var_file = st.file_uploader("1. 上传产品图 (变体源)", type=["jpg", "png", "webp"], key="var_upload")
        if var_file:
            st.image(var_file, caption="变体源图", width=200)
            
        var_prompt = st.text_area(
            "2. 变体指令 (Prompt)", 
            height=150,
            value="Creative variation of the product, change background to different luxury settings, cinematic lighting, 8k resolution.",
            help="描述你希望看到的批量变化方向"
        )
        
        # 【改动 5】批量生成数量设置
        batch_count = st.slider("3. 批量数量 (Batch Size)", 1, 20, 4, help="一次性生成的图片数量，注意数量越多耗时越久")
        
        var_model = st.selectbox("4. 选用模型", GOOGLE_IMG_MODELS, key="var_model")
        
        start_batch = st.button("🚀 启动批量引擎 (Batch Run)", type="primary")

    with col_v_right:
        st.subheader("📦 批量产出池")
        
        # 批量生成的容器
        if "batch_results" not in st.session_state:
            st.session_state["batch_results"] = []
            
        if start_batch and var_file:
            st.session_state["batch_results"] = [] # 清空旧的
            
            my_bar = st.progress(0)
            status_text = st.empty()
            
            # 动态网格布局
            grid_cols = st.columns(3) # 3列显示
            
            for i in range(batch_count):
                status_text.text(f"正在生产变体 {i+1} / {batch_count} ...")
                try:
                    var_file.seek(0)
                    v_img = Image.open(var_file)
                    
                    # 可以在每次循环微调 Prompt seed (Gemini 不支持显式 seed，但循环调用本身会有随机性)
                    # 加上时间戳微调 Prompt 防止缓存
                    loop_prompt = var_prompt + f" (variation id {int(time.time()*1000)})"
                    
                    img_data = generate_image_call(var_model, loop_prompt, v_img, "")
                    
                    if img_data:
                        st.session_state["batch_results"].append(img_data)
                        update_history(img_data, source=f"Batch Var {i+1}", prompt_summary="Variant Batch")
                        
                        # 实时显示在网格中
                        col_idx = i % 3
                        with grid_cols[col_idx]:
                            st.image(img_data, use_column_width=True)
                    
                except Exception as e:
                    st.error(f"变体 {i+1} 失败: {e}")
                
                my_bar.progress((i + 1) / batch_count)
                time.sleep(1.5) # 稍微增加间隔，防止 Google 判定并发攻击
            
            status_text.success(f"✅ 批量任务完成！产出 {len(st.session_state['batch_results'])} 张。")
            
        # 如果有缓存结果，显示出来 (防止刷新消失)
        elif st.session_state["batch_results"]:
            grid_cols = st.columns(3)
            for idx, img_bytes in enumerate(st.session_state["batch_results"]):
                col_idx = idx % 3
                with grid_cols[col_idx]:
                    st.image(img_bytes, caption=f"Var {idx+1}", use_column_width=True)
                    st.download_button("📥", img_bytes, file_name=f"var_{idx}.png", key=f"dl_var_{idx}")
