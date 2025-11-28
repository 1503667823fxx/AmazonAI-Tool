import streamlit as st
import google.generativeai as genai
import os

class BaseService:
    """
    所有服务模块的基类。
    负责统一处理 API Key 鉴权和客户端初始化。
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
        
    def get_model(self, model_name="models/gemini-1.5-flash"):
        """获取一个基础模型实例 (供翻译等简单任务使用)"""
        if not self.is_valid: return None
        return genai.GenerativeModel(model_name)
