"""
Magic Canvas 画布工具
"""

import streamlit as st
from PIL import Image, ImageDraw
import numpy as np


def create_drawing_canvas(image, brush_size=20):
    """
    创建涂抹画布（使用streamlit-drawable-canvas）
    """
    try:
        from streamlit_drawable_canvas import st_canvas
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.4)",
            stroke_width=brush_size,
            stroke_color="rgba(255, 0, 0, 0.8)",
            background_image=image,
            update_streamlit=True,
            height=image.height,
            width=image.width,
            drawing_mode="freedraw",
            key="magic_canvas",
        )
        
        return canvas_result
        
    except ImportError:
        st.error("❌ 请安装 streamlit-drawable-canvas: pip install streamlit-drawable-canvas")
        return None


def extract_mask_from_canvas(canvas_result, image_size):
    """
    从canvas结果中提取mask
    """
    if canvas_result is None or canvas_result.image_data is None:
        return None
    
    canvas_array = np.array(canvas_result.image_data)
    
    if len(canvas_array.shape) != 3:
        return None
    
    # 检查alpha通道或红色通道
    if canvas_array.shape[2] >= 4:
        alpha_channel = canvas_array[:, :, 3]
        mask_array = (alpha_channel > 0).astype(np.uint8) * 255
    else:
        red_channel = canvas_array[:, :, 0]
        mask_array = (red_channel > 100).astype(np.uint8) * 255
    
    # 检查是否有涂抹内容
    if np.sum(mask_array > 0) < 50:
        return None
    
    mask_image = Image.fromarray(mask_array, mode='L')
    
    # 确保尺寸匹配
    if mask_image.size != image_size:
        mask_image = mask_image.resize(image_size, Image.Resampling.NEAREST)
    
    return mask_image
