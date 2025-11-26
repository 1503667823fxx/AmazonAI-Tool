import google.generativeai as genai
import streamlit as st

class AITranslator:
    """
    专门负责项目中英互译的轻量级 AI 模块。
    使用 gemini-1.5-flash 实现毫秒级响应。
    """
    def __init__(self):
        # 尝试从 secrets 获取 key，如果没有则无法初始化
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.model = genai.GenerativeModel("models/gemini-1.5-flash")
            self.valid = True
        else:
            self.valid = False

    def to_chinese(self, text):
        """将英文翻译成中文"""
        if not text or not self.valid: return text
        return self._run_translation(text, "Simplified Chinese")

    def to_english(self, text):
        """将中文翻译成英文"""
        if not text or not self.valid: return text
        return self._run_translation(text, "English")

    def _run_translation(self, text, target_lang):
        try:
            # 强约束 Prompt，防止 AI 废话，只返回翻译结果
            prompt = f"""
            Role: Professional Translator.
            Task: Translate the following text into {target_lang}.
            Constraint: Output ONLY the translated text. Do not add explanations. Do not use markdown blocks.
            
            Text:
            {text}
            """
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return text # 如果失败，返回原文，避免报错
