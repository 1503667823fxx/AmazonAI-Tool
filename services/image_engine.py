import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

class ImageGenEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_safety_settings(self, tolerance_level="Standard"):
        # 保持您原有的安全设置逻辑，这部分没问题
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

    def generate(self, prompt, model_name, ref_image=None, ratio_suffix="", negative_prompt="", 
                 seed=None, creativity=0.5, safety_level="Standard"):
        """
        执行生图任务
        """
        # 1. 强制模型白名单检查 (根据您的要求)
        allowed_models = [
            "models/gemini-3-pro-image-preview", # 首选生图
            "models/gemini-3-pro-preview",       # 备选
            "models/gemini-flash-latest",
            "models/gemini-flash-lite-latest"
        ]
        
        # 如果传入的模型不在白名单，默认回退到 image-preview
        target_model = model_name if model_name in allowed_models else "models/gemini-3-pro-image-preview"

        # 2. 构建 Prompt
        # 移除可能重复的比例词，由 ratio_suffix 控制
        clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "")
        final_prompt = f"{clean_prompt} {ratio_suffix}"
        
        if negative_prompt:
            final_prompt += f" --no {negative_prompt}"

        # 3. 准备输入 Payload
        inputs = [final_prompt]
        if ref_image:
            inputs.append(ref_image)

        # 4. 配置生成参数
        gen_config = genai.types.GenerationConfig(
            temperature=creativity,
            candidate_count=1
        )
        
        # 尝试注入 Seed
        if seed is not None and seed != -1:
            try:
                setattr(gen_config, 'seed', int(seed))
            except:
                pass

        safety_settings = self._get_safety_settings(safety_level)

        # 5. 调用 API (带简单的重试)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # 实例化指定的模型
                gen_model = genai.GenerativeModel(target_model)
                
                response = gen_model.generate_content(
                    inputs,
                    generation_config=gen_config,
                    safety_settings=safety_settings
                )
                
                # 尝试解析图像数据
                if response.parts:
                    for part in response.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            return part.inline_data.data
                
                # 如果没有图像数据但也没报错，可能是由于安全设置被静默拦截
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
