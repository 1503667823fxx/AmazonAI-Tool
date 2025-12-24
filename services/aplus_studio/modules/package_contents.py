"""
包装内容模块生成器

创建开箱和内容展示，突出产品的完整性和附加价值。
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


class PackageContentsGenerator(BaseModuleGenerator):
    """包装内容模块生成器"""
    
    def __init__(self):
        super().__init__(ModuleType.PACKAGE_CONTENTS)
        self.layout_templates = {
            "unboxing_display": {
                "unboxing_area": (0.05, 0.15, 0.6, 0.8),
                "contents_list_area": (0.65, 0.15, 0.95, 0.6),
                "value_proposition_area": (0.65, 0.65, 0.95, 0.8),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        return {
            "name": "包装内容",
            "description": "展示产品包装内容和开箱体验",
            "category": "professional",
            "recommended_use_cases": ["开箱展示", "内容清单", "价值体现", "完整性说明"],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 40
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="包装内容清单",
                examples=["主机 x1", "配件 x2", "说明书 x1"],
                tooltip="详细的包装内容和数量清单"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="开箱照片",
                examples=["开箱过程", "内容展示", "物品排列"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示开箱过程和内容的照片"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.AI_GENERATED,
                description="附加价值说明",
                examples=["免费配件", "超值套装", "贴心赠品"],
                tooltip="强调包装内容的附加价值"
            )
        ]
        return MaterialRequirements(module_type=self.module_type, requirements=requirements)
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        try:
            contents_list = self._extract_contents_list(materials, analysis_result)
            value_items = self._identify_value_items(contents_list)
            packaging_quality = self._assess_packaging_quality(materials, analysis_result)
            
            layout_config = {
                "template": "unboxing_display",
                "contents_list": contents_list,
                "value_items": value_items,
                "packaging_quality": packaging_quality,
                "color_scheme": self._determine_color_scheme(analysis_result),
                "emphasis_style": "value_showcase"
            }
            
            return layout_config
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate layout: {str(e)}", self.module_type, "LAYOUT_GENERATION_FAILED") from e
    
    async def generate_content(self, materials: MaterialSet, layout_config: Dict[str, Any], analysis_result: AnalysisResult) -> GeneratedModule:
        try:
            canvas = self._create_base_canvas()
            template = self.layout_templates[layout_config["template"]]
            
            canvas = self._draw_unboxing_area(canvas, layout_config, template, materials)
            canvas = self._draw_contents_list_area(canvas, layout_config, template)
            canvas = self._draw_value_proposition_area(canvas, layout_config, template)
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
                    "contents_count": len(layout_config["contents_list"]),
                    "value_items_count": len(layout_config["value_items"]),
                    "emphasis_style": layout_config["emphasis_style"]
                }
            )
        except Exception as e:
            raise ModuleGenerationError(f"Failed to generate content: {str(e)}", self.module_type, "CONTENT_GENERATION_FAILED") from e
    
    def _extract_contents_list(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        contents = []
        if "contents" in materials.text_inputs:
            content_lines = materials.text_inputs["contents"].split("\n")
            for line in content_lines:
                if line.strip():
                    # 尝试解析数量
                    parts = line.strip().split()
                    if len(parts) >= 2 and 'x' in parts[-1]:
                        quantity = parts[-1]
                        item_name = ' '.join(parts[:-1])
                    else:
                        quantity = "x1"
                        item_name = line.strip()
                    
                    contents.append({
                        "name": item_name,
                        "quantity": quantity,
                        "type": self._classify_item_type(item_name),
                        "is_bonus": self._is_bonus_item(item_name)
                    })
        
        if len(contents) == 0:
            contents = [
                {"name": "主产品", "quantity": "x1", "type": "main", "is_bonus": False},
                {"name": "配件套装", "quantity": "x1", "type": "accessory", "is_bonus": False},
                {"name": "说明书", "quantity": "x1", "type": "documentation", "is_bonus": False},
                {"name": "保修卡", "quantity": "x1", "type": "documentation", "is_bonus": True}
            ]
        
        return contents
    
    def _identify_value_items(self, contents_list: List[Dict[str, Any]]) -> List[str]:
        value_items = []
        for item in contents_list:
            if item["is_bonus"] or item["type"] == "accessory":
                value_items.append(f"{item['name']} {item['quantity']}")
        
        if len(value_items) == 0:
            value_items = ["免费配件包", "贴心说明书", "质保服务"]
        
        return value_items
    
    def _assess_packaging_quality(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, str]:
        return {
            "protection": "优质包装保护",
            "presentation": "精美开箱体验",
            "sustainability": "环保包装材料"
        }
    
    def _classify_item_type(self, item_name: str) -> str:
        item_lower = item_name.lower()
        if any(word in item_lower for word in ["主", "产品", "设备", "机器"]):
            return "main"
        elif any(word in item_lower for word in ["配件", "附件", "工具"]):
            return "accessory"
        elif any(word in item_lower for word in ["说明", "手册", "保修", "证书"]):
            return "documentation"
        else:
            return "other"
    
    def _is_bonus_item(self, item_name: str) -> bool:
        item_lower = item_name.lower()
        return any(word in item_lower for word in ["赠品", "免费", "额外", "保修", "服务"])
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        return {
            "main_item": "#2C3E50", "accessory": "#3498DB", "bonus": "#E74C3C",
            "documentation": "#95A5A6", "text": "#2C3E50", "background": "#FFFFFF"
        }
    
    def _create_base_canvas(self) -> Image.Image:
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_unboxing_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        
        if "unboxing_area" in template:
            area = template["unboxing_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["main_item"], width=3)
            
            # 如果有开箱照片，显示在此区域
            if materials.images and len(materials.images) > 0:
                unboxing_image = materials.images[0].content
                if isinstance(unboxing_image, Image.Image):
                    area_width = x2 - x1 - 20
                    area_height = y2 - y1 - 20
                    resized_image = unboxing_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized_image, (x1 + 10, y1 + 10))
            else:
                # 绘制简单的开箱示意图
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                draw.rectangle([center_x - 80, center_y - 60, center_x + 80, center_y + 60],
                             outline=layout_config["color_scheme"]["main_item"], width=2)
                draw.text((center_x - 30, center_y - 10), "开箱展示", fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_contents_list_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        contents_list = layout_config["contents_list"]
        
        if "contents_list_area" in template:
            area = template["contents_list_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["accessory"], width=2)
            draw.text((x1 + 10, y1 + 10), "包装内容", fill=layout_config["color_scheme"]["accessory"])
            
            for i, item in enumerate(contents_list[:6]):  # 最多显示6个物品
                y_pos = y1 + 35 + i * 25
                
                # 根据物品类型选择颜色
                color = layout_config["color_scheme"].get(item["type"], layout_config["color_scheme"]["text"])
                if item["is_bonus"]:
                    color = layout_config["color_scheme"]["bonus"]
                
                # 绘制物品
                item_text = f"• {item['name']} {item['quantity']}"
                draw.text((x1 + 10, y_pos), item_text, fill=color)
        
        return canvas
    
    def _draw_value_proposition_area(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        value_items = layout_config["value_items"]
        
        if "value_proposition_area" in template:
            area = template["value_proposition_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], outline=layout_config["color_scheme"]["bonus"], width=2)
            draw.text((x1 + 10, y1 + 10), "超值内容", fill=layout_config["color_scheme"]["bonus"])
            
            for i, value_item in enumerate(value_items[:3]):
                y_pos = y1 + 35 + i * 20
                draw.text((x1 + 10, y_pos), f"+ {value_item}", fill=layout_config["color_scheme"]["bonus"])
        
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], template: Dict[str, Any]) -> Image.Image:
        draw = ImageDraw.Draw(canvas)
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            draw.text((x1, y1), "包装内容", fill=layout_config["color_scheme"]["text"])
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        return f"Package contents module showing {len(layout_config['contents_list'])} items with {len(layout_config['value_items'])} value items"