import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw
import base64
import io
import json

def create_drawing_canvas(image, brush_size=20, canvas_key="drawing_canvas"):
    """
    创建一个基于HTML5 Canvas的绘图组件
    返回用户的绘制数据
    """
    
    # 将图像转换为base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_data_url = f"data:image/png;base64,{img_base64}"
    
    # HTML和JavaScript代码
    canvas_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
            #canvas-container {{ 
                position: relative; 
                display: inline-block; 
                border: 2px solid #ddd; 
                border-radius: 8px; 
                overflow: hidden;
                background: #f9f9f9;
            }}
            #drawing-canvas {{ 
                display: block; 
                cursor: crosshair;
                background-image: url('{img_data_url}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
            }}
            .controls {{
                margin: 10px 0;
                text-align: center;
            }}
            button {{
                padding: 8px 16px;
                margin: 0 5px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }}
            .clear-btn {{ background: #ff4444; color: white; }}
            .undo-btn {{ background: #4444ff; color: white; }}
            .status {{ 
                margin: 10px 0; 
                padding: 8px; 
                background: #e8f4f8; 
                border-radius: 4px; 
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="controls">
            <button class="undo-btn" onclick="undoLastStroke()">↶ 撤销</button>
            <button class="clear-btn" onclick="clearCanvas()">🗑️ 清除</button>
            <span style="margin-left: 20px;">画笔大小: {brush_size}px</span>
        </div>
        
        <div id="canvas-container">
            <canvas id="drawing-canvas" width="{image.width}" height="{image.height}"></canvas>
        </div>
        
        <div class="status" id="status">
            准备就绪 - 在图片上涂抹想要修改的区域
        </div>

        <script>
            const canvas = document.getElementById('drawing-canvas');
            const ctx = canvas.getContext('2d');
            const status = document.getElementById('status');
            
            let isDrawing = false;
            let strokes = [];
            let currentStroke = [];
            let strokeHistory = [];
            
            // 设置画笔样式
            ctx.strokeStyle = 'rgba(255, 50, 50, 0.7)';
            ctx.lineWidth = {brush_size};
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            // 鼠标事件
            canvas.addEventListener('mousedown', startDrawing);
            canvas.addEventListener('mousemove', draw);
            canvas.addEventListener('mouseup', stopDrawing);
            canvas.addEventListener('mouseleave', stopDrawing);
            
            // 触摸事件支持
            canvas.addEventListener('touchstart', handleTouch, {{ passive: false }});
            canvas.addEventListener('touchmove', handleTouch, {{ passive: false }});
            canvas.addEventListener('touchend', stopDrawing);
            
            function getEventPos(e) {{
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                
                if (e.touches) {{
                    return {{
                        x: (e.touches[0].clientX - rect.left) * scaleX,
                        y: (e.touches[0].clientY - rect.top) * scaleY
                    }};
                }} else {{
                    return {{
                        x: (e.clientX - rect.left) * scaleX,
                        y: (e.clientY - rect.top) * scaleY
                    }};
                }}
            }}
            
            function startDrawing(e) {{
                isDrawing = true;
                currentStroke = [];
                const pos = getEventPos(e);
                currentStroke.push(pos);
                
                ctx.beginPath();
                ctx.moveTo(pos.x, pos.y);
                
                status.textContent = '正在绘制...';
            }}
            
            function draw(e) {{
                if (!isDrawing) return;
                
                const pos = getEventPos(e);
                currentStroke.push(pos);
                
                ctx.lineTo(pos.x, pos.y);
                ctx.stroke();
            }}
            
            function stopDrawing() {{
                if (isDrawing && currentStroke.length > 0) {{
                    strokes.push([...currentStroke]);
                    strokeHistory.push([...strokes]);
                    sendDataToStreamlit();
                    status.textContent = `已绘制 ${{strokes.length}} 个笔画`;
                }}
                isDrawing = false;
                currentStroke = [];
            }}
            
            function handleTouch(e) {{
                e.preventDefault();
                const touch = e.touches[0];
                const mouseEvent = new MouseEvent(
                    e.type === 'touchstart' ? 'mousedown' : 
                    e.type === 'touchmove' ? 'mousemove' : 'mouseup',
                    {{
                        clientX: touch.clientX,
                        clientY: touch.clientY
                    }}
                );
                canvas.dispatchEvent(mouseEvent);
            }}
            
            function clearCanvas() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                strokes = [];
                strokeHistory = [];
                sendDataToStreamlit();
                status.textContent = '画布已清除';
            }}
            
            function undoLastStroke() {{
                if (strokes.length > 0) {{
                    strokes.pop();
                    redrawCanvas();
                    sendDataToStreamlit();
                    status.textContent = `撤销成功，剩余 ${{strokes.length}} 个笔画`;
                }}
            }}
            
            function redrawCanvas() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                strokes.forEach(stroke => {{
                    if (stroke.length > 0) {{
                        ctx.beginPath();
                        ctx.moveTo(stroke[0].x, stroke[0].y);
                        stroke.forEach(point => {{
                            ctx.lineTo(point.x, point.y);
                        }});
                        ctx.stroke();
                    }}
                }});
            }}
            
            function sendDataToStreamlit() {{
                const data = {{
                    type: 'canvas_strokes',
                    strokes: strokes,
                    stroke_count: strokes.length
                }};
                
                // 发送数据给Streamlit
                window.parent.postMessage(JSON.stringify(data), '*');
            }}
            
            // 初始化
            status.textContent = '准备就绪 - 在图片上涂抹想要修改的区域';
        </script>
    </body>
    </html>
    """
    
    # 渲染组件并获取返回数据
    component_value = components.html(
        canvas_html, 
        height=image.height + 120,  # 额外空间给控制按钮
        key=canvas_key
    )
    
    return component_value

def strokes_to_mask(strokes, image_size, brush_size):
    """
    将笔画数据转换为PIL mask图像
    """
    mask = Image.new('L', image_size, 0)  # 黑色背景
    draw = ImageDraw.Draw(mask)
    
    for stroke in strokes:
        if len(stroke) > 1:
            # 绘制连续线条
            points = [(point['x'], point['y']) for point in stroke]
            for i in range(len(points) - 1):
                draw.line([points[i], points[i + 1]], fill=255, width=brush_size)
        elif len(stroke) == 1:
            # 单点
            x, y = stroke[0]['x'], stroke[0]['y']
            r = brush_size // 2
            draw.ellipse([x-r, y-r, x+r, y+r], fill=255)
    
    return mask
