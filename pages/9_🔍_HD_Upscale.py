# pages/9_🔍_HD_Upscale.py
import streamlit as st
import auth
from app_utils.hd_upscale.download_handler import fast_convert_and_cache
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result
from app_utils.hd_upscale.image_preprocessor import ImagePreprocessor

st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

if not auth.check_password():
    st.stop()

st.title("🔍 SUPIR v0q 极致高清化 (专业超分辨率)")

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
        
        # 预处理图片以优化SUPIR处理
        with st.spinner("🔧 正在优化图片以提高处理成功率..."):
            optimized_file, was_optimized, optimization_info = ImagePreprocessor.optimize_for_supir(uploaded_file)
            st.session_state["processed_file"] = optimized_file
            st.session_state["optimization_info"] = optimization_info
    
    # 显示优化信息
    if "optimization_info" in st.session_state:
        ImagePreprocessor.show_optimization_info(st.session_state["optimization_info"])

    with st.expander("预览原图", expanded=False):
        st.image(uploaded_file, width=200)

    if st.session_state["upscale_result_url"] is None:
        if st.button("🚀 开始高清放大", type="primary", use_container_width=True):
            if not engine.client:
                st.error("API Key 缺失")
            else:
                try:
                    with st.spinner("正在使用 SUPIR v0q 模型云端运算..."):
                        # 使用预处理后的文件
                        processed_file = st.session_state.get("processed_file", uploaded_file)
                        
                        # A. 获取 URL
                        final_url = engine.process_image(processed_file)
                        
                        # B. 存入状态
                        st.session_state["upscale_result_url"] = final_url
                        st.session_state["output_format"] = output_format
                        
                        # C. 触发缓存
                        fast_convert_and_cache(str(final_url), output_format)
                        
                        st.success("✅ SUPIR v0q 处理完成！")
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
