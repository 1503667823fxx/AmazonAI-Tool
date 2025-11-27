import streamlit as st
import google.generativeai as genai
from services.styles import PRESETS

class LLMEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.valid = True
        else:
            self.valid = False
            
    def translate(self, text, target_lang="English"):
        if not text or not self.valid: return text
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            prompt = f"Translate to {target_lang}. Output ONLY translation. Text: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def analyze_image_style(self, image, prompt_instruction):
        # 此函数保留备用
        if not self.valid: return "Error"
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e: return str(e)

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, style_key, image_input=None, enable_split=False):
        """
        CoT 核心逻辑 (V3 听话版)：
        1. 移除冗余描述。
        2. 强制优先响应用户指令。
        """
        if not self.valid: return []

        # 1. 获取风格数据
        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]
        style_light = style_data["lighting"]

        # 2. 处理图片输入
        images = []
        img_instruction = ""
        if image_input:
            if isinstance(image_input, list):
                images = image_input
                img_instruction = f"【Visual Context】: {len(images)} reference images provided. Use them for Composition and Lighting reference ONLY."
            else:
                images = [image_input]
                img_instruction = "【Visual Context】: 1 reference image provided. Use it for Composition/Lighting reference ONLY."

        # 3. 构建强指令 Prompt (针对痛点优化)
        cot_instructions = f"""
        Role: Expert Prompt Engineer for Google Imagen.
        
        【Input Data】
        - User Intent: "{user_idea}"
        - Style Preset: "{style_key}" ({style_desc})
        - Reference Image: Provided.
        
        【CRITICAL RULES】
        1. **USER IS KING**: If User Intent conflicts with the Reference Image (e.g., image shows a man, user says "female model"), **OBEY THE USER**. Ignore the image content for the subject.
        2. **NO CAPTIONING**: Do NOT describe the reference image content unless the user asks to "keep original". The image will be passed to the generation model directly ("img2img"), so we don't need to describe it in words.
        3. **FOCUS ON QUALITY**: Your job is to ADD quality boosters (e.g., "8k, commercial lighting, {style_light}") and Style keywords.
        4. **KEEP IT CONCISE**: Output clean, keyword-rich prompts.
        
        【Output Requirement】
        - Output English Prompts ONLY.
        - If {enable_split} is True, split distinct variations with "|||".
        - Just the raw prompt string.
        """

        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            inputs = [cot_instructions] + images
            response = model.generate_content(inputs)
            raw_text = response.text.strip()
            
            raw_text = raw_text.replace("Prompt:", "").replace("Here is the prompt:", "").strip()
            prompts = [p.strip() for p in raw_text.split("|||") if p.strip()]
            
            # 兜底：如果AI没生成，至少把用户的话传回去
            if not prompts: return [user_idea]
            return prompts
            
        except Exception as e:
            print(f"CoT Error: {e}")
            return [f"{user_idea}, {style_desc}"]
