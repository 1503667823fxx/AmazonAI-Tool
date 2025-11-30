import streamlit as st

def init_visual_studio_state():
    """
    初始化 Visual Studio 模块所需的 Session State 变量。
    防止页面刷新或首次加载时出现 KeyError。
    """
    # 1. 保存优化后的提示词
    if 'vs_final_prompt' not in st.session_state:
        st.session_state['vs_final_prompt'] = ""

    # 2. 保存当前生成的图片 URL
    if 'vs_current_image' not in st.session_state:
        st.session_state['vs_current_image'] = None

    # 3. (可选) 保存历史记录列表，用于后续做历史回溯功能
    if 'vs_history' not in st.session_state:
        st.session_state['vs_history'] = []

def save_to_history(prompt: str, image_url: str):
    """
    将生成的图片和提示词保存到历史记录中。
    """
    record = {
        "prompt": prompt,
        "image_url": image_url,
        "timestamp": st.session_state.get('vs_timestamp', 'N/A') # 可结合 datetime
    }
    st.session_state['vs_history'].append(record)
