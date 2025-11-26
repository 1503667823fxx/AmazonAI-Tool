import streamlit as st
from PIL import Image, ImageSequence
import io
import sys
import os
import zipfile

# --- 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="A+ Studio", page_icon="🧩", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

st.title("🧩 A+ 创意工场 (APlus Studio)")
st.caption("亚马逊高级内容页面 (EBC) 专属设计工具流")

tab_slice, tab_preview, tab_gif = st.tabs(["📏 智能切图 (Slicer)", "📱 无缝拼接预览", "🎬 动态 GIF 制作"])

# ==========================================
# Tab 1: 智能切图 (把长图切成标准模块)
# ==========================================
with tab_slice:
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        st.subheader("1. 上传长图")
        st.info("💡 用于将设计师制作的整张长海报，自动切割为亚马逊 A+ 标准模块图 (通常宽度 970px)。")
        
        uploaded_long_img = st.file_uploader("上传长图 (JPG/PNG)", type=["jpg", "png", "jpeg"])
        
        slice_height = st.number_input("单张切片高度 (px)", min_value=100, value=600, step=100, help="亚马逊标准模块通常为 600px 或 300px")
        output_format = st.radio("输出格式", ["JPEG", "PNG"], horizontal=True)
        
        btn_slice = st.button("🔪 开始切图", type="primary")

    with col2:
        st.subheader("2. 切片结果")
        if uploaded_long_img and btn_slice:
            image = Image.open(uploaded_long_img)
            img_w, img_h = image.size
            
            st.caption(f"原始尺寸: {img_w}x{img_h} px")
            
            # 切图逻辑
            slices = []
            num_slices = (img_h + slice_height - 1) // slice_height # 向上取整
            
            # 准备压缩包
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                
                for i in range(num_slices):
                    top = i * slice_height
                    bottom = min((i + 1) * slice_height, img_h)
                    
                    # 裁剪
                    crop_img = image.crop((0, top, img_w, bottom))
                    
                    # 转字节
                    img_byte_arr = io.BytesIO()
                    ext = output_format.lower()
                    if ext == "jpeg":
                        crop_img = crop_img.convert("RGB")
                    crop_img.save(img_byte_arr, format=output_format, quality=95)
                    img_bytes = img_byte_arr.getvalue()
                    
                    # 存入列表用于显示
                    slices.append(crop_img)
                    
                    # 写入压缩包
                    zf.writestr(f"slice_{i+1:02d}.{ext}", img_bytes)
            
            # 显示切片
            st.success(f"成功切为 {len(slices)} 张图片！")
            
            # 下载全部
            st.download_button(
                "📦 打包下载所有切片 (ZIP)", 
                data=zip_buffer.getvalue(), 
                file_name="aplus_slices.zip", 
                mime="application/zip"
            )
            
            # 预览
            with st.expander("查看切片详情", expanded=True):
                grid = st.columns(2)
                for idx, s_img in enumerate(slices):
                    with grid[idx % 2]:
                        st.image(s_img, caption=f"Slice {idx+1} ({s_img.width}x{s_img.height})", use_container_width=True)

# ==========================================
# Tab 2: 无缝拼接预览 (模拟前台效果)
# ==========================================
with tab_preview:
    st.subheader("📱 移动端/PC端 滚动预览")
    st.caption("上传多张切片，检查拼接处是否自然无缝。")
    
    preview_files = st.file_uploader("按顺序上传所有切片 (支持多选)", type=["jpg", "png"], accept_multiple_files=True)
    
    if preview_files:
        # 排序逻辑：尝试按文件名排序，否则按上传顺序
        try:
            preview_files.sort(key=lambda x: x.name)
        except:
            pass
            
        st.divider()
        
        # 模拟无缝拼接：使用 st.image 的特性，将 margin 设为 0 (CSS hack)
        st.markdown("""
        <style>
            .seamless-container img {
                display: block;
                margin-bottom: -5px; /* 消除图片间隙 */
                width: 100%;
            }
            .preview-frame {
                border: 10px solid #333;
                border-radius: 20px;
                padding: 10px;
                background: #fff;
                max-width: 500px; /* 模拟手机宽度 */
                margin: 0 auto;
                overflow-y: auto;
                max-height: 800px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="preview-frame">', unsafe_allow_html=True)
        for p_file in preview_files:
            # 直接读取并显示，不加 caption 以免破坏无缝感
            img = Image.open(p_file)
            st.image(img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# Tab 3: 动态 GIF 制作 (简单动效)
# ==========================================
with tab_gif:
    c_g1, c_g2 = st.columns([1, 1.5], gap="large")
    
    with c_g1:
        st.subheader("1. 制作设置")
        gif_files = st.file_uploader("上传关键帧 (2-10张)", type=["jpg", "png"], accept_multiple_files=True, key="gif_upload")
        
        duration = st.slider("每帧停留时间 (毫秒)", 100, 2000, 500, step=100)
        loop_count = st.number_input("循环次数 (0=无限循环)", value=0)
        resize_width = st.number_input("统一宽度缩放 (px, 0=不缩放)", value=970)
        
        btn_gif = st.button("🎬 生成 GIF", type="primary")
        
    with c_g2:
        st.subheader("2. 效果预览")
        if btn_gif and gif_files:
            if len(gif_files) < 2:
                st.error("至少需要上传 2 张图片才能制作 GIF")
            else:
                try:
                    frames = []
                    for f in gif_files:
                        im = Image.open(f)
                        # 统一尺寸逻辑
                        if resize_width > 0:
                            ratio = resize_width / im.width
                            new_h = int(im.height * ratio)
                            im = im.resize((resize_width, new_h), Image.Resampling.LANCZOS)
                        frames.append(im)
                    
                    # 保存 GIF
                    gif_buffer = io.BytesIO()
                    # duration 是每帧的时间(ms)
                    frames[0].save(
                        gif_buffer, 
                        format='GIF', 
                        save_all=True, 
                        append_images=frames[1:], 
                        optimize=True, 
                        duration=duration, 
                        loop=loop_count
                    )
                    
                    st.success("GIF 生成成功！")
                    st.image(gif_buffer.getvalue(), caption="生成的动态 A+ 模块")
                    
                    st.download_button(
                        "📥 下载 GIF", 
                        data=gif_buffer.getvalue(), 
                        file_name="aplus_motion.gif", 
                        mime="image/gif"
                    )
                    
                except Exception as e:
                    st.error(f"生成失败: {e}")
