import streamlit as st
import google.generativeai as genai

class LLMEngine:
    def __init__(self, api_key=None):
        # 优先使用传入的 Key，否则从 secrets 读取
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.valid = True
        else:
            self.valid = False
            
    def translate(self, text, target_lang="English"):
        """通用翻译功能"""
        if not text or not self.valid: return text
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            prompt = f"Translate the following text to {target_lang}. Output ONLY the translation without any explanation. Text: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            print(f"Translation Error: {e}")
            return text

    def analyze_image_style(self, image, prompt_instruction):
        """图生文：分析图片特征"""
        if not self.valid: return "Error: API Key missing"
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e:
            return f"Analysis Failed: {e}"

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, image_obj=None, enable_split=False):
        """
        核心逻辑：根据用户权重生成 Art Director 提示词。
        这是从 Smart_Edit Tab 1 中提取出来的复杂逻辑。
        """
        if not self.valid: return []

        # 1. 构建特殊的指令
        special_instruction = ""
        if "Product Only" in task_type:
            special_instruction = """
            SPECIAL INSTRUCTION FOR PRODUCT PHOTOGRAPHY:
            1. Layout: Use "Knolling photography", "Neatly arranged".
            2. Realism: Use "Contact shadows", "Ambient occlusion".
            3. Texture: Emphasize "fabric texture", "material details".
            """

        weight_instruction = f"""
        WEIGHT CONTROL INSTRUCTION:
        User Weight: {user_weight} (0.0=Image Priority, 1.0=Text Priority).
        - If > 0.7: Follow User Idea strictly.
        - If < 0.3: Follow Image Visuals strictly.
        - 0.4-0.6: Balance both.
        """

        split_instruction = "IMPORTANT: Split distinct outputs into separate prompts using '|||'." if enable_split else "Output ONE unified prompt. NO '|||'."

        full_prompt = f"""
        Role: Art Director. 
        Task: Create detailed prompts based on User Idea and Image. Type: {task_type}.
        {weight_instruction}
        {special_instruction}
        {split_instruction}
        STRICT OUTPUT FORMAT: English Prompts Only. NO Markdown.
        User Idea: {user_idea}
        """

        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            # 如果有图片就一起发过去
            inputs = [full_prompt, image_obj] if image_obj else [full_prompt]
            
            response = model.generate_content(inputs)
            raw_text = response.text.strip()
            
            # 解析返回结果
            prompts = [p.strip() for p in raw_text.split("|||") if p.strip()]
            return prompts
        except Exception as e:
            print(f"Prompt Gen Error: {e}")
            return [user_idea] # 降级返回原输入
