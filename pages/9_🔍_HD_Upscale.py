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

st.title("🔍 SUPIR 极致高清化 (AI超分辨率)")

if "upscale_result_url" not in st.session_state:
    st.session_state["upscale_result_url"] = None

engine = UpscaleEngine()

# 渲染侧边栏并获取参数
output_format, memory_mode, quality_preset = render_upscale_sidebar()

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
                    # 根据设置选择处理模式
                    use_memory_optimization = (memory_mode == "优化")
                    
                    spinner_text = f"正在使用 SUPIR 模型云端运算... ({quality_preset})"
                    if use_memory_optimization:
                        spinner_text += " [内存优化模式]"
                    
                    with st.spinner(spinner_text):
                        try:
                            # 使用预处理后的文件
                            processed_file = st.session_state.get("processed_file", uploaded_file)
                            
                            # A. 获取 URL
                            final_url = engine.process_image(processed_file, use_fallback=use_memory_optimization, quality_preset=quality_preset)
                            
                            # B. 存入状态
                            st.session_state["upscale_result_url"] = final_url
                            st.session_state["output_format"] = output_format
                            
                            # C. 触发缓存
                            fast_convert_and_cache(str(final_url), output_format)
                            
                            st.success("✅ 处理完成！")
                            st.rerun()
                            
                        except Exception as inner_e:
                            # 如果标准模式失败，自动尝试内存优化模式
                            if not use_memory_optimization and "memory" in str(inner_e).lower():
                                st.warning("⚠️ 标准模式内存不足，自动切换到优化模式...")
                                try:
                                    processed_file = st.session_state.get("processed_file", uploaded_file)
                                    final_url = engine.process_image(processed_file, use_fallback=True, quality_preset="快速")
                                    st.session_state["upscale_result_url"] = final_url
                                    st.session_state["output_format"] = output_format
                                    fast_convert_and_cache(str(final_url), output_format)
                                    st.success("✅ 内存优化模式处理完成！")
                                    st.rerun()
                                except Exception as fallback_e:
                                    raise fallback_e
                            else:
                                raise inner_e
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
