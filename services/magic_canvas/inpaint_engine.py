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

    def create_instruction_image(self, original_image, mask_image):
        """
        创建带有清晰标记的指令图像，帮助AI理解要修改的区域
        """
        # 复制原图
        instruction_img = original_image.copy().convert('RGBA')
        
        # 创建更明显的标记覆盖层
        overlay = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 将mask转换为numpy数组进行处理
        mask_array = np.array(mask_image)
        
        # 找到mask的边界
        mask_coords = np.where(mask_array > 128)
        if len(mask_coords[0]) > 0:
            # 在mask区域绘制半透明红色填充
            for y, x in zip(mask_coords[0], mask_coords[1]):
                overlay_draw.point((x, y), fill=(255, 0, 0, 120))
            
            # 绘制边界线使区域更清晰
            from PIL import ImageFilter
            mask_edges = mask_image.filter(ImageFilter.FIND_EDGES)
            edge_coords = np.where(np.array(mask_edges) > 50)
            
            for y, x in zip(edge_coords[0], edge_coords[1]):
                overlay_draw.point((x, y), fill=(255, 0, 0, 200))
        
        # 合成最终的指令图像
        result = Image.alpha_composite(instruction_img, overlay)
        return result.convert('RGB')
    
    def traditional_inpaint(self, original_image, mask_image, prompt):
        """
        传统的图像修复方法，作为Gemini的备选方案
        """
        try:
            # 简单的基于内容感知的填充
            from PIL import ImageFilter
            
            # 创建一个基础的修复结果
            result = original_image.copy()
            
            # 对mask区域进行模糊处理，模拟简单的内容填充
            mask_array = np.array(mask_image)
            result_array = np.array(result)
            
            # 找到mask区域
            mask_coords = np.where(mask_array > 128)
            
            if len(mask_coords[0]) > 0:
                # 简单的颜色填充策略
                # 这里可以根据prompt调整填充颜色
                if "红" in prompt or "red" in prompt.lower():
                    fill_color = [200, 50, 50]
                elif "蓝" in prompt or "blue" in prompt.lower():
                    fill_color = [50, 50, 200]
                elif "绿" in prompt or "green" in prompt.lower():
                    fill_color = [50, 200, 50]
                elif "黄" in prompt or "yellow" in prompt.lower():
                    fill_color = [200, 200, 50]
                else:
                    # 使用周围像素的平均颜色
                    surrounding_pixels = []
                    for y, x in zip(mask_coords[0], mask_coords[1]):
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                ny, nx = y + dy, x + dx
                                if (0 <= ny < result_array.shape[0] and 
                                    0 <= nx < result_array.shape[1] and 
                                    mask_array[ny, nx] <= 128):
                                    surrounding_pixels.append(result_array[ny, nx])
                    
                    if surrounding_pixels:
                        fill_color = np.mean(surrounding_pixels, axis=0).astype(int)
                    else:
                        fill_color = [128, 128, 128]  # 灰色默认
                
                # 应用填充
                for y, x in zip(mask_coords[0], mask_coords[1]):
                    result_array[y, x] = fill_color
            
            result = Image.fromarray(result_array.astype(np.uint8))
            
            # 应用轻微的模糊来平滑边缘
            result = result.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            st.info(f"💡 使用传统方法进行了简单的颜色填充：{prompt}")
            return result
            
        except Exception as e:
            st.error(f"❌ 传统修复方法失败: {str(e)}")
            return None

    def inpaint_with_gemini(self, original_image, mask_image, prompt):
        """
        使用Gemini进行创意重绘
        """
        try:
            if not self.api_key:
                st.error("❌ 未配置Google API密钥")
                return None
            
            # 使用最新的Gemini模型
            model = genai.GenerativeModel('models/gemini-3-pro-preview')
            
            # 创建更清晰的指令图像
            instruction_image = self.create_instruction_image(original_image, mask_image)
            
            # 优化的提示词，避免蒙版被画进图片
            optimized_prompt = f"""
你是一个专业的图像编辑AI。请仔细观察这张图片：

任务：对图片进行局部重绘
- 图片中红色标记的区域需要被替换为：{prompt}
- 红色标记只是指示区域，不要在最终结果中显示红色标记
- 保持其他区域完全不变
- 确保新内容与周围环境自然融合
- 保持原图的光照、色调和风格

重要提醒：
1. 不要在结果中显示任何红色标记或蒙版
2. 只修改红色标记区域内的内容
3. 新内容要与原图风格一致
4. 边缘要自然过渡，无明显拼接痕迹

请直接生成修改后的完整图片。
"""
            
            # 调用Gemini API
            response = model.generate_content([
                optimized_prompt,
                instruction_image
            ])
            
            # 检查响应
            if response and hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        try:
                            # 处理返回的图像数据
                            import base64
                            image_data = base64.b64decode(part.inline_data.data)
                            image_bytes = io.BytesIO(image_data)
                            result_image = Image.open(image_bytes)
                            
                            # 确保尺寸匹配
                            if result_image.size != original_image.size:
                                result_image = result_image.resize(original_image.size, Image.Resampling.LANCZOS)
                            
                            return result_image
                        except Exception as img_error:
                            st.warning(f"图像解析错误: {img_error}")
                            continue
            
            # 如果Gemini不支持图像生成，使用传统的inpainting方法
            st.info("💡 Gemini当前不支持图像生成，使用传统修复方法...")
            return self.traditional_inpaint(original_image, mask_image, prompt)
            
        except Exception as e:
            st.error(f"❌ Gemini API调用失败: {str(e)}")
            return self.traditional_inpaint(original_image, mask_image, prompt)

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
