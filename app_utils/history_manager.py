import streamlit as st
import time
from collections import deque
from app_utils.image_processing import create_preview_thumbnail, process_image_for_download
# 也可以在这里引入 show_preview_modal，或者在 UI 层处理

class HistoryManager:
    """
    管理 Session State 中的历史生成记录。
    """
    def __init__(self, key="history_queue", max_len=20):
        self.key = key
        if self.key not in st.session_state:
            st.session_state[self.key] = deque(maxlen=max_len)

    def add(self, image_bytes, source_name, prompt_summary):
        """
        添加一条新记录到队首。
        """
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
        """获取所有历史记录"""
        return list(st.session_state[self.key])

    def render_sidebar_ui(self, show_modal_callback=None):
        """
        直接在 Sidebar 渲染 UI。
        Args:
            show_modal_callback: 一个回调函数，用于在点击放大镜时显示模态框
        """
        with st.expander("🕒 历史记录 (History)", expanded=False):
            items = self.get_all()
            if not items:
                st.caption("暂无生成记录")
                return

            for item in items:
                col_thumb, col_info = st.columns([1, 2])
                
                with col_thumb:
                    thumb = create_preview_thumbnail(item['image'], max_width=150)
                    st.image(thumb, use_container_width=True)
                
                with col_info:
                    st.caption(f"**{item['source']}** ({item['time']})")
                    desc_preview = (item['desc'][:15] + '...') if len(item['desc']) > 15 else item['desc']
                    st.caption(f"_{desc_preview}_")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        # 放大按钮
                        if st.button("🔍", key=f"h_zoom_{item['id']}"):
                            if show_modal_callback:
                                show_modal_callback(item['image'], item['source'])
                    with b2:
                        # 下载按钮
                        final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                        st.download_button(
                            "📥", 
                            data=final_bytes, 
                            file_name=f"hist_{item['id']}.jpg", 
                            mime
