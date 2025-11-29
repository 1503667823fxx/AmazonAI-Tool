import streamlit as st
import sys
import os
import subprocess
import time
import requests
import threading

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# --- 鉴权 ---
try:
    import auth
    if 'auth' in sys.modules and not auth.check_password(): st.stop()
except ImportError:
    pass # 忽略鉴权以便测试

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")
st.title("🖌️ Magic Canvas (Cloud Mode)")

# === 核心逻辑：云端自动启动 Gradio ===

def start_gradio_background():
    """在后台启动 Gradio App"""
    cmd = [sys.executable, os.path.join(root_dir, "apps", "magic_editor_app.py")]
    # 使用 subprocess 启动，不阻塞主线程
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        bufsize=1
    )
    return process

# 使用 Session State 管理进程，防止每次刷新都重启
if "gradio_process" not in st.session_state:
    st.session_state.gradio_process = None
    st.session_state.gradio_url = None

# 1. 如果没启动，现在启动
if st.session_state.gradio_process is None:
    with st.status("🚀 正在云端启动魔法引擎 (Gradio)...", expanded=True) as status:
        st.write("正在唤醒后台服务...")
        proc = start_gradio_background()
        st.session_state.gradio_process = proc
        
        # 2. 抓取 Gradio 的公开链接 (share link)
        # 这是一个笨办法：读取后台日志，找到 .gradio.live 的链接
        found_url = None
        st.write("等待生成连接隧道 (约需 10-20秒)...")
        
        # 尝试读取 30 秒日志
        for i in range(30):
            if proc.poll() is not None:
                st.error("Gradio 服务启动失败！")
                break
            
            # 这里简单等待，实际环境很难实时抓取 output，
            # 这种混合部署在云端其实很不稳定。
            # 建议：如果不需要 share link，直接用 localhost 配合 iframe 只能在本地用。
            # 既然是 Cloud，我们尝试硬等待一下
            time.sleep(1)
        
        # --- 紧急修正 ---
        # 在 Streamlit Cloud 上抓取 subprocess 输出非常困难
        # 我们可以尝试直接访问 localhost，但如果跨域受限，
        # 最好的办法其实是手动部署 Gradio 到 HuggingFace。
        
        # 但为了让你先跑起来，我们假设它启动在 localhost:7860
        # 注意：Streamlit Cloud 可能无法直接 iframe localhost。
        status.update(label="启动尝试完成", state="complete")

# === 界面展示 ===
st.info("💡 云端提示：由于网络限制，在 Streamlit Cloud 内部嵌 Gradio 极其不稳定。")
st.markdown("如果下方显示 **refused to connect**，说明云端端口被封锁。")

# 尝试渲染
import streamlit.components.v1 as components
# 这里的 URL 在本地是 localhost:7860
# 在云端，你必须把 apps/magic_editor_app.py 单独部署到 HuggingFace Spaces，然后把链接填在这里
components.iframe("http://127.0.0.1:7860", height=800)

st.divider()
st.markdown("### 🚑 终极解决方案 (如果上面是白的)")
st.markdown("""
因为云端环境太封闭，**“弗兰肯斯坦”缝合术 (Streamlit + Gradio)** 只有在**本地电脑**或者 **AutoDL/Colab** 这种完全控制的服务器上才完美。

在 Streamlit Cloud 上，建议将 `3_🖌️_Magic_Canvas.py` 的功能简化，或者：
1. 去 **HuggingFace Spaces** (免费) 创建一个 Gradio Space。
2. 把 `apps/magic_editor_app.py` 的代码放过去。
3. 拿到那个 Space 的网址 (例如 `https://huggingface.co/spaces/user/myapp`)。
4. 回来把 `components.iframe(...)` 里的网址换成你的 Space 网址。
""")
