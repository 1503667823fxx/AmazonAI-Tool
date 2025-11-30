import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 1. 获取 Google API Key
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def fill_image(image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    """
    使用 Google 原生 GenAI 进行图像扩展 (Outpainting)。
    尝试使用用户指定的 Gemini/Imagen 模型。
    """
    try:
        # ------------------------------------------------------------------
        # 模型选择策略：
        # 优先使用你指定的 'models/gemini-3-pro-image-preview' (如果有权限)
        # 如果失败，自动回退到标准的 'imagen-3.0-generate-001'
        # ------------------------------------------------------------------
        target_model = "models/gemini-3-pro-image-preview" 
        fallback_model = "imagen-3.0-generate-001"

        try:
            # 尝试初始化指定的模型
            model = genai.ImageGenerationModel(target_model)
            print(f"尝试使用模型: {target_model}")
        except Exception:
            # 初始化失败，使用 fallback
            print(f"指定模型不可用，切换至: {fallback_model}")
            model = genai.ImageGenerationModel(fallback_model)

        # Google 的 edit_image 接口参数略有不同
        # prompt: 提示词
        # base_image: 原图 (我们传进去的是已经 padding 过的底图)
        # mask: 遮罩 (白色区域为编辑区/扩充区)
        response = model.edit_image(
            prompt=prompt,
            base_image=image,
            mask=mask,
            aspect_ratio=None, # 因为我们已经手动调整了画布尺寸，所以不需要模型再调整比例
            safety_filter_level="block_only_high",
            person_generation="dont_allow", # 【关键】强制禁止生成人物，防止影分身！
        )

        # Google 返回的是 GeneratedImage 对象，直接取第一张
        generated_image = response.images[0]
        
        # 将结果转换为 PIL Image 对象返回
        # 这里的 generated_image 通常有 ._image_bytes 或者可以直接 save
        # 为了兼容性，我们将其转为 PIL
        return Image.open(io.BytesIO(generated_image.image_bytes))

    except Exception as e:
        # 错误处理：如果 Google 编辑接口失败（这通常是因为 Key 权限或模型名称问题）
        print(f"Google GenAI Edit Error: {e}")
        st.error(f"Google AI 绘图失败: {str(e)}")
        st.warning("提示：请确保你的 API Key 开通了 Imagen/ImageGeneration 权限。")
        raise e
