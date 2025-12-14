import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFilter
import io
import numpy as np

class InpaintService:
    """
    [Magic Canvas 专属] 重绘引擎
    专注于使用 Gemini 进行创意重绘
    """
    def __init__(self, api_key=None):
        # 从云端后台获取API密钥
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def create_context_image(self, original_image, mask_image):
        """
        创建带有涂抹区域标记的上下文图像，帮助Gemini理解要修改的区域
        """
        # 复制原图
        context_img = original_image.copy()
        
        # 将mask转换为RGBA，创建半透明的红色覆盖层
        mask_rgba = Image.new('RGBA', mask_image.size, (255, 0, 0, 100))  # 半透明红色
        
        # 只在mask的白色区域应用红色覆盖
        mask_array = np.array(mask_image)
        overlay_array = np.array(mask_rgba)
        
        # 创建最终的覆盖层
        final_overlay = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
        final_overlay_array = np.array(final_overlay)
        
        # 在mask区域应用红色
        final_overlay_array[mask_array > 128] = [255, 0, 0, 100]
        final_overlay = Image.fromarray(final_overlay_array, 'RGBA')
        
        # 将原图转换为RGBA并合成
        if context_img.mode != 'RGBA':
            context_img = context_img.convert('RGBA')
        
        context_img = Image.alpha_composite(context_img, final_overlay)
        return context_img.convert('RGB')

    def inpaint_with_gemini(self, original_image, mask_image, prompt):
        """
        使用Gemini进行创意重绘
        """
        try:
            if not self.api_key:
                st.error("❌ 未配置Google API密钥")
                return None
            
            # 使用models/gemini-3-pro-image-preview模型
            model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
            
            # 创建上下文图像，显示要修改的区域
            context_image = self.create_context_image(original_image, mask_image)
            
            # 简化的提示词，发挥Gemini的创造力
            simple_prompt = f"""
看这张图片，红色半透明区域是需要修改的地方。

请生成一张新图片，要求：
1. 红色区域替换为：{prompt}
2. 其他区域保持原样
3. 整体风格协调自然

直接生成图片，无需解释。
"""
            
            # 调用Gemini API
            response = model.generate_content([
                simple_prompt,
                context_image
            ])
            
            # 检查响应中是否包含图像
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data'):
                        # 处理返回的图像数据
                        image_data = part.inline_data.data
                        image_bytes = io.BytesIO(image_data)
                        return Image.open(image_bytes)
            
            # 如果没有图像返回，尝试文本到图像的方式
            st.warning("⚠️ Gemini未返回图像，尝试使用Imagen...")
            return self.fallback_imagen_generation(original_image, prompt)
            
        except Exception as e:
            st.error(f"❌ Gemini API调用失败: {str(e)}")
            return None

    def fallback_imagen_generation(self, original_image, prompt):
        """
        使用Imagen作为fallback方案
        """
        try:
            # 使用Imagen模型进行图像生成
            model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
            
            # 创建图像生成提示
            generation_prompt = f"""
基于参考图片的风格和构图，生成一张新图片。

要求：
- 保持原图的整体构图和风格
- 在指定区域添加：{prompt}
- 画面自然协调，无违和感

参考图片：
"""
            
            response = model.generate_content([
                generation_prompt,
                original_image
            ])
            
            # 这里需要根据实际的Imagen API响应格式进行调整
            # 目前作为示例返回原图
            st.info("💡 正在使用创意模式重新生成...")
            return original_image
            
        except Exception as e:
            st.error(f"❌ Imagen生成失败: {str(e)}")
            return None

    def inpaint(self, original_image, mask_image, prompt):
        """
        使用Gemini进行创意重绘
        :param original_image: PIL Image - 原始图像
        :param mask_image: PIL Image - 黑白遮罩（白色区域为重绘区域）
        :param prompt: str - 重绘指令
        """
        if not self.api_key:
            st.error("❌ 未配置Google API密钥，无法使用重绘功能")
            return None
        
        st.info("🎨 使用 Gemini 创意重绘引擎...")
        
        try:
            # 使用Gemini进行重绘
            result = self.inpaint_with_gemini(original_image, mask_image, prompt)
            
            if result and result != original_image:
                st.success("✨ Gemini重绘完成！")
                return result
            else:
                st.warning("⚠️ Gemini暂时无法生成图像，请稍后重试")
                st.info("""
                💡 提示：
                - 确保使用简洁明确的描述
                - 尝试不同的表达方式
                - Gemini的图像生成功能可能需要特定的API权限
                """)
                return None
                
        except Exception as e:
            st.error(f"❌ 重绘过程中出现错误: {str(e)}")
            return None
