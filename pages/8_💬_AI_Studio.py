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
    page_title="Amazon AI Studio Enhanced", 
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
        # Initialize and render the enhanced UI
        ui_controller.render_main_interface()
        
    except Exception as e:
        st.error(f"❌ Application Error: {e}")
        
        # Fallback to basic interface
        st.warning("Falling back to basic interface...")
        render_fallback_interface()


def render_fallback_interface():
    """Fallback interface in case of errors with enhanced components"""
    
    st.title("🧪 AI Studio (Basic Mode)")
    st.info("Enhanced features are temporarily unavailable. Using basic interface.")
    
    # Basic model selection
    model_options = {
        "Gemini Flash": "models/gemini-flash-latest",
        "Gemini Pro": "models/gemini-3-pro-preview"
    }
    
    selected_model = st.selectbox("Select Model", list(model_options.keys()), key="fallback_model_selector")
    
    # Basic chat input
    user_input = st.chat_input("Enter your message...")
    
    if user_input:
        st.chat_message("user").write(user_input)
        st.chat_message("assistant").write("Enhanced AI Studio is currently unavailable. Please try again later.")


# --- Application Entry Point ---
if __name__ == "__main__":
    main()
else:
    # When imported as a module, run main
    main()
