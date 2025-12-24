"""
问题解决模块生成器

创建前后对比展示，突出产品如何解决用户痛点。
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


class ProblemSolutionGenerator(BaseModuleGenerator):
    """
    问题解决模块生成器
    
    生成前后对比展示，包括：
    - 问题场景展示
    - 解决方案演示
    - 对比箭头和标注
    - 效果强调
    """
    
    def __init__(self):
        super().__init__(ModuleType.PROBLEM_SOLUTION)
        self.layout_templates = {
            "before_after_horizontal": {
                "before_area": (0.05, 0.1, 0.45, 0.9),
                "after_area": (0.55, 0.1, 0.95, 0.9),
                "arrow_area": (0.45, 0.4, 0.55, 0.6),
                "title_area": (0.1, 0.02, 0.9, 0.08)
            },
            "problem_solution_vertical": {
                "problem_area": (0.1, 0.1, 0.9, 0.4),
                "solution_area": (0.1, 0.6, 0.9, 0.9),
                "transition_area": (0.3, 0.4, 0.7, 0.6)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "问题解决",
            "description": "创建前后对比展示，突出产品解决用户痛点的能力",
            "category": "professional",
            "recommended_use_cases": [
                "痛点解决展示",
                "效果对比",
                "问题分析",
                "解决方案演示"
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
                description="问题描述",
                examples=["使用不便", "效率低下", "体验差"],
                tooltip="描述产品要解决的具体问题或痛点"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="解决方案说明",
                examples=["一键操作", "智能优化", "完美体验"],
                tooltip="说明产品如何解决这些问题"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="问题场景图片",
                examples=["使用前状态", "问题现象", "困扰场景"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示问题或困扰的实际场景"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="解决方案图片",
                examples=["使用后效果", "解决状态", "改善场景"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示使用产品后的改善效果"
            ),
            MaterialRequirement(
                material_type=MaterialType.CUSTOM_PROMPT,
                priority=MaterialPriority.AI_GENERATED,
                description="对比风格偏好",
                examples=["简洁对比", "详细说明", "视觉冲击"],
                tooltip="AI将根据产品特性选择最佳对比展示方式"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 分析问题类型
            problem_type = self._analyze_problem_type(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(problem_type, materials)
            
            # 提取问题和解决方案
            problems = self._extract_problems(materials, analysis_result)
            solutions = self._extract_solutions(materials, analysis_result)
            
            # 确定对比方式
            comparison_style = self._determine_comparison_style(problem_type)
            
            layout_config = {
                "template": layout_template,
                "problem_type": problem_type,
                "problems": problems[:3],  # 最多3个问题
                "solutions": solutions[:3],  # 最多3个解决方案
                "comparison_style": comparison_style,
                "visual_metaphors": self._generate_visual_metaphors(problem_type),
                "color_scheme": self._determine_color_scheme(analysis_result),
                "emphasis_level": "high"
            }
            
            self.logger.info(f"Generated layout config with {len(problems)} problems and {len(solutions)} solutions")
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
            # 创建基础画布
            canvas = self._create_base_canvas()
            
            # 应用布局模板
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 绘制问题区域
            canvas = self._draw_problem_area(canvas, layout_config, template, materials)
            
            # 绘制解决方案区域
            canvas = self._draw_solution_area(canvas, layout_config, template, materials)
            
            # 添加对比箭头和转换元素
            canvas = self._add_transition_elements(canvas, layout_config, template)
            
            # 添加标题和说明
            canvas = self._add_titles_and_labels(canvas, layout_config, template)
            
            # 应用视觉强调
            canvas = self._apply_visual_emphasis(canvas, layout_config)
            
            # 转换为字节数据
            image_data = self._canvas_to_bytes(canvas)
            
            # 生成提示词记录
            prompt_used = self._generate_prompt_description(layout_config)
            
            # 创建生成结果
            generated_module = GeneratedModule(
                module_type=self.module_type,
                image_data=image_data,
                image_path=None,
                materials_used=materials,
                prompt_used=prompt_used,
                metadata={
                    "layout_template": template_name,
                    "problems_count": len(layout_config["problems"]),
                    "solutions_count": len(layout_config["solutions"]),
                    "problem_type": layout_config["problem_type"],
                    "comparison_style": layout_config["comparison_style"]
                }
            )
            
            self.logger.info("Successfully generated problem solution module")
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _analyze_problem_type(self, materials: MaterialSet, analysis_result: AnalysisResult) -> str:
        """分析问题类型"""
        if "problems" in materials.text_inputs:
            problem_text = materials.text_inputs["problems"].lower()
            
            if any(word in problem_text for word in ["效率", "速度", "时间"]):
                return "efficiency"
            elif any(word in problem_text for word in ["复杂", "困难", "麻烦"]):
                return "complexity"
            elif any(word in problem_text for word in ["质量", "效果", "性能"]):
                return "quality"
            elif any(word in problem_text for word in ["安全", "风险", "危险"]):
                return "safety"
        
        return "general"
    
    def _select_layout_template(self, problem_type: str, materials: MaterialSet) -> str:
        """选择布局模板"""
        # 如果有足够的图片，使用水平对比
        if len(materials.images) >= 2:
            return "before_after_horizontal"
        else:
            return "problem_solution_vertical"
    
    def _extract_problems(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取问题描述"""
        problems = []
        
        # 从用户输入提取
        if "problems" in materials.text_inputs:
            user_problems = materials.text_inputs["problems"].split("\n")
            problems.extend([p.strip() for p in user_problems if p.strip()])
        
        # 从分析结果提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.emotional_triggers:
            # 从情感触发点推断问题
            for trigger in analysis_result.listing_analysis.emotional_triggers:
                if "frustration" in trigger.lower() or "problem" in trigger.lower():
                    problems.append(trigger)
        
        # 默认问题
        if len(problems) == 0:
            problems = [
                "传统方式效率低",
                "操作复杂困难",
                "效果不理想"
            ]
        
        return problems[:3]
    
    def _extract_solutions(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取解决方案"""
        solutions = []
        
        # 从用户输入提取
        if "solutions" in materials.text_inputs:
            user_solutions = materials.text_inputs["solutions"].split("\n")
            solutions.extend([s.strip() for s in user_solutions if s.strip()])
        
        # 从分析结果提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.key_selling_points:
            solutions.extend(analysis_result.listing_analysis.key_selling_points[:2])
        
        # 默认解决方案
        if len(solutions) == 0:
            solutions = [
                "一键智能操作",
                "简单易用设计",
                "卓越效果保证"
            ]
        
        return solutions[:3]
    
    def _determine_comparison_style(self, problem_type: str) -> str:
        """确定对比风格"""
        style_mapping = {
            "efficiency": "time_comparison",
            "complexity": "simplicity_contrast",
            "quality": "result_comparison",
            "safety": "risk_reduction",
            "general": "before_after"
        }
        return style_mapping.get(problem_type, "before_after")
    
    def _generate_visual_metaphors(self, problem_type: str) -> List[str]:
        """生成视觉隐喻"""
        metaphor_mapping = {
            "efficiency": ["clock", "speedometer", "progress_bar"],
            "complexity": ["maze_vs_straight", "tangled_vs_organized"],
            "quality": ["broken_vs_perfect", "dull_vs_bright"],
            "safety": ["warning_vs_checkmark", "red_vs_green"],
            "general": ["frown_vs_smile", "cross_vs_tick"]
        }
        return metaphor_mapping.get(problem_type, ["before_vs_after"])
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "problem_color": "#E74C3C",    # 红色表示问题
            "solution_color": "#27AE60",   # 绿色表示解决方案
            "transition_color": "#3498DB", # 蓝色表示转换
            "text_color": "#2C3E50",       # 深色文字
            "background": "#FFFFFF"        # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        canvas = Image.new('RGB', (width, height), color='white')
        return canvas
    
    def _draw_problem_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                          template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制问题区域"""
        draw = ImageDraw.Draw(canvas)
        problems = layout_config["problems"]
        
        if "before_area" in template or "problem_area" in template:
            area_key = "before_area" if "before_area" in template else "problem_area"
            area = template[area_key]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制问题区域背景
            draw.rectangle([x1, y1, x2, y2], 
                         fill=layout_config["color_scheme"]["problem_color"], 
                         outline="#000000", width=2)
            
            # 添加问题文字
            for i, problem in enumerate(problems):
                y_pos = y1 + 20 + i * 25
                draw.text((x1 + 10, y_pos), f"问题 {i+1}: {problem}", 
                         fill="white")
        
        return canvas
    
    def _draw_solution_area(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                           template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制解决方案区域"""
        draw = ImageDraw.Draw(canvas)
        solutions = layout_config["solutions"]
        
        if "after_area" in template or "solution_area" in template:
            area_key = "after_area" if "after_area" in template else "solution_area"
            area = template[area_key]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制解决方案区域背景
            draw.rectangle([x1, y1, x2, y2], 
                         fill=layout_config["color_scheme"]["solution_color"], 
                         outline="#000000", width=2)
            
            # 添加解决方案文字
            for i, solution in enumerate(solutions):
                y_pos = y1 + 20 + i * 25
                draw.text((x1 + 10, y_pos), f"解决 {i+1}: {solution}", 
                         fill="white")
        
        return canvas
    
    def _add_transition_elements(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any]) -> Image.Image:
        """添加转换元素（箭头等）"""
        draw = ImageDraw.Draw(canvas)
        
        if "arrow_area" in template:
            area = template["arrow_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制箭头
            arrow_color = layout_config["color_scheme"]["transition_color"]
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # 简单箭头形状
            arrow_points = [
                (x1, center_y),
                (center_x - 10, center_y - 10),
                (center_x - 10, center_y + 10)
            ]
            draw.polygon(arrow_points, fill=arrow_color)
        
        return canvas
    
    def _add_titles_and_labels(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                              template: Dict[str, Any]) -> Image.Image:
        """添加标题和标签"""
        draw = ImageDraw.Draw(canvas)
        
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加主标题
            draw.text((x1, y1), "问题解决对比", 
                     fill=layout_config["color_scheme"]["text_color"])
        
        return canvas
    
    def _apply_visual_emphasis(self, canvas: Image.Image, layout_config: Dict[str, Any]) -> Image.Image:
        """应用视觉强调"""
        # 添加视觉强调元素，如高亮、阴影等
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Problem solution module with {layout_config['template']} layout, " \
               f"showing {len(layout_config['problems'])} problems and " \
               f"{len(layout_config['solutions'])} solutions in " \
               f"{layout_config['comparison_style']} style"