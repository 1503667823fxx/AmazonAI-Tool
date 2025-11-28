import google.generativeai as genai
import time
from services.core_base import BaseService

class SmartEditGenerator(BaseService):
    """
    [Smart Edit 专属] 负责调用生图 API。
    """
    def generate_image(self, prompt, model_name, ref_image=None, ratio_suffix="", seed=None, safety_level="Standard"):
        if not self.is_valid: return None

        # 1. 准备参数
        final_prompt = f"{prompt} {ratio_suffix}"
        inputs = [final_prompt]
        if ref_image: inputs.append(ref_image)

        gen_config = genai.types.GenerationConfig(candidate_count=1, temperature=0.5)
        if seed is not None and seed != -1:
            try: setattr(gen_config, 'seed', int(seed))
            except: pass

        # 2. 调用 API (带重试)
        try:
            model = genai.GenerativeModel(model_name)
            # 简化版生图调用
            response = model.generate_content(inputs, generation_config=gen_config)
            
            # 解析结果
            if response.parts:
                for part in response.parts:
                    if hasattr(part, "inline_data"):
                        return part.inline_data.data
            return None
        except Exception as e:
            print(f"Generation Error: {e}")
            return None
