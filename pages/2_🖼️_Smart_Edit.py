import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time

# --- 0. 基础设置与核心库引入 ---
sys.path.append(os.path.abspath('.'))

# --- 定义备用（Fallback）类和函数 ---
class MockTranslator:
    def to_english(self, t): return t
    def to_chinese(self, t): return t

class MockHistoryManager:
    def add(self, image_bytes, source, prompt_summary): pass
    def render_sidebar(self): pass

def mock_process_image(image_bytes, format="PNG"): return image_bytes, "image/png"
def mock_create_thumbnail(image_bytes, max_width=800): return image_bytes
def mock_analyze(model, img, type, idea, weight, split, trans): return []
def mock_show_modal(b, c): pass

# --- 尝试导入核心工具 ---
try:
    import auth
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False

try:
    from core_utils import (
        AITranslator, process_image_for_download, create_preview_thumbnail, 
        HistoryManager, show_preview_modal, smart_analyze_image
    )
except ImportError:
    AITranslator = MockTranslator
    HistoryManager = MockHistoryManager
    process_image_for_download = mock_process_image
    create_preview_thumbnail = mock_create_thumbnail
    smart_analyze_image = mock_analyze
    show_preview_modal = mock_show_modal

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

if HAS_AUTH and 'auth' in sys.modules and not auth.check_password(): st.stop()

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY")
    st.stop()

# --- 初始化 ---
if "translator" not in st.session_state: st.session_state.translator = AITranslator()
if "history_manager" not in st.session_state: st.session_state.history_manager = HistoryManager()

# --- CSS ---
st.markdown("""
<style>
    .step-header { background: #f0f8ff; padding: 10px; border-left: 5px solid #2196F3; margin: 20px 0; font-weight: bold; }
    .stButton button { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 常量 ---
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "4:3 (常规横向)": ", adjust composition to 4:3 landscape aspect ratio",
    "21:9 (电影感超宽)": ", cinematic 21:9 ultrawide aspect ratio"
}

# --- 状态初始化 ---
for key in ["std_prompt_data", "std_images", "batch_results", "bg_results"]:
    if key not in st.session_state: st.session_state[key] = []
for key in ["var_prompt_en", "var_prompt_zh", "bg_prompt_en", "bg_prompt_zh"]:
    if key not in st.session_state: st.session_state[key] = ""

# --- 核心生图函数 ---
def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
    final_prompt = clean_prompt + ratio_suffix + ", high quality, 8k resolution, photorealistic"
    gen_model = genai.GenerativeModel(model_name)
    try:
        response = gen_model.generate_content([final_prompt, image_input], stream=True)
        for chunk in response:
            if hasattr(chunk, "parts"):
                for part in chunk.parts:
                    if part.inline_data: return part.inline_data.data
    except Exception as e: print(f"Gen Error: {e}")
    return None

# --- 辅助：根据权重生成指令 ---
def get_weight_instruction(weight):
    if weight > 0.7:
        return "Important: Prioritize the text prompt heavily. You may significantly alter the original image structure to fit the description."
    elif weight < 0.3:
        return "Important: Strictly preserve the original image structure, composition, and pose. Only apply subtle changes."
    else:
        return "Important: Balance the original image structure with the new prompt requirements."

# --- 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 工作区")
    download_format = st.radio("📥 下载格式", ["PNG", "JPEG"], horizontal=True)
    st.session_state.history_manager.render_sidebar()

# ==========================================
# 🚀 主界面
# ==========================================
st.title("🧬 Fashion AI Core V5.6")
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# --- TAB 1: 标准工作流 ---
with tab_workflow:
    c_main, c_prev = st.columns([1.5, 1], gap="large")
    with c_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        ana_model = c1.selectbox("1. 读图模型", ANALYSIS_MODELS)
        up_files = c2.file_uploader("2. 上传参考图", type=["jpg","png","webp"], accept_multiple_files=True, key="std_up")
        
        active_file = None
        if up_files:
            active_file = up_files[0] if len(up_files) == 1 else next((f for f in up_files if f.name == st.selectbox("选择图片", [f.name for f in up_files])), up_files[0])

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        user_idea = st.text_area("4. 你的创意", height=80, placeholder="例如：改为极简主义风格...")
        user_weight = st.slider("5. 创意权重", 0.0, 1.0, 0.6)
        enable_split = st.checkbox("🧩 启用智能拆分")

        if st.button("🧠 生成 Prompt", type="primary"):
            if not active_file: st.warning("请上传图片")
            else:
                with st.spinner("AI 正在分析..."):
                    res = smart_analyze_image(
                        ana_model, active_file, task_type, user_idea, user_weight, enable_split, st.session_state.translator
                    )
                    st.session_state["std_prompt_data"] = res
                    st.rerun()

        if st.session_state["std_prompt_data"]:
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            for i, p_data in enumerate(st.session_state["std_prompt_data"]):
                with st.expander(f"任务 {i+1}", expanded=True):
                    cz, ce = st.columns(2)
                    def sync_std(idx=i):
                        nz = st.session_state[f"sz_{idx}"]
                        st.session_state["std_prompt_data"][idx]["zh"] = nz
                        st.session_state["std_prompt_data"][idx]["en"] = st.session_state.translator.to_english(nz)
                        st.toast(f"✅ 任务 {idx+1}：中文已同步翻译为英文")
                    
                    cz.text_area("中文", key=f"sz_{i}", value=p_data["zh"], on_change=sync_std, height=100)
                    ce.text_area("英文", value=p_data["en"], disabled=True, height=100)

            cg1, cg2, cg3 = st.columns(3)
            gen_model = cg1.selectbox("生成模型", GOOGLE_IMG_MODELS)
            ratio = cg2.selectbox("比例", list(RATIO_MAP.keys()))
            num = cg3.number_input("数量", 1, 4, 1)

            if "flash" in gen_model.lower() and "1:1" not in ratio:
                st.info("💡 提示：您选择了 Flash 模型，建议使用 1:1 画幅。")

            if st.button("🎨 开始生成", type="primary"):
                st.session_state["std_images"] = []
                bar = st.progress(0)
                if active_file:
                    total = len(st.session_state["std_prompt_data"]) * num
                    done = 0
                    for t_idx, t_data in enumerate(st.session_state["std_prompt_data"]):
                        for _ in range(num):
                            active_file.seek(0)
                            img = Image.open(active_file)
                            res_img = generate_image_call(gen_model, t_data["en"], img, RATIO_MAP[ratio])
                            if res_img:
                                st.session_state["std_images"].append(res_img)
                                st.session_state.history_manager.add(res_img, f"Task {t_idx+1}", t_data["zh"])
                            done += 1
                            bar.progress(done/total)
                    st.success("完成")

    with c_prev:
        st.subheader("预览")
        if active_file:
            with st.expander("原图", expanded=True):
                active_file.seek(0)
                st.image(Image.open(active_file), use_container_width=True)
        if st.session_state["std_images"]:
            st.divider()
            for idx, bits in enumerate(st.session_state["std_images"]):
                st.image(create_preview_thumbnail(bits, max_width=300), caption=f"R {idx+1}")
                d_btn, z_btn = st.columns([2, 1])
                fb, fm = process_image_for_download(bits, format=download_format)
                d_btn.download_button("下载", fb, file_name=f"s_{idx}.{download_format}", mime=fm, use_container_width=True)
                if z_btn.button("🔍", key=f"zs_{idx}"): show_preview_modal(bits, f"R {idx+1}")

# --- TAB 2: 变体改款 ---
with tab_variants:
    c1, c2 = st.columns([1.5, 1], gap="large")
    
    def sync_var():
        v = st.session_state.var_prompt_zh
        if v: 
            st.session_state.var_prompt_en = st.session_state.translator.to_english(v)
            st.toast("✅ 中文已同步翻译为英文")

    with c1:
        st.markdown("#### Step 1: 读取")
        vf = st.file_uploader("原图", key="vf")
        if st.button("👁️ 读图") and vf:
            with st.spinner("分析中..."):
                vf.seek(0)
                txt = genai.GenerativeModel("models/gemini-flash-latest").generate_content(
                    ["Describe fashion details: Silhouette, Fabric, Color. Output pure English text.", Image.open(vf)]
                ).text.strip()
                st.session_state.var_prompt_en = txt
                st.session_state.var_prompt_zh = st.session_state.translator.to_chinese(txt)
                st.rerun()

        st.markdown("#### Step 2: 改款")
        vc1, vc2 = st.columns(2)
        # 确保左边是中文
        vc1.text_area("中文 (编辑)", key="var_prompt_zh", on_change=sync_var, height=100)
        vc2.text_area("English (Auto)", key="var_prompt_en", disabled=True, height=100)
        
        mode = st.selectbox("模式", ["微调 (Texture)", "中改 (Details)", "大改 (Silhouette)"])
        req = st.text_area("改款指令")
        
        # 新增：权重控制
        var_weight = st.slider("创意权重 (0=保真, 1=听你的)", 0.0, 1.0, 0.5, key="vw")
        
        # 新增：数量上限提高
        cnt = st.slider("数量", 1, 20, 1, key="vc")
        vm = st.selectbox("模型", GOOGLE_IMG_MODELS, key="vm")

        if "flash" in vm.lower(): st.caption("ℹ️ Flash 模型处理速度极快。")
        
        if st.button("🚀 改款") and vf:
            st.session_state.batch_results = []
            vb = st.progress(0)
            weight_prompt = get_weight_instruction(var_weight)
            
            for i in range(cnt):
                vf.seek(0)
                # 将权重指令加入 prompt
                p = f"Restyle. Base: {st.session_state.var_prompt_en}. Mode: {mode}. Request: {req}. {weight_prompt}"
                r = generate_image_call(vm, p, Image.open(vf), "")
                if r:
                    st.session_state.batch_results.append(r)
                    st.session_state.history_manager.add(r, f"Var {i+1}", req)
                vb.progress((i+1)/cnt)
                # 批量生成时稍微缓冲，避免 API 拥塞
                if cnt > 5: time.sleep(1)

    with c2:
        if vf:
            with st.expander("原图"):
                vf.seek(0)
                st.image(Image.open(vf), use_container_width=True)
        if st.session_state.batch_results:
            st.divider()
            for idx, b in enumerate(st.session_state.batch_results):
                st.image(create_preview_thumbnail(b, 300))
                fb, fm = process_image_for_download(b, format=download_format)
                st.download_button(f"下载 {idx+1}", fb, file_name=f"v_{idx}.{download_format}", mime=fm)

# --- TAB 3: 场景置换 ---
with tab_background:
    c1, c2 = st.columns([1.5, 1], gap="large")
    
    def sync_bg():
        v = st.session_state.bg_prompt_zh
        if v: 
            st.session_state.bg_prompt_en = st.session_state.translator.to_english(v)
            st.toast("✅ 中文已同步翻译为英文")

    with c1:
        st.markdown("#### Step 1: 锁定")
        bf = st.file_uploader("产品图", key="bf")
        if st.button("🔒 锁定") and bf:
            with st.spinner("分析..."):
                bf.seek(0)
                txt = genai.GenerativeModel("models/gemini-flash-latest").generate_content(
                    ["Describe FOREGROUND PRODUCT ONLY. Output pure English text.", Image.open(bf)]
                ).text.strip()
                st.session_state.bg_prompt_en = txt
                st.session_state.bg_prompt_zh = st.session_state.translator.to_chinese(txt)
                st.rerun()

        st.markdown("#### Step 2: 换背景")
        bc1, bc2 = st.columns(2)
        bc1.text_area("中文 (编辑)", key="bg_prompt_zh", on_change=sync_bg, height=100)
        bc2.text_area("English (Auto)", key="bg_prompt_en", disabled=True, height=100)
        
        bg_req = st.text_area("新背景")
        
        # 新增：权重控制
        bg_weight = st.slider("创意权重 (0=保真, 1=听你的)", 0.0, 1.0, 0.5, key="bw")
        
        # 新增：数量上限提高
        bcnt = st.slider("数量", 1, 20, 1, key="bc")
        bm = st.selectbox("模型", GOOGLE_IMG_MODELS, index=1, key="bm")

        if "flash" in bm.lower(): st.caption("ℹ️ Flash 模型表现稳定。")
        
        if st.button("🚀 换背景") and bf:
            st.session_state.bg_results = []
            bb = st.progress(0)
            weight_prompt = get_weight_instruction(bg_weight)
            
            for i in range(bcnt):
                bf.seek(0)
                p = f"BG Swap. Product: {st.session_state.bg_prompt_en}. New BG: {bg_req}. {weight_prompt}."
                r = generate_image_call(bm, p, Image.open(bf), "")
                if r:
                    st.session_state.bg_results.append(r)
                    st.session_state.history_manager.add(r, f"BG {i+1}", bg_req)
                bb.progress((i+1)/bcnt)
                if bcnt > 5: time.sleep(1)

    with c2:
        if bf:
            with st.expander("原图"):
                bf.seek(0)
                st.image(Image.open(bf), use_container_width=True)
        if st.session_state.bg_results:
            st.divider()
            for idx, b in enumerate(st.session_state.bg_results):
                st.image(create_preview_thumbnail(b, 300))
                fb, fm = process_image_for_download(b, format=download_format)
                st.download_button(f"下载 {idx+1}", fb, file_name=f"b_{idx}.{download_format}", mime=fm)
