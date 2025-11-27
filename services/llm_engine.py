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
        if not self.valid: return "Error"
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest")
            resp = model.generate_content([prompt_instruction, image])
            return resp.text.strip()
        except Exception as e: return str(e)

    def optimize_art_director_prompt(self, user_idea, task_type, user_weight, style_key, image_input=None, enable_split=False):
        """
        V4 强力意图理解版：
        解决“听不懂人话”的问题。强制 AI 将用户的抽象修改要求（如‘换成好莱坞模特’）
        转化为具体的视觉描述（如‘Caucasian female, blonde hair, western facial features’），
        从而在生图时覆盖原图的特征。
        """
        if not self.valid: return []

        # 1. 获取风格数据
        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]

        # 2. 构建输入数据
        inputs = []
        img_context = ""
        if image_input:
            if isinstance(image_input, list):
                inputs.extend(image_input)
                img_context = f"provided {len(image_input)} reference images"
            else:
                inputs.append(image_input)
                img_context = "provided 1 reference image"

        # 3. 构建 CoT (思维链) 系统指令
        # 核心改动：要求 AI 先检测冲突，再重写描述
        system_prompt = f"""
        Role: Senior Visual Prompt Engineer.
        
        【Goal】
        Transform the User's Request into a HIGHLY DESCRIPTIVE English prompt for image generation.
        You are looking at {img_context}.
        
        【User Request】: "{user_idea}"
        【Target Style】: "{style_key}" ({style_desc})
        
        【CRITICAL THINKING PROCESS】
        1. **ANALYZE DELTA**: Compare User Request vs. Reference Image. 
           - Does user want to change the Subject? (e.g. "change model", "swap into dog")
           - Does user want to change the Background? (e.g. "at a party", "on beach")
           - Does user want to change the Clothes?
           
        2. **OVERRIDE RULE (The most important rule)**: 
           - If user asks to CHANGE something, you MUST describe the NEW element in EXTREME DETAIL.
           - Example: User says "Hollywood Model". You write: "A glamorous Hollywood supermodel, Caucasian female, American facial features, blonde wavy hair, blue eyes, confident smile, western aesthetic." 
           - **DO NOT** just say "Hollywood model". The AI needs VISUAL ADJECTIVES to override the reference image.
           
        3. **COMPOSITION**: Keep the pose/composition from reference image unless told otherwise.

        【Output Format】
        - Output ONLY the final English prompt string. 
        - Include high quality tags: 8k, photorealistic, masterpiece, {style_desc}.
        - Do not output explanations.
        """
        
        inputs.insert(0, system_prompt)

        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash") # 建议使用 1.5 flash，理解力更好
            
            # 设置生成配置，降低随机性，提高遵从度
            config = genai.types.GenerationConfig(
                temperature=0.4, 
                candidate_count=1
            )
            
            response = model.generate_content(inputs, generation_config=config)
            raw_text = response.text.strip()
            
            # 清理可能产生的 markdown 格式
            final_prompt = raw_text.replace("```text", "").replace("```", "").strip()
            
            return [final_prompt]
            
        except Exception as e:
            print(f"Prompt Optimization Error: {e}")
            # 降级处理：简单的拼接
            return [f"{user_idea}, {style_desc}, high quality, 8k"]
