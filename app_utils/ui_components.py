import streamlit as st
from app_utils.image_processing import create_preview_thumbnail, process_image_for_download

def show_image_modal(image_bytes, title="Preview"):
    """
    通用弹窗组件：用于预览大图
    """
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

def render_history_sidebar(history_manager):
    """
    侧边栏组件：专门负责渲染历史记录列表
    Args:
        history_manager: 传入数据管理器实例，用于获取数据
    """
    with st.expander("🕒 历史记录 (History)", expanded=False):
        # 从管理器获取纯数据
        items = history_manager.get_all()
        
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
                # 截取简短描述
                desc_preview = (item['desc'][:15] + '...') if len(item['desc']) > 15 else item['desc']
                st.caption(f"_{desc_preview}_")
                
                b1, b2 = st.columns(2)
                with b1:
                    # 点击放大镜 -> 调用上面的弹窗组件
                    if st.button("🔍", key=f"h_zoom_{item['id']}"):
                        show_image_modal(item['image'], item['source'])
                with b2:
                    # 下载按钮
                    final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                    st.download_button(
                        "📥", 
                        data=final_bytes, 
                        file_name=f"hist_{item['id']}.jpg", 
                        mime=mime, 
                        key=f"h_dl_{item['id']}"
                    )
            st.divider()
