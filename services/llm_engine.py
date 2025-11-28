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
        V6 逻辑升级：支持多主体生成 (Multi-Subject Generation)
        解决痛点：用户要求"生成两位不同模特"时，AI 只输出单人 Prompt。
        """
        if not self.valid: return []

        style_data = PRESETS.get(style_key, PRESETS["💡 默认 (None)"])
        style_desc = style_data["desc"]

        # 构建输入
        inputs = []
        inputs.append(image_input if image_input else "No reference image provided.")
        
        # --- 核心 System Prompt (针对人数问题进行了深度重构) ---
        system_prompt = f"""
        You are an expert AI Art Director. Your goal is to write a precise image generation prompt based on the User's Request and the Reference Image.

        【User Request】: "{user_idea}"
        【Style Preset】: "{style_desc}"

        【STEP 1: ANALYZE SUBJECT COUNT】
        Check if the user wants **MORE THAN ONE** person (e.g., "two models", "couple", "group", "twins", "friends").
        
        👉 CASE A: MULTIPLE SUBJECTS (Target > 1 person)
        1. **Composition**: Start with "A medium shot of TWO models..." (or relevant number).
        2. **Differentiation**: You MUST invent DISTINCT looks for each model if requested.
           - Write: "Model on left is [Physique A, Hair A, Ethnicity A]. Model on right is [Physique B, Hair B, Ethnicity B]."
           - Do NOT make them look like clones unless user asks for "twins".
        3. **Clothing Logic**: Explicitly state that **BOTH** are wearing the clothing from the reference image (or as user requested).
           - Write: "Both models are wearing matching [Clothing Description from Ref Image]."

        👉 CASE B: SINGLE SUBJECT (Target = 1 person)
        1. **Identity Check**: Does user want to change the model?
           - IF YES: Invent NEW physical traits (e.g., "Caucasian, blonde" or "Asian, short hair") to override the reference image face.
           - IF NO: Describe the person in the reference image accurately.

        【STEP 2: EXTRACT VISUALS FROM REFERENCE】
        - Look at the Reference Image. Extract the **Clothing Details** (Texture, Color, Cut) and **Environment** (if needed).
        - If the user wants to keep the clothing, describe it in high detail so the generated image matches the product.

        【Final Output Format】
        Write a single, continuous English prompt.
        Structure: [Subject Count & Composition] + [Distinct Subject Details (Model A, Model B...)] + [Clothing/Product Details] + [Action/Interaction] + [Background] + [Style tags].
        """
        
        inputs.append(system_prompt)

        try:
            # 依然使用最聪明的 Gemini 3 Pro Preview (Reasoning)
            model = self._get_model("reasoning")
            
            config = genai.types.GenerationConfig(
                temperature=0.45, #稍微提高一点点创造力，让它能编造出两个不同的人
                candidate_count=1
            )
            
            response = model.generate_content(inputs, generation_config=config)
            final_prompt = response.text.strip()
            
            # 调试日志：可以在后台看到 LLM 到底输出了什么
            print(f"🐛 Generated Prompt: {final_prompt}")
            
            return [final_prompt]

        except Exception as e:
            print(f"LLM Error: {e}")
            return [f"{user_idea}, {style_desc}, high quality, 8k resolution"]
    # 在 LLMEngine 类中添加

    def get_chat_model(self, model_name="models/gemini-3-pro-image-preview", system_instruction=None):
        """
        获取一个配置好的聊天模型实例
        """
        if not self.valid: return None
        
        # 安全设置
        safety = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }
        
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction, # 支持动态人设
            safety_settings=safety
        )

    def chat_stream(self, chat_session, user_input, image_input=None):
        """
        流式对话接口
        chat_session: genai.ChatSession 对象
        user_input: 文本输入
        image_input: PIL Image 对象 (可选)
        """
        if not self.valid: 
            yield "❌ API Key 无效"
            return

        # 构建消息内容
        content = []
        if user_input:
            content.append(user_input)
        if image_input:
            content.append(image_input)
            
        if not content: return

        try:
            # 流式发送消息
            response = chat_session.send_message(content, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"⚠️ Error: {str(e)}"
