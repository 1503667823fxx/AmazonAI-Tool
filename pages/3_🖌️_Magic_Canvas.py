import streamlit as st
from PIL import Image, ImageDraw, ImageOps
import io
import numpy as np
import base64
import json

# --- 1. 环境与依赖设置 ---
import sys
import os

# 确保路径正确
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.magic_canvas.inpaint_engine import InpaintService
    from services.magic_canvas.canvas_utils import create_drawing_canvas
except ImportError as e:
    st.error(f"❌ 核心模块丢失: {e}")
    st.stop()

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

# --- 2. 鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# --- 3. 初始化服务 ---
if "inpaint_service" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.inpaint_service = InpaintService(api_key)

# --- 4. 页面布局 ---



# --- 5. 页面布局 ---
st.title("🖌️ Magic Canvas - Gemini创意重绘")
st.caption("上传图片，输入简洁的创意描述，让Gemini为你重新创作图片的中心区域。")

# 初始化状态
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "canvas_strokes" not in st.session_state:
    st.session_state.canvas_strokes = []

col_tools, col_canvas = st.columns([1, 2])

with col_tools:
    st.subheader("🛠️ 控制面板")
    
    # A. 上传图片
    uploaded_file = st.file_uploader("📁 上传原图", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        # 限制尺寸以提高性能
        max_size = 800
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        st.session_state.uploaded_image = image
        st.session_state.canvas_strokes = []  # 重置画布
    
    if st.session_state.uploaded_image:
        st.success(f"✅ 图片已加载 ({st.session_state.uploaded_image.size[0]}×{st.session_state.uploaded_image.size[1]})")
    
    st.divider()
    
    # B. 画笔设置
    brush_size = st.slider("🖊️ 画笔大小", min_value=5, max_value=50, value=20, step=5)
    
    # C. 清除按钮
    if st.button("🗑️ 清除涂抹", use_container_width=True):
        st.session_state.canvas_strokes = []
        st.rerun()
    
    st.divider()
    
    # D. 重绘指令
    prompt = st.text_area(
        "✨ 重绘指令", 
        height=120, 
        placeholder="简单描述你想要的效果，Gemini会发挥创造力：\n\n• 一朵红玫瑰\n• 戴墨镜\n• 蓝天白云\n• 金色头发\n• 彩虹\n\n保持简洁，让AI自由发挥！"
    )
    
    # 提示信息
    st.info("💡 **Gemini创意模式**：使用简洁的描述词，AI会自动匹配风格和场景")
    
    # F. 执行按钮
    generate_btn = st.button("🎨 开始重绘", type="primary", use_container_width=True, disabled=not st.session_state.uploaded_image or not prompt.strip())

with col_canvas:
    if st.session_state.uploaded_image:
        st.subheader("🎨 编辑画布")
        
        # 显示操作提示
        st.info("💡 可以在画布上涂抹（当前版本将重绘中心区域）")
        
        # 使用改进的canvas组件
        create_drawing_canvas(
            st.session_state.uploaded_image, 
            brush_size=brush_size
        )
        
        # 简化的状态管理
        st.info("💡 在上方画布中涂抹要修改的区域，然后输入重绘指令")
        
        # 处理重绘请求
        if generate_btn:
            with st.status("🎨 正在进行创意重绘...", expanded=True) as status:
                try:
                    # 1. 创建一个简单的中心区域mask作为示例
                    st.write("🔍 准备重绘区域...")
                    
                    # 创建一个中心区域的mask（用户应该在这个区域涂抹）
                    mask_image = Image.new('L', st.session_state.uploaded_image.size, 0)
                    draw = ImageDraw.Draw(mask_image)
                    
                    # 创建一个中心圆形区域作为默认mask
                    w, h = st.session_state.uploaded_image.size
                    center_x, center_y = w // 2, h // 2
                    radius = min(w, h) // 4
                    draw.ellipse([
                        center_x - radius, center_y - radius,
                        center_x + radius, center_y + radius
                    ], fill=255)
                    
                    # 显示生成的mask
                    with st.expander("🔍 查看重绘区域", expanded=False):
                        st.image(mask_image, caption="重绘区域 (白色部分)", width=300)
                        st.info("💡 当前使用中心区域作为重绘范围，未来版本将支持自定义涂抹")
                    
                    # 2. 调用Gemini重绘服务
                    st.write("🎨 Gemini正在发挥创意...")
                    result_image = st.session_state.inpaint_service.inpaint(
                        original_image=st.session_state.uploaded_image,
                        mask_image=mask_image,
                        prompt=prompt
                    )
                    
                    if result_image:
                        status.update(label="✅ 创意重绘完成！", state="complete")
                        
                        # 显示结果对比
                        col1, col2 = st.columns(2)
                        with col1:
                            st.image(st.session_state.uploaded_image, caption="原图", use_column_width=True)
                        with col2:
                            st.image(result_image, caption="Gemini创意结果", use_column_width=True)
                        
                        # 提供下载按钮
                        buf = io.BytesIO()
                        result_image.save(buf, format='PNG')
                        st.download_button(
                            label="📥 下载创意结果",
                            data=buf.getvalue(),
                            file_name="gemini_magic_result.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ 重绘失败，请检查API配置")
                        
                except Exception as e:
                    st.error(f"❌ 处理过程中出现错误: {str(e)}")
                    st.info("💡 提示：请确保已正确配置Google API密钥")
    else:
        # 空状态显示
        st.subheader("📁 请上传图片开始编辑")
        st.markdown("""
        <div style="
            border: 2px dashed #ccc; 
            border-radius: 10px; 
            padding: 60px 20px; 
            text-align: center; 
            color: #666;
            background: #f9f9f9;
            margin: 20px 0;
        ">
            <h3>🎨 Magic Canvas</h3>
            <p>上传一张图片，然后在想要修改的区域涂抹，AI将帮你实现精准的局部重绘</p>
            <p><small>支持 PNG、JPG、JPEG、WebP 格式</small></p>
        </div>
        """, unsafe_allow_html=True)
