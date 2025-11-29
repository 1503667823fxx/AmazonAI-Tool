# ... 前面的 import 和 setup 代码不变 ...



# 🔴 关键修改：填入你 Hugging Face Space 的地址
# 注意：要在链接末尾加上 /?__theme=light 这样嵌入进去好看点
GRADIO_URL = "https://www.modelscope.cn/studios/veredis/magic-editor/summary/?__theme=light" 

# 判断是否是云端嵌入链接
if "huggingface.co" in GRADIO_URL:
    # 使用 components.iframe 嵌入
    # scrolling=True 很重要，否则操作不了
    import streamlit.components.v1 as components
    components.iframe(GRADIO_URL, height=900, scrolling=True)

else:
    # 以前的本地逻辑 (留着备用)
    from app_utils.magic_canvas.iframe_manager import render_gradio_app, check_server_status
    if check_server_status("http://127.0.0.1:7860"):
        render_gradio_app("http://127.0.0.1:7860", height=900)
    else:

