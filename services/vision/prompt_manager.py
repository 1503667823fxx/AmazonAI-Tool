import google.generativeai as genai
from services.core_base import BaseService
from services.vision.styles_config import PRESETS

class SmartEditPrompter(BaseService):
    """
    [Smart Edit 专属] 负责 Prompt 的优化、改写和翻译。
    """
    def translate_to_en(self, text):
        """简单翻译功能"""
        if not text or not self.is_valid: return text
        try:
            model = self.get_model("models/gemini-1.5-flash")
            resp = model.generate_content(f"Translate to English, output ONLY text: {text}")
            return resp.text.strip()
        except: return text

    def optimize_prompt(self, user_idea, task_type, style_key, image_input=None):
        """
        Art Director 逻辑：根据用户输入和图片优化 Prompt
        """
        if not self.is_valid: return ["Error: Invalid API Key"]

        style_desc = PRESETS.get(style_key, {}).get("desc", "high quality")
        
        # 构建输入 (Gemini 支持直接传入 Image 对象)
        inputs = []
        if image_input:
            inputs.append(image_input)
        else:
            inputs.append("No reference image provided.")
            
        system_prompt = f"""
        Act as an Expert AI Art Director.
        User Request: "{user_idea}"
        Task Type: "{task_type}"
        Target Style: "{style_desc}"

        RULES:
        1. If user asks to change model/person, explicitly describe a NEW person (e.g., "Caucasian model with blonde hair") to override the reference.
        2. Keep clothing details from reference image EXACTLY.
        3. Output a single, high-quality English prompt for image generation.
        """
        inputs.append(system_prompt)

        try:
            # 使用推理能力较强的模型来写 Prompt
            model = self.get_model("models/gemini-1.5-pro-latest")
            resp = model.generate_content(inputs)
            return [resp.text.strip()]
        except Exception as e:
            return [f"{user_idea}, {style_desc} (Fallback due to error: {e})"]
