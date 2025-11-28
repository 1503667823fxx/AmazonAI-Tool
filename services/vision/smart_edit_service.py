import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
from services.core_base import BaseService
from services.vision.styles import PRESETS # 引用同目录下的 styles

class SmartEditService(BaseService):
    """
    Smart Edit 专属后端。
    集成了：Prompt优化 (原LLM功能) + 图像生成 (原ImageGen功能) + 翻译
    """
    
    def __init__(self, api_key=None):
        super().__init__(api_key)

    # ================= 1. 文本/Prompt 处理能力 =================
    
    def _get_llm_model(self, model_type="reasoning"):
        if model_type == "reasoning":
            return genai.GenerativeModel("models/gemini-3-pro-preview")
        return genai.GenerativeModel("models/gemini-flash-latest")

    def translate(self, text, target_lang="English"):
        """简单的翻译工具"""
        if not text or not self.is_valid: return text
        try:
            model = self._get_llm_model("fast")
            prompt = f"Translate the following text to {target_lang}. Return ONLY the translation, no extra text.\nText: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def optimize_art_director_prompt(self, user_idea, task_type, weight, style_key, image_input=None, enable_split=False):
        """
        [原 llm_engine.optimize_art_director_prompt 逻辑复刻]
        专门用于修图的 Prompt 优化专家。
        """
        if not self.is_valid: return []

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
            model = self._get_llm_model("reasoning")
            config = genai.types.GenerationConfig(temperature=0.45, candidate_count=1)
            response = model.generate_content(inputs, generation_config=config)
            return [response.text.strip()]
        except Exception as e:
            print(f"Prompt Optimization Error: {e}")
            return [f"{user_idea}, {style_desc}, high quality"]

    # ================= 2. 图像生成能力 =================

    def _get_safety_settings(self, tolerance_level="Standard"):
        threshold = HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        if tolerance_level.startswith("Permissive"):
            threshold = HarmBlockThreshold.BLOCK_ONLY_HIGH
        elif tolerance_level.startswith("Strict"):
            threshold = HarmBlockThreshold.BLOCK_LOW_AND_ABOVE

        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        }

    def generate_image(self, prompt, model_name, ref_image=None, ratio_suffix="", seed=None, safety_level="Standard"):
        """
        [原 image_engine.generate 逻辑复刻]
        """
        # 1. 强制模型白名单检查
        allowed_models = [
            "models/gemini-3-pro-image-preview",
            "models/gemini-3-pro-preview",
            "models/gemini-2.5-flash-image",
            "models/gemini-flash-latest",
            "models/gemini-flash-lite-latest"
        ]
        target_model = model_name if model_name in allowed_models else "models/gemini-3-pro-image-preview"

        # 2. Prompt 清理
        clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "")
        final_prompt = f"{clean_prompt} {ratio_suffix}"
        
        # 3. 输入构建
        inputs = [final_prompt]
        if ref_image:
            inputs.append(ref_image)

        # 4. 配置
        gen_config = genai.types.GenerationConfig(
            temperature=0.5,
            candidate_count=1
        )
        if seed is not None and seed != -1:
            try:
                setattr(gen_config, 'seed', int(seed))
            except: pass

        safety_settings = self._get_safety_settings(safety_level)

        # 5. 调用 API (带重试)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                gen_model = genai.GenerativeModel(target_model)
                response = gen_model.generate_content(
                    inputs,
                    generation_config=gen_config,
                    safety_settings=safety_settings
                )
                if response.parts:
                    for part in response.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            return part.inline_data.data
                
                if attempt == max_retries:
                    print(f"No image returned. Prompt blocked? {response.prompt_feedback}")

            except Exception as e:
                if "429" in str(e): # Resource Exhausted
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    print(f"Gen Error ({target_model}): {e}")
                    if attempt == max_retries:
                        return None
        return None
