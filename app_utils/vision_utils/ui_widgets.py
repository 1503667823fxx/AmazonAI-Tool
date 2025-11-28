import streamlit as st
from app_utils.vision_utils.media_tools import create_thumbnail, prepare_download

def render_vision_sidebar(history_manager):
    """
    [Smart Edit 专属] 侧边栏历史记录组件
    """
    with st.sidebar: # 或者传入 container
        st.title("🗂️ 视觉历史")
        items = history_manager.get_all()
        
        if not items:
            st.caption("暂无记录")
            return

        # 清空按钮
        if st.button("🗑️ 清空记录", use_container_width=True):
            history_manager.clear()
            st.rerun()

        for item in items:
            with st.container(border=True):
                col_img, col_btn = st.columns([1, 1])
                with col_img:
                    thumb = create_thumbnail(item['image'], 150)
                    st.image(thumb, use_container_width=True)
                with col_btn:
                    st.caption(f"{item['time']}")
                    # 下载逻辑
                    dl_data, mime = prepare_download(item['image'])
                    if dl_data:
                        st.download_button("📥", dl_data, f"{item['id']}.jpg", mime=mime, key=f"dl_{item['id']}")
