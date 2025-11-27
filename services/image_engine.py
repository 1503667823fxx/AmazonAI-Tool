import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import random

class ImageGenEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_safety_settings(self, tolerance_level="Standard"):
        """
        根据用户选择的安全容忍度，生成安全设置配置。
        解决痛点：电商模特图经常被误判为成人内容而被拦截。
        """
        # 默认屏蔽阈值 (BLOCK_MEDIUM_AND_ABOVE)
        threshold = HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
        
        if tolerance_level == "Permissive (宽松 - 适合内衣/泳装)":
            # 仅屏蔽极度危险内容，放行普通皮肤暴露
            threshold = HarmBlockThreshold.BLOCK_ONLY_HIGH
        elif tolerance_level == "Strict (严格)":
            threshold = HarmBlockThreshold.BLOCK_LOW_AND_ABOVE

        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: threshold,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: threshold,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: threshold,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: threshold,
        }

    def generate(self, prompt, model_name, ref_image=None, ratio_suffix="", negative_prompt="", 
                 seed=None, creativity=0.5, safety_level="Standard", max_retries=3):
        """
        增强版生图接口：支持重试、安全设置、参数控制。
        """
        # 1. 预处理 Prompt
        clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
        final_prompt = f"{clean_prompt} {ratio_suffix}, high quality, 8k resolution, photorealistic"
        
        if negative_prompt and negative_prompt.strip():
            final_prompt += f" --no {negative_prompt.strip()}"

        # 2. 准备输入
        inputs = [final_prompt]
        if ref_image:
            inputs.append(ref_image)

        # 3. 准备生成配置 (Generation Config)
        # 注意：temperature 在生图模型中通常影响“创意度/随机性”
        gen_config = genai.types.GenerationConfig(
            temperature=creativity, # 0.0=保守/一致, 1.0=狂野/随机
            candidate_count=1
        )
        
        # 尝试注入 Seed (如果模型支持)
        # 注意：目前部分 Gemini 版本会自动忽略此参数，但保留接口是为了未来兼容
        if seed is not None and isinstance(seed, int):
            # 这是一个 Hack，因为 python sdk 有时未显式暴露 seed
            # 如果报错，我们会捕获异常
            try:
                setattr(gen_config, 'seed', seed)
            except:
                pass

        # 4. 获取安全设置
        safety_settings = self._get_safety_settings(safety_level)

        # 5. 带重试机制的调用循环
        for attempt in range(max_retries):
            try:
                gen_model = genai.GenerativeModel(model_name)
                
                # 发起调用
                response = gen_model.generate_content(
                    inputs, 
                    stream=True,
                    generation_config=gen_config,
                    safety_settings=safety_settings
                )
                
                # 解析流式结果
                for chunk in response:
                    if hasattr(chunk, "parts"):
                        for part in chunk.parts:
                            if part.inline_data:
                                return part.inline_data.data
                
                # 如果代码走到这里还没返回，说明可能被拦截了
                if attempt == max_retries - 1:
                    print(f"Generation finished but no image found. Safety filter triggered?")
            
            except Exception as e:
                # 捕获错误并决定是否重试
                error_msg = str(e)
                is_last_attempt = (attempt == max_retries - 1)
                
                if "429" in error_msg: # 频率限制
                    wait_time = 2 ** (attempt + 1) # 指数退避: 2s, 4s, 8s...
                    print(f"Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                elif "500" in error_msg or "503" in error_msg: # 服务器错误
                    if not is_last_attempt:
                        time.sleep(1)
                        continue
                else:
                    # 其他错误（如 400 参数错误）直接抛出，不重试
                    if is_last_attempt:
                        st.error(f"❌ 生成失败 (Attempt {attempt+1}/{max_retries}): {e}")
                    else:
                        print(f"Error: {e}. Retrying...")
                        
        return None
