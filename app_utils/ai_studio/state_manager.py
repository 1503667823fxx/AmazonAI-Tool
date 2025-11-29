import streamlit as st
from services.ai_studio.vision_service import StudioVisionService

def init_session_state():
    if "studio_msgs" not in st.session_state: 
        st.session_state.studio_msgs = []
    
    if "msg_uid" not in st.session_state: 
        st.session_state.msg_uid = 0
        
    if "uploader_key_id" not in st.session_state: 
        st.session_state.uploader_key_id = 0
        
    if "system_prompt_val" not in st.session_state: 
        st.session_state.system_prompt_val = "You are a helpful AI assistant for Amazon E-commerce sellers."
        
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if "studio_vision_svc" not in st.session_state:
        st.session_state.studio_vision_svc = StudioVisionService(api_key)

def clear_history():
    st.session_state.studio_msgs = []
    st.session_state.uploader_key_id += 1
    st.rerun()

def undo_last_turn():
    if st.session_state.studio_msgs:
        st.session_state.studio_msgs.pop()
        if st.session_state.studio_msgs and st.session_state.studio_msgs[-1]["role"] == "user":
            st.session_state.studio_msgs.pop()
        st.rerun()
