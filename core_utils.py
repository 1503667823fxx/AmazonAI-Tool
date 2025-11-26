import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import time
from collections import deque

# ==========================================
# 🗂️ 历史记录核心 (History Manager)
# ==========================================
class HistoryManager:
    """
    专门负责管理、渲染侧边栏历史记录的组件。
    支持：预览、放大、下载、自动缩略图。
    """
    def __init__(self):
        # 初始化队列，最大保留 20 条
        if "history_queue" not in st.session_state:
            st.session_state["history_queue"] = deque(maxlen=20)

    def add(self, image_bytes, source, prompt_summary):
        """添加一条新记录"""
        timestamp = time.strftime("%H:%M")
        # 生成唯一 ID (用于控件 key)
        unique_id = f"{int(time.time()*1000)}"
        
        # 存入队列
        st.session_state["history_queue"].appendleft({
            "id": unique_id,
            "image": image_bytes,
            "source": source,
            "time": timestamp,
            "desc": prompt_summary
        })

    def render_sidebar(self):
        """在侧边栏渲染历史记录列表"""
        with st.expander("🕒 历史记录 (History)", expanded=False):
            if not st.session_state["history_queue"]:
                st.caption("暂无生成记录")
                return

            # 遍历显示
            for item in st.session_state["history_queue"]:
                col_thumb, col_info = st.columns([1, 2])
                
                with col_thumb:
                    # 生成极速缩略图
                    thumb = create_preview_thumbnail(item['image'], max_width=150)
                    st.image(thumb, use_container_width=True)
                
                with col_info:
                    st.caption(f"**{item['source']}** ({item['time']})")
                    # 简略描述
                    st.caption(f"_{item['desc'][:15]}..._")
                    
                    # 功能区：放大 & 下载
                    b1, b2 = st.columns(2)
                    with b1:
                        # 放大预览按钮
                        if st.button("🔍", key=f"h_zoom_{item['id']}", help="放大预览"):
                            show_preview_modal(item['image'], f"{item['source']} - {item['time']}")
                    with b2:
                        # 下载按钮
                        final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                        st.download_button("📥", data=final_bytes, file_name=f"history_{item['id']}.jpg", mime=mime, key=f"h_dl_{item['id']}")
                
                st.divider()
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
