# app_utils/hd_upscale/ui_components.py
import streamlit as st
import requests
from io import BytesIO
from PIL import Image

def load_image_from_url(url):
    """辅助函数：从 URL 下载图片并转为 PIL 格式 (仅用于显示)"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        st.error(f"无法加载结果图片: {e}")
        return None

def render_upscale_sidebar():
    """渲染侧边栏控制面板"""
    st.sidebar.header("⚙️ 放大设置")
    
    scale = st.sidebar.select_slider(
        "🔎 放大倍数 (Scale)",
        options=[2, 4],
        value=4,
        help="2x 速度更快，4x 细节更丰富"
    )
    
    face_enhance = st.sidebar.checkbox(
        "🙂 面部增强 (Face Enhance)",
        value=False,
        help="如果是人像模特图，建议开启此选项以修复面部细节"
    )
    
    return scale, face_enhance

def render_comparison_result(original_file, result_url, download_data):
    """
    渲染 原图 vs 高清图 的对比结果
    :param original_file: 上传的原图文件对象
    :param result_url: 高清图 URL (不再用于直接显示，仅作备用)
    :param download_data: 已经转换好的 JPEG 二进制数据 (用于显示和下载)
    """
    st.markdown("---")
    st.subheader("🎉 处理完成 | Result")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Original (原图)")
        st.image(original_file, use_container_width=True)
        
    with col2:
        st.success(f"Upscaled (高清图)")
        
        # [核心修复] 优先使用二进制数据展示，避开 URL/格式错误
        if download_data:
            st.image(download_data, use_container_width=True)
        else:
            # 兜底：如果没有二进制数据，才尝试用 URL
            st.image(result_url, use_container_width=True)
        
        # 下载按钮：零延迟
        if download_data:
            st.download_button(
                label="📥 下载高清大图 (JPEG)",
                data=download_data,
                file_name="upscaled_image.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
