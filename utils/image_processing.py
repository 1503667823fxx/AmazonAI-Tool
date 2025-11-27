import io
from PIL import Image
import streamlit as st

@st.cache_data(show_spinner=False, max_entries=50)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    """
    将图片字节流转换为下载所需的格式 (JPEG/PNG)。
    """
    try:
        if not image_bytes: return None, None
        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        target_format = format.upper()
        mime_type = f"image/{target_format.lower()}"

        if target_format == "JPEG":
            # JPEG 不支持透明通道，需转换为 RGB
            if image.mode in ("RGBA", "P"): 
                image = image.convert("RGB")
            image.save(buf, format="JPEG", quality=quality, optimize=True)
        elif target_format == "PNG":
            image.save(buf, format="PNG")
            
        return buf.getvalue(), mime_type
    except Exception as e:
        print(f"Image Processing Error: {e}")
        return image_bytes, "image/png"

@st.cache_data(show_spinner=False)
def create_preview_thumbnail(image_bytes, max_width=800):
    """
    生成用于 UI 展示的缩略图，减少内存占用。
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        if image.mode in ("RGBA", "P"): 
            image = image.convert("RGB")
        image.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except:
        return image_bytes
