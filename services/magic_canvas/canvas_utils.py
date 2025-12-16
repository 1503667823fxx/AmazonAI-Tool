import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw
import base64
import io
import json
import numpy as np

def create_drawing_canvas(image, brush_size=20):
    """
    创建一个真正能检测涂抹的HTML Canvas绘图组件
    """
    st.info("💡 在图片上涂抹想要修改的区域，涂抹完成后点击'获取涂抹区域'按钮")
    return create_real_canvas(image, brush_size)

def create_real_canvas(image, brush_size=20):
    """
    真正能检测涂抹的HTML Canvas绘图组件
    """
    # 将图像转换为base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_data_url = f"data:image/png;base64,{img_base64}"
    
    # 创建唯一的canvas ID
    canvas_id = f"magic_canvas_{hash(str(image.size) + str(brush_size))}"
    
    canvas_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
            .canvas-container {{ 
                position: relative;
                display: inline-block;
                border: 2px solid #ddd; 
                border-radius: 8px; 
                overflow: hidden;
                background: #f9f9f9;
            }}
            .background-layer {{
                position: absolute;
                top: 0;
                left: 0;
                background-image: url('{img_data_url}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                width: {image.width}px;
                height: {image.height}px;
            }}
            #drawingCanvas {{ 
                position: relative;
                display: block; 
                cursor: none;  /* 隐藏默认指针，使用自定义圆形指针 */
                background: transparent;
            }}
            .canvas-wrapper {{
                position: relative;
                display: inline-block;
            }}
            .brush-cursor {{
                position: absolute;
                border: 2px solid #ff0000;
                border-radius: 50%;
                pointer-events: none;
                background: rgba(255, 0, 0, 0.1);
                z-index: 1000;
                display: none;
                transform: translate(-50%, -50%);
            }}
            .controls {{
                text-align: center;
                padding: 10px;
                background: #f0f0f0;
                border-bottom: 1px solid #ddd;
            }}
            button {{
                padding: 6px 12px;
                margin: 0 5px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }}
            .clear {{ background: #ff4444; color: white; }}
            .save {{ background: #44aa44; color: white; }}
            .info {{ 
                padding: 8px; 
                background: #e8f4f8; 
                font-size: 12px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="canvas-container">
            <div class="controls">
                <button class="clear" onclick="clearCanvas()">🗑️ 清除</button>
                <button class="save" onclick="saveMask()">💾 保存涂抹</button>
                <span>画笔: {brush_size}px | </span>
                <span id="status">准备绘制</span>
            </div>
            <div class="canvas-wrapper">
                <div class="background-layer"></div>
                <canvas id="drawingCanvas" width="{image.width}" height="{image.height}"></canvas>
                <div id="brushCursor" class="brush-cursor" style="width: {brush_size}px; height: {brush_size}px;"></div>
            </div>
            <div class="info">在图片上涂抹想要修改的区域，然后点击"保存涂抹"按钮</div>
        </div>

        <script>
            const canvas = document.getElementById('drawingCanvas');
            const ctx = canvas.getContext('2d');
            const status = document.getElementById('status');
            const brushCursor = document.getElementById('brushCursor');
            
            let isDrawing = false;
            let hasDrawn = false;
            let strokes = [];
            let currentStroke = [];
            
            // 画笔设置
            ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
            ctx.lineWidth = {brush_size};
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            // 事件监听
            canvas.addEventListener('mousedown', startDraw);
            canvas.addEventListener('mousemove', handleMouseMove);
            canvas.addEventListener('mouseup', stopDraw);
            canvas.addEventListener('mouseleave', hideCursor);
            canvas.addEventListener('mouseenter', showCursor);
            
            // 触摸支持
            canvas.addEventListener('touchstart', handleTouch, {{passive: false}});
            canvas.addEventListener('touchmove', handleTouch, {{passive: false}});
            canvas.addEventListener('touchend', stopDraw);
            
            function getPos(e) {{
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                
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
            
            function startDraw(e) {{
                isDrawing = true;
                const pos = getPos(e);
                ctx.beginPath();
                ctx.moveTo(pos.x, pos.y);
                currentStroke = [{{x: pos.x, y: pos.y}}];
                status.textContent = '绘制中...';
            }}
            
            function handleMouseMove(e) {{
                const pos = getPos(e);
                updateCursor(pos.x, pos.y);
                
                if (isDrawing) {{
                    ctx.lineTo(pos.x, pos.y);
                    ctx.stroke();
                    currentStroke.push({{x: pos.x, y: pos.y}});
                    hasDrawn = true;
                }}
            }}
            
            function updateCursor(x, y) {{
                const rect = canvas.getBoundingClientRect();
                const wrapper = canvas.parentElement;
                const wrapperRect = wrapper.getBoundingClientRect();
                
                // 计算鼠标在canvas上的相对位置
                const scaleX = rect.width / canvas.width;
                const scaleY = rect.height / canvas.height;
                
                const cursorX = x * scaleX;
                const cursorY = y * scaleY;
                
                brushCursor.style.left = cursorX + 'px';
                brushCursor.style.top = cursorY + 'px';
            }}
            
            function showCursor() {{
                brushCursor.style.display = 'block';
            }}
            
            function hideCursor() {{
                brushCursor.style.display = 'none';
                if (isDrawing) {{
                    stopDraw();
                }}
            }}
            
            function stopDraw() {{
                if (isDrawing) {{
                    isDrawing = false;
                    if (currentStroke.length > 0) {{
                        strokes.push([...currentStroke]);
                        currentStroke = [];
                    }}
                    if (hasDrawn) {{
                        status.textContent = '已涂抹 - 请点击"保存涂抹"按钮';
                    }}
                }}
            }}
            
            function handleTouch(e) {{
                e.preventDefault();
                const touch = e.touches[0];
                const mouseEvent = new MouseEvent(
                    e.type === 'touchstart' ? 'mousedown' : 'mousemove',
                    {{ clientX: touch.clientX, clientY: touch.clientY }}
                );
                canvas.dispatchEvent(mouseEvent);
            }}
            
            function clearCanvas() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                strokes = [];
                currentStroke = [];
                hasDrawn = false;
                status.textContent = '已清除';
                
                // 清除localStorage数据
                localStorage.removeItem('magic_canvas_mask');
                localStorage.removeItem('magic_canvas_has_drawing');
                localStorage.removeItem('magic_canvas_timestamp');
                
                // 触发清除事件
                window.dispatchEvent(new Event('canvas_cleared'));
            }}
            
            function saveMask() {{
                if (!hasDrawn) {{
                    status.textContent = '请先涂抹一些区域';
                    return;
                }}
                
                const maskData = createMaskFromStrokes();
                
                // 将mask数据保存到localStorage，供Streamlit读取
                localStorage.setItem('magic_canvas_mask', maskData);
                localStorage.setItem('magic_canvas_has_drawing', 'true');
                localStorage.setItem('magic_canvas_timestamp', Date.now().toString());
                
                status.textContent = '✅ 涂抹区域已保存到本地存储';
                
                // 触发页面刷新事件
                window.dispatchEvent(new Event('canvas_mask_saved'));
            }}
            
            function createMaskFromStrokes() {{
                // 创建mask canvas
                const maskCanvas = document.createElement('canvas');
                maskCanvas.width = canvas.width;
                maskCanvas.height = canvas.height;
                const maskCtx = maskCanvas.getContext('2d');
                
                // 黑色背景
                maskCtx.fillStyle = 'black';
                maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
                
                // 白色笔画
                maskCtx.strokeStyle = 'white';
                maskCtx.lineWidth = {brush_size};
                maskCtx.lineCap = 'round';
                maskCtx.lineJoin = 'round';
                maskCtx.fillStyle = 'white';
                
                // 绘制所有笔画
                strokes.forEach(stroke => {{
                    if (stroke.length > 1) {{
                        maskCtx.beginPath();
                        maskCtx.moveTo(stroke[0].x, stroke[0].y);
                        for (let i = 1; i < stroke.length; i++) {{
                            maskCtx.lineTo(stroke[i].x, stroke[i].y);
                        }}
                        maskCtx.stroke();
                    }} else if (stroke.length === 1) {{
                        // 单点
                        maskCtx.beginPath();
                        maskCtx.arc(stroke[0].x, stroke[0].y, {brush_size}/2, 0, 2 * Math.PI);
                        maskCtx.fill();
                    }}
                }});
                
                return maskCanvas.toDataURL('image/png');
            }}
            
            // 简化的函数
            window.hasDrawnContent = function() {{
                return hasDrawn;
            }};
            
            window.clearDrawing = function() {{
                clearCanvas();
            }};
        </script>
    </body>
    </html>
    """
    
    # 渲染组件
    components.html(canvas_html, height=image.height + 120)
    
    # 返回一个包含localStorage检查功能的对象
    class CanvasResult:
        def __init__(self):
            self.canvas_id = canvas_id
    
    return CanvasResult()

def create_simple_canvas(image, brush_size=20):
    """保留原来的简单canvas作为备用"""
    return create_real_canvas(image, brush_size)


