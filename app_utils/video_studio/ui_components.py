import streamlit as st

def setup_page_config():
    """页面基础配置"""
    st.set_page_config(
        page_title="Amazon Video Studio",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 注入自定义 CSS 以优化视频工作台体验
    st.markdown("""
        <style>
        .stTextArea textarea {
            font-size: 16px !important;
            line-height: 1.5;
        }
        .stTab {
            font-weight: 600;
        }
        /* 进度条样式优化 */
        .stProgress > div > div > div > div {
            background-color: #FF9900;
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    """侧边栏配置区"""
    with st.sidebar:
        st.header("⚙️ 工作室设置")
        
        st.subheader("🔑 模型配置")
        api_key = st.text_input("OpenAI/Claude API Key", type="password")
        video_model = st.selectbox("视频模型引擎", ["Runway Gen-2 (模拟)", "Pika Labs (模拟)", "Stable Video (模拟)"])
        
        st.divider()
        
        st.subheader("🎨 风格预设")
        style = st.selectbox("视频风格", ["Amazon 极简风", "TikTok甚至快节奏", "高端奢华风", "生活方式(Lifestyle)"])
        aspect_ratio = st.radio("画幅比例", ["16:9 (横屏)", "9:16 (竖屏/Shorts)"], index=0)
        
        st.info("💡 提示：竖屏视频适合 TikTok 和 Amazon Inspire。")
        
        return {
            "api_key": api_key,
            "video_model": video_model,
            "style": style,
            "aspect_ratio": aspect_ratio
        }

def render_step_indicator(current_step):
    """可视化的步骤指示器"""
    steps = ["1. 编写剧本", "2. 生成素材", "3. 剪辑合成"]
    # 简单的文本进度条，也可以做成更复杂的图形
    st.markdown(f"**当前阶段:** {' » '.join([f'`{s}`' if i == current_step else s for i, s in enumerate(steps)])}")
    st.divider()
