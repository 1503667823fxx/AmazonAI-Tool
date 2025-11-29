import streamlit as st
import sys
import os

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from app_utils.magic_canvas.iframe_manager import render_gradio_app, check_server_status
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

# --- 鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# --- 主界面 ---
st.title("🖌️ Magic Canvas")
st.caption("基于 SAM (Segment Anything) 的智能重绘工作台。")

# 检查 Gradio 是否在运行
gradio_url = "http://127.0.0.1:7860"
is_running = check_server_status(gradio_url)

if not is_running:
    st.warning("⚠️ 编辑器服务未启动")
    st.code("python apps/magic_editor_app.py", language="bash")
    st.info("请在终端运行上述命令启动后台编辑器，然后刷新本页面。")
else:
    st.success("✅ 编辑器服务已连接")
    # 渲染 Iframe
    render_gradio_app(url=gradio_url, height=900)
