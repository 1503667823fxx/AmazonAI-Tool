"""
安装指南模块生成器

创建逐步安装说明，提供清晰的安装指导。
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


class InstallationGuideGenerator(BaseModuleGenerator):
    """
    安装指南模块生成器
    
    生成逐步安装说明，包括：
    - 逐步布局模板
    - 顺序说明组织
    - 工具和材料清单
    - 安全警告突出显示
    """
    
    def __init__(self):
        super().__init__(ModuleType.INSTALLATION_GUIDE)
        self.layout_templates = {
            "step_by_step_visual": {
                "steps_area": [
                    (0.05, 0.15, 0.48, 0.4),
                    (0.52, 0.15, 0.95, 0.4),
                    (0.05, 0.45, 0.48, 0.7),
                    (0.52, 0.45, 0.95, 0.7)
                ],
                "tools_area": (0.05, 0.75, 0.95, 0.9),
                "title_area": (0.1, 0.02, 0.9, 0.12)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "安装指南",
            "description": "提供清晰的逐步安装说明和工具清单",
            "category": "professional",
            "recommended_use_cases": [
                "产品安装说明",
                "组装指导",
                "设置教程",
                "操作指南"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 60
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="安装步骤说明",
                examples=["步骤1: 准备工具", "步骤2: 连接部件", "步骤3: 测试功能"],
                tooltip="详细的安装步骤说明"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="所需工具清单",
                examples=["螺丝刀", "扳手", "电钻"],
                tooltip="安装过程中需要的工具和材料"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="安装过程照片",
                examples=["安装步骤图", "工具使用图", "完成效果图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示安装过程的实际照片"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 提取安装步骤
            steps = self._extract_installation_steps(materials, analysis_result)
            
            # 提取工具清单
            tools = self._extract_tools_list(materials, analysis_result)
            
            # 识别安全警告
            safety_warnings = self._identify_safety_warnings(materials, steps)
            
            layout_config = {
                "template": "step_by_step_visual",
                "steps": steps[:4],  # 最多4个步骤
                "tools": tools,
                "safety_warnings": safety_warnings,
                "color_scheme": self._determine_color_scheme(analysis_result),
                "instruction_style": "clear_and_detailed"
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
            
            # 绘制安装步骤
            canvas = self._draw_installation_steps(canvas, layout_config, template, materials)
            
            # 添加工具清单
            canvas = self._add_tools_list(canvas, layout_config, template)
            
            # 添加安全警告
            canvas = self._add_safety_warnings(canvas, layout_config, template)
            
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
                    "steps_count": len(layout_config["steps"]),
                    "tools_count": len(layout_config["tools"]),
                    "safety_warnings_count": len(layout_config["safety_warnings"])
                }
            )
            
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _extract_installation_steps(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取安装步骤"""
        steps = []
        
        if "installation_steps" in materials.text_inputs:
            step_lines = materials.text_inputs["installation_steps"].split("\n")
            for i, line in enumerate(step_lines):
                if line.strip():
                    steps.append({
                        "number": i + 1,
                        "title": f"步骤 {i + 1}",
                        "description": line.strip(),
                        "safety_note": ""
                    })
        
        # 默认步骤
        if len(steps) == 0:
            steps = [
                {"number": 1, "title": "步骤 1", "description": "准备所需工具和材料", "safety_note": ""},
                {"number": 2, "title": "步骤 2", "description": "按照说明连接主要部件", "safety_note": "注意安全"},
                {"number": 3, "title": "步骤 3", "description": "检查连接是否牢固", "safety_note": ""},
                {"number": 4, "title": "步骤 4", "description": "测试功能是否正常", "safety_note": ""}
            ]
        
        return steps[:4]
    
    def _extract_tools_list(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取工具清单"""
        tools = []
        
        if "tools" in materials.text_inputs:
            tool_lines = materials.text_inputs["tools"].split("\n")
            tools.extend([t.strip() for t in tool_lines if t.strip()])
        
        # 默认工具
        if len(tools) == 0:
            tools = ["螺丝刀", "扳手", "说明书"]
        
        return tools
    
    def _identify_safety_warnings(self, materials: MaterialSet, steps: List[Dict[str, str]]) -> List[str]:
        """识别安全警告"""
        warnings = []
        
        # 从步骤中提取安全相关内容
        for step in steps:
            if any(word in step["description"].lower() for word in ["注意", "小心", "安全", "警告"]):
                warnings.append(f"安装{step['title']}时请注意安全")
        
        # 默认安全警告
        if len(warnings) == 0:
            warnings = ["请在安装前仔细阅读说明书", "使用工具时注意安全"]
        
        return warnings
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "step": "#3498DB",
            "tool": "#27AE60",
            "warning": "#E74C3C",
            "text": "#2C3E50",
            "background": "#FFFFFF"
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_installation_steps(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制安装步骤"""
        draw = ImageDraw.Draw(canvas)
        steps = layout_config["steps"]
        
        if "steps_area" in template:
            step_areas = template["steps_area"]
            for i, (step, area) in enumerate(zip(steps, step_areas)):
                x1, y1, x2, y2 = [int(coord * dim) for coord, dim in zip(area, [canvas.width, canvas.height, canvas.width, canvas.height])]
                
                # 绘制步骤边框
                draw.rectangle([x1, y1, x2, y2], 
                             outline=layout_config["color_scheme"]["step"], 
                             width=2)
                
                # 添加步骤编号
                draw.ellipse([x1 + 5, y1 + 5, x1 + 25, y1 + 25], 
                           fill=layout_config["color_scheme"]["step"])
                draw.text((x1 + 12, y1 + 10), str(step["number"]), fill="white")
                
                # 添加步骤描述
                draw.text((x1 + 35, y1 + 10), step["description"][:40] + "...", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_tools_list(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                       template: Dict[str, Any]) -> Image.Image:
        """添加工具清单"""
        draw = ImageDraw.Draw(canvas)
        tools = layout_config["tools"]
        
        if "tools_area" in template:
            area = template["tools_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加工具清单标题
            draw.text((x1, y1), "所需工具:", fill=layout_config["color_scheme"]["tool"])
            
            # 添加工具列表
            tools_text = " | ".join(tools[:6])  # 最多6个工具
            draw.text((x1 + 80, y1), tools_text, fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_safety_warnings(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                           template: Dict[str, Any]) -> Image.Image:
        """添加安全警告"""
        # 在适当位置添加安全警告图标和文字
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                  template: Dict[str, Any]) -> Image.Image:
        """添加标题"""
        draw = ImageDraw.Draw(canvas)
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            draw.text((x1, y1), "安装指南", fill=layout_config["color_scheme"]["text"])
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Installation guide module with {len(layout_config['steps'])} steps and {len(layout_config['tools'])} tools"