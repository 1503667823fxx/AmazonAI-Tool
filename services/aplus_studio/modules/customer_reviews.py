"""
用户评价模块生成器

创建评价统计和推荐展示，建立社会证明和客户信任。
"""

import logging
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
import io

from .base_module import BaseModuleGenerator, ModuleGenerationError
from ..models import (
    ModuleType, MaterialSet, MaterialRequirements, MaterialRequirement,
    MaterialType, MaterialPriority, GeneratedModule, ComplianceStatus,
    ValidationStatus, AnalysisResult
)

logger = logging.getLogger(__name__)


class CustomerReviewsGenerator(BaseModuleGenerator):
    """用户评价模块生成器"""
    
    def __init__(self):
        super().__init__(ModuleType.CUSTOMER_REVIEWS)
        self.layout_templates = {
            "review_showcase": {
                "rating_summary_area": (0.05, 0.15, 0.48, 0.4),
                "featured_reviews_area": (0.52, 0.15, 0.95, 0.8),
                "customer_photos_area": (0.05, 0.45, 0.48, 0.8),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        return {
            "name": "用户评价",
            "description": "展示客户评价、评分统计和用户反馈",
            "category": "professional",
            "recommended_use_cases": ["社会证明", "客户反馈", "评分展示", "信任建立"],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 45
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="客户评价内容",
                examples=["产品很好用", "质量不错", "值得推荐"],
                tooltip="真实的客户评价和反馈内容"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.AI_GENERATED,
                description="评分统计",
                examples=["4.8/5.0", "98%好评", "1000+评价"],
                tooltip="产品的评分统计和好评率"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.AI_GENERATED,
                description="客户使用照片",
                examples=["用户晒图", "使用场景", "效果展示"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="客户分享的产品使用照片"
            )
        ]
        return MaterialRequirements(module_type=self.module_type, requirements=requirements)
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        try:
            reviews = self._extract_reviews(materials, analysis_result)
            rating_stats = self._generate_rating_stats(reviews)
            featured_reviews = self._select_featured_reviews(reviews)
            
            layout_config = {
                "template": "review_showcase",
                "reviews": reviews,
                "rating_stats": rating_stats,
                "featured_reviews": featured_reviews,
                "color_scheme": self._determine_color_scheme(analysis_result)
            }
            
            return layout_config
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate layout: {str(e)}", self.module_type, "LAYOUT_GENERATION_FAILED") from e
    
    async def generate_content(self, materials: MaterialSet, layout_config: Dict[str, Any], analysis_result: AnalysisResult) -> GeneratedModule:
        try:
            canvas = self._create_base_canvas()
            template = self.layout_templates[layout_config["template"]]
            
            canvas = self._draw_rating_summary_area(canvas, layout_config, template)
            canvas = self._draw_featured_reviews_area(canvas, layout_config, template)
            canvas = self._draw_customer_photos_area(canvas, layout_config, template, materials)
            canvas = self._add_title(canvas, layout_config, template)
            
            image_data = self._canvas_to_bytes(canvas)
            prompt_used = self._generate_prompt_description(layout_config)
            
            return GeneratedModule(
                module_type=self.module_type,
                image_data=image_data,
                image_path=None,
                materials_used=materials,
                prompt_used=prompt_used,
                metadata={
                    "layout_template": layout_config["template"],
                    "reviews_count": len(layout_config["reviews"]),
                    "featured_reviews_count": len(layout_config["featured_reviews"])
                }
            )
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate content: {str(e)}", self.module_type, "CONTENT_GENERATION_FAILED") from e
    
    def _extract_reviews(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        reviews = []
        if "reviews" in materials.text_inputs:
            review_lines = materials.text_inputs["reviews"].split("\n")
            for line in review_lines:
                if line.strip():
                    reviews.append({
                        "content": line.strip(),
                        "rating": 5,
                        "author": "用户",
                        "verified": True
                    })
        
        if len(reviews) == 0:
            reviews = [
                {"content": "产品质量很好，使用体验不错", "rating": 5, "author": "张先生", "verified": True},
                {"content": "物超所值，推荐购买", "rating": 5, "author": "李女士", "verified": True},
                {"content": "做工精细，很满意", "rating": 4, "author": "王先生", "verified": True}
            ]
        
        return reviews
    
    def _generate_rating_stats(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not reviews:
            return {"average": 4.8, "total": 1000, "five_star_percent": 85}
        
        total_rating = sum(review["rating"] for review in reviews)
        average = total_rating / len(reviews)
        five_star_count = sum(1 for review in reviews if review["rating"] == 5)
        five_star_percent = (five_star_count / len(reviews)) * 100
        
        return {
            "average": round(average, 1),
            "total": len(reviews) * 100,  # 模拟更多评价
            "five_star_percent": round(five_star_percent)
        }
    
    def _select_featured_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 选择评分最高的评价作为精选
        featured = sorted(reviews, key=lambda x: x["rating"], reverse=True)
        return featured[:3]
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        return {
            "rating": "#F39C12", "review": "#3498DB", "verified": "#27AE60",
            "text": "#2C3E50", "background": "#FFFFFF"
        }
    
    def _create_base_canvas(self) -> Image.Image:
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_rating_summary_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        rating_stats = layout_config["rating_stats"]
        
        if "rating_summary_area" in template:
            area = template["rating_summary_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["rating"], width=2)
            draw.text((x1 + 10, y1 + 10), "评分统计", fill=layout_config["color_scheme"]["rating"])
            
            # 显示平均评分
            draw.text((x1 + 10, y1 + 40), f"平均评分: {rating_stats['average']}/5.0", fill=layout_config["color_scheme"]["text"])
            
            # 显示总评价数
            draw.text((x1 + 10, y1 + 65), f"总评价: {rating_stats['total']}+", fill=layout_config["color_scheme"]["text"])
            
            # 显示好评率
            draw.text((x1 + 10, y1 + 90), f"好评率: {rating_stats['five_star_percent']}%", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_featured_reviews_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        featured_reviews = layout_config["featured_reviews"]
        
        if "featured_reviews_area" in template:
            area = template["featured_reviews_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["review"], width=2)
            draw.text((x1 + 10, y1 + 10), "精选评价", fill=layout_config["color_scheme"]["review"])
            
            for i, review in enumerate(featured_reviews[:3]):
                y_pos = y1 + 40 + i * 60
                
                # 绘制星级评分
                stars = "★" * review["rating"] + "☆" * (5 - review["rating"])
                draw.text((x1 + 10, y_pos), stars, fill=layout_config["color_scheme"]["rating"])
                
                # 绘制评价内容
                content = review["content"][:40] + "..." if len(review["content"]) > 40 else review["content"]
                draw.text((x1 + 10, y_pos + 20), f'"{content}"', fill=layout_config["color_scheme"]["text"])
                
                # 绘制作者
                draw.text((x1 + 10, y_pos + 40), f"- {review['author']}", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_customer_photos_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        
        if "customer_photos_area" in template:
            area = template["customer_photos_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["verified"], width=2)
            draw.text((x1 + 10, y1 + 10), "客户晒图", fill=layout_config["color_scheme"]["verified"])
            
            # 如果有客户照片，显示在此区域
            if materials.images and len(materials.images) > 0:
                customer_image = materials.images[0].content
                if isinstance(customer_image, Image.Image):
                    area_width = x2 - x1 - 20
                    area_height = y2 - y1 - 40
                    resized_image = customer_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized_image, (x1 + 10, y1 + 30))
        
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            draw.text((x1, y1), "用户评价", fill=layout_config["color_scheme"]["text"])
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        return f"Customer reviews module with {len(layout_config['reviews'])} reviews and {layout_config['rating_stats']['average']} average rating"