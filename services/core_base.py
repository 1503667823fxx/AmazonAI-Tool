import streamlit as st
import google.generativeai as genai

class CoreBase:
    """
    所有专属 Service 的基类。
    只负责一件事：初始化 Google API Key。
    """
    def __init__(self):
        self.api_key = st.secrets.get("GOOGLE_API_KEY")
        self.valid = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.valid = True
            except Exception as e:
                print(f"API Config Error: {e}")
