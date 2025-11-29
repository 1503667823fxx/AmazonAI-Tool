import streamlit as st
import streamlit.components.v1 as components

def render_gradio_app(url="http://127.0.0.1:7860", height=800):
    """
    嵌入 Gradio 应用
    """
    st.markdown(f"""
        <style>
        iframe {{
            border: 1px solid #eee;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        </style>
    """, unsafe_allow_html=True)
    
    try:
        components.iframe(url, height=height, scrolling=True)
    except Exception as e:
        st.error(f"无法加载 Magic Canvas 编辑器: {e}")
        st.info("💡 请确保您已在后台运行了 Gradio 服务: `python apps/magic_editor_app.py`")

def check_server_status(url="http://127.0.0.1:7860"):
    """
    (可选) 检查后台服务是否存活
    """
    try:
        import requests
        response = requests.get(url, timeout=1)
        return response.status_code == 200
    except:
        return False
