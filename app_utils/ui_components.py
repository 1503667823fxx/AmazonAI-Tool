import streamlit as st
from app_utils.image_processing import create_preview_thumbnail, process_image_for_download

def inject_chat_css():
    """注入聊天界面的 CSS 样式"""
    st.markdown("""
    <style>
        /* 底部留白，防止输入框遮挡 */
        .block-container { padding-bottom: 120px !important; }
        
        /* 悬浮附件按钮 - 右下角 */
        .stApp [data-testid="stPopover"] {
            position: fixed !important;
            bottom: 90px !important;
            right: 40px !important;
            z-index: 999;
        }
        .stApp [data-testid="stPopover"] button {
            border-radius: 50% !important;
            width: 50px !important;
            height: 50px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
        }
        
        /* 消息操作栏 */
        .msg-actions { opacity: 0.4; transition: opacity 0.2s; font-size: 0.8rem; margin-top: 5px; }
        .stChatMessage:hover .msg-actions { opacity: 1; }
    </style>
    """, unsafe_allow_html=True)

def show_image_modal(image_bytes, title="Preview"):
    """通用弹窗组件"""
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

def render_chat_message(idx, msg, on_delete, on_regen=None):
    """
    渲染单条聊天消息
    :param idx: 消息索引
    :param msg: 消息对象
    :param on_delete: 删除回调函数
    :param on_regen: 重生成回调函数 (仅 Model 有效)
    """
    with st.chat_message(msg["role"]):
        # 1. 如果有引用图片（用户发送的），先展示
        if msg.get("ref_images"):
            cols = st.columns(min(len(msg["ref_images"]), 4))
            for i, img in enumerate(msg["ref_images"]):
                with cols[i]:
                    st.image(img, use_container_width=True)

        # 2. 内容展示区
        if msg["type"] == "image_result":
            # === 图片结果展示 ===
            # 创建一个唯一的key前缀，防止组件ID冲突
            key_pfx = f"msg_{msg['id']}"
            
            st.image(msg["content"], width=400)
            
            # 图片操作栏
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
            # === 文本/对话展示 ===
            key_pfx = f"msg_{msg['id']}"
            st.markdown(msg["content"])
            
            # 文本操作栏 (悬停显示)
            st.markdown('<div class="msg-actions">', unsafe_allow_html=True)
            ac1, ac2 = st.columns([1, 6])
            with ac1:
                if st.button("🗑️", key=f"{key_pfx}_del_t"): on_delete(idx)
            with ac2:
                if msg["role"] == "model" and on_regen:
                    if st.button("🔄 Regen", key=f"{key_pfx}_rg"): on_regen(idx)
            st.markdown('</div>', unsafe_allow_html=True)

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
