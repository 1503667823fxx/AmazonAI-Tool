# pages/9_🔍_HD_Upscale.py
import streamlit as st
import auth
from app_utils.hd_upscale.download_handler import fast_convert_and_cache
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result

st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

if not auth.check_password():
    st.stop()

st.title("🔍 SUPIR 极致高清化 (AI超分辨率)")

if "upscale_result_url" not in st.session_state:
    st.session_state["upscale_result_url"] = None

engine = UpscaleEngine()

# 渲染侧边栏并获取参数
output_format = render_upscale_sidebar()

uploaded_file = st.file_uploader("📤 上传图片", type=["jpg", "jpeg", "png"])

if uploaded_file:
    if "last_uploaded_name" not in st.session_state or st.session_state["last_uploaded_name"] != uploaded_file.name:
        st.session_state["upscale_result_url"] = None
        st.session_state["last_uploaded_name"] = uploaded_file.name

    with st.expander("预览原图", expanded=False):
        st.image(uploaded_file, width=200)

    if st.session_state["upscale_result_url"] is None:
        if st.button("🚀 开始高清放大", type="primary", use_container_width=True):
            if not engine.client:
                st.error("API Key 缺失")
            else:
                try:
                    with st.spinner("正在使用 SUPIR 模型云端运算..."):
                        # A. 获取 URL
                        final_url = engine.process_image(uploaded_file)
                        
                        # B. 存入状态
                        st.session_state["upscale_result_url"] = final_url
                        st.session_state["output_format"] = output_format
                        
                        # C. 触发缓存
                        fast_convert_and_cache(str(final_url), output_format)
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # 7. 结果展示
    if st.session_state["upscale_result_url"]:
        url = st.session_state["upscale_result_url"]
        saved_format = st.session_state.get("output_format", "PNG")
        
        # [关键] 这里的 url 必须是字符串，缓存才能工作
        cached_data = fast_convert_and_cache(str(url), saved_format)
        
        render_comparison_result(
            original_file=uploaded_file, 
            result_url=url, 
            download_data=cached_data
        )
        
        if st.button("🔄 处理下一张"):
            st.session_state["upscale_result_url"] = None
            st.rerun()
