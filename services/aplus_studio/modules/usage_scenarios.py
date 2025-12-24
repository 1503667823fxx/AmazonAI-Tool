"""
使用场景模块生成器

创建实际应用环境展示，突出产品在真实场景中的应用。
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


class UsageScenariosGenerator(BaseModuleGenerator):
    """
    使用场景模块生成器
    
    生成实际应用环境展示，包括：
    - 多场景布局展示
    - 现实环境集成
    - 多功能用例显示
    - 实际应用重点
    """
    
    def __init__(self):
        super().__init__(ModuleType.USAGE_SCENARIOS)
        self.layout_templates = {
            "multi_panel_scenarios": {
                "scenario_panels": [
                    (0.05, 0.1, 0.48, 0.45),
                    (0.52, 0.1, 0.95, 0.45),
                    (0.05, 0.55, 0.48, 0.9),
                    (0.52, 0.55, 0.95, 0.9)
                ],
                "title_area": (0.1, 0.02, 0.9, 0.08)
            },
            "timeline_usage": {
                "timeline_area": (0.1, 0.3, 0.9, 0.7),
                "scenario_details": (0.1, 0.75, 0.9, 0.9),
                "title_area": (0.1, 0.05, 0.9, 0.25)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "使用场景",
            "description": "展示产品在实际环境中的多种应用场景和用例",
            "category": "professional",
            "recommended_use_cases": [
                "实际应用展示",
                "多功能演示",
                "使用环境说明",
                "用户场景分析"
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
                description="使用场景描述",
                examples=["家庭使用", "办公环境", "户外活动"],
                tooltip="描述产品的主要使用场景和环境"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="场景应用照片",
                examples=["实际使用图", "环境应用图", "场景展示图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示产品在实际场景中使用的照片"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="用例说明",
                examples=["适用人群", "使用时机", "应用优势"],
                tooltip="说明不同场景下的具体用例和优势"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 提取使用场景
            scenarios = self._extract_usage_scenarios(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(scenarios, materials)
            
            # 生成场景详情
            scenario_details = self._generate_scenario_details(scenarios, materials)
            
            layout_config = {
                "template": layout_template,
                "scenarios": scenarios[:4],  # 最多4个场景
                "scenario_details": scenario_details,
                "color_scheme": self._determine_color_scheme(analysis_result),
                "focus_style": "practical_applications"
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
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 绘制场景面板
            canvas = self._draw_scenario_panels(canvas, layout_config, template, materials)
            
            # 添加场景标题和描述
            canvas = self._add_scenario_descriptions(canvas, layout_config, template)
            
            # 添加主标题
            canvas = self._add_main_title(canvas, layout_config, template)
            
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
                    "scenarios_count": len(layout_config["scenarios"]),
                    "focus_style": layout_config["focus_style"]
                }
            )
            
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _extract_usage_scenarios(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取使用场景"""
        scenarios = []
        
        if "scenarios" in materials.text_inputs:
            user_scenarios = materials.text_inputs["scenarios"].split("\n")
            scenarios.extend([s.strip() for s in user_scenarios if s.strip()])
        
        # 默认场景
        if len(scenarios) == 0:
            scenarios = ["家庭日常使用", "办公环境应用", "户外便携使用", "专业工作场景"]
        
        return scenarios[:4]
    
    def _select_layout_template(self, scenarios: List[str], materials: MaterialSet) -> str:
        """选择布局模板"""
        return "multi_panel_scenarios"  # 默认使用多面板布局
    
    def _generate_scenario_details(self, scenarios: List[str], materials: MaterialSet) -> List[Dict[str, str]]:
        """生成场景详情"""
        details = []
        for scenario in scenarios:
            details.append({
                "name": scenario,
                "description": f"{scenario}的详细说明和优势",
                "key_benefits": f"{scenario}中的主要优势"
            })
        return details
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "primary": "#2C3E50",
            "scenario": "#3498DB",
            "text": "#2C3E50",
            "background": "#FFFFFF"
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_scenario_panels(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                            template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制场景面板"""
        draw = ImageDraw.Draw(canvas)
        scenarios = layout_config["scenarios"]
        
        if "scenario_panels" in template:
            panels = template["scenario_panels"]
            for i, (scenario, panel) in enumerate(zip(scenarios, panels)):
                x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(panel, [canvas.width, canvas.height, canvas.width, canvas.height])]
                
                # 绘制面板边框
                draw.rectangle([x1, y1, x2, y2], 
                             outline=layout_config["color_scheme"]["scenario"], 
                             width=2)
                
                # 添加场景标题
                draw.text((x1 + 10, y1 + 10), f"场景 {i+1}: {scenario}", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_scenario_descriptions(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                 template: Dict[str, Any]) -> Image.Image:
        """添加场景描述"""
        # 在面板中添加详细描述
        return canvas
    
    def _add_main_title(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                       template: Dict[str, Any]) -> Image.Image:
        """添加主标题"""
        draw = ImageDraw.Draw(canvas)
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            draw.text((x1, y1), "使用场景", fill=layout_config["color_scheme"]["primary"])
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Usage scenarios module showing {len(layout_config['scenarios'])} practical application scenarios"