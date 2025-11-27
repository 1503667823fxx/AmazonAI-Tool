import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))

# --- Mock Fallback ---
class Mock:
    def to_english(self, t): return t
    def to_chinese(self, t): return t
    def add(self, a, b, c): pass
    def render_sidebar(self): pass
def mock_bi(m, i, t): return "Mock English", "Mock Chinese"
def mock_an(m, i, t, ui, uw, es, tr): return []
def mock_img(b, f="PNG"): return b, "image/png"
def mock_th(b, w=800): return b
def mock_mo(b, c): pass

try:
    import auth
    HAS_AUTH = True
except ImportError: HAS_AUTH = False

try:
    from core_utils import (
        AITranslator, process_image_for_download, create_preview_thumbnail, 
        HistoryManager, show_preview_modal, smart_analyze_image, analyze_image_bilingual
    )
except ImportError:
    AITranslator = Mock; HistoryManager = Mock
    process_image_for_download = mock_img; create_preview_thumbnail = mock_th
    smart_analyze_image = mock_an; analyze_image_bilingual = mock_bi
    show_preview_modal = mock_mo

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

if HAS_AUTH and 'auth' in sys.modules and not auth.check_password(): st.stop()

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY"); st.stop()

# --- Init ---
if "translator" not in st.session_state: st.session_state.translator = AITranslator()
if "history_manager" not in st.session_state: st.session_state.history_manager = HistoryManager()

st.markdown("""
<style>
    .step-header { background: #f0f8ff; padding: 10px; border-left: 5px solid #2196F3; margin: 20px 0; font-weight: bold; }
    .stButton button { font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 38px; white-space: pre-wrap; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- Constants ---
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (正方形)": ", crop 1:1 square ratio",
    "4:3 (横向)": ", 4:3 landscape ratio",
    "21:9 (宽屏)": ", 21:9 ultrawide ratio"
}

# --- State ---
for key in ["std_prompt_data", "std_images", "batch_results", "bg_results"]:
    if key not in st.session_state: st.session_state[key] = []
for key in ["var_prompt_en", "var_prompt_zh", "bg_prompt_en", "bg_prompt_zh"]:
    if key not in st.session_state: st.session_state[key] = ""

def generate_image_call(model, prompt, img, ratio):
    full_prompt = prompt.replace("1:1", "").replace("4:3", "") + ratio + ", 8k photorealistic, commercial lighting"
    try:
        resp = genai.GenerativeModel(model).generate_content([full_prompt, img], stream=True)
        for chunk in resp:
            if chunk.parts: 
                for p in chunk.parts: 
                    if p.inline_data: return p.inline_data.data
    except Exception as e: print(e)
    return None

def get_weight_instruction(w):
    if w > 0.7: return "Ignore original structure, follow prompt completely."
    if w < 0.3: return "Strictly preserve original structure and pose."
    return "Balance original structure with new prompt."

# --- Sidebar ---
with st.sidebar:
    st.title("🗂️ 工作区")
    dl_fmt = st.radio("📥 格式", ["PNG", "JPEG"], horizontal=True)
    st.session_state.history_manager.render_sidebar()

st.title("🧬 Fashion AI Core V5.6")
t1, t2, t3 = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# --- TAB 1 ---
with t1:
    c_main, c_prev = st.columns([1.5, 1], gap="large")
    with c_main:
        st.markdown('<div class="step-header">Step 1: 分析</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        am = c1.selectbox("1. 读图模型", ANALYSIS_MODELS)
        ufs = c2.file_uploader("2. 上传参考图", type=["jpg","png","webp"], accept_multiple_files=True, key="u1")
        af = ufs[0] if ufs else None
        if ufs and len(ufs)>1: af = next((f for f in ufs if f.name == st.selectbox("选图", [f.name for f in ufs])), ufs[0])

        tt = st.selectbox("3. 类型", ["场景图", "展示图", "产品图"])
        idea = st.text_area("4. 创意", height=80)
        wt = st.slider("5. 权重", 0.0, 1.0, 0.6)
        esp = st.checkbox("🧩 拆分任务")

        if st.button("🧠 生成指令", type="primary"):
            if not af: st.warning("请上传")
            else:
                with st.spinner("分析中..."):
                    res = smart_analyze_image(am, af, tt, idea, wt, esp, st.session_state.translator)
                    st.session_state["std_prompt_data"] = res
                    st.rerun()

        if st.session_state["std_prompt_data"]:
            st.markdown('<div class="step-header">Step 2: 执行</div>', unsafe_allow_html=True)
            for i, d in enumerate(st.session_state["std_prompt_data"]):
                with st.expander(f"任务 {i+1}", expanded=True):
                    tz, te = st.tabs(["🇨🇳 中文", "🇺🇸 英文"])
                    def sync1(idx=i):
                        nz = st.session_state[f"z_{idx}"]
                        st.session_state["std_prompt_data"][idx]["zh"] = nz
                        st.session_state["std_prompt_data"][idx]["en"] = st.session_state.translator.to_english(nz)
                    with tz: st.text_area("中文", key=f"z_{i}", value=d["zh"], on_change=sync1, height=100)
                    with te: st.text_area("英文", value=d["en"], disabled=True, height=100)

            cc1, cc2, cc3 = st.columns(3)
            gm = cc1.selectbox("生成模型", GOOGLE_IMG_MODELS)
            rt = cc2.selectbox("比例", list(RATIO_MAP.keys()))
            nm = cc3.number_input("数量", 1, 4, 1)
            
            if "flash" in gm.lower() and "1:1" not in rt: st.info("Flash 模型建议使用 1:1")

            if st.button("🎨 生成"):
                st.session_state["std_images"] = []
                bar = st.progress(0)
                tot = len(st.session_state["std_prompt_data"]) * nm
                cur = 0
                for task in st.session_state["std_prompt_data"]:
                    for _ in range(nm):
                        af.seek(0); im = Image.open(af)
                        r = generate_image_call(gm, task["en"], im, RATIO_MAP[rt])
                        if r: 
                            st.session_state["std_images"].append(r)
                            st.session_state.history_manager.add(r, "Standard", task["zh"])
                        cur+=1; bar.progress(cur/tot)
    
    with c_prev:
        if af: 
            with st.expander("原图", True): af.seek(0); st.image(Image.open(af), use_container_width=True)
        if st.session_state["std_images"]:
            st.divider()
            for idx, b in enumerate(st.session_state["std_images"]):
                st.image(create_preview_thumbnail(b, 300), caption=f"R {idx+1}")
                fb, m = process_image_for_download(b, dl_fmt)
                st.download_button("下载", fb, f"s_{idx}.{dl_fmt}", m)

# --- TAB 2 ---
with t2:
    c1, c2 = st.columns([1.5, 1], gap="large")
    def sync_var():
        v = st.session_state.var_prompt_zh
        if v: st.session_state.var_prompt_en = st.session_state.translator.to_english(v)

    with c1:
        st.markdown("#### Step 1: 读取")
        vf = st.file_uploader("原图", key="vfu")
        vam = st.selectbox("分析模型", ANALYSIS_MODELS, key="vam")
        
        if st.button("👁️ 双语读图", key="vbtn"):
            if vf:
                with st.spinner("AI 正在同时生成中英文描述..."):
                    en, zh = analyze_image_bilingual(vam, vf, "fashion")
                    st.session_state.var_prompt_en = en
                    st.session_state.var_prompt_zh = zh
                    st.success("读取成功！")
                    st.rerun()

        st.markdown("#### Step 2: 改款")
        tz, te = st.tabs(["🇨🇳 中文版 (默认)", "🇺🇸 英文版"])
        with tz:
            st.text_area("特征 (中文 - 修改此处会同步英文)", key="var_prompt_zh", on_change=sync_var, height=120)
        with te:
            st.text_area("Feature (English - AI uses this)", key="var_prompt_en", disabled=True, height=120)

        md = st.selectbox("模式", ["微调 (Texture)", "中改 (Details)", "大改 (Silhouette)"])
        req = st.text_area("改款指令")
        
        # 新增：权重与数量
        vw = st.slider("创意权重 (0=保真, 1=听你的)", 0.0, 1.0, 0.5, key="vw")
        vc = st.slider("数量", 1, 20, 1, key="vc")
        vm = st.selectbox("生成模型", GOOGLE_IMG_MODELS, key="vgm")
        if "flash" in vm.lower(): st.caption("ℹ️ Flash 模型建议 1:1 画幅")

        if st.button("🚀 改款"):
            st.session_state.batch_results = []
            bar = st.progress(0)
            wp = get_weight_instruction(vw)
            for i in range(vc):
                vf.seek(0)
                p = f"Restyle. Base: {st.session_state.var_prompt_en}. Mode: {md}. Request: {req}. {wp}"
                r = generate_image_call(vm, p, Image.open(vf), "")
                if r: 
                    st.session_state.batch_results.append(r)
                    st.session_state.history_manager.add(r, "Restyle", req)
                bar.progress((i+1)/vc)
                if vc>5: time.sleep(1)

    with c2:
        if vf: 
            with st.expander("原图", True): vf.seek(0); st.image(Image.open(vf), use_container_width=True)
        if st.session_state.batch_results:
            st.divider()
            for idx, b in enumerate(st.session_state.batch_results):
                st.image(create_preview_thumbnail(b, 300))
                fb, m = process_image_for_download(b, dl_fmt)
                st.download_button("下载", fb, f"v_{idx}.{dl_fmt}", m)

# --- TAB 3 ---
with t3:
    c1, c2 = st.columns([1.5, 1], gap="large")
    def sync_bg():
        v = st.session_state.bg_prompt_zh
        if v: st.session_state.bg_prompt_en = st.session_state.translator.to_english(v)

    with c1:
        st.markdown("#### Step 1: 锁定")
        bf = st.file_uploader("产品图", key="bfu")
        bam = st.selectbox("分析模型", ANALYSIS_MODELS, key="bam")
        
        if st.button("🔒 双语锁定", key="bbtn"):
            if bf:
                with st.spinner("AI 正在分析..."):
                    en, zh = analyze_image_bilingual(bam, bf, "product")
                    st.session_state.bg_prompt_en = en
                    st.session_state.bg_prompt_zh = zh
                    st.success("锁定成功！")
                    st.rerun()

        st.markdown("#### Step 2: 换背景")
        tz, te = st.tabs(["🇨🇳 中文版 (默认)", "🇺🇸 英文版"])
        with tz:
            st.text_area("特征 (中文 - 修改此处会同步英文)", key="bg_prompt_zh", on_change=sync_bg, height=120)
        with te:
            st.text_area("Features (English)", key="bg_prompt_en", disabled=True, height=120)
            
        breq = st.text_area("新背景")
        
        # 新增：权重与数量
        bw = st.slider("权重", 0.0, 1.0, 0.5, key="bw")
        bc = st.slider("数量", 1, 20, 1, key="bc")
        bm = st.selectbox("生成模型", GOOGLE_IMG_MODELS, index=1, key="bgm")
        if "flash" in bm.lower(): st.caption("ℹ️ Flash 模型建议 1:1 画幅")

        if st.button("🚀 换背景"):
            st.session_state.bg_results = []
            bar = st.progress(0)
            wp = get_weight_instruction(bw)
            for i in range(bc):
                bf.seek(0)
                p = f"BG Swap. Product: {st.session_state.bg_prompt_en}. New BG: {breq}. {wp}"
                r = generate_image_call(bm, p, Image.open(bf), "")
                if r: 
                    st.session_state.bg_results.append(r)
                    st.session_state.history_manager.add(r, "Scene", breq)
                bar.progress((i+1)/bc)
                if bc>5: time.sleep(1)

    with c2:
        if bf: 
            with st.expander("原图", True): bf.seek(0); st.image(Image.open(bf), use_container_width=True)
        if st.session_state.bg_results:
            st.divider()
            for idx, b in enumerate(st.session_state.bg_results):
                st.image(create_preview_thumbnail(b, 300))
                fb, m = process_image_for_download(b, dl_fmt)
                st.download_button("下载", fb, f"b_{idx}.{dl_fmt}", m)
