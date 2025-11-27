import streamlit as st
import google.generativeai as genai
# 👇 引入风格库
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
        if not self.valid: return "Error: API Key missing"
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e: return f"Analysis Failed: {e}"

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, style_key, image_obj=None, enable_split=False):
        """
        CoT 核心逻辑：基于用户权重和风格预设，进行链式思考。
        """
        if not self.valid: return []

        # 1. 获取风格数据
        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]
        style_light = style_data["lighting"]

        # 2. 构建思维链 Prompt
        # 我们告诉 AI：不要急着输出，先思考(Thinking Process)，最后再输出 Prompt。
        cot_instructions = f"""
        Role: Senior Art Director for Amazon Fashion.
        
        【Input Data】
        - User Idea: "{user_idea}"
        - Selected Style: "{style_key}" ({style_desc})
        - Task Type: {task_type}
        - User Control Weight: {user_weight} (0.0=Trust Image, 1.0=Trust User Idea)
        
        【Thinking Process (Internal Monologue)】
        1. **Analyze Intent**: How much should I listen to the user based on weight {user_weight}? 
           - If > 0.7: Prioritize user's idea and syntax like (word) or [word].
           - If < 0.3: Ignore user idea conflicts, prioritize image consistency.
        2. **Visual Planning**: 
           - Composition: Best angle for {task_type}.
           - Lighting: Apply "{style_light}" logic.
           - Atmosphere: Integrate "{style_desc}".
        3. **Refinement**: Ensure commercial quality (8k, highly detailed).
        
        【Output Requirement】
        - Output English Prompts ONLY.
        - If {enable_split} is True, split distinct variations with "|||".
        - NO explanation, NO "Here is the prompt". Just the raw prompt string.
        """

        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            inputs = [cot_instructions, image_obj] if image_obj else [cot_instructions]
            
            response = model.generate_content(inputs)
            raw_text = response.text.strip()
            
            # 清洗一下可能带出的 "Prompt: " 前缀
            raw_text = raw_text.replace("Prompt:", "").replace("Here is the prompt:", "").strip()
            
            prompts = [p.strip() for p in raw_text.split("|||") if p.strip()]
            return prompts
        except Exception as e:
            print(f"CoT Error: {e}")
            return [f"{user_idea}, {style_desc}"]
