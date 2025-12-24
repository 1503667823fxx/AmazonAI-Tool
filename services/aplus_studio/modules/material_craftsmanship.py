"""
材质工艺模块生成器

创建质量和构造细节展示，突出产品的材料品质和制造工艺。
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


class MaterialCraftsmanshipGenerator(BaseModuleGenerator):
    """
    材质工艺模块生成器
    
    生成质量和构造细节展示，包括：
    - 材料展示模板
    - 质量指标突出显示
    - 构造技术可视化
    - 制造工艺集成
    """
    
    def __init__(self):
        super().__init__(ModuleType.MATERIAL_CRAFTSMANSHIP)
        self.layout_templates = {
            "material_closeups": {
                "materials_area": (0.05, 0.15, 0.6, 0.8),
                "quality_indicators_area": (0.65, 0.15, 0.95, 0.5),
                "craftsmanship_area": (0.65, 0.55, 0.95, 0.8),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "材质工艺",
            "description": "展示产品的优质材料和精湛制造工艺",
            "category": "professional",
            "recommended_use_cases": [
                "材料品质展示",
                "制造工艺说明",
                "质量保证展示",
                "工艺细节突出"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 50
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="材料信息",
                examples=["优质不锈钢", "天然皮革", "环保材料"],
                tooltip="详细的材料类型和特性说明"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="材料特写照片",
                examples=["材料纹理图", "工艺细节图", "质量展示图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示材料质感和工艺细节的高清照片"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="制造工艺说明",
                examples=["精密加工", "手工制作", "先进工艺"],
                tooltip="说明产品的制造工艺和技术特点"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 提取材料信息
            materials_info = self._extract_materials_info(materials, analysis_result)
            
            # 提取工艺信息
            craftsmanship_info = self._extract_craftsmanship_info(materials, analysis_result)
            
            # 生成质量指标
            quality_indicators = self._generate_quality_indicators(materials_info, craftsmanship_info)
            
            layout_config = {
                "template": "material_closeups",
                "materials_info": materials_info,
                "craftsmanship_info": craftsmanship_info,
                "quality_indicators": quality_indicators,
                "color_scheme": self._determine_color_scheme(analysis_result),
                "emphasis_style": "premium_quality"
            }
            
            return layout_config
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate layout: {str(e)}",
                self.module_type,
                "LAYOUT_GENERATION_FAILED"
            ) from e
    
    async def generate_content(self, 
                             materials: MaterialSet, 
                             layout_config: Dict[str, Any],
                             analysis_result: AnalysisResult) -> GeneratedModule:
        """生成模块内容"""
        try:
            canvas = self._create_base_canvas()
            template = self.layout_templates[layout_config["template"]]
            
            # 绘制材料展示区域
            canvas = self._draw_materials_area(canvas, layout_config, template, materials)
            
            # 绘制质量指标区域
            canvas = self._draw_quality_indicators_area(canvas, layout_config, template)
            
            # 绘制工艺展示区域
            canvas = self._draw_craftsmanship_area(canvas, layout_config, template)
            
            # 添加标题
            canvas = self._add_title(canvas, layout_config, template)
            
            image_data = self._canvas_to_bytes(canvas)
            prompt_used = self._generate_prompt_description(layout_config)
            
            generated_module = GeneratedModule(
                module_type=self.module_type,
                image_data=image_data,
                image_path=None,
                materials_used=materials,
                prompt_used=prompt_used,
                metadata={
                    "layout_template": layout_config["template"],
                    "materials_count": len(layout_config["materials_info"]),
                    "craftsmanship_count": len(layout_config["craftsmanship_info"]),
                    "emphasis_style": layout_config["emphasis_style"]
                }
            )
            
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _extract_materials_info(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取材料信息"""
        materials_info = []
        
        if "materials" in materials.text_inputs:
            material_lines = materials.text_inputs["materials"].split("\n")
            for line in material_lines:
                if line.strip():
                    materials_info.append({
                        "name": line.strip(),
                        "description": f"{line.strip()}的优质特性",
                        "quality_level": "premium"
                    })
        
        # 默认材料信息
        if len(materials_info) == 0:
            materials_info = [
                {"name": "优质不锈钢", "description": "耐腐蚀、持久耐用", "quality_level": "premium"},
                {"name": "精选材料", "description": "严格筛选、品质保证", "quality_level": "high"},
                {"name": "环保工艺", "description": "绿色制造、安全可靠", "quality_level": "certified"}
            ]
        
        return materials_info
    
    def _extract_craftsmanship_info(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取工艺信息"""
        craftsmanship = []
        
        if "craftsmanship" in materials.text_inputs:
            craft_lines = materials.text_inputs["craftsmanship"].split("\n")
            craftsmanship.extend([c.strip() for c in craft_lines if c.strip()])
        
        # 默认工艺信息
        if len(craftsmanship) == 0:
            craftsmanship = [
                "精密加工工艺",
                "严格质量控制",
                "专业制造技术",
                "细节完美处理"
            ]
        
        return craftsmanship
    
    def _generate_quality_indicators(self, materials_info: List[Dict[str, str]], 
                                   craftsmanship_info: List[str]) -> List[Dict[str, str]]:
        """生成质量指标"""
        indicators = []
        
        # 基于材料生成指标
        for material in materials_info:
            indicators.append({
                "type": "material_quality",
                "name": material["name"],
                "level": material["quality_level"],
                "icon": "✓"
            })
        
        # 基于工艺生成指标
        for craft in craftsmanship_info[:2]:
            indicators.append({
                "type": "craftsmanship_quality",
                "name": craft,
                "level": "excellent",
                "icon": "★"
            })
        
        return indicators
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "material": "#8E44AD",     # 紫色 - 材料
            "craftsmanship": "#E67E22", # 橙色 - 工艺
            "quality": "#27AE60",      # 绿色 - 质量
            "premium": "#F39C12",      # 金色 - 高端
            "text": "#2C3E50",         # 深色文字
            "background": "#FFFFFF"    # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_materials_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                           template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制材料展示区域"""
        draw = ImageDraw.Draw(canvas)
        materials_info = layout_config["materials_info"]
        
        if "materials_area" in template:
            area = template["materials_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["material"], 
                         width=3)
            
            # 如果有材料图片，显示在此区域
            if materials.images and len(materials.images) > 0:
                material_image = materials.images[0].content
                if isinstance(material_image, Image.Image):
                    area_width = x2 - x1 - 20
                    area_height = y2 - y1 - 20
                    resized_image = material_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized_image, (x1 + 10, y1 + 10))
            
            # 添加材料标签
            for i, material in enumerate(materials_info[:3]):
                y_pos = y2 - 80 + i * 20
                draw.text((x1 + 10, y_pos), f"• {material['name']}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_quality_indicators_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                    template: Dict[str, Any]) -> Image.Image:
        """绘制质量指标区域"""
        draw = ImageDraw.Draw(canvas)
        quality_indicators = layout_config["quality_indicators"]
        
        if "quality_indicators_area" in template:
            area = template["quality_indicators_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["quality"], 
                         width=2)
            
            draw.text((x1 + 10, y1 + 10), "品质保证", 
                     fill=layout_config["color_scheme"]["quality"])
            
            for i, indicator in enumerate(quality_indicators[:4]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"{indicator['icon']} {indicator['name']}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_craftsmanship_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any]) -> Image.Image:
        """绘制工艺展示区域"""
        draw = ImageDraw.Draw(canvas)
        craftsmanship_info = layout_config["craftsmanship_info"]
        
        if "craftsmanship_area" in template:
            area = template["craftsmanship_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["craftsmanship"], 
                         width=2)
            
            draw.text((x1 + 10, y1 + 10), "制造工艺", 
                     fill=layout_config["color_scheme"]["craftsmanship"])
            
            for i, craft in enumerate(craftsmanship_info[:3]):
                y_pos = y1 + 35 + i * 20
                draw.text((x1 + 10, y_pos), f"• {craft}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                  template: Dict[str, Any]) -> Image.Image:
        """添加标题"""
        draw = ImageDraw.Draw(canvas)
        
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            draw.text((x1, y1), "材质工艺", 
                     fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Material craftsmanship module showcasing {len(layout_config['materials_info'])} materials and {len(layout_config['craftsmanship_info'])} craftsmanship details"