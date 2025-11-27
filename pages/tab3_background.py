import streamlit as st
from PIL import Image
import time
from core_utils import analyze_image_bilingual, get_weight_instruction, generate_image_call, create_preview_thumbnail, process_image_for_download, show_preview_modal

def render_tab3(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, download_format):
    c1, c2 = st.columns([1.5, 1], gap="large")
    
    def sync_bg():
        v = st.session_state.bg_prompt_zh
        if v: 
            trans = st.session_state.translator.to_english(v)
            st.session_state.bg_prompt_en = trans
            st.toast("✅ 英文底稿已更新")

    with c1:
        st.markdown("#### Step 1: 锁定")
        bf = st.file_uploader("产品图", key="t3_up")
        bam = st.selectbox("分析模型", ANALYSIS_MODELS, key="t3_am")
        
        if st.button("🔒 双语锁定", key="t3_btn_ana"):
            if bf:
                with st.spinner("AI 正在分析..."):
                    st.session_state.bg_prompt_en = ""
                    st.session_state.bg_prompt_zh = ""
                    en, zh = analyze_image_bilingual(bam, bf, "product")
                    st.session_state.bg_prompt_en = en
                    st.session_state.bg_prompt_zh = zh
                    st.success("锁定成功！")
                    st.rerun()

        st.markdown("#### Step 2: 换背景")
        t3_zh, t3_en = st.tabs(["🇨🇳 中文版 (编辑)", "🇺🇸 英文版 (只读)"])
        
        with t3_zh:
            st.text_area("产品特征 (中文)", key="bg_prompt_zh", on_change=sync_bg, height=120)
        with t3_en:
            st.text_area("AI Used Features", value=st.session_state.get("bg_prompt_en", ""), disabled=True, height=120, key="t3_en_disp")
            
        breq = st.text_area("新背景", key="t3_req")
        bw = st.slider("权重", 0.0, 1.0, 0.5, key="t3_wt")
        bc = st.slider("数量", 1, 20, 1, key="t3_cnt")
        bm = st.selectbox("生成模型", GOOGLE_IMG_MODELS, index=1, key="t3_gm")

        if "flash" in bm.lower():
             st.warning("⚠️ 注意：Flash 模型建议使用正方形构图，非 1:1 图片可能会被裁剪。")

        if st.button("🚀 换背景", key="t3_btn_gen"):
            st.session_state["bg_results"] = []
            bar = st.progress(0)
            wp = get_weight_instruction(bw)
            
            if bf:
                for i in range(bc):
                    bf.seek(0)
                    p = f"BG Swap. Product: {st.session_state.get('bg_prompt_en', '')}. New BG: {breq}. {wp}"
                    r = generate_image_call(bm, p, Image.open(bf), "")
                    if r: 
                        st.session_state["bg_results"].append(r)
                        st.session_state.history_manager.add(r, "Scene", breq)
                    bar.progress((i+1)/bc)
                    if bc > 5: time.sleep(1)

    with c2:
        if bf: 
            with st.expander("原图", True): bf.seek(0); st.image(Image.open(bf), use_container_width=True)
        
        if st.session_state.get("bg_results"):
            st.divider()
            for idx, b in enumerate(st.session_state["bg_results"]):
                st.image(create_preview_thumbnail(b, 300), caption=f"R {idx+1}")
                c_dl, c_zm = st.columns([2, 1])
                fb, m = process_image_for_download(b, download_format)
                c_dl.download_button("下载", fb, f"b_{idx}.{download_format}", m, key=f"t3_dl_{idx}")
                if c_zm.button("🔍", key=f"t3_zm_{idx}"): show_preview_modal(b, f"R {idx+1}")
