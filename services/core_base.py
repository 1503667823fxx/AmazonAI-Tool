import streamlit as st
import google.generativeai as genai

class BaseService:
    """
    所有服务的基类，负责处理 API Key 和基础连接。
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        self.is_valid = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.is_valid = True
            except Exception as e:
                print(f"Auth Error: {e}")
