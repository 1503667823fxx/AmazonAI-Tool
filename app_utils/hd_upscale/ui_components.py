# app_utils/hd_upscale/ui_components.py
import streamlit as st

def render_upscale_sidebar():
    """渲染侧边栏控制面板"""
    st.sidebar.header("⚙️ Crystal Upscaler 高清放大")
    
    # 显示模型信息
    st.sidebar.info("⚠非特殊情况请默认使用2倍放大，8倍一次11元，6倍一次6元，4倍一次1.5元，2倍3毛钱")
    
    # 放大倍数选择
    scale_factor = st.sidebar.selectbox(
        "🔎 放大倍数",
        options=[2, 4, 6, 8],
        index=0,  # 默认选择2倍
        help="选择图片放大倍数，倍数越高细节越丰富但处理时间越长"
    )
    
    # 输出格式选择
    output_format = st.sidebar.selectbox(
        "💾 输出格式",
        options=["PNG", "JPEG"],
        help="PNG无损保持最佳细节，JPEG文件更小"
    )
    
    return scale_factor, output_format

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
        # 显示放大倍数信息
        scale_info = st.session_state.get("scale_factor", "")
        if scale_info:
            st.success(f"Crystal Upscaled {scale_info}x (高清图)")
        else:
            st.success(f"Crystal Upscaled (高清图)")
        
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
