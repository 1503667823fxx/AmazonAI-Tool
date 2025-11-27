import streamlit as st
from PIL import Image
from core_utils import smart_analyze_image, generate_image_call, create_preview_thumbnail, process_image_for_download, show_preview_modal

def render_tab1(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, RATIO_MAP, download_format):
    c_main, c_prev = st.columns([1.5, 1], gap="large")

    
    with c_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        am = c1.selectbox("1. 读图模型", ANALYSIS_MODELS, key="t1_am")
        ufs = c2.file_uploader("2. 上传参考图", type=["jpg","png","webp"], accept_multiple_files=True, key="t1_up")
        
        af = None
        if ufs:
            af = ufs[0] if len(ufs) == 1 else next((f for f in ufs if f.name == st.selectbox("选择图片", [f.name for f in ufs], key="t1_sel")), ufs[0])

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"], key="t1_tt")
        user_idea = st.text_area("4. 你的创意", height=80, placeholder="例如：改为极简主义风格...", key="t1_idea")
        user_weight = st.slider("5. 创意权重", 0.0, 1.0, 0.6, key="t1_wt")

        if st.button("🧠 生成 Prompt", type="primary", key="t1_btn_ana"):
            if not af: st.warning("请上传图片")
            else:
                with st.spinner("AI 正在分析..."):
                    st.session_state["std_prompt_data"] = []
                    res = smart_analyze_image(am, af, task_type, user_idea, user_weight)
                    st.session_state["std_prompt_data"] = res
                    st.rerun()

        if st.session_state.get("std_prompt_data"):
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            for i, d in enumerate(st.session_state["std_prompt_data"]):
                with st.expander(f"任务 {i+1}", expanded=True):
                    tz, te = st.tabs(["🇨🇳 中文 (编辑)", "🇺🇸 英文 (只读结果)"])
                    
                    def sync1(idx=i):
                        nz = st.session_state[f"t1_z_{idx}"]
                        st.session_state["std_prompt_data"][idx]["zh"] = nz
                        trans_en = st.session_state.translator.to_english(nz)
                        st.session_state["std_prompt_data"][idx]["en"] = trans_en
                        st.toast("✅ 英文底稿已更新")
                        
                    with tz: st.text_area("中文提示词", key=f"t1_z_{i}", value=d["zh"], on_change=sync1, height=100)
                    with te: st.text_area("AI 使用的英文指令", value=d["en"], disabled=True, height=100)

            cg1, cg2, cg3 = st.columns(3)
            gm = cg1.selectbox("生成模型", GOOGLE_IMG_MODELS, key="t1_gm")
            rt = cg2.selectbox("比例", list(RATIO_MAP.keys()), key="t1_rt")
            nm = cg3.number_input("数量", 1, 4, 1, key="t1_nm")
            
            if "flash" in gm.lower() and "1:1" not in rt:
                st.warning("⚠️ 注意：您选择了 Flash 模型但画幅非 1:1。建议切换为 Pro 模型或使用 1:1 画幅。")

            if st.button("🎨 开始生成", type="primary", key="t1_btn_gen"):
                st.session_state["std_images"] = []
                bar = st.progress(0)
                if af:
                    total = len(st.session_state["std_prompt_data"]) * nm
                    done = 0
                    for t_idx, t_data in enumerate(st.session_state["std_prompt_data"]):
                        for _ in range(nm):
                            af.seek(0); img = Image.open(af)
                            res_img = generate_image_call(gm, t_data["en"], img, RATIO_MAP[rt])
                            if res_img:
                                st.session_state["std_images"].append(res_img)
                                st.session_state.history_manager.add(res_img, f"Task {t_idx+1}", t_data["zh"])
                            done += 1
                            bar.progress(done/total)
                    st.success("完成")

    with c_prev:
        st.subheader("预览")
        if af:
            with st.expander("原图", expanded=True):
                af.seek(0); st.image(Image.open(af), use_container_width=True)
        
        if st.session_state.get("std_images"):
            st.divider()
            for idx, bits in enumerate(st.session_state["std_images"]):
                st.image(create_preview_thumbnail(bits, max_width=300), caption=f"R {idx+1}")
                c_dl, c_zm = st.columns([2, 1])
                fb, fm = process_image_for_download(bits, format=download_format)
                c_dl.download_button("下载", fb, file_name=f"s_{idx}.{download_format}", mime=fm, use_container_width=True, key=f"t1_dl_{idx}")
                if c_zm.button("🔍", key=f"t1_zm_{idx}"): show_preview_modal(bits, f"R {idx+1}")
