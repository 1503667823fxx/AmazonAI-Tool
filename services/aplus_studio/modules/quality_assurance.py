"""
品质保证模块生成器

创建认证和信任指标展示，建立客户对产品质量的信心。
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


class QualityAssuranceGenerator(BaseModuleGenerator):
    """品质保证模块生成器"""
    
    def __init__(self):
        super().__init__(ModuleType.QUALITY_ASSURANCE)
        self.layout_templates = {
            "certification_display": {
                "certifications_area": (0.05, 0.15, 0.48, 0.8),
                "trust_indicators_area": (0.52, 0.15, 0.95, 0.5),
                "warranty_area": (0.52, 0.55, 0.95, 0.8),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        return {
            "name": "品质保证",
            "description": "展示产品认证、保修和质量保证信息",
            "category": "professional",
            "recommended_use_cases": ["质量认证展示", "信任建立", "保修说明", "合规展示"],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 40
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="质量认证信息",
                examples=["ISO认证", "CE标志", "质量保证"],
                tooltip="产品获得的各种质量认证和标准"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="保修信息",
                examples=["2年保修", "终身维护", "质量承诺"],
                tooltip="产品的保修政策和质量承诺"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.AI_GENERATED,
                description="认证证书图片",
                examples=["证书照片", "认证标志", "检测报告"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示认证证书或标志的图片"
            )
        ]
        return MaterialRequirements(module_type=self.module_type, requirements=requirements)
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        try:
            certifications = self._extract_certifications(materials, analysis_result)
            trust_indicators = self._generate_trust_indicators(certifications)
            warranty_info = self._extract_warranty_info(materials, analysis_result)
            
            layout_config = {
                "template": "certification_display",
                "certifications": certifications,
                "trust_indicators": trust_indicators,
                "warranty_info": warranty_info,
                "color_scheme": self._determine_color_scheme(analysis_result)
            }
            
            return layout_config
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate layout: {str(e)}", self.module_type, "LAYOUT_GENERATION_FAILED") from e
    
    async def generate_content(self, materials: MaterialSet, layout_config: Dict[str, Any], analysis_result: AnalysisResult) -> GeneratedModule:
        try:
            canvas = self._create_base_canvas()
            template = self.layout_templates[layout_config["template"]]
            
            canvas = self._draw_certifications_area(canvas, layout_config, template, materials)
            canvas = self._draw_trust_indicators_area(canvas, layout_config, template)
            canvas = self._draw_warranty_area(canvas, layout_config, template)
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
                    "certifications_count": len(layout_config["certifications"]),
                    "trust_indicators_count": len(layout_config["trust_indicators"])
                }
            )
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate content: {str(e)}", self.module_type, "CONTENT_GENERATION_FAILED") from e
    
    def _extract_certifications(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        certifications = []
        if "certifications" in materials.text_inputs:
            cert_lines = materials.text_inputs["certifications"].split("\n")
            certifications.extend([c.strip() for c in cert_lines if c.strip()])
        
        if len(certifications) == 0:
            certifications = ["ISO 9001质量认证", "CE欧盟认证", "品质保证承诺"]
        
        return certifications
    
    def _generate_trust_indicators(self, certifications: List[str]) -> List[Dict[str, str]]:
        indicators = []
        for cert in certifications:
            indicators.append({"name": cert, "status": "verified", "icon": "✓"})
        return indicators
    
    def _extract_warranty_info(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        warranty = []
        if "warranty" in materials.text_inputs:
            warranty_lines = materials.text_inputs["warranty"].split("\n")
            warranty.extend([w.strip() for w in warranty_lines if w.strip()])
        
        if len(warranty) == 0:
            warranty = ["2年质量保修", "终身技术支持", "30天无理由退换"]
        
        return warranty
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        return {
            "certification": "#27AE60", "trust": "#3498DB", "warranty": "#E67E22",
            "text": "#2C3E50", "background": "#FFFFFF"
        }
    
    def _create_base_canvas(self) -> Image.Image:
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_certifications_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        certifications = layout_config["certifications"]
        
        if "certifications_area" in template:
            area = template["certifications_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["certification"], width=2)
            draw.text((x1 + 10, y1 + 10), "质量认证", fill=layout_config["color_scheme"]["certification"])
            
            for i, cert in enumerate(certifications[:4]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"✓ {cert}", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_trust_indicators_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        trust_indicators = layout_config["trust_indicators"]
        
        if "trust_indicators_area" in template:
            area = template["trust_indicators_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["trust"], width=2)
            draw.text((x1 + 10, y1 + 10), "信任指标", fill=layout_config["color_scheme"]["trust"])
            
            for i, indicator in enumerate(trust_indicators[:3]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"{indicator['icon']} {indicator['name']}", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_warranty_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        warranty_info = layout_config["warranty_info"]
        
        if "warranty_area" in template:
            area = template["warranty_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["warranty"], width=2)
            draw.text((x1 + 10, y1 + 10), "保修承诺", fill=layout_config["color_scheme"]["warranty"])
            
            for i, warranty in enumerate(warranty_info[:3]):
                y_pos = y1 + 35 + i * 20
                draw.text((x1 + 10, y_pos), f"• {warranty}", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            draw.text((x1, y1), "品质保证", fill=layout_config["color_scheme"]["text"])
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        return f"Quality assurance module with {len(layout_config['certifications'])} certifications and {len(layout_config['warranty_info'])} warranty items"