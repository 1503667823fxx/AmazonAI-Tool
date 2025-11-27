import streamlit as st
from app_utils.image_processing import create_preview_thumbnail, process_image_for_download

def show_image_modal(image_bytes, title="Preview"):
    """通用弹窗组件"""
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

def render_history_sidebar(history_manager):
    """
    侧边栏组件：升级版 (带删除功能)
    """
    with st.expander("🕒 历史记录 (History)", expanded=False):
        items = history_manager.get_all()
        
        # 1. 顶部操作栏
        if items:
            if st.button("🗑️ 清空所有记录", key="clear_all_hist", use_container_width=True):
                history_manager.clear()
                st.rerun()

        # 2. 列表渲染
        if not items:
            st.caption("暂无生成记录")
            return

        for item in items:
            # 使用 container 稍微美化一下
            with st.container(border=True):
                col_thumb, col_info = st.columns([1, 2])
                
                with col_thumb:
                    thumb = create_preview_thumbnail(item['image'], max_width=150)
                    st.image(thumb, use_container_width=True)
                
                with col_info:
                    st.caption(f"**{item['source']}**")
                    st.caption(f"🕒 {item['time']}")
                    
                    # 按钮行：放大 | 下载 | 删除
                    b1, b2, b3 = st.columns([1, 1, 1])
                    
                    with b1:
                        if st.button("🔍", key=f"zoom_{item['id']}", help="预览"):
                            show_image_modal(item['image'], item['source'])
                    
                    with b2:
                        final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                        st.download_button(
                            "📥", 
                            data=final_bytes, 
                            file_name=f"hist_{item['id']}.jpg", 
                            mime=mime, 
                            key=f"dl_{item['id']}",
                            help="下载"
                        )
                    
                    with b3:
                        if st.button("🗑️", key=f"del_{item['id']}", help="删除此条"):
                            history_manager.delete(item['id'])
                            st.rerun()
            
            # 显示简短描述 (放在卡片外面或里面皆可)
            st.caption(f"📝 {item['desc'][:30]}...")
