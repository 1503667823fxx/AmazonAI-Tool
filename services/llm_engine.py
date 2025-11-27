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
        if not self.valid: return "Error: API Key missing"
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e: return f"Analysis Failed: {e}"

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, style_key, image_input=None, enable_split=False):
        """
        CoT 核心逻辑 (升级版)：支持多图融合分析。
        image_input: 可以是单个 PIL.Image，也可以是 List[PIL.Image]
        """
        if not self.valid: return []

        # 1. 获取风格数据
        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]
        style_light = style_data["lighting"]

        # 2. 智能处理图片输入
        images = []
        img_instruction = ""
        
        if image_input:
            if isinstance(image_input, list):
                images = image_input
                img_instruction = f"【Visual Input】: {len(images)} images provided. \nLogic: Analyze ALL images. If one looks like a person/product and another looks like a background/scene, FUSE them logically. If they are all products, arrange them together."
            else:
                images = [image_input]
                img_instruction = "【Visual Input】: 1 image provided. Use it as the main visual reference."

        # 3. 构建思维链 Prompt
        cot_instructions = f"""
        Role: Senior Art Director for Amazon Fashion.
        
        【Input Data】
        - User Idea: "{user_idea}"
        - Selected Style: "{style_key}" ({style_desc})
        - Task Type: {task_type}
        - User Control Weight: {user_weight} (0.0=Trust Images, 1.0=Trust User Idea)
        {img_instruction}
        
        【Thinking Process (Internal Monologue)】
        1. **Analyze Input Images**: 
           - Identify main subjects (Models/Products) and Context (Backgrounds).
           - If multiple images: Infer the user's composition intent (e.g., Person A + Scene B -> Person A standing in Scene B).
        2. **Analyze Intent**: 
           - Weight {user_weight}: Balance visual references with user text.
        3. **Visual Planning**: 
           - Composition: Best angle for {task_type}.
           - Lighting: Apply "{style_light}" logic.
           - Atmosphere: Integrate "{style_desc}".
        4. **Refinement**: Ensure commercial quality (8k, highly detailed).
        
        【Output Requirement】
        - Output English Prompts ONLY.
        - If {enable_split} is True, split distinct variations with "|||".
        - NO explanation. Just the raw prompt string.
        """

        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            # 拼接：指令 + 图片列表
            inputs = [cot_instructions] + images
            
            response = model.generate_content(inputs)
            raw_text = response.text.strip()
            
            raw_text = raw_text.replace("Prompt:", "").replace("Here is the prompt:", "").strip()
            prompts = [p.strip() for p in raw_text.split("|||") if p.strip()]
            return prompts
        except Exception as e:
            print(f"CoT Error: {e}")
            return [f"{user_idea}, {style_desc}"]
