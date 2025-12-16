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
    st.info("请确保已安装所有依赖: pip install -r requirements.txt")
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
st.title("🖌️ Magic Canvas - AI智能重绘")
st.caption("上传图片，涂抹想要修改的区域，输入创意描述，AI帮你精准重绘。")

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
        st.info("💡 在图片上涂抹想要修改的区域，红色区域将被AI重绘")
        
        # 使用涂抹画布组件
        canvas_result = create_drawing_canvas(
            st.session_state.uploaded_image, 
            brush_size=brush_size
        )
        
        # 初始化mask状态
        if "current_mask" not in st.session_state:
            st.session_state.current_mask = None
        
        # 检查是否有绘制内容
        has_drawing = False
        mask_image = None
        
        # 检查URL参数中的绘制状态
        query_params = st.query_params
        canvas_drawing = query_params.get('canvas_drawing', '0') == '1'
        
        if canvas_result:
            # 处理streamlit-drawable-canvas数据（如果可用）
            if hasattr(canvas_result, 'image_data') and canvas_result.image_data is not None:
                # 获取canvas数据
                canvas_array = np.array(canvas_result.image_data)
                
                # 检查是否有绘制内容（非透明像素）
                if len(canvas_array.shape) == 3 and canvas_array.shape[2] >= 4:
                    alpha_channel = canvas_array[:, :, 3]
                    
                    # 创建二值mask
                    mask_array = (alpha_channel > 0).astype(np.uint8) * 255
                    
                    # 计算涂抹面积
                    white_pixels = np.sum(mask_array > 0)
                    
                    if white_pixels > 100:  # 最小面积检查
                        mask_image = Image.fromarray(mask_array, mode='L')
                        
                        # 确保尺寸匹配
                        if mask_image.size != st.session_state.uploaded_image.size:
                            mask_image = mask_image.resize(st.session_state.uploaded_image.size, Image.Resampling.NEAREST)
                        
                        has_drawing = True
                        st.session_state.current_mask = mask_image
                    else:
                        st.warning("⚠️ 涂抹区域太小，请涂抹更大的区域")
            
            # 处理HTML Canvas数据
            elif canvas_drawing or (hasattr(canvas_result, 'has_drawing') and canvas_result.has_drawing):
                # 创建一个简单的测试mask来验证功能
                if "test_mask" not in st.session_state:
                    # 创建一个中心区域的测试mask
                    test_mask = Image.new('L', st.session_state.uploaded_image.size, 0)
                    draw = ImageDraw.Draw(test_mask)
                    w, h = st.session_state.uploaded_image.size
                    center_x, center_y = w // 2, h // 2
                    radius = min(w, h) // 6
                    draw.ellipse([
                        center_x - radius, center_y - radius,
                        center_x + radius, center_y + radius
                    ], fill=255)
                    st.session_state.test_mask = test_mask
                
                mask_image = st.session_state.test_mask
                has_drawing = True
                st.session_state.current_mask = mask_image
                st.info("💡 检测到涂抹活动，使用测试区域进行重绘")
        
        # 添加控制按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("🔍 检测涂抹区域", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🎯 创建测试区域", use_container_width=True):
                # 创建一个中心测试区域
                test_mask = Image.new('L', st.session_state.uploaded_image.size, 0)
                draw = ImageDraw.Draw(test_mask)
                w, h = st.session_state.uploaded_image.size
                center_x, center_y = w // 2, h // 2
                radius = min(w, h) // 6
                draw.ellipse([
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius
                ], fill=255)
                st.session_state.current_mask = test_mask
                st.session_state.test_mask = test_mask
                st.success("✅ 已创建测试区域")
                st.rerun()
        with col3:
            if st.button("🗑️ 清除画布", use_container_width=True):
                # 清除所有相关状态
                keys_to_clear = ["current_mask", "html_canvas_mask", "test_mask", "canvas_has_drawing", "canvas_mask_data"]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                # 清除URL参数
                st.query_params.clear()
                st.rerun()
        
        # 简化的状态信息
        col_status1, col_status2 = st.columns(2)
        with col_status1:
            if canvas_drawing:
                st.success("🎨 检测到涂抹活动")
            else:
                st.info("⏳ 等待涂抹...")
        
        with col_status2:
            if has_drawing:
                st.success("✅ 涂抹区域已准备")
            else:
                st.warning("❌ 未检测到涂抹区域")
        
        # 显示当前状态
        if has_drawing and mask_image:
            st.success("✅ 已检测到涂抹区域")
            with st.expander("🔍 查看涂抹区域", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.image(st.session_state.uploaded_image, caption="原图", use_column_width=True)
                with col2:
                    st.image(mask_image, caption="涂抹区域 (白色部分将被重绘)", use_column_width=True)
        else:
            st.info("💡 请在上方画布中涂抹要修改的区域，涂抹后点击'检测涂抹区域'按钮")
        
        # 处理重绘请求
        if generate_btn:
            if not has_drawing and st.session_state.current_mask is None:
                st.error("❌ 请先在画布上涂抹要修改的区域")
            else:
                # 使用当前mask或者用户刚绘制的mask
                final_mask = mask_image if mask_image else st.session_state.current_mask
                
                with st.status("🎨 正在进行创意重绘...", expanded=True) as status:
                    try:
                        st.write("🔍 分析涂抹区域...")
                        
                        if final_mask:
                            # 显示将要重绘的区域
                            with st.expander("🔍 重绘区域预览", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.image(st.session_state.uploaded_image, caption="原图", use_column_width=True)
                                with col2:
                                    st.image(final_mask, caption="重绘区域 (白色部分)", use_column_width=True)
                            
                            # 2. 调用Gemini重绘服务
                            st.write("🎨 Gemini正在发挥创意...")
                            result_image = st.session_state.inpaint_service.inpaint(
                                original_image=st.session_state.uploaded_image,
                                mask_image=final_mask,
                                prompt=prompt
                            )
                            
                            if result_image:
                                status.update(label="✅ 创意重绘完成！", state="complete")
                                
                                # 显示结果对比
                                st.subheader("🎨 重绘结果")
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
                        else:
                            st.error("❌ 无法获取涂抹区域，请重新涂抹")
                            
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
