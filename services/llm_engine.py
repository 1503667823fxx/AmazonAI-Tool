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
            
    # --- 模型路由配置 ---
    def _get_model(self, model_type="reasoning"):
        """
        根据任务类型分配您指定的模型
        """
        if model_type == "reasoning":
            # 优先使用最聪明的 Gemini 3 Pro Preview 处理复杂的 Prompt 推理
            return genai.GenerativeModel("models/gemini-3-pro-preview")
        elif model_type == "fast":
            # 翻译或简单任务使用 Flash Latest
            return genai.GenerativeModel("models/gemini-flash-latest")
        return genai.GenerativeModel("models/gemini-flash-lite-latest")

    def translate(self, text, target_lang="English"):
        if not text or not self.valid: return text
        try:
            model = self._get_model("fast")
            prompt = f"Translate the following text to {target_lang}. Return ONLY the translation, no extra text.\nText: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def optimize_art_director_prompt(self, user_idea, task_type, weight, style_key, image_input=None, enable_split=False):
        """
        优化核心：解决'换模特'无效的问题。
        策略：强制 LLM 提取原图的'服装/环境'，但重写'人物特征'。
        """
        if not self.valid: return []

        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]

        # 构建多模态输入
        inputs = []
        inputs.append(image_input if image_input else "No reference image provided.")
        
        # --- 核心 System Prompt ---
        # 这一段 Prompt 是解决 Bug 的关键
        system_prompt = f"""
        You are an expert AI Art Director. Your goal is to write a precise image generation prompt based on the User's Request and the Reference Image.

        【User Request】: "{user_idea}"
        【Style Preset】: "{style_desc}"

        【CRITICAL INSTRUCTION FOR IDENTITY SWAPPING】
        Analyze if the user wants to CHANGE the model/person (e.g., "swap model", "use a foreigner", "change to man").
        
        IF YES (Change Model):
        1. **IGNORE** the face/body traits in the Reference Image.
        2. **INVENT** specific, high-contrast physical details for the new person to OVERRIDE the image signal.
           - Instead of just "Western model", write: "Portrait of a Caucasian female model, platinum blonde wavy hair, icy blue eyes, fair skin structure, sharp jawline."
           - Instead of just "Black model", write: "Portrait of an African American male model, dark skin tone, short buzz cut, brown eyes."
        3. **KEEP** the clothing details from the Reference Image (describe the clothes you see in the image explicitly).

        IF NO (Keep Model):
        1. Describe the person in the Reference Image accurately to maintain consistency.

        【Final Output Format】
        Write a single, high-quality English prompt suitable for a text-to-image model.
        Format: [Subject Description (Face/Body)] + [Clothing Details (from Ref Image)] + [Action/Pose] + [Background/Environment] + [Lighting/Style].
        """
        
        inputs.append(system_prompt)

        try:
            # 使用最强的 Gemini 3 Pro Preview 进行思考
            model = self._get_model("reasoning")
            
            config = genai.types.GenerationConfig(
                temperature=0.4, # 降低随机性，确保严格遵循指令
                candidate_count=1
            )
            
            response = model.generate_content(inputs, generation_config=config)
            final_prompt = response.text.strip()
            
            return [final_prompt]

        except Exception as e:
            print(f"LLM Error: {e}")
            # 降级策略
            return [f"{user_idea}, {style_desc}, high quality, 8k resolution"]
