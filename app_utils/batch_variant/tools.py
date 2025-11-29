import streamlit as st
import io
import time
from PIL import Image
from collections import deque

# ================= 1. 图像处理工具 =================

@st.cache_data(show_spinner=False, max_entries=50)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    """将图片字节流转换为下载所需的格式"""
    try:
        if not image_bytes: return None, None
        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        target_format = format.upper()
        mime_type = f"image/{target_format.lower()}"

        if target_format == "JPEG":
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
    """生成缩略图"""
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

# ================= 2. 弹窗组件 =================
def show_image_modal(image_bytes, title="Preview"):
    """通用弹窗组件"""
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

# ================= 3. 历史记录管理 =================

class BatchHistoryManager:
    """[Batch Variant 专属] 历史记录管理器"""
    def __init__(self, key="batch_variant_history", max_len=50): # 批量模式增加容量
        self.key = key
        if self.key not in st.session_state:
            st.session_state[self.key] = deque(maxlen=max_len)

    def add(self, image_bytes, source_name, prompt_summary):
        timestamp = time.strftime("%H:%M")
        unique_id = f"{int(time.time()*1000)}"
        
        st.session_state[self.key].appendleft({
            "id": unique_id,
            "image": image_bytes,
            "source": source_name,
            "time": timestamp,
            "desc": prompt_summary
        })

    def get_all(self):
        return list(st.session_state[self.key])

    def delete(self, item_id):
        current_list = list(st.session_state[self.key])
        new_list = [item for item in current_list if item['id'] != item_id]
        st.session_state[self.key] = deque(new_list, maxlen=st.session_state[self.key].maxlen)

    def clear(self):
        st.session_state[self.key].clear()

# ================= 4. 侧边栏 UI =================

def render_history_sidebar(history_manager):
    """[Batch Variant 专属] 侧边栏渲染"""
    with st.expander("🕒 历史记录 (History)", expanded=False):
        items = history_manager.get_all()
        
        if items:
            if st.button("🗑️ 清空所有记录", key="bv_clear_all", use_container_width=True):
                history_manager.clear()
                st.rerun()

        if not items:
            st.caption("暂无生成记录")
            return

        for item in items:
            with st.container(border=True):
                col_thumb, col_info = st.columns([1, 2])
                
                with col_thumb:
                    thumb = create_preview_thumbnail(item['image'], max_width=150)
                    st.image(thumb, use_container_width=True)
                
                with col_info:
                    st.caption(f"**{item['source']}**")
                    st.caption(f"🕒 {item['time']}")
                    
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("🔍", key=f"bv_zoom_{item['id']}", help="预览"):
                            show_image_modal(item['image'], item['source'])
                    with b2:
                        final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                        st.download_button("📥", data=final_bytes, file_name=f"hist_{item['id']}.jpg", mime=mime, key=f"bv_dl_{item['id']}")
                    with b3:
                        if st.button("🗑️", key=f"bv_del_{item['id']}", help="删除"):
                            history_manager.delete(item['id'])
                            st.rerun()
