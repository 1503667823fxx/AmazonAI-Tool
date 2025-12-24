"""
维护保养模块生成器

创建保养说明和指南，提供产品维护的详细指导。
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


class MaintenanceCareGenerator(BaseModuleGenerator):
    """
    维护保养模块生成器
    
    生成保养说明和指南，包括：
    - 保养说明模板
    - 清洁方法可视化
    - 存储和处理指导
    - 寿命延长强调
    """
    
    def __init__(self):
        super().__init__(ModuleType.MAINTENANCE_CARE)
        self.layout_templates = {
            "care_instructions": {
                "daily_care_area": (0.05, 0.15, 0.48, 0.45),
                "cleaning_area": (0.52, 0.15, 0.95, 0.45),
                "storage_area": (0.05, 0.5, 0.48, 0.8),
                "products_area": (0.52, 0.5, 0.95, 0.8),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            },
            "maintenance_timeline": {
                "timeline_area": (0.1, 0.2, 0.9, 0.6),
                "tips_area": (0.1, 0.65, 0.9, 0.85),
                "title_area": (0.1, 0.05, 0.9, 0.15)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "维护保养",
            "description": "提供详细的产品维护保养指南和建议",
            "category": "professional",
            "recommended_use_cases": [
                "产品保养指导",
                "清洁方法说明",
                "维护计划制定",
                "寿命延长建议"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 45
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="保养说明",
                examples=["日常清洁", "定期维护", "存储方法"],
                tooltip="详细的产品保养和维护说明"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="清洁方法",
                examples=["温水清洗", "软布擦拭", "避免化学清洁剂"],
                tooltip="具体的清洁方法和注意事项"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="保养过程照片",
                examples=["清洁示范图", "保养步骤图", "存储方式图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示保养过程的实际照片"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.AI_GENERATED,
                description="保养产品推荐",
                examples=["专用清洁剂", "保养工具", "存储配件"],
                tooltip="推荐的保养产品和工具"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 提取保养说明
            care_instructions = self._extract_care_instructions(materials, analysis_result)
            
            # 提取清洁方法
            cleaning_methods = self._extract_cleaning_methods(materials, analysis_result)
            
            # 提取存储指导
            storage_guidance = self._extract_storage_guidance(materials, analysis_result)
            
            # 提取保养产品推荐
            recommended_products = self._extract_recommended_products(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(care_instructions, materials)
            
            layout_config = {
                "template": layout_template,
                "care_instructions": care_instructions,
                "cleaning_methods": cleaning_methods,
                "storage_guidance": storage_guidance,
                "recommended_products": recommended_products,
                "maintenance_schedule": self._generate_maintenance_schedule(care_instructions),
                "color_scheme": self._determine_color_scheme(analysis_result),
                "emphasis_style": "lifespan_extension"
            }
            
            self.logger.info(f"Generated layout config with {len(care_instructions)} care instructions")
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
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 绘制日常保养区域
            canvas = self._draw_daily_care_area(canvas, layout_config, template, materials)
            
            # 绘制清洁方法区域
            canvas = self._draw_cleaning_area(canvas, layout_config, template)
            
            # 绘制存储指导区域
            canvas = self._draw_storage_area(canvas, layout_config, template)
            
            # 绘制推荐产品区域
            canvas = self._draw_products_area(canvas, layout_config, template)
            
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
                    "layout_template": template_name,
                    "care_instructions_count": len(layout_config["care_instructions"]),
                    "cleaning_methods_count": len(layout_config["cleaning_methods"]),
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
    
    def _extract_care_instructions(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取保养说明"""
        instructions = []
        
        if "care_instructions" in materials.text_inputs:
            inst_lines = materials.text_inputs["care_instructions"].split("\n")
            for line in inst_lines:
                if line.strip():
                    instructions.append({
                        "title": line.strip(),
                        "description": f"{line.strip()}的详细说明",
                        "frequency": self._determine_frequency(line.strip())
                    })
        
        # 默认保养说明
        if len(instructions) == 0:
            instructions = [
                {"title": "日常清洁", "description": "每次使用后进行基本清洁", "frequency": "每次使用后"},
                {"title": "深度清洁", "description": "定期进行全面清洁保养", "frequency": "每周一次"},
                {"title": "检查维护", "description": "检查各部件是否正常", "frequency": "每月一次"},
                {"title": "专业保养", "description": "专业维护和检修", "frequency": "每年一次"}
            ]
        
        return instructions
    
    def _extract_cleaning_methods(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取清洁方法"""
        methods = []
        
        if "cleaning_methods" in materials.text_inputs:
            method_lines = materials.text_inputs["cleaning_methods"].split("\n")
            methods.extend([m.strip() for m in method_lines if m.strip()])
        
        # 默认清洁方法
        if len(methods) == 0:
            methods = [
                "使用温水和中性清洁剂",
                "用软布轻柔擦拭",
                "避免使用化学溶剂",
                "清洁后充分晾干"
            ]
        
        return methods
    
    def _extract_storage_guidance(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取存储指导"""
        guidance = []
        
        if "storage_guidance" in materials.text_inputs:
            storage_lines = materials.text_inputs["storage_guidance"].split("\n")
            guidance.extend([g.strip() for g in storage_lines if g.strip()])
        
        # 默认存储指导
        if len(guidance) == 0:
            guidance = [
                "存放在干燥通风处",
                "避免阳光直射",
                "远离热源和潮湿",
                "定期检查存储状态"
            ]
        
        return guidance
    
    def _extract_recommended_products(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取推荐产品"""
        products = []
        
        if "recommended_products" in materials.text_inputs:
            product_lines = materials.text_inputs["recommended_products"].split("\n")
            products.extend([p.strip() for p in product_lines if p.strip()])
        
        # 默认推荐产品
        if len(products) == 0:
            products = [
                "专用清洁剂",
                "微纤维清洁布",
                "保护套/收纳盒"
            ]
        
        return products
    
    def _select_layout_template(self, care_instructions: List[Dict[str, str]], materials: MaterialSet) -> str:
        """选择布局模板"""
        return "care_instructions"  # 默认使用保养说明模板
    
    def _generate_maintenance_schedule(self, care_instructions: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """生成维护计划"""
        schedule = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "yearly": []
        }
        
        for instruction in care_instructions:
            frequency = instruction["frequency"].lower()
            if "每天" in frequency or "每次" in frequency:
                schedule["daily"].append(instruction["title"])
            elif "每周" in frequency:
                schedule["weekly"].append(instruction["title"])
            elif "每月" in frequency:
                schedule["monthly"].append(instruction["title"])
            elif "每年" in frequency:
                schedule["yearly"].append(instruction["title"])
        
        return schedule
    
    def _determine_frequency(self, instruction: str) -> str:
        """确定保养频率"""
        instruction_lower = instruction.lower()
        if "日常" in instruction_lower:
            return "每天"
        elif "定期" in instruction_lower:
            return "每周一次"
        elif "检查" in instruction_lower:
            return "每月一次"
        elif "专业" in instruction_lower:
            return "每年一次"
        else:
            return "根据需要"
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "care": "#27AE60",         # 绿色 - 保养
            "cleaning": "#3498DB",     # 蓝色 - 清洁
            "storage": "#E67E22",      # 橙色 - 存储
            "products": "#9B59B6",     # 紫色 - 产品
            "text": "#2C3E50",         # 深色文字
            "background": "#FFFFFF"    # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_daily_care_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                             template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制日常保养区域"""
        draw = ImageDraw.Draw(canvas)
        care_instructions = layout_config["care_instructions"]
        
        if "daily_care_area" in template:
            area = template["daily_care_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            # 绘制区域边框
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["care"], 
                         width=2)
            
            # 添加标题
            draw.text((x1 + 10, y1 + 10), "日常保养", 
                     fill=layout_config["color_scheme"]["care"])
            
            # 添加保养项目
            for i, instruction in enumerate(care_instructions[:3]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"• {instruction['title']}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_cleaning_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                           template: Dict[str, Any]) -> Image.Image:
        """绘制清洁方法区域"""
        draw = ImageDraw.Draw(canvas)
        cleaning_methods = layout_config["cleaning_methods"]
        
        if "cleaning_area" in template:
            area = template["cleaning_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["cleaning"], 
                         width=2)
            
            draw.text((x1 + 10, y1 + 10), "清洁方法", 
                     fill=layout_config["color_scheme"]["cleaning"])
            
            for i, method in enumerate(cleaning_methods[:3]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"• {method}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_storage_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                          template: Dict[str, Any]) -> Image.Image:
        """绘制存储指导区域"""
        draw = ImageDraw.Draw(canvas)
        storage_guidance = layout_config["storage_guidance"]
        
        if "storage_area" in template:
            area = template["storage_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["storage"], 
                         width=2)
            
            draw.text((x1 + 10, y1 + 10), "存储指导", 
                     fill=layout_config["color_scheme"]["storage"])
            
            for i, guidance in enumerate(storage_guidance[:3]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"• {guidance}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _draw_products_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                           template: Dict[str, Any]) -> Image.Image:
        """绘制推荐产品区域"""
        draw = ImageDraw.Draw(canvas)
        recommended_products = layout_config["recommended_products"]
        
        if "products_area" in template:
            area = template["products_area"]
            x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
            
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["products"], 
                         width=2)
            
            draw.text((x1 + 10, y1 + 10), "推荐产品", 
                     fill=layout_config["color_scheme"]["products"])
            
            for i, product in enumerate(recommended_products[:3]):
                y_pos = y1 + 35 + i * 25
                draw.text((x1 + 10, y_pos), f"• {product}", 
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
            
            draw.text((x1, y1), "维护保养指南", 
                     fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Maintenance care module with {len(layout_config['care_instructions'])} care instructions and {len(layout_config['cleaning_methods'])} cleaning methods"