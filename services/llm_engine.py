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
            model = genai.GenerativeModel("models/gemini-3-pro-preview") # 建议尝试更聪明的模型，或者回退到 gemini-1.5-flash
            prompt = f"Translate to {target_lang}. Output ONLY translation. Text: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def analyze_image_style(self, image, prompt_instruction):
        if not self.valid: return "Error"
        try:
            model = genai.GenerativeModel("models/gemini-3-pro-preview")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e: return str(e)

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, style_key, image_input=None, enable_split=False):
        """
        V5 激进覆写版 (Aggressive Overwrite Edition)：
        解决“换脸/换人失败”的核心痛点。
        核心逻辑：当检测到用户想要“换人”时，强制 AI 编造具体的面部/身体特征，
        以物理描述的冲突（Physical Conflict）来强迫生图模型放弃原图特征。
        """
        if not self.valid: return []

        # 1. 样式上下文
        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]

        # 2. 视觉输入处理
        inputs = []
        img_context_str = "No reference image."
        if image_input:
            if isinstance(image_input, list):
                inputs.extend(image_input)
                img_context_str = f"User provided {len(image_input)} reference images."
            else:
                inputs.append(image_input)
                img_context_str = "User provided 1 reference image."

        # 3. 核心 System Prompt (重写重点：特征注入)
        system_prompt = f"""
        Role: Aggressive Visual Director for AI Image Generation.
        
        【Context】
        You are looking at a Reference Image ({img_context_str}).
        The User wants to generate a NEW image based on this, but with specific changes.
        
        【User Command】: "{user_idea}"
        【Style】: "{style_key}" ({style_desc})
        
        【CRITICAL RULES FOR "CHANGING THE MODEL"】
        If the user says "Change model", "Don't use this person", "Foreigner", "Hollywood model", or implies a change in identity:
        
        1. **STOP CAPTIONING THE FACE**: Do NOT describe the face you see in the reference image.
        2. **INVENT CONTRADICTORY TRAITS**: You MUST invent specific physical traits that correspond to the user's request to FORCE the AI to draw someone else.
           - "Hollywood/Western Model" -> Translate to: "Caucasian female, platinum blonde wavy hair, icy blue eyes, sharp jawline, fair skin, high fashion makeup."
           - "Black Model" -> Translate to: "African American female, dark skin tone, curly hair, full lips."
           - "Plus Size" -> Translate to: "Curvy plus size model, full figured."
        
        3. **BE EXPLICIT**: 
           - BAD: "A Hollywood style model..." (Too weak, AI will keep the original face).
           - GOOD: "Close up of a stunning Caucasian supermodel with blonde hair and blue eyes..." (Strong visual instructions).

        4. **PRESERVE CLOTHING?**: 
           - If user ONLY says "change model", keep the clothing description from the reference image, but attach it to the NEW body/face description.
           - If user says "change clothing" too, describe new clothing.

        【Output Structure】
        Output a single paragraph English prompt.
        Structure: [Subject Physical Description] + [Clothing/Action Details] + [Background/Context] + [Style/Lighting tags].
        Start with the Subject Description immediately.
        """
        
        inputs.insert(0, system_prompt)

        try:
            # 优先使用 2.0-flash-exp (如果你的 key 支持)，它的指令遵循能力最强
            # 如果报错，请改回 models/gemini-1.5-flash
            model_name = "models/gemini-3-pro-preview" 
            try:
                model = genai.GenerativeModel(model_name)
            except:
                model = genai.GenerativeModel("models/gemini-3-pro-preview")

            # 降低 Temperature，让它严格执行"覆写"逻辑，不要随意发挥
            config = genai.types.GenerationConfig(
                temperature=0.3, 
                candidate_count=1
            )
            
            response = model.generate_content(inputs, generation_config=config)
            raw_text = response.text.strip()
            
            # 清理格式
            final_prompt = raw_text.replace("```text", "").replace("```", "").replace("Prompt:", "").strip()
            
            return [final_prompt]
            
        except Exception as e:
            print(f"Prompt Gen Error: {e}")
            # 降级：直接把用户的话加重权拼上去
            return [f"(({user_idea})), {style_desc}, detailed face, high quality"]
