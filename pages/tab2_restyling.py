import streamlit as st
from PIL import Image
import time
from core_utils import analyze_image_bilingual, get_weight_instruction, generate_image_call, create_preview_thumbnail, process_image_for_download, show_preview_modal

def render_tab2(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, download_format):
    c1, c2 = st.columns([1.5, 1], gap="large")
    
    def sync_var():
        v = st.session_state.var_prompt_zh
        if v: 
            trans = st.session_state.translator.to_english(v)
            st.session_state.var_prompt_en = trans
            st.toast("✅ 英文底稿已更新")

    with c1:
        st.markdown("#### Step 1: 读取")
        vf = st.file_uploader("原图", key="t2_up")
        vam = st.selectbox("分析模型", ANALYSIS_MODELS, key="t2_am")
        
        if st.button("👁️ 双语读图", key="t2_btn_ana"):
            if vf:
                with st.spinner("AI 正在同时生成中英文描述..."):
                    st.session_state.var_prompt_en = ""
                    st.session_state.var_prompt_zh = ""
                    en, zh = analyze_image_bilingual(vam, vf, "fashion")
                    st.session_state.var_prompt_en = en
                    st.session_state.var_prompt_zh = zh
                    st.success("读取成功！")
                    st.rerun()

        st.markdown("#### Step 2: 改款")
        t2_zh, t2_en = st.tabs(["🇨🇳 中文版 (编辑)", "🇺🇸 英文版 (只读)"])
        
        with t2_zh:
            st.text_area("特征描述 (中文)", key="var_prompt_zh", on_change=sync_var, height=120)
        with t2_en:
            st.text_area("AI Used Features", value=st.session_state.get("var_prompt_en", ""), disabled=True, height=120, key="t2_en_disp")

        md = st.selectbox("模式", ["微调 (Texture)", "中改 (Details)", "大改 (Silhouette)"], key="t2_mode")
        req = st.text_area("改款指令", key="t2_req")
        vw = st.slider("权重", 0.0, 1.0, 0.5, key="t2_wt")
        vc = st.slider("数量", 1, 20, 1, key="t2_cnt")
        vm = st.selectbox("生成模型", GOOGLE_IMG_MODELS, key="t2_gm")
        
        if "flash" in vm.lower():
             st.warning("⚠️ 注意：Flash 模型建议使用正方形构图，非 1:1 图片可能会被裁剪。")

        if st.button("🚀 改款", key="t2_btn_gen"):
            st.session_state["batch_results"] = []
            bar = st.progress(0)
            wp = get_weight_instruction(vw)
            
            if vf:
                for i in range(vc):
                    vf.seek(0)
                    p = f"Restyle. Base: {st.session_state.get('var_prompt_en', '')}. Mode: {md}. Request: {req}. {wp}"
                    r = generate_image_call(vm, p, Image.open(vf), "")
                    if r: 
                        st.session_state["batch_results"].append(r)
                        st.session_state.history_manager.add(r, "Restyle", req)
                    bar.progress((i+1)/vc)
                    if vc > 5: time.sleep(1)

    with c2:
        if vf: 
            with st.expander("原图", True): vf.seek(0); st.image(Image.open(vf), use_container_width=True)
        
        if st.session_state.get("batch_results"):
            st.divider()
            for idx, b in enumerate(st.session_state["batch_results"]):
                st.image(create_preview_thumbnail(b, 300), caption=f"R {idx+1}")
                c_dl, c_zm = st.columns([2, 1])
                fb, m = process_image_for_download(b, download_format)
                c_dl.download_button("下载", fb, f"v_{idx}.{download_format}", m, key=f"t2_dl_{idx}")
                if c_zm.button("🔍", key=f"t2_zm_{idx}"): show_preview_modal(b, f"R {idx+1}")
