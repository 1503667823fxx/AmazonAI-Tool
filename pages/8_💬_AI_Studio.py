import streamlit as st
from PIL import Image
import sys
import os

# --- Path Environment Setup ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path: 
    sys.path.append(root_dir)

try:
    import auth
    # Import enhanced AI Studio components
    from app_utils.ai_studio.ui_controller import ui_controller
    from app_utils.ai_studio.enhanced_state_manager import state_manager
    from app_utils.ai_studio.design_tokens import inject_modern_styles
    
    # Legacy imports for backward compatibility
    from services.ai_studio.vision_service import StudioVisionService
    from services.ai_studio.chat_service import StudioChatService
    
except ImportError as e:
    st.error(f"❌ Module Import Error: {e}")
    st.stop()

# --- Page Configuration ---
st.set_page_config(
    page_title="亚马逊 AI 工作室", 
    page_icon="🧪", 
    layout="wide"
)

# --- Authentication Check ---
if 'auth' in sys.modules and not auth.check_password(): 
    st.stop()

# --- Main Application ---
def main():
    """Main application entry point using enhanced architecture"""
    
    try:
        # Inject custom CSS for better UI
        st.markdown("""
        <style>
        /* 减小侧边栏字体大小 */
        .css-1d391kg {
            font-size: 0.85rem;
        }
        
        /* 减小标题大小 */
        .css-10trblm {
            font-size: 1.1rem;
        }
        
        /* 减小子标题大小 */
        .css-1629p8f h2 {
            font-size: 1rem;
        }
        
        /* 减小metric组件的字体 */
        [data-testid="metric-container"] {
            font-size: 0.8rem;
        }
        
        /* 改善侧边栏间距 */
        .css-1d391kg .element-container {
            margin-bottom: 0.5rem;
        }
        
        /* 减小selectbox的高度 */
        .stSelectbox > div > div {
            min-height: 2rem;
        }
        
        /* 减小text_area的默认高度 */
        .stTextArea textarea {
            min-height: 80px !important;
        }
        
        /* 改善按钮样式 */
        .stButton > button {
            font-size: 0.8rem;
            padding: 0.25rem 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Initialize and render the enhanced UI
        ui_controller.render_main_interface()
        
    except Exception as e:
        st.error(f"❌ Application Error: {e}")
        
        # Fallback to basic interface
        st.warning("Falling back to basic interface...")
        render_fallback_interface()


def render_fallback_interface():
    """Fallback interface in case of errors with enhanced components"""
    
    st.title("🧪 AI 工作室 (基础模式)")
    st.info("增强功能暂时不可用。正在使用基础界面。")
    
    # Basic model selection
    model_options = {
        "Gemini Flash": "models/gemini-flash-latest",
        "Gemini Pro": "models/gemini-3-pro-preview"
    }
    
    selected_model = st.selectbox("选择模型", list(model_options.keys()), key="fallback_model_selector")
    
    # Basic chat input
    user_input = st.chat_input("输入您的消息...")
    
    if user_input:
        st.chat_message("user").write(user_input)
        st.chat_message("assistant").write("增强版 AI 工作室当前不可用。请稍后重试。")


# --- Application Entry Point ---
if __name__ == "__main__":
    main()
else:
    # When imported as a module, run main
    main()
