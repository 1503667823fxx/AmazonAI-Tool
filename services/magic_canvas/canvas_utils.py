import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw
import base64
import io
import json

def create_drawing_canvas(image, brush_size=20, canvas_key="drawing_canvas"):
    """
    创建一个基于streamlit-drawable-canvas的绘图组件
    能够真正捕获用户的涂抹数据
    """
    try:
        from streamlit_drawable_canvas import st_canvas
        
        # 创建画布
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",  # 半透明红色填充
            stroke_width=brush_size,
            stroke_color="rgba(255, 0, 0, 0.8)",  # 红色描边
            background_image=image,
            update_streamlit=True,
            height=image.height,
            width=image.width,
            drawing_mode="freedraw",
            point_display_radius=0,
            key=canvas_key,
        )
        
        return canvas_result
        
    except ImportError:
        st.error("❌ 缺少 streamlit-drawable-canvas 依赖")
        st.info("请运行: pip install streamlit-drawable-canvas")
        
        # 降级到简单的HTML Canvas
        return create_simple_canvas(image, brush_size)

def create_simple_canvas(image, brush_size=20):
    """
    简化版HTML Canvas，用于降级处理
    """
    # 将图像转换为base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_data_url = f"data:image/png;base64,{img_base64}"
    
    # 创建一个唯一的组件ID
    component_id = f"canvas_{hash(str(image.size))}"
    
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
                cursor: crosshair;
                background: transparent;
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
            <div style="position: relative;">
                <div class="background-layer"></div>
                <canvas id="drawingCanvas" width="{image.width}" height="{image.height}"></canvas>
            </div>
            <div class="info">在图片上涂抹想要修改的区域，然后点击"保存涂抹"</div>
        </div>

        <script>
            const canvas = document.getElementById('drawingCanvas');
            const ctx = canvas.getContext('2d');
            const status = document.getElementById('status');
            
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
                currentStroke = [{{x: pos.x, y: pos.y}}];
                status.textContent = '绘制中...';
            }}
            
            function draw(e) {{
                if (!isDrawing) return;
                const pos = getPos(e);
                ctx.lineTo(pos.x, pos.y);
                ctx.stroke();
                currentStroke.push({{x: pos.x, y: pos.y}});
                hasDrawn = true;
            }}
            
            function stopDraw() {{
                if (isDrawing) {{
                    isDrawing = false;
                    if (currentStroke.length > 0) {{
                        strokes.push([...currentStroke]);
                        currentStroke = [];
                    }}
                    if (hasDrawn) {{
                        status.textContent = '已涂抹区域 - 请点击"保存涂抹"';
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
                // 通知Streamlit清除数据
                window.parent.postMessage({{
                    type: 'canvas_cleared',
                    data: null
                }}, '*');
            }}
            
            function saveMask() {{
                if (!hasDrawn) {{
                    status.textContent = '请先涂抹一些区域';
                    return;
                }}
                
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
                
                // 获取mask数据
                const maskDataUrl = maskCanvas.toDataURL('image/png');
                
                // 发送数据到Streamlit
                window.parent.postMessage({{
                    type: 'mask_saved',
                    data: {{
                        mask: maskDataUrl,
                        strokes: strokes,
                        hasContent: hasDrawn
                    }}
                }}, '*');
                
                status.textContent = '✅ 涂抹区域已保存';
            }}
            
            // 全局函数供外部调用
            window.hasDrawnContent = function() {{
                return hasDrawn;
            }};
            
            window.getMaskData = function() {{
                if (!hasDrawn) return null;
                saveMask();
                return true;
            }};
        </script>
    </body>
    </html>
    """
    
    # 渲染组件
    result = components.html(canvas_html, height=image.height + 120)
    
    return result

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

def canvas_data_to_mask(canvas_data, image_size):
    """
    将streamlit-drawable-canvas的数据转换为mask
    """
    if canvas_data is None or canvas_data.image_data is None:
        return None
    
    # 获取canvas数据
    canvas_array = np.array(canvas_data.image_data)
    
    # 检查是否有绘制内容（非透明像素）
    if len(canvas_array.shape) == 3 and canvas_array.shape[2] >= 4:
        alpha_channel = canvas_array[:, :, 3]
        
        # 创建二值mask
        mask_array = (alpha_channel > 0).astype(np.uint8) * 255
        
        # 转换为PIL图像
        mask_image = Image.fromarray(mask_array, mode='L')
        
        # 确保尺寸匹配
        if mask_image.size != image_size:
            mask_image = mask_image.resize(image_size, Image.Resampling.NEAREST)
        
        return mask_image
    
    return None

def validate_mask(mask_image, min_area=100):
    """
    验证mask是否有效
    """
    if mask_image is None:
        return False, "没有检测到涂抹区域"
    
    # 计算mask面积
    mask_array = np.array(mask_image)
    white_pixels = np.sum(mask_array > 128)
    
    if white_pixels < min_area:
        return False, f"涂抹区域太小（{white_pixels}像素），请涂抹更大的区域"
    
    total_pixels = mask_array.size
    if white_pixels > total_pixels * 0.8:
        return False, "涂抹区域过大，请涂抹较小的局部区域"
    
    return True, f"涂抹区域有效（{white_pixels}像素）"
