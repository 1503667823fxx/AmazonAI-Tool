import streamlit as st

def inject_studio_css():
    """注入 AI Studio 专属样式"""
    st.markdown("""
    <style>
        /* 1. 调整底部内边距 */
        .block-container {
            padding-bottom: 120px !important;
        }

        /* 2. 强力定位上传按钮 (Popover) */
        div[data-testid="stPopover"] {
            position: fixed !important;
            bottom: 75px !important; 
            left: 30px !important;   
            z-index: 2147483647 !important;
            width: 45px !important;
            height: 45px !important;
        }

        /* 3. 按钮样式美化 */
        div[data-testid="stPopover"] > div > button {
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            background-color: white !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            border: 1px solid #eee !important;
            color: #444 !important;
            font-size: 1.2rem !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        div[data-testid="stPopover"] > div > button:hover {
            transform: scale(1.1);
            color: #000 !important;
            border-color: #ccc !important;
        }

        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
