# pages/9_🔍_HD_Upscale.py
import streamlit as st
import auth
# [核心] 引入新的下载处理器
from app_utils.hd_upscale.download_handler import fast_convert_and_cache
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result

# 1. 页面配置
st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

# 2. 门禁系统
if not auth.check_password():
    st.stop()

st.title("🔍 图片极致高清化 (HD Upscale)")

# --- 初始化 Session ---
if "upscale_result_url" not in st.session_state:
    st.session_state["upscale_result_url"] = None
# 注意：我们不再手动存 image_bytes 到 session，因为 st.cache_data 帮我们自动管理了
    
# 3. 初始化引擎
engine = UpscaleEngine()

# 4. 侧边栏
scale_factor, enable_face_enhance = render_upscale_sidebar()

# 5. 上传区
uploaded_file = st.file_uploader("📤 上传图片", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # 换文件时清理状态
    if "last_uploaded_name" not in st.session_state or st.session_state["last_uploaded_name"] != uploaded_file.name:
        st.session_state["upscale_result_url"] = None
        st.session_state["last_uploaded_name"] = uploaded_file.name

    with st.expander("预览原图", expanded=False):
        st.image(uploaded_file, width=200)

    # 6. 执行逻辑
    if st.session_state["upscale_result_url"] is None:
        if st.button("🚀 开始高清放大", type="primary", use_container_width=True):
            if not engine.client:
                st.error("API Key 缺失")
            else:
                try:
                    with st.spinner("正在云端运算..."):
                        # A. 获取 URL
                        url = engine.process_image(uploaded_file, scale_factor, enable_face_enhance)
                        
                        # 容错提取
                        final_url = url[0] if isinstance(url, list) else url
                        
                        # B. 存入状态
                        st.session_state["upscale_result_url"] = final_url
                        
                        # C. [关键] 立即触发缓存处理
                        # 这一步会把图片拉取并转码存入服务器内存
                        fast_convert_and_cache(final_url)
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # 7. 结果展示
    if st.session_state["upscale_result_url"]:
        url = st.session_state["upscale_result_url"]
        
        # [关键] 直接从缓存获取数据，速度极快
        # 因为在上面生成完的那一刻，数据已经被 cache 了，这里是秒读
        cached_data = fast_convert_and_cache(url)
        
        render_comparison_result(
            original_file=uploaded_file, 
            result_url=url, 
            download_data=cached_data
        )
        
        if st.button("🔄 处理下一张"):
            st.session_state["upscale_result_url"] = None
            st.rerun()
