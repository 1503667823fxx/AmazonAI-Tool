# app_utils/hd_upscale/ui_components.py
import streamlit as st

def render_upscale_sidebar():
    """渲染侧边栏控制面板"""
    st.sidebar.header("⚙️ 放大设置")
    
    # 模型选择
    model_choice = st.sidebar.selectbox(
        "🤖 AI模型选择",
        options=[
            ("real_esrgan", "🌟 Real-ESRGAN (通用推荐)"),
            ("real_esrgan_v2", "🔧 Real-ESRGAN V2 (结构优化)")
        ],
        format_func=lambda x: x[1],
        help="""选择最适合你图像类型的AI模型：
        
🌟 Real-ESRGAN: 照片和自然图像的通用选择，经过验证稳定可用
🔧 Real-ESRGAN V2: 可能有更好的结构保持能力，适合细节图像

注意：为了确保稳定性，目前只提供经过验证的模型"""
    )
    
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
    
    # 高级设置
    with st.sidebar.expander("🔧 高级设置"):
        preserve_structure = st.checkbox(
            "📐 结构保护模式",
            value=False,
            help="启用后会优先保持原图的几何结构和线条清晰度"
        )
        
        output_format = st.selectbox(
            "💾 输出格式",
            options=["JPEG", "PNG"],
            help="PNG无损但文件大，JPEG有损但文件小"
        )
    
    return model_choice[0], scale, face_enhance, preserve_structure, output_format

def render_comparison_result(original_file, result_url, download_data):
    """
    渲染 原图 vs 高清图 的对比结果
    """
    st.markdown("---")
    st.subheader("🎉 处理完成 | Result")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Original (原图)")
        st.image(original_file, use_container_width=True)
        
    with col2:
        st.success(f"Upscaled (高清图)")
        
        # 优先显示 URL (速度最快)，因为 download_data 可能还在后台处理
        # 容错：处理列表类型的 URL
        display_url = result_url[0] if isinstance(result_url, list) else result_url
        st.image(display_url, use_container_width=True)
        
        st.markdown("---")
        
        # === 极速下载区 ===
        if download_data:
            # 根据格式动态调整下载按钮
            file_ext = "png" if st.session_state.get("output_format", "JPEG") == "PNG" else "jpg"
            mime_type = "image/png" if file_ext == "png" else "image/jpeg"
            
            st.download_button(
                label=f"📥 点击下载 {file_ext.upper()} (已转码)",
                data=download_data,
                file_name=f"upscaled_hd.{file_ext}",
                mime=mime_type,
                use_container_width=True,
                type="primary" # 高亮按钮
            )
        else:
            st.warning("⏳ 图片转码中，请稍等...")
            
        # 方案 B: 备用直接链接 (防止服务器卡死)
        st.markdown(f"""
        <div style="text-align: center; margin-top: 10px;">
            <a href="{display_url}" target="_blank" style="color: #666; text-decoration: none; font-size: 0.8em;">
                🔗 如果下载慢，点此直接打开原图 (PNG)
            </a>
        </div>
        """, unsafe_allow_html=True)
