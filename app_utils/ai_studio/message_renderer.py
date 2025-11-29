import streamlit as st
from app_utils.image_processing import process_image_for_download # 复用通用图片处理

def show_image_modal(image_bytes, title="Preview"):
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

def render_studio_message(idx, msg, on_delete, on_regen):
    """渲染单条消息"""
    with st.chat_message(msg["role"]):
        # 1. 引用图片
        if msg.get("ref_images"):
            cols = st.columns(min(len(msg["ref_images"]), 4))
            for i, img in enumerate(msg["ref_images"]):
                with cols[i]:
                    st.image(img, use_container_width=True)

        # 2. 内容区
        if msg.get("type") == "image_result":
            # === 图片结果 ===
            key_pfx = f"msg_{msg['id']}"
            st.image(msg["content"], width=400)
            
            c1, c2, c3 = st.columns([1, 1, 3])
            with c1:
                if st.button("🔍", key=f"{key_pfx}_zoom"):
                    show_image_modal(msg["hd_data"], f"Result-{msg['id']}")
            with c2:
                final_bytes, mime = process_image_for_download(msg["hd_data"], format="JPEG")
                st.download_button("📥", data=final_bytes, file_name=f"gen_{msg['id']}.jpg", mime=mime, key=f"{key_pfx}_dl")
            with c3:
                if st.button("🗑️", key=f"{key_pfx}_del"): on_delete(idx)
        
        else:
            # === 文本结果 ===
            key_pfx = f"msg_{msg['id']}"
            st.markdown(msg["content"])
            
            # 操作栏
            ac1, ac2 = st.columns([1, 8])
            with ac1:
                if st.button("🗑️", key=f"{key_pfx}_del_t"): on_delete(idx)
            with ac2:
                if msg["role"] == "model" and on_regen:
                    if st.button("🔄 Regen", key=f"{key_pfx}_rg"): on_regen(idx)
