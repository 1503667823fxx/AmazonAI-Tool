# app_utils/hd_upscale/download_handler.py
import streamlit as st
import requests
from io import BytesIO
from PIL import Image

# 使用 Streamlit 的缓存装饰器
# show_spinner=False 防止在后台静默处理时界面乱跳
# ttl=3600 缓存保留1小时，避免内存撑爆
@st.cache_data(show_spinner=False, ttl=3600)
def fast_convert_and_cache(image_url):
    """
    高速下载并转换处理模块。
    被 @st.cache_data 标记后，对同一个 URL，此函数只会运行一次。
    后续调用会直接从内存返回数据，实现'零延迟'下载。
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
        
        # 处理透明通道 (RGBA -> RGB)，防止转 JPEG 报错
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # 4. 转码为 JPEG
        output_buffer = BytesIO()
        # quality=95 是体积和画质的最佳平衡点，比 100 快很多，肉眼看不出区别
        img.save(output_buffer, format="JPEG", quality=95)
        
        return output_buffer.getvalue()

    except Exception as e:
        # 打印后台日志用于调试，但不打断前台
        print(f"Download Handler Error: {e}")
        return None
