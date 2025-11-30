# app_utils/hd_upscale/ui_components.py
import streamlit as st
import requests
from io import BytesIO
from PIL import Image

def load_image_from_url(url):
    """辅助函数：从 URL 下载图片并转为 PIL 格式"""
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

def render_comparison_result(original_file, result_url):
    """渲染 原图 vs 高清图 的对比结果"""
    st.markdown("---")
    st.subheader("🎉 处理完成 | Result")
    
    # 获取结果图片对象
    result_img = load_image_from_url(result_url)
    
    if result_img:
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("Original (原图)")
            st.image(original_file, use_container_width=True)
            
        with col2:
            st.success(f"Upscaled (高清图)")
            st.image(result_img, use_container_width=True)
            
            # 提供下载按钮
            # 将 PIL 图片转为 Bytes 用于下载
            buf = BytesIO()
            result_img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 下载高清大图 (PNG)",
                data=byte_im,
                file_name="upscaled_image.png",
                mime="image/png",
                use_container_width=True
            )
