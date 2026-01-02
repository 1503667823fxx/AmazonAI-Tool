import google.generativeai as genai
import streamlit as st

# === [复制来源: styles.py] 风格预设 ===
PRESETS = {
    "💡 默认 (None)": {
        "desc": "",
        "lighting": "natural commercial lighting",
        "negative": ""
    },
    "⚪ 亚马逊纯白 (Studio White)": {
        "desc": "professional Amazon e-commerce photography, clean pure white background, high end fashion",
        "lighting": "soft studio lighting, uniform illumination, no harsh shadows",
        "negative": "dark background, messy background, low light, shadows"
    },
    "🏙️ 街头潮流 (Urban Street)": {
        "desc": "trendy streetwear fashion photography, blurred city street background, bokeh",
        "lighting": "natural sunlight, golden hour, dynamic shadows",
        "negative": "studio lighting, indoor, plain background"
    },
    "🏠 居家休闲 (Cozy Home)": {
        "desc": "lifestyle photography, cozy modern living room background, comfortable atmosphere",
        "lighting": "warm interior lighting, soft window light",
        "negative": "cold colors, industrial, outdoor"
    },
    "✨ 极简高级 (Luxury Minimalist)": {
        "desc": "luxury fashion editorial, minimalist architectural background, concrete or marble texture",
        "lighting": "dramatic high-contrast lighting, artistic shadows",
        "negative": "cluttered, messy, colorful background"
    },
    "🌲 户外自然 (Nature/Outdoor)": {
        "desc": "outdoor lifestyle photography, nature park or forest background, fresh vibe",
        "lighting": "bright daylight, sun flare",
        "negative": "urban, building, indoor"
    }
}

class SmartEditPrompter:
    """
    [Smart Edit 专属] Prompt 优化与翻译服务
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.valid = True
        else:
            self.valid = False

    def _get_model(self, model_type="reasoning"):
        """内部路由"""
        if model_type == "reasoning":
            return genai.GenerativeModel("models/gemini-3-pro-preview")
        elif model_type == "fast":
            return genai.GenerativeModel("models/gemini-flash-latest")
        return genai.GenerativeModel("models/gemini-flash-lite-latest")

    def translate(self, text, target_lang="English"):
        """[复制来源: llm_engine.py] 基础翻译"""
        if not text or not self.valid: return text
        try:
            model = self._get_model("fast")
            prompt = f"Translate the following text to {target_lang}. Return ONLY the translation, no extra text.\nText: {text}"
            resp = model.generate_content(prompt)
            return resp.text.strip()
        except: return text

    def optimize_art_director_prompt(self, user_idea, task_type, weight, style_key, image_input=None, enable_split=False):
        """[复制来源: llm_engine.py] 核心 Prompt 优化逻辑 - 支持多图处理"""
        if not self.valid: return []

        style_data = PRESETS.get(style_key, PRESETS.get("💡 默认 (None)"))
        style_desc = style_data["desc"] if style_data else "high quality"

        inputs = []
        
        # 处理图片输入 - 支持单图或多图
        if image_input:
            if isinstance(image_input, list):
                # 多图模式
                for i, img in enumerate(image_input):
                    if img is not None:
                        inputs.append(img)
                image_context = f"Multiple reference images provided ({len([img for img in image_input if img is not None])} images) for multi-image fusion."
            else:
                # 单图模式
                inputs.append(image_input)
                image_context = "Single reference image provided."
        else:
            image_context = "No reference image provided."
        
        system_prompt = f"""
        You are an expert AI Art Director.
        【User Request】: "{user_idea}"
        【Style Preset】: "{style_desc}"
        【Image Context】: {image_context}

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
        
        【STEP 3: MULTI-IMAGE FUSION】
        If multiple reference images are provided:
        - Analyze and combine elements from all reference images
        - Maintain consistency in style and quality across all reference sources
        - Blend complementary aspects (e.g., pose from image 1, clothing from image 2, background from image 3)

        【Output】
        Write a single, continuous English prompt that incorporates all reference elements effectively.
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
