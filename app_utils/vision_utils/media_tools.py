import io
from PIL import Image
import streamlit as st

# 从原 image_processing.py 复制并简化
@st.cache_data(show_spinner=False)
def create_thumbnail(image_bytes, max_width=400):
    """生成小图用于预览"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)))
        
        buf = io.BytesIO()
        if img.mode != "RGB": img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except: return image_bytes

def prepare_download(image_bytes):
    """准备下载数据"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=95)
        return buf.getvalue(), "image/jpeg"
    except: return None, None
