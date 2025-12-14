import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw
import base64
import io
import json

def create_drawing_canvas(image, brush_size=20):
    """
    创建一个基于HTML5 Canvas的绘图组件
    使用更简单的方式处理用户绘制
    """
    
    # 将图像转换为base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_data_url = f"data:image/png;base64,{img_base64}"
    
    # 简化的HTML Canvas实现
    canvas_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 10px; font-family: Arial, sans-serif; }}
            .canvas-wrapper {{ 
                border: 2px solid #ddd; 
                border-radius: 8px; 
                overflow: hidden;
                display: inline-block;
                background: #f9f9f9;
            }}
            #canvas {{ 
                display: block; 
                cursor: crosshair;
                background-image: url('{img_data_url}');
                background-size: cover;
                background-repeat: no-repeat;
                background-position: center;
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
            .info {{ 
                padding: 8px; 
                background: #e8f4f8; 
                font-size: 12px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="canvas-wrapper">
            <div class="controls">
                <button class="clear" onclick="clearCanvas()">🗑️ 清除</button>
                <span>画笔: {brush_size}px | </span>
                <span id="status">准备绘制</span>
            </div>
            <canvas id="canvas" width="{image.width}" height="{image.height}"></canvas>
            <div class="info">在图片上涂抹想要修改的区域</div>
        </div>

        <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            const status = document.getElementById('status');
            
            let isDrawing = false;
            let hasDrawn = false;
            
            // 画笔设置
            ctx.strokeStyle = 'rgba(255, 0, 0, 0.6)';
            ctx.lineWidth = {brush_size};
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            // 事件监听
            canvas.addEventListener('mousedown', startDraw);
            canvas.addEventListener('mousemove', draw);
            canvas.addEventListener('mouseup', stopDraw);
            canvas.addEventListener('mouseleave', stopDraw);
            
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
                status.textContent = '绘制中...';
            }}
            
            function draw(e) {{
                if (!isDrawing) return;
                const pos = getPos(e);
                ctx.lineTo(pos.x, pos.y);
                ctx.stroke();
                hasDrawn = true;
            }}
            
            function stopDraw() {{
                if (isDrawing) {{
                    isDrawing = false;
                    if (hasDrawn) {{
                        status.textContent = '已涂抹区域';
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
                hasDrawn = false;
                status.textContent = '已清除';
            }}
            
            // 全局函数供外部调用
            window.hasDrawnContent = function() {{
                return hasDrawn;
            }};
            
            window.getCanvasImageData = function() {{
                return canvas.toDataURL('image/png');
            }};
        </script>
    </body>
    </html>
    """
    
    # 渲染组件
    components.html(canvas_html, height=image.height + 100)
    
    # 返回简单的状态指示
    return True

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
