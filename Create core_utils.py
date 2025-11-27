import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# 🛠️ 图片处理核心 (Image Engine)
# ==========================================

@st.cache_data(show_spinner=False, max_entries=50)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    """
    核心加速函数：
    1. 接收原始图片字节流
    2. 转换格式 (PNG/JPEG)
    3. 缓存结果 (下次点击下载直接从内存读取，无需重新转换)
    """
    try:
        # 如果源数据为空，直接返回
        if not image_bytes:
            return None, None

        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        
        target_format = format.upper()
        mime_type = f"image/{target_format.lower()}"

        # JPEG 优化逻辑
        if target_format == "JPEG":
            # JPEG 不支持透明通道，必须转 RGB
            if image.mode in ("RGBA", "P"): 
                image = image.convert("RGB")
            # 使用优化保存模式
            image.save(buf, format="JPEG", quality=quality, optimize=True)
        
        # PNG 优化逻辑
        elif target_format == "PNG":
            # PNG 压缩级别 (默认即可)
            image.save(buf, format="PNG")
        
        return buf.getvalue(), mime_type

    except Exception as e:
        print(f"Image processing error: {e}")
        # 降级处理：如果转换失败，返回原图和默认 MIME
        return image_bytes, "image/png"

@st.cache_data(show_spinner=False)
def create_preview_thumbnail(image_bytes, max_width=800):
    """
    生成极速预览图：
    将大图压缩为小尺寸 JPEG，用于页面快速展示，不占用带宽。
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # 只有当图片宽度大于 max_width 时才缩小，否则保持原样
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        if image.mode in ("RGBA", "P"): 
            image = image.convert("RGB")
        
        # 预览图用较低质量即可 (70)，换取极速加载
        image.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except:
        return image_bytes

# ==========================================
# 🗣️ 翻译核心 (Translation Engine)
# ==========================================

class AITranslator:
    def __init__(self):
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.model = genai.GenerativeModel("models/gemini-flash-latest")
            self.valid = True
        else:
            self.valid = False

    def to_chinese(self, text):
        if not text or not self.valid: return text
        return self._run(text, "Simplified Chinese")

    def to_english(self, text):
        if not text or not self.valid: return text
        return self._run(text, "English")

    def _run(self, text, lang):
        try:
            prompt = f"Translate to {lang}. Output ONLY the translation. Text: {text}"
            resp = self.model.generate_content(prompt)
            return resp.text.strip()
        except:
            return text
