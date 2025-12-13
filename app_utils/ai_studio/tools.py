import streamlit as st
from PIL import Image
import io


@st.cache_data(show_spinner=False, max_entries=50)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    """将图片字节流转换为下载所需的格式"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode == "RGBA" and format == "JPEG":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        
        output = io.BytesIO()
        img.save(output, format=format, quality=quality)
        return output.getvalue(), f"image/{format.lower()}"
    except Exception as e:
        st.error(f"图片处理失败: {e}")
        return image_bytes, "application/octet-stream"


@st.cache_data(show_spinner=False)
def create_preview_thumbnail(image_bytes, max_width=800):
    """生成缩略图"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception as e:
        st.error(f"缩略图生成失败: {e}")
        return image_bytes
