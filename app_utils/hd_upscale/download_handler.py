# app_utils/hd_upscale/download_handler.py
import streamlit as st
import requests
from io import BytesIO
from PIL import Image

# 使用 Streamlit 的缓存装饰器
# show_spinner=False 防止在后台静默处理时界面乱跳
# ttl=3600 缓存保留1小时，避免内存撑爆
@st.cache_data(show_spinner=False, ttl=3600)
def fast_convert_and_cache(image_url, output_format="JPEG", preserve_structure=False):
    """
    高速下载并转换处理模块。
    被 @st.cache_data 标记后，对同一个 URL，此函数只会运行一次。
    后续调用会直接从内存返回数据，实现'零延迟'下载。
    
    :param output_format: 输出格式 "JPEG" 或 "PNG"
    :param preserve_structure: 是否保护结构细节
    """
    try:
        # 1. 容错处理：确保 URL 是字符串
        if isinstance(image_url, list):
            target_url = image_url[0]
        else:
            target_url = image_url
            
        # 2. 从云端 (Replicate) 拉取图片
        # stream=True 优化大文件下载
        response = requests.get(target_url, stream=True, timeout=60)
        response.raise_for_status()
        
        # 3. 内存转换 (不存硬盘，速度最快)
        img = Image.open(BytesIO(response.content))
        
        # 4. 根据输出格式处理
        output_buffer = BytesIO()
        
        if output_format == "PNG":
            # PNG无损格式，保持最佳细节
            img.save(output_buffer, format="PNG", optimize=True)
        else:
            # JPEG格式处理
            # 处理透明通道 (RGBA -> RGB)，防止转 JPEG 报错
            if img.mode in ("RGBA", "P"):
                # 使用白色背景而不是黑色，保持更好的视觉效果
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            
            # 根据是否保护结构调整质量
            quality = 98 if preserve_structure else 95
            img.save(output_buffer, format="JPEG", quality=quality, optimize=True)
        
        return output_buffer.getvalue()

    except Exception as e:
        # 打印后台日志用于调试，但不打断前台
        print(f"Download Handler Error: {e}")
        return None
