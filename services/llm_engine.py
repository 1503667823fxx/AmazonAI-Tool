import streamlit as st
import google.generativeai as genai
import os

# 尝试导入预设，如果失败则使用空字典防报错
try:
    from services.styles import PRESETS
except ImportError:
    PRESETS = {"💡 默认 (None)": {"desc": "high quality, photorealistic, 8k"}}

class LLMEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.valid = True
        else:
            self.valid = False

    def _get_model(self, model_type="reasoning"):
        """内部路由：根据任务类型获取模型"""
        if model_type == "reasoning":
            return genai.GenerativeModel("models/gemini-3-pro-preview")
        elif model_type == "fast":
            return genai.GenerativeModel("models/gemini-flash-latest")
        return genai.GenerativeModel("models/gemini-flash-lite-latest")

    # --- 基础工具 ---
    def translate(self, text, target_lang="English"):
        if not text or not self.valid: return text
        try:
            model = self._get_model("fast")
            prompt = f"Translate the following text to {target_lang}. Return ONLY the translation, no extra text.\nText: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    # --- V6 核心优化：解决换人/多主体问题 ---
    def optimize_art_director_prompt(self, user_idea, task_type, weight, style_key, image_input=None, enable_split=False):
        if not self.valid: return []

        style_data = PRESETS.get(style_key, PRESETS.get("💡 默认 (None)"))
        style_desc = style_data["desc"] if style_data else "high quality"

        inputs = []
        inputs.append(image_input if image_input else "No reference image provided.")
        
        system_prompt = f"""
        You are an expert AI Art Director.
        【User Request】: "{user_idea}"
        【Style Preset】: "{style_desc}"

        【STEP 1: ANALYZE SUBJECT COUNT & TYPE】
        1. **Multiple Subjects?** If user asks for "two models", "couple", "group":
           - You MUST start prompt with composition: "A medium shot of TWO models..."
           - You MUST invent DISTINCT looks (e.g., "Model on left is [Trait A], Model on right is [Trait B]").
           - Explicitly state: "Both models are wearing [Clothing from Ref Image]."
        
        2. **Identity Swap?** If user asks to "change model/person":
           - IGNORE the face in the reference image.
           - INVENT specific physical traits (e.g., "Caucasian, blonde hair" or "Asian, short black hair") to override the image signal.
        
        【STEP 2: PRESERVE PRODUCT】
        - Keep the clothing/product details from the Reference Image exactly as they are.

        【Output】
        Write a single, continuous English prompt.
        """
        inputs.append(system_prompt)

        try:
            model = self._get_model("reasoning")
            config = genai.types.GenerationConfig(temperature=0.45, candidate_count=1)
            response = model.generate_content(inputs, generation_config=config)
            return [response.text.strip()]
        except Exception as e:
            print(f"LLM Error: {e}")
            return [f"{user_idea}, {style_desc}, high quality"]

    # --- 对话框支持 (Chat Studio) ---
    def get_chat_model(self, model_name, system_instruction=None):
        """获取聊天模型实例"""
        if not self.valid: return None
        
        # 宽容的安全设置，防止正常对话被拦截
        safety = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }
        
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            safety_settings=safety
        )

    def chat_stream(self, chat_session, user_input, image_input=None):
        """流式对话生成器"""
        if not self.valid: 
            yield "❌ API Key 无效"
            return

        content = []
        if user_input: content.append(user_input)
        if image_input: content.append(image_input)
        
        if not content: return

        try:
            response = chat_session.send_message(content, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"
