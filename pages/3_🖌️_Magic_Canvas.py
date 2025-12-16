import streamlit as st
from PIL import Image, ImageDraw
import io
import numpy as np
import base64
import streamlit.components.v1 as components

# --- 环境设置 ---
import sys
import os

current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.magic_canvas.inpaint_engine import InpaintService
except ImportError as e:
    st.error(f"❌ 核心模块丢失: {e}")
    st.stop()

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "inpaint_service" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.inpaint_service = InpaintService(api_key)

st.title("🖌️ Magic Canvas - AI智能重绘")
st.caption("上传图片，涂抹想要修改的区域，AI帮你精准重绘涂抹的地方。")

# 初始化session state
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "mask_data" not in st.session_state:
    st.session_state.mask_data = None
if "canvas_key" not in st.session_state:
    st.session_state.canvas_key = 0
if "confirmed_mask_data" not in st.session_state:
    st.session_state.confirmed_mask_data = ""

col_tools, col_canvas = st.columns([1, 2])

with col_tools:
    st.subheader("🛠️ 控制面板")
    
    uploaded_file = st.file_uploader("📁 上传原图", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        max_size = 600
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        st.session_state.uploaded_image = image
        st.session_state.mask_data = None
        st.session_state.confirmed_mask_data = ""
        st.session_state.canvas_key += 1
    
    if st.session_state.uploaded_image:
        st.success(f"✅ 图片已加载 ({st.session_state.uploaded_image.size[0]}×{st.session_state.uploaded_image.size[1]})")
    
    st.divider()
    brush_size = st.slider("🖊️ 画笔大小", min_value=10, max_value=80, value=30, step=5)
    
    st.divider()
    prompt = st.text_area("✨ 重绘指令", height=100, placeholder="描述你想要的效果：\n• 一朵红玫瑰\n• 蓝天白云")
    st.info("💡 使用简洁的描述词效果更好")
    
    generate_btn = st.button("🎨 开始重绘", type="primary", use_container_width=True, 
                             disabled=not st.session_state.uploaded_image or not prompt.strip())

with col_canvas:
    if st.session_state.uploaded_image:
        st.subheader("🎨 涂抹画布")
        
        # 将图片转为base64
        buffered = io.BytesIO()
        st.session_state.uploaded_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        w, h = st.session_state.uploaded_image.size
        
        # HTML Canvas组件
        canvas_html = f"""
        <div style="border: 2px solid #ddd; border-radius: 8px; padding: 10px; background: #f9f9f9;">
            <div style="margin-bottom: 10px; text-align: center;">
                <button onclick="clearCanvas()" style="padding: 8px 16px; margin: 5px; background: #ff4444; color: white; border: none; border-radius: 4px; cursor: pointer;">🗑️ 清除涂抹</button>
                <button onclick="exportMask()" style="padding: 8px 16px; margin: 5px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">💾 保存涂抹数据</button>
                <span id="status" style="margin-left: 10px; color: #666;">准备涂抹</span>
            </div>
            
            <div style="position: relative; display: inline-block; cursor: none;" id="canvasContainer">
                <canvas id="bgCanvas" width="{w}" height="{h}" style="position: absolute; top: 0; left: 0;"></canvas>
                <canvas id="drawCanvas" width="{w}" height="{h}" style="position: relative; cursor: none;"></canvas>
                <div id="cursor" style="position: absolute; width: {brush_size}px; height: {brush_size}px; border: 2px solid red; border-radius: 50%; pointer-events: none; display: none; background: rgba(255,0,0,0.2);"></div>
            </div>
            
            <div style="margin-top: 10px; padding: 10px; background: #e8f4f8; border-radius: 4px;">
                <div style="text-align: center; margin-bottom: 8px;">
                    <strong>📋 涂抹数据</strong> <span style="font-size: 12px; color: #666;">(保存后复制下方数据)</span>
                </div>
                <textarea id="maskOutput" style="width: 100%; height: 60px; font-size: 10px; border: 1px solid #ccc; border-radius: 4px; padding: 5px;" placeholder="涂抹数据将显示在这里，保存后全选复制"></textarea>
            </div>
        </div>
        
        <script>
            const bgCanvas = document.getElementById('bgCanvas');
            const drawCanvas = document.getElementById('drawCanvas');
            const bgCtx = bgCanvas.getContext('2d');
            const drawCtx = drawCanvas.getContext('2d');
            const cursor = document.getElementById('cursor');
            const status = document.getElementById('status');
            const container = document.getElementById('canvasContainer');
            
            // 加载背景图
            const img = new Image();
            img.onload = function() {{
                bgCtx.drawImage(img, 0, 0, {w}, {h});
            }};
            img.src = 'data:image/png;base64,{img_base64}';
            
            let isDrawing = false;
            let hasDrawn = false;
            
            drawCtx.strokeStyle = 'rgba(255, 0, 0, 0.7)';
            drawCtx.lineWidth = {brush_size};
            drawCtx.lineCap = 'round';
            drawCtx.lineJoin = 'round';
            
            function getPos(e) {{
                const rect = drawCanvas.getBoundingClientRect();
                const scaleX = drawCanvas.width / rect.width;
                const scaleY = drawCanvas.height / rect.height;
                if (e.touches) {{
                    return {{
                        x: (e.touches[0].clientX - rect.left) * scaleX,
                        y: (e.touches[0].clientY - rect.top) * scaleY
                    }};
                }}
                return {{
                    x: (e.clientX - rect.left) * scaleX,
                    y: (e.clientY - rect.top) * scaleY
                }};
            }}
            
            function updateCursor(e) {{
                const rect = container.getBoundingClientRect();
                let x, y;
                if (e.touches) {{
                    x = e.touches[0].clientX - rect.left;
                    y = e.touches[0].clientY - rect.top;
                }} else {{
                    x = e.clientX - rect.left;
                    y = e.clientY - rect.top;
                }}
                cursor.style.left = (x - {brush_size}/2) + 'px';
                cursor.style.top = (y - {brush_size}/2) + 'px';
            }}
            
            container.addEventListener('mouseenter', () => cursor.style.display = 'block');
            container.addEventListener('mouseleave', () => {{ cursor.style.display = 'none'; if(isDrawing) stopDraw(); }});
            container.addEventListener('mousemove', updateCursor);
            
            drawCanvas.addEventListener('mousedown', startDraw);
            drawCanvas.addEventListener('mousemove', draw);
            drawCanvas.addEventListener('mouseup', stopDraw);
            drawCanvas.addEventListener('touchstart', (e) => {{ e.preventDefault(); startDraw(e); }});
            drawCanvas.addEventListener('touchmove', (e) => {{ e.preventDefault(); draw(e); updateCursor(e); }});
            drawCanvas.addEventListener('touchend', stopDraw);
            
            function startDraw(e) {{
                isDrawing = true;
                const pos = getPos(e);
                drawCtx.beginPath();
                drawCtx.moveTo(pos.x, pos.y);
            }}
            
            function draw(e) {{
                if (!isDrawing) return;
                const pos = getPos(e);
                drawCtx.lineTo(pos.x, pos.y);
                drawCtx.stroke();
                drawCtx.beginPath();
                drawCtx.moveTo(pos.x, pos.y);
                hasDrawn = true;
                status.textContent = '已涂抹';
                status.style.color = '#4CAF50';
            }}
            
            function stopDraw() {{
                isDrawing = false;
            }}
            
            function clearCanvas() {{
                drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
                hasDrawn = false;
                status.textContent = '已清除';
                status.style.color = '#666';
                document.getElementById('maskOutput').value = '';
            }}
            
            function exportMask() {{
                if (!hasDrawn) {{
                    alert('请先在图片上涂抹');
                    return;
                }}
                
                // 创建mask
                const maskCanvas = document.createElement('canvas');
                maskCanvas.width = {w};
                maskCanvas.height = {h};
                const maskCtx = maskCanvas.getContext('2d');
                
                maskCtx.fillStyle = 'black';
                maskCtx.fillRect(0, 0, {w}, {h});
                
                // 获取涂抹数据
                const imageData = drawCtx.getImageData(0, 0, {w}, {h});
                const data = imageData.data;
                
                maskCtx.fillStyle = 'white';
                for (let y = 0; y < {h}; y++) {{
                    for (let x = 0; x < {w}; x++) {{
                        const i = (y * {w} + x) * 4;
                        if (data[i+3] > 0 || data[i] > 100) {{
                            maskCtx.fillRect(x, y, 1, 1);
                        }}
                    }}
                }}
                
                const maskData = maskCanvas.toDataURL('image/png');
                const outputArea = document.getElementById('maskOutput');
                outputArea.value = maskData;
                
                // 自动选中文本方便复制
                outputArea.select();
                outputArea.setSelectionRange(0, 99999);
                
                status.textContent = '✅ 已保存！请复制下方数据';
                status.style.color = '#4CAF50';
            }}
        </script>
        """
        
        components.html(canvas_html, height=h + 200)
        
        st.divider()
        
        # 操作说明
        st.info("📝 **操作步骤：** ① 在图片上涂抹红色区域 → ② 点击「保存涂抹数据」→ ③ 复制上方文本框中的数据 → ④ 使用下方工具确认数据")
        
        # 实用的解决方案：接受Streamlit的限制，优化用户体验
        st.write("📋 **涂抹数据输入**")
        
        if st.session_state.confirmed_mask_data:
            data_preview = st.session_state.confirmed_mask_data[:50] + "..." if len(st.session_state.confirmed_mask_data) > 50 else st.session_state.confirmed_mask_data
            st.success(f"✅ 已确认数据: {data_preview}")
            if st.button("🗑️ 清除数据"):
                st.session_state.confirmed_mask_data = ""
                st.session_state.mask_data = None
                st.session_state.pending_mask_input = ""  # 同时清空临时输入
                st.rerun()
        else:
            # 显示操作提示
            st.warning("⚠️ **重要提示：** 由于技术限制，粘贴长数据时可能会触发页面刷新导致数据丢失")
            
            with st.expander("💡 **推荐的操作方法**", expanded=True):
                st.write("""
                **方法1：快速粘贴法**
                1. 复制上方保存的涂抹数据
                2. 快速粘贴到下方输入框（一次性粘贴完整数据）
                3. 立即点击「确认数据」按钮
                
                **方法2：如果数据丢失**
                1. 重新涂抹并保存数据
                2. 尝试分批粘贴（先粘贴一半，确认后再粘贴剩余部分）
                
                **方法3：使用外部工具**
                1. 将数据保存到记事本
                2. 从记事本复制粘贴到输入框
                """)
            
            # 简单的输入框
            st.write("**粘贴涂抹数据：**")
            
            # 初始化持久化的输入数据
            if "pending_mask_input" not in st.session_state:
                st.session_state.pending_mask_input = ""
            
            # 使用 on_change 回调来立即保存数据，防止 rerun 时丢失
            def save_mask_input():
                """回调函数：在输入变化时立即保存到 session_state"""
                input_value = st.session_state.get("mask_input_widget", "")
                if input_value:
                    st.session_state.pending_mask_input = input_value
            
            # 使用固定的 key（不随 canvas_key 变化），并添加 on_change 回调
            mask_data_input = st.text_area(
                "将复制的涂抹数据粘贴到这里",
                value=st.session_state.pending_mask_input,  # 从 session_state 恢复数据
                height=120,
                placeholder="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                help="粘贴完成后立即点击下方确认按钮",
                key="mask_input_widget",  # 使用固定的 key
                on_change=save_mask_input  # 输入变化时立即保存
            )
            
            # 同步当前输入到 pending_mask_input
            if mask_data_input:
                st.session_state.pending_mask_input = mask_data_input
            
            # 显示数据状态
            if mask_data_input:
                data_length = len(mask_data_input.strip())
                if mask_data_input.startswith('data:image/png;base64,'):
                    if data_length > 1000:
                        st.success(f"✅ 数据格式正确 ({data_length} 字符)")
                        valid_data = True
                    else:
                        st.warning(f"⚠️ 数据可能不完整 ({data_length} 字符)")
                        valid_data = False
                else:
                    st.error("❌ 数据格式错误，应该以 'data:image/png;base64,' 开头")
                    valid_data = False
            else:
                valid_data = False
            
            # 确认按钮
            col_confirm, col_tips = st.columns([1, 2])
            
            with col_confirm:
                if st.button("✅ 确认数据", type="primary", disabled=not valid_data):
                    if mask_data_input and mask_data_input.startswith('data:image/png;base64,'):
                        st.session_state.confirmed_mask_data = mask_data_input.strip()
                        st.session_state.pending_mask_input = ""  # 清空临时输入
                        st.success("✅ 数据已保存！")
                        st.rerun()
                    else:
                        st.error("❌ 数据格式不正确")
            
            with col_tips:
                if mask_data_input:
                    st.info("👆 数据已输入，点击确认按钮保存")
                else:
                    st.info("💡 请先粘贴涂抹数据")
        
        # 处理mask数据
        has_drawing = False
        mask_image = None
        
        if st.session_state.confirmed_mask_data:
            try:
                base64_data = st.session_state.confirmed_mask_data.split(',')[1]
                mask_bytes = base64.b64decode(base64_data)
                mask_image = Image.open(io.BytesIO(mask_bytes)).convert('L')
                
                if mask_image.size != st.session_state.uploaded_image.size:
                    mask_image = mask_image.resize(st.session_state.uploaded_image.size, Image.Resampling.NEAREST)
                
                mask_array = np.array(mask_image)
                white_pixels = np.sum(mask_array > 128)
                
                if white_pixels > 50:
                    has_drawing = True
                    st.session_state.mask_data = mask_image
                    st.success(f"✅ 已识别涂抹区域 ({white_pixels} 像素)")
                else:
                    st.warning("⚠️ 涂抹区域太小，请涂抹更大的区域")
            except Exception as e:
                st.error(f"❌ 数据解析错误: {e}")
        
        # 显示涂抹区域预览
        if has_drawing and mask_image:
            with st.expander("🔍 查看涂抹区域预览", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.image(st.session_state.uploaded_image, caption="原图", use_column_width=True)
                with col2:
                    st.image(mask_image, caption="涂抹区域 (白色=重绘)", use_column_width=True)
        
        # 处理重绘
        if generate_btn:
            if not has_drawing:
                st.error("❌ 请先涂抹并确认涂抹数据")
            else:
                final_mask = mask_image if mask_image else st.session_state.mask_data
                
                if final_mask:
                    with st.status("🎨 正在AI重绘...", expanded=True) as status_widget:
                        try:
                            st.write("🎨 AI正在重绘涂抹区域...")
                            result_image = st.session_state.inpaint_service.inpaint(
                                original_image=st.session_state.uploaded_image,
                                mask_image=final_mask,
                                prompt=prompt
                            )
                            
                            if result_image:
                                status_widget.update(label="✅ 重绘完成！", state="complete")
                                st.subheader("🎨 重绘结果")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.image(st.session_state.uploaded_image, caption="原图", use_column_width=True)
                                with col2:
                                    st.image(result_image, caption="重绘结果", use_column_width=True)
                                
                                buf = io.BytesIO()
                                result_image.save(buf, format='PNG')
                                st.download_button("📥 下载结果", buf.getvalue(), "result.png", "image/png", use_container_width=True)
                            else:
                                st.error("❌ 重绘失败，请检查API配置或稍后重试")
                        except Exception as e:
                            st.error(f"❌ 错误: {e}")
                else:
                    st.error("❌ 未找到涂抹数据")
    else:
        st.subheader("📁 请上传图片")
        st.markdown('<div style="border: 2px dashed #ccc; padding: 60px; text-align: center; color: #666; border-radius: 10px;"><h3>🎨 Magic Canvas</h3><p>上传图片开始涂抹重绘</p></div>', unsafe_allow_html=True)
