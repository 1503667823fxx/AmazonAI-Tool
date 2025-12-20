"""
A+ AI处理服务
负责Gemini API集成和图片合成处理
"""

import base64
import io
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from datetime import datetime

from app_utils.aplus_studio.models.core_models import Template, ProductData, UploadedFile


class GeminiService:
    """Gemini API服务"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = None
        self.retry_count = 3
        self.retry_delay = 1.0
        
        if api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化Gemini客户端"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            return True
        except Exception as e:
            print(f"Gemini客户端初始化失败: {e}")
            return False
    
    def set_api_key(self, api_key: str) -> bool:
        """设置API密钥"""
        self.api_key = api_key
        return self._initialize_client()
    
    def generate_content_suggestions(self, product_data: ProductData, template: Template) -> Dict[str, Any]:
        """生成内容建议"""
        if not self.model:
            return {"error": "Gemini客户端未初始化"}
        
        try:
            prompt = self._build_content_prompt(product_data, template)
            
            for attempt in range(self.retry_count):
                try:
                    response = self.model.generate_content(prompt)
                    
                    if response.text:
                        return {
                            "success": True,
                            "suggestions": self._parse_content_response(response.text),
                            "raw_response": response.text
                        }
                    else:
                        return {"error": "API返回空响应"}
                        
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        return {"error": f"API调用失败: {e}"}
            
        except Exception as e:
            return {"error": f"生成内容建议失败: {e}"}
    
    def analyze_product_image(self, image_data: bytes) -> Dict[str, Any]:
        """分析产品图片"""
        if not self.model:
            return {"error": "Gemini客户端未初始化"}
        
        try:
            # 将图片转换为PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            prompt = """
            请分析这张产品图片，提供以下信息：
            1. 产品类型和特征
            2. 主要颜色
            3. 风格特点
            4. 建议的文案方向
            5. 适合的模板类型
            
            请以JSON格式返回结果。
            """
            
            for attempt in range(self.retry_count):
                try:
                    response = self.model.generate_content([prompt, image])
                    
                    if response.text:
                        return {
                            "success": True,
                            "analysis": self._parse_image_analysis(response.text),
                            "raw_response": response.text
                        }
                    else:
                        return {"error": "API返回空响应"}
                        
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        return {"error": f"API调用失败: {e}"}
            
        except Exception as e:
            return {"error": f"图片分析失败: {e}"}
    
    def optimize_layout(self, template: Template, product_data: ProductData) -> Dict[str, Any]:
        """优化布局建议"""
        if not self.model:
            return {"error": "Gemini客户端未初始化"}
        
        try:
            prompt = self._build_layout_prompt(template, product_data)
            
            for attempt in range(self.retry_count):
                try:
                    response = self.model.generate_content(prompt)
                    
                    if response.text:
                        return {
                            "success": True,
                            "layout_suggestions": self._parse_layout_response(response.text),
                            "raw_response": response.text
                        }
                    else:
                        return {"error": "API返回空响应"}
                        
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    else:
                        return {"error": f"API调用失败: {e}"}
            
        except Exception as e:
            return {"error": f"布局优化失败: {e}"}
    
    def _build_content_prompt(self, product_data: ProductData, template: Template) -> str:
        """构建内容生成提示"""
        return f"""
        请为以下产品生成A+页面内容建议：
        
        产品信息：
        - 名称：{product_data.name}
        - 分类：{product_data.category}
        - 特性：{', '.join(product_data.features)}
        - 品牌：{product_data.brand_name}
        
        模板信息：
        - 名称：{template.name}
        - 风格：{template.description}
        - 配色：{', '.join(template.color_schemes)}
        
        请生成：
        1. 主标题建议（3个选项）
        2. 特性描述文案（针对每个特性）
        3. 品牌故事文案
        4. 号召性用语建议
        
        请以JSON格式返回，确保内容吸引人且符合A+页面规范。
        """
    
    def _build_layout_prompt(self, template: Template, product_data: ProductData) -> str:
        """构建布局优化提示"""
        return f"""
        请为以下产品和模板组合提供布局优化建议：
        
        模板：{template.name}
        产品：{product_data.name}
        产品特性数量：{len(product_data.features)}
        
        可替换区域：
        {json.dumps({name: area.to_dict() for name, area in template.replaceable_areas.items()}, indent=2, ensure_ascii=False)}
        
        请提供：
        1. 区域优先级排序
        2. 内容分布建议
        3. 视觉层次建议
        4. 色彩搭配建议
        
        请以JSON格式返回建议。
        """
    
    def _parse_content_response(self, response_text: str) -> Dict[str, Any]:
        """解析内容响应"""
        try:
            # 尝试解析JSON
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_text = response_text[start:end]
                return json.loads(json_text)
            else:
                # 如果不是JSON格式，返回原始文本
                return {"raw_content": response_text}
        except json.JSONDecodeError:
            return {"raw_content": response_text}
    
    def _parse_image_analysis(self, response_text: str) -> Dict[str, Any]:
        """解析图片分析响应"""
        try:
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_text = response_text[start:end]
                return json.loads(json_text)
            else:
                return {"analysis": response_text}
        except json.JSONDecodeError:
            return {"analysis": response_text}
    
    def _parse_layout_response(self, response_text: str) -> Dict[str, Any]:
        """解析布局响应"""
        try:
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_text = response_text[start:end]
                return json.loads(json_text)
            else:
                return {"suggestions": response_text}
        except json.JSONDecodeError:
            return {"suggestions": response_text}
    
    def get_api_status(self) -> Dict[str, Any]:
        """获取API状态"""
        return {
            "initialized": self.model is not None,
            "api_key_set": self.api_key is not None,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay
        }


class ImageCompositorService:
    """图片合成服务"""
    
    def __init__(self):
        self.supported_formats = ["JPEG", "PNG", "WebP"]
        self.max_image_size = (2048, 2048)
        self.quality_settings = {
            "high": 95,
            "medium": 85,
            "low": 75
        }
    
    def compose_aplus_page(self, template: Template, product_data: ProductData, 
                          customization_options: Dict[str, Any]) -> Dict[str, Any]:
        """合成A+页面"""
        try:
            # 创建基础画布
            canvas_width = customization_options.get("canvas_width", 970)
            canvas_height = customization_options.get("canvas_height", 600)
            
            canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
            draw = ImageDraw.Draw(canvas)
            
            # 应用背景色
            bg_color = self._get_background_color(customization_options.get("color_scheme", "默认"))
            canvas = Image.new("RGB", (canvas_width, canvas_height), bg_color)
            draw = ImageDraw.Draw(canvas)
            
            # 处理可替换区域
            composition_result = self._process_replaceable_areas(
                canvas, draw, template, product_data, customization_options
            )
            
            if not composition_result["success"]:
                return composition_result
            
            # 应用样式效果
            final_image = self._apply_style_effects(canvas, customization_options)
            
            # 转换为输出格式
            output_data = self._convert_to_output_format(
                final_image, 
                customization_options.get("output_format", "PNG"),
                customization_options.get("quality", "high")
            )
            
            return {
                "success": True,
                "image_data": output_data,
                "metadata": {
                    "width": canvas_width,
                    "height": canvas_height,
                    "format": customization_options.get("output_format", "PNG"),
                    "composition_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"图片合成失败: {e}"}
    
    def _process_replaceable_areas(self, canvas: Image.Image, draw: ImageDraw.Draw,
                                 template: Template, product_data: ProductData,
                                 customization_options: Dict[str, Any]) -> Dict[str, Any]:
        """处理可替换区域"""
        try:
            for area_name, area in template.replaceable_areas.items():
                if area.type == "image":
                    success = self._place_product_image(canvas, area, product_data)
                    if not success:
                        return {"success": False, "error": f"放置产品图片失败: {area_name}"}
                
                elif area.type == "text":
                    success = self._place_text_content(draw, area, product_data, area_name)
                    if not success:
                        return {"success": False, "error": f"放置文本内容失败: {area_name}"}
                
                elif area.type == "logo":
                    success = self._place_brand_logo(canvas, area, product_data)
                    if not success:
                        return {"success": False, "error": f"放置品牌logo失败: {area_name}"}
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": f"处理可替换区域失败: {e}"}
    
    def _place_product_image(self, canvas: Image.Image, area, product_data: ProductData) -> bool:
        """放置产品图片"""
        try:
            if not product_data.images:
                return True  # 没有图片不算错误
            
            # 使用第一张产品图片
            product_image_data = product_data.images[0].data
            product_image = Image.open(io.BytesIO(product_image_data))
            
            # 调整图片尺寸适配区域
            target_size = (area.width, area.height)
            
            # 保持宽高比的缩放
            product_image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # 计算居中位置
            paste_x = area.x + (area.width - product_image.width) // 2
            paste_y = area.y + (area.height - product_image.height) // 2
            
            # 粘贴图片
            if product_image.mode == 'RGBA':
                canvas.paste(product_image, (paste_x, paste_y), product_image)
            else:
                canvas.paste(product_image, (paste_x, paste_y))
            
            return True
            
        except Exception as e:
            print(f"放置产品图片失败: {e}")
            return False
    
    def _place_text_content(self, draw: ImageDraw.Draw, area, product_data: ProductData, area_name: str) -> bool:
        """放置文本内容"""
        try:
            # 根据区域名称确定文本内容
            text_content = self._get_text_content(area_name, product_data)
            
            if not text_content:
                return True  # 没有文本内容不算错误
            
            # 尝试加载字体
            try:
                font_size = min(area.height // 3, 24)  # 根据区域高度调整字体大小
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # 计算文本位置（居中）
            bbox = draw.textbbox((0, 0), text_content, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            text_x = area.x + (area.width - text_width) // 2
            text_y = area.y + (area.height - text_height) // 2
            
            # 绘制文本
            draw.text((text_x, text_y), text_content, fill="black", font=font)
            
            return True
            
        except Exception as e:
            print(f"放置文本内容失败: {e}")
            return False
    
    def _place_brand_logo(self, canvas: Image.Image, area, product_data: ProductData) -> bool:
        """放置品牌logo"""
        try:
            # 这里可以实现品牌logo的放置逻辑
            # 目前简单绘制品牌名称
            draw = ImageDraw.Draw(canvas)
            
            if product_data.brand_name:
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                # 计算文本位置
                bbox = draw.textbbox((0, 0), product_data.brand_name, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_x = area.x + (area.width - text_width) // 2
                text_y = area.y + (area.height - text_height) // 2
                
                # 使用品牌颜色
                brand_color = product_data.brand_color if product_data.brand_color else "black"
                draw.text((text_x, text_y), product_data.brand_name, fill=brand_color, font=font)
            
            return True
            
        except Exception as e:
            print(f"放置品牌logo失败: {e}")
            return False
    
    def _get_text_content(self, area_name: str, product_data: ProductData) -> str:
        """根据区域名称获取文本内容"""
        content_map = {
            "title_text": product_data.name,
            "product_name": product_data.name,
            "brand_name": product_data.brand_name,
            "feature_1": product_data.features[0] if len(product_data.features) > 0 else "",
            "feature_2": product_data.features[1] if len(product_data.features) > 1 else "",
            "feature_3": product_data.features[2] if len(product_data.features) > 2 else "",
        }
        
        return content_map.get(area_name, "")
    
    def _get_background_color(self, color_scheme: str) -> str:
        """获取背景颜色"""
        color_schemes = {
            "蓝色科技": "#E3F2FD",
            "黑白简约": "#FAFAFA",
            "渐变炫彩": "#F3E5F5",
            "粉色浪漫": "#FCE4EC",
            "金色奢华": "#FFF8E1",
            "自然绿调": "#E8F5E8",
            "默认": "#FFFFFF"
        }
        
        return color_schemes.get(color_scheme, "#FFFFFF")
    
    def _apply_style_effects(self, image: Image.Image, customization_options: Dict[str, Any]) -> Image.Image:
        """应用样式效果"""
        # 这里可以添加各种图像效果
        # 目前返回原图
        return image
    
    def _convert_to_output_format(self, image: Image.Image, output_format: str, quality: str) -> bytes:
        """转换为输出格式"""
        output_buffer = io.BytesIO()
        
        format_map = {
            "PNG": "PNG",
            "JPEG": "JPEG",
            "JPG": "JPEG",
            "WebP": "WEBP"
        }
        
        pil_format = format_map.get(output_format.upper(), "PNG")
        quality_value = self.quality_settings.get(quality, 85)
        
        if pil_format == "JPEG":
            # JPEG不支持透明度，转换为RGB
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(output_buffer, format=pil_format, quality=quality_value)
        else:
            image.save(output_buffer, format=pil_format)
        
        return output_buffer.getvalue()
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        return self.supported_formats.copy()
    
    def get_max_image_size(self) -> Tuple[int, int]:
        """获取最大图片尺寸"""
        return self.max_image_size