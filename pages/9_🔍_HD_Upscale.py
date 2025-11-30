# pages/9_🔍_HD_Upscale.py
import streamlit as st
# [核心] 引用专属模块，不依赖其他任何旧代码
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result

# 1. 页面配置
st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

st.title("🔍 图片极致高清化 (HD Upscale)")
st.markdown("""
使用 **Real-ESRGAN** SOTA 模型对电商图片进行无损放大与细节修复。
适用于：`商品细节图`、`模糊素材修复`、`模特图面部增强`。
""")

# 2. 初始化服务引擎
engine = UpscaleEngine()

# 3. 侧边栏设置
scale_factor, enable_face_enhance = render_upscale_sidebar()

# 4. 主界面：上传区域
uploaded_file = st.file_uploader("📤 请上传需要放大的图片 (支持 JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # 展示预览
    with st.expander("👁️ 预览原图", expanded=False):
        st.image(uploaded_file, width=300)

    # 5. 执行逻辑
    btn = st.button("🚀 开始高清放大 (Start Upscaling)", type="primary", use_container_width=True)
    
    if btn:
        if not engine.client:
            st.error("API Key 配置缺失，无法运行。")
        else:
            try:
                with st.spinner(f"正在进行 {scale_factor}x 极速放大，请稍候..."):
                    # 调用专属服务层
                    result_url = engine.process_image(
                        image_file=uploaded_file,
                        scale=scale_factor,
                        face_enhance=enable_face_enhance
                    )
                
                # 调用专属组件层展示结果
                if result_url:
                    render_comparison_result(uploaded_file, result_url)
                    
            except Exception as e:
                st.error(f"处理过程中发生错误: {e}")
