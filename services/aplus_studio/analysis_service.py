"""
Product Analysis Service for A+ Studio system.

This service uses Gemini AI models to analyze product listings and images,
extracting key information needed for A+ image generation.
"""

import asyncio
import json
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from PIL import Image
import google.generativeai as genai

from .models import (
    ProductInfo, ListingAnalysis, ImageAnalysis, 
    VisualStyle, AnalysisResult
)
from .config import aplus_config


class ProductAnalysisService:
    """产品分析服务 - 使用Gemini模型分析产品listing和图片"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.config = aplus_config
        self.api_key = api_key  # 保存传入的API密钥
        self._setup_gemini()
    
    def _setup_gemini(self):
        """设置Gemini API"""
        # 优先使用传入的API密钥，然后使用配置的API密钥
        effective_api_key = self.api_key
        
        if not effective_api_key and self.config.is_configured:
            effective_api_key = self.config.gemini_config.api_key
        
        # 如果还是没有API密钥，尝试直接从secrets获取
        if not effective_api_key:
            try:
                import streamlit as st
                if hasattr(st, 'secrets'):
                    effective_api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass
        
        if effective_api_key:
            genai.configure(api_key=effective_api_key)
            # 使用配置的模型或默认模型
            text_model_name = (self.config.gemini_config.text_model 
                             if self.config.is_configured 
                             else "models/gemini-3-pro-preview")
            image_model_name = (self.config.gemini_config.image_model 
                              if self.config.is_configured 
                              else "models/gemini-3-pro-image-preview")
            
            self.text_model = genai.GenerativeModel(text_model_name)
            self.vision_model = genai.GenerativeModel(image_model_name)
        else:
            self.text_model = None
            self.vision_model = None
            # 记录配置问题，但不抛出异常
            print("Warning: Gemini API not configured properly")
    
    async def analyze_listing(self, text: str) -> ListingAnalysis:
        """分析产品listing文本"""
        if not self.text_model:
            raise ValueError("Gemini API配置未找到。请检查API密钥配置。")
        
        prompt = f"""
        请分析以下产品listing，提取关键信息用于Amazon A+页面制作。请以JSON格式返回分析结果：

        产品描述：
        {text}

        请提供以下信息的JSON格式分析：
        {{
            "product_category": "产品类别（如Electronics, Home & Kitchen, Sports等）",
            "target_demographics": "目标用户群体（详细描述，包括年龄、收入、生活方式）",
            "key_selling_points": ["核心卖点1", "核心卖点2", "核心卖点3"],
            "competitive_advantages": ["竞争优势1", "竞争优势2"],
            "emotional_triggers": ["情感触发点1", "情感触发点2"],
            "technical_specifications": {{"规格名称": "规格值"}},
            "confidence_score": 0.95
        }}

        分析要求：
        1. 专注于北美市场消费者心理
        2. 识别适合A+页面展示的卖点
        3. 提取能引起情感共鸣的元素
        4. 确保分析结果适合视觉化展示
        
        只返回JSON，不要其他文字。
        """
        
        try:
            response = await asyncio.to_thread(
                self.text_model.generate_content, prompt
            )
            
            # 解析JSON响应
            response_text = response.text.strip()
            
            # 清理响应文本，移除可能的markdown标记
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                analysis_data = json.loads(response_text)
                
                return ListingAnalysis(
                    product_category=analysis_data.get("product_category", "Unknown"),
                    target_demographics=analysis_data.get("target_demographics", "General consumers"),
                    key_selling_points=analysis_data.get("key_selling_points", []),
                    competitive_advantages=analysis_data.get("competitive_advantages", []),
                    emotional_triggers=analysis_data.get("emotional_triggers", []),
                    technical_specifications=analysis_data.get("technical_specifications", {}),
                    confidence_score=analysis_data.get("confidence_score", 0.8)
                )
                
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，尝试从文本中提取信息
                return self._extract_listing_info_from_text(response_text, text)
            
        except Exception as e:
            raise Exception(f"Listing analysis failed: {str(e)}")
    
    def _extract_listing_info_from_text(self, response_text: str, original_text: str) -> ListingAnalysis:
        """从非结构化文本中提取listing信息的备用方法"""
        # 基本的文本分析作为备用
        words = original_text.lower().split()
        
        # 简单的类别识别
        category_keywords = {
            "electronics": ["electronic", "digital", "tech", "device", "gadget"],
            "home": ["home", "kitchen", "house", "room", "furniture"],
            "sports": ["sport", "fitness", "exercise", "outdoor", "athletic"],
            "beauty": ["beauty", "cosmetic", "skin", "hair", "makeup"],
            "clothing": ["clothing", "apparel", "wear", "fashion", "style"]
        }
        
        detected_category = "General"
        for category, keywords in category_keywords.items():
            if any(keyword in words for keyword in keywords):
                detected_category = category.title()
                break
        
        return ListingAnalysis(
            product_category=detected_category,
            target_demographics="North American middle-class consumers",
            key_selling_points=["Quality construction", "User-friendly design", "Great value"],
            competitive_advantages=["Superior quality", "Competitive pricing"],
            emotional_triggers=["Convenience", "Reliability", "Status"],
            technical_specifications={},
            confidence_score=0.6
        )
    
    async def analyze_multiple_images(self, images: List[Image.Image]) -> ImageAnalysis:
        """分析多张产品图片并合并洞察"""
        if not images:
            raise ValueError("No images provided for analysis")
        
        if len(images) == 1:
            return await self.analyze_single_image_comprehensive(images[0])
        
        # 分析每张图片
        analyses = []
        for i, image in enumerate(images[:3]):  # 最多分析前3张图片以控制成本
            try:
                analysis = await self.analyze_single_image_comprehensive(image)
                analyses.append(analysis)
            except Exception as e:
                print(f"Warning: Failed to analyze image {i+1}: {str(e)}")
                continue
        
        if not analyses:
            raise Exception("Failed to analyze any of the provided images")
        
        # 合并分析结果
        return self._merge_image_analyses(analyses)
    
    async def analyze_single_image_comprehensive(self, image: Image.Image) -> ImageAnalysis:
        """对单张图片进行全面分析"""
        try:
            # 基础图片分析
            basic_analysis = await self.analyze_product_images([image])
            
            # 提取详细颜色调色板
            color_palette = await self.extract_color_palette(image)
            
            # 分析材质特征
            material_analysis = await self.analyze_material_characteristics(image)
            
            # 评估构图质量
            composition_analysis = await self.evaluate_composition_quality(image)
            
            # 合并所有分析结果
            enhanced_analysis = ImageAnalysis(
                dominant_colors=color_palette if color_palette else basic_analysis.dominant_colors,
                material_types=material_analysis.get("primary_materials", basic_analysis.material_types),
                design_style=basic_analysis.design_style,
                lighting_conditions=basic_analysis.lighting_conditions,
                composition_elements=composition_analysis.get("composition_rules", basic_analysis.composition_elements),
                quality_assessment=self._determine_overall_quality(basic_analysis, composition_analysis),
                confidence_score=min(basic_analysis.confidence_score, 
                                   composition_analysis.get("professional_quality", 7) / 10)
            )
            
            return enhanced_analysis
            
        except Exception as e:
            # 如果增强分析失败，回退到基础分析
            print(f"Enhanced analysis failed, using basic analysis: {str(e)}")
            return await self.analyze_product_images([image])
    
    def _determine_overall_quality(self, basic_analysis: ImageAnalysis, composition_analysis: Dict[str, Any]) -> str:
        """基于多个分析结果确定整体质量评估"""
        # 获取构图质量分数
        composition_score = composition_analysis.get("professional_quality", 7)
        aplus_score = composition_analysis.get("aplus_suitability", 7)
        
        # 基础质量映射
        quality_map = {
            "excellent": 9,
            "good": 7,
            "fair": 5,
            "needs_improvement": 3
        }
        
        basic_score = quality_map.get(basic_analysis.quality_assessment, 7)
        
        # 计算综合分数
        overall_score = (basic_score + composition_score + aplus_score) / 3
        
        # 映射回质量等级
        if overall_score >= 8.5:
            return "excellent"
        elif overall_score >= 7:
            return "good"
        elif overall_score >= 5:
            return "fair"
        else:
            return "needs_improvement"
    
    def _merge_image_analyses(self, analyses: List[ImageAnalysis]) -> ImageAnalysis:
        """合并多个图片分析结果"""
        if len(analyses) == 1:
            return analyses[0]
        
        # 合并主要颜色（去重并保持前几个最常见的）
        all_colors = []
        for analysis in analyses:
            all_colors.extend(analysis.dominant_colors)
        
        # 去重并保持顺序
        seen_colors = set()
        merged_colors = []
        for color in all_colors:
            if color not in seen_colors:
                seen_colors.add(color)
                merged_colors.append(color)
                if len(merged_colors) >= 5:  # 最多保留5种主要颜色
                    break
        
        # 合并材质类型
        all_materials = []
        for analysis in analyses:
            all_materials.extend(analysis.material_types)
        merged_materials = list(set(all_materials))  # 去重
        
        # 选择最常见的设计风格
        styles = [analysis.design_style for analysis in analyses]
        merged_style = max(set(styles), key=styles.count)
        
        # 选择最常见的光照条件
        lighting = [analysis.lighting_conditions for analysis in analyses]
        merged_lighting = max(set(lighting), key=lighting.count)
        
        # 合并构图元素
        all_composition = []
        for analysis in analyses:
            all_composition.extend(analysis.composition_elements)
        merged_composition = list(set(all_composition))
        
        # 选择最好的质量评估
        quality_scores = {"excellent": 4, "good": 3, "fair": 2, "needs_improvement": 1}
        qualities = [analysis.quality_assessment for analysis in analyses]
        best_quality = max(qualities, key=lambda q: quality_scores.get(q, 0))
        
        # 计算平均置信度
        avg_confidence = sum(analysis.confidence_score for analysis in analyses) / len(analyses)
        
        return ImageAnalysis(
            dominant_colors=merged_colors,
            material_types=merged_materials,
            design_style=merged_style,
            lighting_conditions=merged_lighting,
            composition_elements=merged_composition,
            quality_assessment=best_quality,
            confidence_score=avg_confidence
        )
    
    async def analyze_product_images(self, images: List[Image.Image]) -> ImageAnalysis:
        """分析产品图片，提取颜色、材质、设计风格等视觉特征"""
        if not self.vision_model:
            raise ValueError("Gemini Vision API配置未找到。请检查API密钥配置。")
        
        if not images:
            raise ValueError("No images provided for analysis")
        
        prompt = """
        请分析这些产品图片，提取适合Amazon A+页面制作的视觉特征。请以JSON格式返回分析结果：

        {
            "dominant_colors": ["主要颜色的十六进制代码，如#FF5733", "#2E86AB"],
            "material_types": ["材质类型，如metal, plastic, leather, fabric, wood, glass"],
            "design_style": "设计风格（如modern, classic, minimalist, industrial, luxury）",
            "lighting_conditions": "光照条件（如natural, studio, golden_hour, high_contrast, soft_diffused）",
            "composition_elements": ["构图元素，如centered, rule_of_thirds, diagonal, symmetrical"],
            "quality_assessment": "图片质量评估（如excellent, good, fair, needs_improvement）",
            "texture_details": ["纹理细节，如smooth, rough, glossy, matte, textured"],
            "product_positioning": "产品摆放角度（如front_view, three_quarter, side_view, top_down）",
            "background_style": "背景风格（如white_background, lifestyle_scene, studio_setup, natural_environment）",
            "visual_appeal_score": 8.5,
            "confidence_score": 0.92
        }

        分析要求：
        1. 专注于适合A+页面展示的视觉元素
        2. 识别能够在600x450尺寸下保持清晰的细节
        3. 评估颜色搭配是否符合北美审美
        4. 分析材质表现是否能突出产品品质感
        5. 考虑光线和构图对情感传达的影响

        只返回JSON，不要其他文字。
        """
        
        try:
            # 使用第一张图片进行分析，如果有多张图片，可以分析主要的那张
            main_image = images[0]
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content, [prompt, main_image]
            )
            
            # 解析JSON响应
            response_text = response.text.strip()
            
            # 清理响应文本
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                analysis_data = json.loads(response_text)
                
                return ImageAnalysis(
                    dominant_colors=analysis_data.get("dominant_colors", ["#FFFFFF", "#000000"]),
                    material_types=analysis_data.get("material_types", ["unknown"]),
                    design_style=analysis_data.get("design_style", "modern"),
                    lighting_conditions=analysis_data.get("lighting_conditions", "natural"),
                    composition_elements=analysis_data.get("composition_elements", ["centered"]),
                    quality_assessment=analysis_data.get("quality_assessment", "good"),
                    confidence_score=analysis_data.get("confidence_score", 0.8)
                )
                
            except json.JSONDecodeError:
                # 备用方案：基于图片进行基础分析
                return await self._analyze_image_basic(main_image)
            
        except Exception as e:
            raise Exception(f"Image analysis failed: {str(e)}")
    
    async def extract_color_palette(self, image: Image.Image) -> List[str]:
        """提取图片的主要颜色调色板"""
        if not self.vision_model:
            # 使用基础颜色提取作为备用
            return await self._extract_colors_basic(image)
        
        prompt = """
        请分析这张图片的颜色构成，提取主要的颜色调色板。请以JSON格式返回：

        {
            "primary_colors": ["#主要颜色1", "#主要颜色2", "#主要颜色3"],
            "accent_colors": ["#强调色1", "#强调色2"],
            "neutral_colors": ["#中性色1", "#中性色2"],
            "color_harmony": "颜色和谐度评估（如complementary, analogous, triadic, monochromatic）",
            "color_temperature": "色温（如warm, cool, neutral）",
            "saturation_level": "饱和度水平（如high, medium, low）"
        }

        要求：
        1. 提取最具代表性的颜色
        2. 考虑颜色在A+页面中的视觉效果
        3. 评估颜色搭配的专业性和吸引力

        只返回JSON，不要其他文字。
        """
        
        try:
            response = await asyncio.to_thread(
                self.vision_model.generate_content, [prompt, image]
            )
            
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            color_data = json.loads(response_text)
            
            # 合并所有颜色
            all_colors = []
            all_colors.extend(color_data.get("primary_colors", []))
            all_colors.extend(color_data.get("accent_colors", []))
            all_colors.extend(color_data.get("neutral_colors", []))
            
            return all_colors[:6]  # 返回最多6种主要颜色
            
        except Exception:
            # 备用方案
            return await self._extract_colors_basic(image)
    
    async def _extract_colors_basic(self, image: Image.Image) -> List[str]:
        """基础颜色提取的备用方法"""
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 缩小图片以提高处理速度
            image.thumbnail((150, 150))
            
            # 获取颜色统计
            colors = image.getcolors(maxcolors=256*256*256)
            if not colors:
                return ["#FFFFFF", "#000000"]
            
            # 按出现频率排序
            sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
            
            # 提取前几种主要颜色
            dominant_colors = []
            for count, color in sorted_colors[:6]:
                # 跳过过于相似的颜色
                hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                if not self._is_similar_color(hex_color, dominant_colors):
                    dominant_colors.append(hex_color)
                if len(dominant_colors) >= 5:
                    break
            
            return dominant_colors if dominant_colors else ["#FFFFFF", "#000000"]
            
        except Exception:
            return ["#FFFFFF", "#000000"]
    
    def _is_similar_color(self, new_color: str, existing_colors: List[str], threshold: int = 30) -> bool:
        """检查颜色是否与现有颜色过于相似"""
        if not existing_colors:
            return False
        
        try:
            # 转换新颜色为RGB
            new_r = int(new_color[1:3], 16)
            new_g = int(new_color[3:5], 16)
            new_b = int(new_color[5:7], 16)
            
            for existing_color in existing_colors:
                # 转换现有颜色为RGB
                exist_r = int(existing_color[1:3], 16)
                exist_g = int(existing_color[3:5], 16)
                exist_b = int(existing_color[5:7], 16)
                
                # 计算颜色距离
                distance = ((new_r - exist_r) ** 2 + (new_g - exist_g) ** 2 + (new_b - exist_b) ** 2) ** 0.5
                
                if distance < threshold:
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def analyze_material_characteristics(self, image: Image.Image) -> Dict[str, Any]:
        """分析产品材质特征"""
        if not self.vision_model:
            return {"materials": ["unknown"], "texture_quality": "medium", "surface_finish": "unknown"}
        
        prompt = """
        请分析这张产品图片的材质特征，专注于材质类型和表面处理。请以JSON格式返回：

        {
            "primary_materials": ["主要材质，如metal, plastic, leather, fabric, wood, glass, ceramic"],
            "surface_finishes": ["表面处理，如brushed, polished, matte, glossy, textured, smooth"],
            "texture_quality": "纹理质量评估（如premium, standard, basic）",
            "material_authenticity": "材质真实感（如authentic, synthetic, mixed）",
            "craftsmanship_level": "工艺水平（如artisan, industrial, mass_produced）",
            "durability_indicators": ["耐用性指标，如reinforced_edges, quality_joints, protective_coating"],
            "luxury_perception": "奢华感知度评分（1-10）"
        }

        分析要求：
        1. 识别能够传达品质感的材质特征
        2. 评估材质在A+页面中的视觉表现力
        3. 考虑材质对消费者购买决策的影响

        只返回JSON，不要其他文字。
        """
        
        try:
            response = await asyncio.to_thread(
                self.vision_model.generate_content, [prompt, image]
            )
            
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            material_data = json.loads(response_text)
            return material_data
            
        except Exception as e:
            # 备用方案：返回基础材质分析
            return {
                "primary_materials": ["unknown"],
                "surface_finishes": ["standard"],
                "texture_quality": "medium",
                "material_authenticity": "unknown",
                "craftsmanship_level": "standard",
                "durability_indicators": [],
                "luxury_perception": 5
            }
    
    async def evaluate_composition_quality(self, image: Image.Image) -> Dict[str, Any]:
        """评估图片构图质量"""
        if not self.vision_model:
            return self._evaluate_composition_basic(image)
        
        prompt = """
        请分析这张产品图片的构图质量，评估其在A+页面中的视觉效果。请以JSON格式返回：

        {
            "composition_rules": ["应用的构图规则，如rule_of_thirds, golden_ratio, symmetry, leading_lines"],
            "visual_balance": "视觉平衡评估（如balanced, left_heavy, right_heavy, top_heavy, bottom_heavy）",
            "focal_point_clarity": "焦点清晰度（如clear, moderate, unclear）",
            "background_effectiveness": "背景效果（如enhances_product, neutral, distracting）",
            "depth_perception": "景深效果（如excellent, good, flat）",
            "professional_quality": "专业质量评分（1-10）",
            "aplus_suitability": "A+页面适用性评分（1-10）",
            "improvement_suggestions": ["改进建议"]
        }

        评估标准：
        1. 产品是否为视觉焦点
        2. 构图是否符合专业摄影标准
        3. 是否适合600x450尺寸展示
        4. 视觉层次是否清晰

        只返回JSON，不要其他文字。
        """
        
        try:
            response = await asyncio.to_thread(
                self.vision_model.generate_content, [prompt, image]
            )
            
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            composition_data = json.loads(response_text)
            return composition_data
            
        except Exception as e:
            return self._evaluate_composition_basic(image)
    
    def _evaluate_composition_basic(self, image: Image.Image) -> Dict[str, Any]:
        """基础构图评估的备用方法"""
        width, height = image.size
        aspect_ratio = width / height
        
        # 基于尺寸和比例的基础评估
        quality_score = 7  # 默认分数
        
        if width >= 1200 and height >= 900:
            quality_score += 1
        elif width < 600 or height < 450:
            quality_score -= 2
        
        # 评估宽高比
        if 1.2 <= aspect_ratio <= 1.5:  # 接近4:3比例
            quality_score += 1
        
        return {
            "composition_rules": ["centered"],
            "visual_balance": "balanced",
            "focal_point_clarity": "moderate",
            "background_effectiveness": "neutral",
            "depth_perception": "good",
            "professional_quality": min(10, max(1, quality_score)),
            "aplus_suitability": min(10, max(1, quality_score)),
            "improvement_suggestions": ["Consider professional lighting", "Optimize for 4:3 aspect ratio"]
        }
    
    async def analyze_product_images_detailed(self, images: List[Image.Image]) -> ImageAnalysis:
        """详细分析产品图片，提取适合A+页面制作的视觉特征"""
        if not self.vision_model:
            raise ValueError("Gemini Vision API not configured")
        
        if not images:
            raise ValueError("No images provided for analysis")
        
        prompt = """
        请分析这些产品图片，提取适合Amazon A+页面制作的视觉特征。请以JSON格式返回分析结果：

        {
            "dominant_colors": ["主要颜色的十六进制代码，如#FF5733", "#2E86AB"],
            "material_types": ["材质类型，如metal, plastic, leather, fabric, wood, glass"],
            "design_style": "设计风格（如modern, classic, minimalist, industrial, luxury）",
            "lighting_conditions": "光照条件（如natural, studio, golden_hour, high_contrast, soft_diffused）",
            "composition_elements": ["构图元素，如centered, rule_of_thirds, diagonal, symmetrical"],
            "quality_assessment": "图片质量评估（如excellent, good, fair, needs_improvement）",
            "texture_details": ["纹理细节，如smooth, rough, glossy, matte, textured"],
            "product_positioning": "产品摆放角度（如front_view, three_quarter, side_view, top_down）",
            "background_style": "背景风格（如white_background, lifestyle_scene, studio_setup, natural_environment）",
            "visual_appeal_score": 8.5,
            "confidence_score": 0.92
        }

        分析要求：
        1. 专注于适合A+页面展示的视觉元素
        2. 识别能够在600x450尺寸下保持清晰的细节
        3. 评估颜色搭配是否符合北美审美
        4. 分析材质表现是否能突出产品品质感
        5. 考虑光线和构图对情感传达的影响

        只返回JSON，不要其他文字。
        """
        
        try:
            # 使用第一张图片进行分析，如果有多张图片，可以分析主要的那张
            main_image = images[0]
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content, [prompt, main_image]
            )
            
            # 解析JSON响应
            response_text = response.text.strip()
            
            # 清理响应文本
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                analysis_data = json.loads(response_text)
                
                return ImageAnalysis(
                    dominant_colors=analysis_data.get("dominant_colors", ["#FFFFFF", "#000000"]),
                    material_types=analysis_data.get("material_types", ["unknown"]),
                    design_style=analysis_data.get("design_style", "modern"),
                    lighting_conditions=analysis_data.get("lighting_conditions", "natural"),
                    composition_elements=analysis_data.get("composition_elements", ["centered"]),
                    quality_assessment=analysis_data.get("quality_assessment", "good"),
                    confidence_score=analysis_data.get("confidence_score", 0.8)
                )
                
            except json.JSONDecodeError:
                # 备用方案：基于图片进行基础分析
                return await self._analyze_image_basic(main_image)
            
        except Exception as e:
            raise Exception(f"Image analysis failed: {str(e)}")
    
    async def _analyze_image_basic(self, image: Image.Image) -> ImageAnalysis:
        """基础图片分析的备用方法"""
        # 获取图片的基本信息
        width, height = image.size
        
        # 简单的颜色分析
        try:
            # 转换为RGB模式以便分析
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 获取主要颜色（简化版本）
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                # 获取最常见的几种颜色
                sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
                dominant_colors = []
                for count, color in sorted_colors[:3]:
                    hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                    dominant_colors.append(hex_color)
            else:
                dominant_colors = ["#FFFFFF", "#000000"]
                
        except Exception:
            dominant_colors = ["#FFFFFF", "#000000"]
        
        # 基于图片尺寸和比例推断质量
        quality = "good"
        if width >= 1200 and height >= 900:
            quality = "excellent"
        elif width < 600 or height < 450:
            quality = "needs_improvement"
        
        return ImageAnalysis(
            dominant_colors=dominant_colors,
            material_types=["unknown"],
            design_style="modern",
            lighting_conditions="natural",
            composition_elements=["centered"],
            quality_assessment=quality,
            confidence_score=0.6
        )
    
    def extract_visual_style(self, analysis: ImageAnalysis) -> VisualStyle:
        """基于图片分析提取视觉风格"""
        # 构建一致性指南
        consistency_guidelines = {
            "color_harmony": "maintain_palette",
            "lighting_consistency": "match_original",
            "composition_style": "follow_rules",
            "material_representation": "preserve_texture",
            "aesthetic_direction": analysis.design_style
        }
        
        # 根据设计风格调整构图规则
        composition_rules = analysis.composition_elements.copy()
        if analysis.design_style in ["luxury", "premium", "minimalist"]:
            composition_rules.append("negative_space")
            composition_rules.append("clean_lines")
        elif analysis.design_style in ["lifestyle", "casual"]:
            composition_rules.append("natural_placement")
            composition_rules.append("contextual_elements")
        
        # 根据光照条件确定光线风格
        lighting_style = analysis.lighting_conditions
        if "golden" in lighting_style.lower():
            consistency_guidelines["time_of_day"] = "golden_hour"
        elif "studio" in lighting_style.lower():
            consistency_guidelines["lighting_setup"] = "professional_studio"
        
        return VisualStyle(
            color_palette=analysis.dominant_colors,
            lighting_style=lighting_style,
            composition_rules=composition_rules,
            aesthetic_direction=analysis.design_style,
            consistency_guidelines=consistency_guidelines
        )
    
    async def generate_market_insights(self, listing: ListingAnalysis) -> dict:
        """基于listing分析生成市场洞察"""
        if not self.text_model:
            raise ValueError("Gemini API not configured")
        
        prompt = f"""
        基于以下产品分析，生成针对北美市场的营销洞察和A+页面制作建议。请以JSON格式返回：

        产品类别: {listing.product_category}
        目标用户: {listing.target_demographics}
        核心卖点: {', '.join(listing.key_selling_points)}
        竞争优势: {', '.join(listing.competitive_advantages)}
        情感触发点: {', '.join(listing.emotional_triggers)}

        请提供以下JSON格式的洞察：
        {{
            "consumer_psychology": "北美消费者心理分析（详细描述购买动机和决策因素）",
            "aplus_recommendations": "A+页面展示建议（具体的视觉和内容建议）",
            "visual_style_suggestions": "视觉风格推荐（颜色、光线、构图建议）",
            "emotional_connection_strategy": "情感连接策略（如何在视觉上建立情感联系）",
            "lifestyle_integration": "生活方式融入建议（如何展示产品融入北美生活场景）",
            "trust_building_elements": "信任建立要素（需要强调的可信度元素）"
        }}

        要求：
        1. 专注于北美中产阶级消费心理
        2. 考虑Amazon A+页面的视觉特点
        3. 提供具体可执行的建议
        4. 强调情感共鸣和生活方式匹配

        只返回JSON，不要其他文字。
        """
        
        try:
            response = await asyncio.to_thread(
                self.text_model.generate_content, prompt
            )
            
            # 解析JSON响应
            response_text = response.text.strip()
            
            # 清理响应文本
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                insights_data = json.loads(response_text)
                return insights_data
                
            except json.JSONDecodeError:
                # 备用方案：返回基于分析的默认洞察
                return self._generate_default_insights(listing)
            
        except Exception as e:
            raise Exception(f"Market insights generation failed: {str(e)}")
    
    def _generate_default_insights(self, listing: ListingAnalysis) -> dict:
        """生成默认市场洞察的备用方法"""
        return {
            "consumer_psychology": f"北美{listing.target_demographics}重视品质、便利性和价值。他们在购买决策中会考虑产品的实用性、耐用性和社会认同感。",
            "aplus_recommendations": f"突出{', '.join(listing.key_selling_points[:2])}，使用高质量的生活场景图片，展示产品在实际使用中的价值。",
            "visual_style_suggestions": "采用温暖的自然光线，使用符合北美审美的色彩搭配，注重构图的平衡和专业感。",
            "emotional_connection_strategy": f"通过展示{', '.join(listing.emotional_triggers)}来建立情感连接，让消费者看到产品如何改善他们的生活质量。",
            "lifestyle_integration": "将产品自然地融入到典型的北美家庭场景中，展示其在日常生活中的实际应用价值。",
            "trust_building_elements": f"强调{', '.join(listing.competitive_advantages)}，展示产品认证、保修信息和用户评价。"
        }
    
    async def analyze_product(self, product_info: ProductInfo) -> AnalysisResult:
        """完整的产品分析流程"""
        # 分析listing文本
        listing_analysis = await self.analyze_listing(
            f"{product_info.name}\n{product_info.description}\n" +
            f"特征: {', '.join(product_info.key_features)}\n" +
            f"目标用户: {product_info.target_audience}\n" +
            f"价格范围: {product_info.price_range}"
        )
        
        # 分析产品图片
        image_analysis = None
        if product_info.uploaded_images:
            # 转换为PIL Images（如果需要）
            pil_images = []
            for img in product_info.uploaded_images:
                if isinstance(img, Image.Image):
                    pil_images.append(img)
                # 这里可以添加其他图片格式的处理
            
            if pil_images:
                image_analysis = await self.analyze_multiple_images(pil_images)
        
        # 如果没有图片分析，创建默认结构
        if not image_analysis:
            image_analysis = ImageAnalysis(
                dominant_colors=["#FFFFFF", "#333333"],
                material_types=["unknown"],
                design_style="modern",
                lighting_conditions="natural",
                composition_elements=["centered"],
                quality_assessment="pending",
                confidence_score=0.5
            )
        
        # 提取视觉风格
        visual_style = self.extract_visual_style(image_analysis)
        
        return AnalysisResult(
            listing_analysis=listing_analysis,
            image_analysis=image_analysis,
            visual_style=visual_style,
            product_info=product_info  # 添加产品信息
        )
    
    async def analyze_product_simplified(self, product_info: ProductInfo) -> AnalysisResult:
        """简化的产品分析流程，用于错误恢复"""
        try:
            # 使用更简单的分析逻辑
            simplified_listing_analysis = ListingAnalysis(
                product_category=self._extract_simple_category(product_info.description),
                target_demographics="消费者",
                key_selling_points=self._extract_simple_features(product_info.description),
                competitive_advantages=["高质量", "实用性强"],
                emotional_triggers=["便利", "品质"],
                technical_specifications={},
                confidence_score=0.6
            )
            
            # 简化的图片分析
            simplified_image_analysis = None
            if product_info.uploaded_images:
                simplified_image_analysis = ImageAnalysis(
                    dominant_colors=["#FFFFFF", "#000000"],
                    material_types=["通用材质"],
                    design_style="现代简约",
                    lighting_conditions="自然光",
                    composition_elements=["产品主体"],
                    quality_assessment="良好",
                    confidence_score=0.6
                )
            
            # 简化的视觉风格
            simplified_visual_style = VisualStyle(
                color_palette=["#FFFFFF", "#000000", "#808080"],
                lighting_style="自然光",
                composition_rules=["居中构图"],
                aesthetic_direction="简约现代",
                consistency_guidelines={"color_temperature": "6500K"}
            )
            
            analysis_result = AnalysisResult(
                listing_analysis=simplified_listing_analysis,
                image_analysis=simplified_image_analysis,
                visual_style=simplified_visual_style,
                product_info=product_info  # 添加产品信息
            )
            
            return analysis_result
            
        except Exception as e:
            raise Exception(f"Simplified product analysis failed: {str(e)}")
    
    def _extract_simple_category(self, description: str) -> str:
        """简单的产品类别提取"""
        description_lower = description.lower()
        
        # 基本类别关键词匹配
        categories = {
            "电子产品": ["电子", "数码", "手机", "电脑", "耳机", "充电"],
            "家居用品": ["家居", "厨房", "卫浴", "收纳", "装饰"],
            "服装配饰": ["服装", "衣服", "鞋子", "包包", "配饰"],
            "美妆护肤": ["美妆", "护肤", "化妆品", "面膜", "洗护"],
            "运动户外": ["运动", "健身", "户外", "跑步", "瑜伽"],
            "母婴用品": ["母婴", "儿童", "玩具", "奶粉", "尿布"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in description_lower for keyword in keywords):
                return category
        
        return "通用产品"
    
    def _extract_simple_features(self, description: str) -> List[str]:
        """简单的特征提取"""
        features = []
        
        # 基本特征关键词
        feature_keywords = [
            "高质量", "耐用", "便携", "轻便", "防水", "防滑",
            "舒适", "安全", "环保", "节能", "智能", "多功能"
        ]
        
        description_lower = description.lower()
        for keyword in feature_keywords:
            if keyword in description_lower:
                features.append(keyword)
        
        # 如果没有找到特征，添加默认特征
        if not features:
            features = ["高品质", "实用性强", "性价比高"]
        
        return features[:5]  # 最多返回5个特征
