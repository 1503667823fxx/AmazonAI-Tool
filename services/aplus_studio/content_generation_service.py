"""
A+ 智能工作流内容生成服务

该模块实现模块内容自动生成功能，包括：
- 为每个模块类型创建内容生成逻辑
- 集成多语言内容生成支持
- 实现基于产品分析的内容定制
- 识别AI无法生成的内容项
- 生成具体的素材需求提示
- 实现素材与内容的关联更新
"""

import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import streamlit as st
import google.generativeai as genai

from .models import ModuleType, Priority, ProductCategory
from .intelligent_workflow import (
    ProductAnalysis, ModuleContent, MaterialRequest,
    IntelligentModuleContent, IntelligentMaterialRequest
)
from .amazon_compliance_service import AmazonComplianceService
from .performance_monitor import (
    PerformanceMonitor, performance_monitor, get_global_performance_monitor
)
from .error_handler import (
    ErrorHandler, error_handler, get_global_error_handler
)

logger = logging.getLogger(__name__)


class ContentGenerationType(Enum):
    """内容生成类型"""
    AI_GENERATED = "ai_generated"      # AI完全生成
    TEMPLATE_BASED = "template_based"  # 基于模板生成
    USER_PROVIDED = "user_provided"    # 需要用户提供
    HYBRID = "hybrid"                  # 混合模式


class MaterialType(Enum):
    """素材类型"""
    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    DATA = "data"
    SPECIFICATION = "specification"
    CUSTOM_PROMPT = "custom_prompt"


@dataclass
class ContentTemplate:
    """内容模板"""
    module_type: ModuleType
    language: str
    title_template: str
    description_template: str
    key_points_templates: List[str]
    content_sections: Dict[str, str]
    required_variables: List[str]
    
    def format_content(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """格式化内容模板"""
        try:
            formatted_content = {}
            
            # 格式化标题
            formatted_content["title"] = self.title_template.format(**variables)
            
            # 格式化描述
            formatted_content["description"] = self.description_template.format(**variables)
            
            # 格式化关键点
            formatted_content["key_points"] = []
            for template in self.key_points_templates:
                formatted_content["key_points"].append(template.format(**variables))
            
            # 格式化其他内容部分
            for section_name, section_template in self.content_sections.items():
                formatted_content[section_name] = section_template.format(**variables)
            
            return formatted_content
            
        except KeyError as e:
            logger.error(f"Missing variable for template formatting: {e}")
            raise ValueError(f"缺少模板变量: {e}")
        except Exception as e:
            logger.error(f"Template formatting failed: {e}")
            raise


@dataclass
class GenerationContext:
    """内容生成上下文"""
    product_analysis: ProductAnalysis
    module_type: ModuleType
    language: str
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    user_inputs: Dict[str, Any] = field(default_factory=dict)
    existing_content: Optional[Dict[str, Any]] = None


class ContentGenerationService:
    """内容生成服务"""
    
    def __init__(self):
        self._gemini_model = None
        self.content_templates = self._initialize_content_templates()
        self.material_requirements = self._initialize_material_requirements()
        self.supported_languages = ["zh", "en", "es", "de", "fr", "ja"]
        
        # 初始化亚马逊合规检查服务
        self.compliance_service = AmazonComplianceService()
        
        # 初始化性能监控和错误处理
        self._performance_monitor = get_global_performance_monitor()
        self._error_handler = get_global_error_handler()
        
        # 注册回退处理器
        self._register_fallback_handlers()
        
        logger.info("Content Generation Service initialized")
    
    def _register_fallback_handlers(self):
        """注册回退处理器"""
        def content_generation_fallback(*args, **kwargs):
            logger.info("Using fallback for content generation")
            context = args[0] if args else kwargs.get("context")
            if context:
                return self._get_default_content(context)
            return {
                "title": "产品内容",
                "description": "产品描述",
                "key_points": ["特点1", "特点2", "特点3"],
                "sections": {"main_content": "主要内容"}
            }
        
        self._error_handler.register_fallback_handler("generate_module_content", content_generation_fallback)
    
    def _get_gemini_client(self):
        """获取Gemini客户端"""
        if self._gemini_model is None:
            try:
                api_key = st.secrets["GOOGLE_API_KEY"]
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel('models/gemini-3-pro-preview')
                logger.info("Gemini client initialized for content generation")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
                raise ValueError(f"Gemini API配置错误: {str(e)}")
        
        return self._gemini_model
    
    def _initialize_content_templates(self) -> Dict[Tuple[ModuleType, str], ContentTemplate]:
        """初始化内容模板"""
        templates = {}
        
        # 产品概览模块 - 中文
        templates[(ModuleType.PRODUCT_OVERVIEW, "zh")] = ContentTemplate(
            module_type=ModuleType.PRODUCT_OVERVIEW,
            language="zh",
            title_template="{product_type} - 全面概览",
            description_template="深入了解{product_type}的核心特性和优势，为您的选择提供全面参考。",
            key_points_templates=[
                "核心功能：{key_feature_1}",
                "设计亮点：{key_feature_2}",
                "品质保证：{key_feature_3}",
                "适用场景：{primary_use_case}"
            ],
            content_sections={
                "main_description": "这款{product_type}专为{target_audience}设计，具备{key_feature_1}等核心功能。",
                "value_proposition": "选择我们的{product_type}，享受{marketing_angle_1}的卓越体验。"
            },
            required_variables=["product_type", "key_feature_1", "key_feature_2", "key_feature_3", 
                              "primary_use_case", "target_audience", "marketing_angle_1"]
        )
        
        # 产品概览模块 - 英文
        templates[(ModuleType.PRODUCT_OVERVIEW, "en")] = ContentTemplate(
            module_type=ModuleType.PRODUCT_OVERVIEW,
            language="en",
            title_template="{product_type} - Complete Overview",
            description_template="Discover the core features and advantages of {product_type} for comprehensive reference.",
            key_points_templates=[
                "Core Function: {key_feature_1}",
                "Design Highlight: {key_feature_2}",
                "Quality Assurance: {key_feature_3}",
                "Application: {primary_use_case}"
            ],
            content_sections={
                "main_description": "This {product_type} is designed for {target_audience} with core functions like {key_feature_1}.",
                "value_proposition": "Choose our {product_type} for {marketing_angle_1} excellence."
            },
            required_variables=["product_type", "key_feature_1", "key_feature_2", "key_feature_3", 
                              "primary_use_case", "target_audience", "marketing_angle_1"]
        )
        
        # 问题解决模块 - 中文
        templates[(ModuleType.PROBLEM_SOLUTION, "zh")] = ContentTemplate(
            module_type=ModuleType.PROBLEM_SOLUTION,
            language="zh",
            title_template="解决方案：{product_type}如何改善您的体验",
            description_template="了解{product_type}如何有效解决常见问题，提升使用体验。",
            key_points_templates=[
                "问题识别：{common_problem}",
                "解决方案：{solution_approach}",
                "效果提升：{improvement_result}",
                "用户受益：{user_benefit}"
            ],
            content_sections={
                "problem_statement": "传统方式存在{common_problem}的困扰。",
                "solution_description": "我们的{product_type}通过{solution_approach}有效解决这一问题。",
                "benefit_summary": "使用后，您将体验到{improvement_result}的显著改善。"
            },
            required_variables=["product_type", "common_problem", "solution_approach", 
                              "improvement_result", "user_benefit"]
        )
        
        # 功能解析模块 - 中文
        templates[(ModuleType.FEATURE_ANALYSIS, "zh")] = ContentTemplate(
            module_type=ModuleType.FEATURE_ANALYSIS,
            language="zh",
            title_template="{product_type} 功能深度解析",
            description_template="详细解析{product_type}的各项功能特性，帮助您全面了解产品价值。",
            key_points_templates=[
                "主要功能：{primary_function}",
                "技术特点：{technical_feature}",
                "操作便捷：{usability_feature}",
                "性能优势：{performance_advantage}"
            ],
            content_sections={
                "function_overview": "{product_type}集成了{primary_function}等多项先进功能。",
                "technical_details": "采用{technical_feature}技术，确保{performance_advantage}。",
                "user_experience": "简化的操作设计，实现{usability_feature}的便捷体验。"
            },
            required_variables=["product_type", "primary_function", "technical_feature", 
                              "usability_feature", "performance_advantage"]
        )
        
        # 规格对比模块 - 中文
        templates[(ModuleType.SPECIFICATION_COMPARISON, "zh")] = ContentTemplate(
            module_type=ModuleType.SPECIFICATION_COMPARISON,
            language="zh",
            title_template="{product_type} 规格参数对比",
            description_template="全面对比{product_type}的技术规格，突出产品优势。",
            key_points_templates=[
                "核心参数：{key_specification}",
                "性能指标：{performance_metric}",
                "技术优势：{technical_advantage}",
                "兼容性：{compatibility_info}"
            ],
            content_sections={
                "spec_highlight": "关键规格：{key_specification}，性能表现：{performance_metric}。",
                "advantage_summary": "相比同类产品，具备{technical_advantage}的明显优势。",
                "compatibility_note": "支持{compatibility_info}，确保广泛适用性。"
            },
            required_variables=["product_type", "key_specification", "performance_metric", 
                              "technical_advantage", "compatibility_info"]
        )
        
        # 使用场景模块 - 中文
        templates[(ModuleType.USAGE_SCENARIOS, "zh")] = ContentTemplate(
            module_type=ModuleType.USAGE_SCENARIOS,
            language="zh",
            title_template="{product_type} 实际应用场景",
            description_template="展示{product_type}在不同场景下的实际应用效果。",
            key_points_templates=[
                "场景一：{scenario_1}",
                "场景二：{scenario_2}",
                "场景三：{scenario_3}",
                "适用范围：{application_range}"
            ],
            content_sections={
                "scenario_intro": "{product_type}适用于{application_range}等多种场景。",
                "practical_examples": "无论是{scenario_1}还是{scenario_2}，都能发挥出色效果。",
                "versatility_note": "多样化的应用场景，满足{scenario_3}等不同需求。"
            },
            required_variables=["product_type", "scenario_1", "scenario_2", "scenario_3", "application_range"]
        )
        
        return templates
    
    def _initialize_material_requirements(self) -> Dict[ModuleType, List[Dict[str, Any]]]:
        """初始化素材需求配置"""
        requirements = {}
        
        # 产品概览模块素材需求
        requirements[ModuleType.PRODUCT_OVERVIEW] = [
            {
                "material_type": MaterialType.IMAGE,
                "priority": Priority.RECOMMENDED,
                "description": "产品高清主图（多角度展示）",
                "examples": ["正面图", "侧面图", "细节图"],
                "help_text": "提供产品的多角度高清图片，有助于生成更准确的概览内容"
            }
        ]
        
        # 问题解决模块素材需求
        requirements[ModuleType.PROBLEM_SOLUTION] = [
            {
                "material_type": MaterialType.TEXT,
                "priority": Priority.RECOMMENDED,
                "description": "用户常见问题描述",
                "examples": ["使用中遇到的困难", "传统方案的不足"],
                "help_text": "描述用户在使用类似产品时遇到的问题，帮助AI生成更贴切的解决方案"
            },
            {
                "material_type": MaterialType.IMAGE,
                "priority": Priority.OPTIONAL,
                "description": "问题场景对比图",
                "examples": ["使用前后对比", "问题现象图片"],
                "help_text": "展示问题场景的图片，增强解决方案的说服力"
            }
        ]
        
        # 功能解析模块素材需求
        requirements[ModuleType.FEATURE_ANALYSIS] = [
            {
                "material_type": MaterialType.SPECIFICATION,
                "priority": Priority.REQUIRED,
                "description": "详细技术规格参数",
                "examples": ["功能列表", "技术参数表", "性能指标"],
                "help_text": "提供产品的详细技术规格，确保功能解析的准确性"
            },
            {
                "material_type": MaterialType.IMAGE,
                "priority": Priority.RECOMMENDED,
                "description": "功能展示图片",
                "examples": ["功能界面截图", "操作演示图", "内部结构图"],
                "help_text": "展示产品功能的图片，帮助用户更好理解功能特点"
            }
        ]
        
        # 规格对比模块素材需求
        requirements[ModuleType.SPECIFICATION_COMPARISON] = [
            {
                "material_type": MaterialType.DATA,
                "priority": Priority.REQUIRED,
                "description": "竞品对比数据",
                "examples": ["性能参数对比表", "功能差异列表", "价格对比"],
                "help_text": "提供与竞品的对比数据，突出产品优势"
            },
            {
                "material_type": MaterialType.SPECIFICATION,
                "priority": Priority.REQUIRED,
                "description": "完整产品规格表",
                "examples": ["技术参数", "尺寸重量", "兼容性信息"],
                "help_text": "详细的产品规格信息，用于生成准确的对比内容"
            }
        ]
        
        # 使用场景模块素材需求
        requirements[ModuleType.USAGE_SCENARIOS] = [
            {
                "material_type": MaterialType.TEXT,
                "priority": Priority.RECOMMENDED,
                "description": "具体使用场景描述",
                "examples": ["办公场景", "家庭使用", "户外应用"],
                "help_text": "描述产品的具体使用场景，帮助生成更真实的应用展示"
            },
            {
                "material_type": MaterialType.IMAGE,
                "priority": Priority.OPTIONAL,
                "description": "场景应用图片",
                "examples": ["实际使用环境照片", "应用场景示意图"],
                "help_text": "展示产品在实际场景中的应用图片"
            }
        ]
        
        # 安装指南模块素材需求
        requirements[ModuleType.INSTALLATION_GUIDE] = [
            {
                "material_type": MaterialType.DOCUMENT,
                "priority": Priority.REQUIRED,
                "description": "安装说明文档",
                "examples": ["安装步骤", "注意事项", "工具清单"],
                "help_text": "提供详细的安装说明，确保指南的准确性和完整性"
            },
            {
                "material_type": MaterialType.IMAGE,
                "priority": Priority.RECOMMENDED,
                "description": "安装过程图片",
                "examples": ["安装步骤图", "工具使用图", "完成效果图"],
                "help_text": "安装过程的图片说明，提高指南的可理解性"
            }
        ]
        
        return requirements
    
    @performance_monitor("generate_module_content", cache_key_params={"context": 0}, cache_ttl=1800)
    @error_handler("generate_module_content", max_retries=3, enable_recovery=True)
    def generate_module_content(self, context: GenerationContext) -> IntelligentModuleContent:
        """生成模块内容
        
        Args:
            context: 生成上下文，包含产品分析、模块类型、语言等信息
            
        Returns:
            IntelligentModuleContent: 生成的模块内容
            
        Raises:
            ValueError: 输入参数无效
            Exception: 内容生成失败
        """
        try:
            logger.info(f"Generating content for module: {context.module_type.value} in {context.language}")
            
            # 验证输入
            if context.language not in self.supported_languages:
                raise ValueError(f"不支持的语言: {context.language}")
            
            # 生成内容
            if self._should_use_ai_generation(context):
                content = self._generate_with_ai(context)
            else:
                content = self._generate_with_template(context)
            
            # 识别素材需求
            material_requests = self._identify_material_needs(context)
            
            # 执行合规检查和自动修正
            content = self._apply_compliance_check(content, context)
            
            # 创建模块内容对象
            module_content = IntelligentModuleContent(
                module_type=context.module_type,
                title=content["title"],
                description=content["description"],
                key_points=content["key_points"],
                generated_text=content.get("sections", {}),
                material_requests=material_requests,
                language=context.language
            )
            
            logger.info(f"Content generation completed for {context.module_type.value}")
            return module_content
            
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise
    
    def _should_use_ai_generation(self, context: GenerationContext) -> bool:
        """判断是否应该使用AI生成"""
        # 检查是否有Gemini API配置
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY")
            if not api_key:
                return False
        except:
            return False
        
        # 复杂模块优先使用AI生成
        complex_modules = [
            ModuleType.FEATURE_ANALYSIS,
            ModuleType.SPECIFICATION_COMPARISON,
            ModuleType.PROBLEM_SOLUTION
        ]
        
        if context.module_type in complex_modules:
            return True
        
        # 如果产品分析置信度较高，使用AI生成
        if context.product_analysis.confidence_score > 0.8:
            return True
        
        # 默认使用模板生成
        return False
    
    def _generate_with_ai(self, context: GenerationContext) -> Dict[str, Any]:
        """使用AI生成内容"""
        try:
            logger.info(f"Using AI generation for {context.module_type.value}")
            
            # 获取Gemini客户端
            model = self._get_gemini_client()
            
            # 构建生成提示词
            prompt = self._build_content_generation_prompt(context)
            
            # 调用AI生成
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,  # 适中的创造性
                    max_output_tokens=1500,
                )
            )
            
            if not response.text:
                raise Exception("AI生成返回空响应")
            
            # 解析AI响应
            content = self._parse_ai_content_response(response.text, context)
            
            logger.info(f"AI content generation completed for {context.module_type.value}")
            return content
            
        except Exception as e:
            logger.error(f"AI content generation failed: {str(e)}")
            # 回退到模板生成
            logger.info("Falling back to template generation")
            return self._generate_with_template(context)
    
    def _build_content_generation_prompt(self, context: GenerationContext) -> str:
        """构建内容生成提示词"""
        analysis = context.product_analysis
        module_type = context.module_type
        language = context.language
        
        # 基础提示词
        if language == "zh":
            base_prompt = f"""请为{analysis.product_type}生成{self._get_module_display_name(module_type, language)}模块的内容。

产品信息：
- 产品类型：{analysis.product_type}
- 产品类别：{analysis.product_category.value}
- 关键特征：{', '.join(analysis.key_features)}
- 材料：{', '.join(analysis.materials)}
- 目标用户：{analysis.target_audience}
- 使用场景：{', '.join(analysis.use_cases)}
- 营销角度：{', '.join(analysis.marketing_angles)}

请以JSON格式返回内容，包含以下字段：
{{
  "title": "模块标题",
  "description": "模块描述",
  "key_points": ["要点1", "要点2", "要点3", "要点4"],
  "sections": {{
    "main_content": "主要内容",
    "highlight": "重点强调",
    "summary": "总结"
  }}
}}

内容要求：
1. 符合亚马逊A+页面规范，避免主观性词汇
2. 突出产品特性和实用价值
3. 语言专业且易懂
4. 内容信息密集，避免过度装饰
5. 确保内容与{self._get_module_display_name(module_type, language)}模块主题相关

请确保返回有效的JSON格式。"""
        else:
            base_prompt = f"""Please generate content for the {self._get_module_display_name(module_type, language)} module for {analysis.product_type}.

Product Information:
- Product Type: {analysis.product_type}
- Product Category: {analysis.product_category.value}
- Key Features: {', '.join(analysis.key_features)}
- Materials: {', '.join(analysis.materials)}
- Target Audience: {analysis.target_audience}
- Use Cases: {', '.join(analysis.use_cases)}
- Marketing Angles: {', '.join(analysis.marketing_angles)}

Please return content in JSON format with the following fields:
{{
  "title": "Module Title",
  "description": "Module Description", 
  "key_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
  "sections": {{
    "main_content": "Main Content",
    "highlight": "Key Highlight",
    "summary": "Summary"
  }}
}}

Content Requirements:
1. Comply with Amazon A+ page standards, avoid subjective terms
2. Highlight product features and practical value
3. Professional yet understandable language
4. Information-dense content, avoid excessive decoration
5. Ensure content is relevant to {self._get_module_display_name(module_type, language)} module theme

Please ensure valid JSON format is returned."""
        
        # 添加模块特定要求
        module_specific_prompt = self._get_module_specific_prompt(module_type, language)
        if module_specific_prompt:
            base_prompt += f"\n\n{module_specific_prompt}"
        
        return base_prompt
    
    def _get_module_display_name(self, module_type: ModuleType, language: str) -> str:
        """获取模块显示名称"""
        if language == "zh":
            names = {
                ModuleType.PRODUCT_OVERVIEW: "产品概览",
                ModuleType.PROBLEM_SOLUTION: "问题解决",
                ModuleType.FEATURE_ANALYSIS: "功能解析",
                ModuleType.SPECIFICATION_COMPARISON: "规格对比",
                ModuleType.USAGE_SCENARIOS: "使用场景",
                ModuleType.INSTALLATION_GUIDE: "安装指南",
                ModuleType.SIZE_COMPATIBILITY: "尺寸兼容",
                ModuleType.MAINTENANCE_CARE: "维护保养",
                ModuleType.MATERIAL_CRAFTSMANSHIP: "材质工艺",
                ModuleType.QUALITY_ASSURANCE: "品质保证",
                ModuleType.CUSTOMER_REVIEWS: "用户评价",
                ModuleType.PACKAGE_CONTENTS: "包装内容"
            }
        else:
            names = {
                ModuleType.PRODUCT_OVERVIEW: "Product Overview",
                ModuleType.PROBLEM_SOLUTION: "Problem Solution",
                ModuleType.FEATURE_ANALYSIS: "Feature Analysis",
                ModuleType.SPECIFICATION_COMPARISON: "Specification Comparison",
                ModuleType.USAGE_SCENARIOS: "Usage Scenarios",
                ModuleType.INSTALLATION_GUIDE: "Installation Guide",
                ModuleType.SIZE_COMPATIBILITY: "Size Compatibility",
                ModuleType.MAINTENANCE_CARE: "Maintenance Care",
                ModuleType.MATERIAL_CRAFTSMANSHIP: "Material Craftsmanship",
                ModuleType.QUALITY_ASSURANCE: "Quality Assurance",
                ModuleType.CUSTOMER_REVIEWS: "Customer Reviews",
                ModuleType.PACKAGE_CONTENTS: "Package Contents"
            }
        
        return names.get(module_type, module_type.value)
    
    def _get_module_specific_prompt(self, module_type: ModuleType, language: str) -> str:
        """获取模块特定的提示词要求"""
        if language == "zh":
            specific_prompts = {
                ModuleType.PRODUCT_OVERVIEW: "重点展示产品的核心价值和整体特性，使用英雄式布局思维。",
                ModuleType.PROBLEM_SOLUTION: "采用问题-解决方案的对比结构，突出产品如何解决用户痛点。",
                ModuleType.FEATURE_ANALYSIS: "使用技术图表和标注思维，详细解析功能细节。",
                ModuleType.SPECIFICATION_COMPARISON: "创建清晰的对比表格思维，突出技术优势。",
                ModuleType.USAGE_SCENARIOS: "展示产品在实际环境中的应用，避免生活方式化表达。",
                ModuleType.INSTALLATION_GUIDE: "提供清晰的步骤指导，包含工具和安全提示。",
                ModuleType.SIZE_COMPATIBILITY: "重点说明尺寸规格和兼容性信息。",
                ModuleType.MAINTENANCE_CARE: "提供实用的维护保养建议和注意事项。",
                ModuleType.MATERIAL_CRAFTSMANSHIP: "突出材质特点和工艺细节。",
                ModuleType.QUALITY_ASSURANCE: "展示品质认证和质量保证信息。",
                ModuleType.CUSTOMER_REVIEWS: "整理用户反馈和评价要点。",
                ModuleType.PACKAGE_CONTENTS: "详细列出包装内容和价值体现。"
            }
        else:
            specific_prompts = {
                ModuleType.PRODUCT_OVERVIEW: "Focus on core value and overall features with hero layout thinking.",
                ModuleType.PROBLEM_SOLUTION: "Use problem-solution comparison structure, highlight how product solves pain points.",
                ModuleType.FEATURE_ANALYSIS: "Use technical diagram and annotation thinking for detailed feature breakdown.",
                ModuleType.SPECIFICATION_COMPARISON: "Create clear comparison table thinking, highlight technical advantages.",
                ModuleType.USAGE_SCENARIOS: "Show product applications in real environments, avoid lifestyle expressions.",
                ModuleType.INSTALLATION_GUIDE: "Provide clear step-by-step guidance with tools and safety tips.",
                ModuleType.SIZE_COMPATIBILITY: "Focus on size specifications and compatibility information.",
                ModuleType.MAINTENANCE_CARE: "Provide practical maintenance advice and precautions.",
                ModuleType.MATERIAL_CRAFTSMANSHIP: "Highlight material characteristics and craftsmanship details.",
                ModuleType.QUALITY_ASSURANCE: "Show quality certifications and assurance information.",
                ModuleType.CUSTOMER_REVIEWS: "Organize user feedback and review highlights.",
                ModuleType.PACKAGE_CONTENTS: "Detail package contents and value demonstration."
            }
        
        return specific_prompts.get(module_type, "")
    
    def _parse_ai_content_response(self, response_text: str, context: GenerationContext) -> Dict[str, Any]:
        """解析AI内容响应"""
        try:
            # 清理响应文本
            response_text = response_text.strip()
            
            # 移除可能的markdown代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # 解析JSON
            parsed_data = json.loads(response_text)
            
            # 验证和清理数据
            content = {
                "title": parsed_data.get("title", f"{self._get_module_display_name(context.module_type, context.language)}"),
                "description": parsed_data.get("description", ""),
                "key_points": parsed_data.get("key_points", [])[:4],  # 最多4个要点
                "sections": parsed_data.get("sections", {})
            }
            
            # 确保关键点不为空
            if not content["key_points"]:
                content["key_points"] = self._get_default_key_points(context)
            
            # 确保描述不为空
            if not content["description"]:
                content["description"] = self._get_default_description(context)
            
            return content
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
            # 尝试从文本中提取内容
            return self._extract_content_from_text(response_text, context)
        except Exception as e:
            logger.error(f"Error parsing AI content response: {str(e)}")
            # 返回默认内容
            return self._get_default_content(context)
    
    def _extract_content_from_text(self, response_text: str, context: GenerationContext) -> Dict[str, Any]:
        """从文本响应中提取内容"""
        try:
            # 简单的文本解析逻辑
            lines = response_text.split('\n')
            
            title = ""
            description = ""
            key_points = []
            
            # 查找标题
            for line in lines:
                if "标题" in line or "title" in line.lower():
                    title = line.split("：")[-1].split(":")[-1].strip()
                    break
            
            # 查找描述
            for line in lines:
                if "描述" in line or "description" in line.lower():
                    description = line.split("：")[-1].split(":")[-1].strip()
                    break
            
            # 查找要点
            for line in lines:
                if line.strip().startswith(("•", "-", "*", "1.", "2.", "3.", "4.")):
                    point = line.strip().lstrip("•-*1234.").strip()
                    if point and len(key_points) < 4:
                        key_points.append(point)
            
            # 如果提取失败，使用默认内容
            if not title:
                title = self._get_default_title(context)
            if not description:
                description = self._get_default_description(context)
            if not key_points:
                key_points = self._get_default_key_points(context)
            
            return {
                "title": title,
                "description": description,
                "key_points": key_points,
                "sections": {"main_content": response_text[:500]}  # 取前500字符作为主要内容
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return self._get_default_content(context)
    
    def _generate_with_template(self, context: GenerationContext) -> Dict[str, Any]:
        """使用模板生成内容"""
        try:
            logger.info(f"Using template generation for {context.module_type.value}")
            
            # 获取模板
            template_key = (context.module_type, context.language)
            template = self.content_templates.get(template_key)
            
            if not template:
                # 如果没有对应语言的模板，尝试使用英文模板
                template = self.content_templates.get((context.module_type, "en"))
            
            if not template:
                # 如果仍然没有模板，使用默认内容
                return self._get_default_content(context)
            
            # 准备模板变量
            variables = self._prepare_template_variables(context)
            
            # 格式化模板
            formatted_content = template.format_content(variables)
            
            # 转换为标准格式
            content = {
                "title": formatted_content["title"],
                "description": formatted_content["description"],
                "key_points": formatted_content["key_points"],
                "sections": {k: v for k, v in formatted_content.items() 
                           if k not in ["title", "description", "key_points"]}
            }
            
            logger.info(f"Template content generation completed for {context.module_type.value}")
            return content
            
        except Exception as e:
            logger.error(f"Template generation failed: {str(e)}")
            return self._get_default_content(context)
    
    def _prepare_template_variables(self, context: GenerationContext) -> Dict[str, Any]:
        """准备模板变量"""
        analysis = context.product_analysis
        
        # 基础变量
        variables = {
            "product_type": analysis.product_type,
            "target_audience": analysis.target_audience,
            "product_category": analysis.product_category.value
        }
        
        # 添加关键特征变量
        for i, feature in enumerate(analysis.key_features[:5], 1):
            variables[f"key_feature_{i}"] = feature
        
        # 添加材料变量
        for i, material in enumerate(analysis.materials[:3], 1):
            variables[f"material_{i}"] = material
        
        # 添加使用场景变量
        for i, use_case in enumerate(analysis.use_cases[:3], 1):
            variables[f"scenario_{i}"] = use_case
            if i == 1:
                variables["primary_use_case"] = use_case
        
        # 添加营销角度变量
        for i, angle in enumerate(analysis.marketing_angles[:3], 1):
            variables[f"marketing_angle_{i}"] = angle
        
        # 添加模块特定变量
        module_variables = self._get_module_specific_variables(context)
        variables.update(module_variables)
        
        # 填充缺失的变量
        required_vars = ["key_feature_1", "key_feature_2", "key_feature_3", 
                        "primary_use_case", "marketing_angle_1"]
        for var in required_vars:
            if var not in variables:
                variables[var] = "优质特性" if context.language == "zh" else "Quality Feature"
        
        return variables
    
    def _get_module_specific_variables(self, context: GenerationContext) -> Dict[str, Any]:
        """获取模块特定变量"""
        analysis = context.product_analysis
        variables = {}
        
        if context.module_type == ModuleType.PROBLEM_SOLUTION:
            variables.update({
                "common_problem": "传统方案的不足" if context.language == "zh" else "Traditional solution limitations",
                "solution_approach": "创新解决方案" if context.language == "zh" else "Innovative solution",
                "improvement_result": "显著改善" if context.language == "zh" else "Significant improvement",
                "user_benefit": "用户体验提升" if context.language == "zh" else "Enhanced user experience"
            })
        
        elif context.module_type == ModuleType.FEATURE_ANALYSIS:
            variables.update({
                "primary_function": analysis.key_features[0] if analysis.key_features else "核心功能",
                "technical_feature": "先进技术" if context.language == "zh" else "Advanced technology",
                "usability_feature": "便捷操作" if context.language == "zh" else "Easy operation",
                "performance_advantage": "卓越性能" if context.language == "zh" else "Excellent performance"
            })
        
        elif context.module_type == ModuleType.SPECIFICATION_COMPARISON:
            variables.update({
                "key_specification": "关键参数" if context.language == "zh" else "Key specifications",
                "performance_metric": "性能指标" if context.language == "zh" else "Performance metrics",
                "technical_advantage": "技术优势" if context.language == "zh" else "Technical advantages",
                "compatibility_info": "兼容性信息" if context.language == "zh" else "Compatibility information"
            })
        
        elif context.module_type == ModuleType.USAGE_SCENARIOS:
            # 使用场景变量已在基础变量中处理
            variables.update({
                "application_range": "多种应用" if context.language == "zh" else "Multiple applications"
            })
        
        return variables
    
    def _get_default_content(self, context: GenerationContext) -> Dict[str, Any]:
        """获取默认内容"""
        if context.language == "zh":
            return {
                "title": f"{context.product_analysis.product_type} - {self._get_module_display_name(context.module_type, context.language)}",
                "description": f"了解{context.product_analysis.product_type}的{self._get_module_display_name(context.module_type, context.language)}信息。",
                "key_points": [
                    f"核心特性：{context.product_analysis.key_features[0] if context.product_analysis.key_features else '优质功能'}",
                    f"适用场景：{context.product_analysis.use_cases[0] if context.product_analysis.use_cases else '日常使用'}",
                    f"目标用户：{context.product_analysis.target_audience}",
                    f"品质保证：{context.product_analysis.materials[0] if context.product_analysis.materials else '优质材料'}"
                ],
                "sections": {
                    "main_content": f"这款{context.product_analysis.product_type}专为{context.product_analysis.target_audience}设计。"
                }
            }
        else:
            return {
                "title": f"{context.product_analysis.product_type} - {self._get_module_display_name(context.module_type, context.language)}",
                "description": f"Learn about {context.product_analysis.product_type} {self._get_module_display_name(context.module_type, context.language)} information.",
                "key_points": [
                    f"Core Feature: {context.product_analysis.key_features[0] if context.product_analysis.key_features else 'Quality Function'}",
                    f"Application: {context.product_analysis.use_cases[0] if context.product_analysis.use_cases else 'Daily Use'}",
                    f"Target Users: {context.product_analysis.target_audience}",
                    f"Quality Assurance: {context.product_analysis.materials[0] if context.product_analysis.materials else 'Quality Materials'}"
                ],
                "sections": {
                    "main_content": f"This {context.product_analysis.product_type} is designed for {context.product_analysis.target_audience}."
                }
            }
    
    def _get_default_title(self, context: GenerationContext) -> str:
        """获取默认标题"""
        return f"{context.product_analysis.product_type} - {self._get_module_display_name(context.module_type, context.language)}"
    
    def _get_default_description(self, context: GenerationContext) -> str:
        """获取默认描述"""
        if context.language == "zh":
            return f"了解{context.product_analysis.product_type}的{self._get_module_display_name(context.module_type, context.language)}信息。"
        else:
            return f"Learn about {context.product_analysis.product_type} {self._get_module_display_name(context.module_type, context.language)} information."
    
    def _get_default_key_points(self, context: GenerationContext) -> List[str]:
        """获取默认关键点"""
        analysis = context.product_analysis
        
        if context.language == "zh":
            points = [
                f"核心特性：{analysis.key_features[0] if analysis.key_features else '优质功能'}",
                f"适用场景：{analysis.use_cases[0] if analysis.use_cases else '日常使用'}",
                f"目标用户：{analysis.target_audience}",
                f"品质保证：{analysis.materials[0] if analysis.materials else '优质材料'}"
            ]
        else:
            points = [
                f"Core Feature: {analysis.key_features[0] if analysis.key_features else 'Quality Function'}",
                f"Application: {analysis.use_cases[0] if analysis.use_cases else 'Daily Use'}",
                f"Target Users: {analysis.target_audience}",
                f"Quality Assurance: {analysis.materials[0] if analysis.materials else 'Quality Materials'}"
            ]
        
        return points
    
    def _identify_material_needs(self, context: GenerationContext) -> List[IntelligentMaterialRequest]:
        """识别素材需求"""
        try:
            logger.info(f"Identifying material needs for {context.module_type.value}")
            
            # 获取模块的素材需求配置
            module_requirements = self.material_requirements.get(context.module_type, [])
            
            material_requests = []
            
            for req_config in module_requirements:
                # 创建素材请求
                request = IntelligentMaterialRequest(
                    request_id=str(uuid.uuid4()),
                    material_type=req_config["material_type"].value,
                    description=req_config["description"],
                    importance=req_config["priority"],
                    example=", ".join(req_config["examples"]) if req_config["examples"] else None,
                    help_text=req_config["help_text"]
                )
                
                material_requests.append(request)
            
            # 添加通用素材需求
            if not any(req.material_type == MaterialType.IMAGE.value for req in material_requests):
                # 如果没有图片需求，添加通用图片需求
                image_request = IntelligentMaterialRequest(
                    request_id=str(uuid.uuid4()),
                    material_type=MaterialType.IMAGE.value,
                    description="产品相关图片" if context.language == "zh" else "Product related images",
                    importance=Priority.OPTIONAL,
                    example="产品图片, 使用场景图" if context.language == "zh" else "Product images, usage scenario images",
                    help_text="提供相关图片可以提升内容质量" if context.language == "zh" else "Providing related images can improve content quality"
                )
                material_requests.append(image_request)
            
            logger.info(f"Identified {len(material_requests)} material needs for {context.module_type.value}")
            return material_requests
            
        except Exception as e:
            logger.error(f"Material needs identification failed: {str(e)}")
            return []
    
    def update_content_with_materials(self, content: IntelligentModuleContent, 
                                    materials: Dict[str, Any]) -> IntelligentModuleContent:
        """根据用户提供的素材更新内容
        
        Args:
            content: 原始模块内容
            materials: 用户提供的素材，格式为 {material_type: material_data}
            
        Returns:
            IntelligentModuleContent: 更新后的模块内容
        """
        try:
            logger.info(f"Updating content with materials for {content.module_type.value}")
            
            # 创建更新后的内容副本
            updated_content = IntelligentModuleContent(
                module_type=content.module_type,
                title=content.title,
                description=content.description,
                key_points=content.key_points.copy(),
                generated_text=content.generated_text.copy(),
                material_requests=content.material_requests.copy(),
                language=content.language,
                generation_timestamp=datetime.now()
            )
            
            # 根据提供的素材更新内容
            for material_type, material_data in materials.items():
                if material_type == MaterialType.TEXT.value and material_data:
                    # 更新文本内容
                    updated_content = self._update_content_with_text(updated_content, material_data)
                
                elif material_type == MaterialType.SPECIFICATION.value and material_data:
                    # 更新规格信息
                    updated_content = self._update_content_with_specifications(updated_content, material_data)
                
                elif material_type == MaterialType.DATA.value and material_data:
                    # 更新数据信息
                    updated_content = self._update_content_with_data(updated_content, material_data)
            
            # 更新素材请求状态（标记已提供的素材）
            for request in updated_content.material_requests:
                if request.material_type in materials and materials[request.material_type]:
                    # 可以添加一个状态字段来标记已提供
                    request.help_text += " [已提供]" if content.language == "zh" else " [Provided]"
            
            logger.info(f"Content updated with materials for {content.module_type.value}")
            return updated_content
            
        except Exception as e:
            logger.error(f"Content update with materials failed: {str(e)}")
            return content  # 返回原始内容
    
    def _update_content_with_text(self, content: IntelligentModuleContent, text_data: str) -> IntelligentModuleContent:
        """使用文本数据更新内容"""
        try:
            # 将用户提供的文本信息整合到内容中
            if "user_input" not in content.generated_text:
                content.generated_text["user_input"] = text_data
            else:
                content.generated_text["user_input"] += f"\n\n{text_data}"
            
            # 根据文本内容更新关键点
            if len(text_data) > 50:  # 如果文本足够长，尝试提取关键信息
                # 简单的关键信息提取（可以后续优化为AI提取）
                sentences = text_data.split('。')[:2]  # 取前两句
                for sentence in sentences:
                    if sentence.strip() and len(content.key_points) < 4:
                        content.key_points.append(sentence.strip())
            
            return content
            
        except Exception as e:
            logger.error(f"Text content update failed: {str(e)}")
            return content
    
    def _update_content_with_specifications(self, content: IntelligentModuleContent, spec_data: str) -> IntelligentModuleContent:
        """使用规格数据更新内容"""
        try:
            # 将规格信息添加到生成文本中
            content.generated_text["specifications"] = spec_data
            
            # 如果是规格对比模块，更新相关内容
            if content.module_type == ModuleType.SPECIFICATION_COMPARISON:
                # 尝试从规格数据中提取关键参数
                lines = spec_data.split('\n')
                spec_points = []
                
                for line in lines[:3]:  # 取前3行作为关键规格
                    if line.strip() and ':' in line:
                        spec_points.append(f"规格参数：{line.strip()}")
                
                if spec_points:
                    content.key_points = spec_points + content.key_points[len(spec_points):]
            
            return content
            
        except Exception as e:
            logger.error(f"Specification content update failed: {str(e)}")
            return content
    
    def _update_content_with_data(self, content: IntelligentModuleContent, data_info: str) -> IntelligentModuleContent:
        """使用数据信息更新内容"""
        try:
            # 将数据信息添加到生成文本中
            content.generated_text["data_info"] = data_info
            
            # 根据数据类型更新内容
            if "对比" in data_info or "comparison" in data_info.lower():
                # 对比数据
                content.generated_text["comparison_data"] = data_info
            
            return content
            
        except Exception as e:
            logger.error(f"Data content update failed: {str(e)}")
            return content
    
    def _apply_compliance_check(self, content: Dict[str, Any], context: GenerationContext) -> Dict[str, Any]:
        """应用合规检查和自动修正
        
        Args:
            content: 生成的内容
            context: 生成上下文
            
        Returns:
            Dict[str, Any]: 合规检查后的内容
        """
        try:
            logger.info(f"Applying compliance check for {context.module_type.value}")
            
            # 收集所有文本内容进行合规检查
            all_text_content = []
            
            # 检查标题
            if content.get("title"):
                all_text_content.append(("title", content["title"]))
            
            # 检查描述
            if content.get("description"):
                all_text_content.append(("description", content["description"]))
            
            # 检查关键点
            for i, point in enumerate(content.get("key_points", [])):
                all_text_content.append((f"key_point_{i}", point))
            
            # 检查其他文本部分
            for section_name, section_content in content.get("sections", {}).items():
                if isinstance(section_content, str):
                    all_text_content.append((f"section_{section_name}", section_content))
            
            # 对每个文本部分进行合规检查
            compliance_issues = []
            corrected_content = content.copy()
            
            for content_type, text_content in all_text_content:
                if not text_content:
                    continue
                
                # 执行合规检查
                compliance_result = self.compliance_service.check_content_compliance(text_content)
                
                if not compliance_result.is_compliant:
                    compliance_issues.extend(compliance_result.flagged_issues)
                    
                    # 应用自动修正
                    corrected_text = self.compliance_service.sanitize_content(text_content, auto_fix=True)
                    
                    # 更新内容
                    if content_type == "title":
                        corrected_content["title"] = corrected_text
                    elif content_type == "description":
                        corrected_content["description"] = corrected_text
                    elif content_type.startswith("key_point_"):
                        point_index = int(content_type.split("_")[-1])
                        if point_index < len(corrected_content.get("key_points", [])):
                            corrected_content["key_points"][point_index] = corrected_text
                    elif content_type.startswith("section_"):
                        section_name = content_type.replace("section_", "")
                        if "sections" not in corrected_content:
                            corrected_content["sections"] = {}
                        corrected_content["sections"][section_name] = corrected_text
            
            # 记录合规检查结果
            if compliance_issues:
                logger.warning(f"Found {len(compliance_issues)} compliance issues in {context.module_type.value}")
                
                # 将合规问题信息添加到内容的元数据中
                if "sections" not in corrected_content:
                    corrected_content["sections"] = {}
                
                corrected_content["sections"]["compliance_info"] = {
                    "issues_found": len(compliance_issues),
                    "auto_fixes_applied": True,
                    "check_timestamp": datetime.now().isoformat()
                }
            else:
                logger.info(f"Content passed compliance check for {context.module_type.value}")
            
            return corrected_content
            
        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            # 如果合规检查失败，返回原始内容
            return content
    
    def check_content_compliance_manual(self, content: IntelligentModuleContent) -> Dict[str, Any]:
        """手动检查内容合规性（供用户审核使用）
        
        Args:
            content: 要检查的模块内容
            
        Returns:
            Dict[str, Any]: 合规检查结果
        """
        try:
            logger.info(f"Manual compliance check for {content.module_type.value}")
            
            # 收集所有文本内容
            all_text = []
            all_text.append(content.title)
            all_text.append(content.description)
            all_text.extend(content.key_points)
            
            for section_content in content.generated_text.values():
                if isinstance(section_content, str):
                    all_text.append(section_content)
            
            combined_text = " ".join(filter(None, all_text))
            
            # 执行合规检查
            compliance_result = self.compliance_service.check_content_compliance(combined_text)
            
            # 格式化结果供用户查看
            formatted_result = {
                "is_compliant": compliance_result.is_compliant,
                "compliance_score": compliance_result.compliance_score,
                "total_issues": len(compliance_result.flagged_issues),
                "issues_by_type": {},
                "suggested_fixes": compliance_result.suggested_fixes,
                "check_timestamp": compliance_result.check_timestamp.isoformat()
            }
            
            # 按类型分组问题
            for issue in compliance_result.flagged_issues:
                issue_type = issue.issue_type.value
                if issue_type not in formatted_result["issues_by_type"]:
                    formatted_result["issues_by_type"][issue_type] = []
                
                formatted_result["issues_by_type"][issue_type].append({
                    "flagged_text": issue.flagged_text,
                    "explanation": issue.explanation,
                    "severity": issue.severity.value,
                    "alternatives": issue.suggested_alternatives
                })
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Manual compliance check failed: {str(e)}")
            return {
                "is_compliant": False,
                "compliance_score": 0.0,
                "total_issues": 0,
                "issues_by_type": {},
                "suggested_fixes": {},
                "error": str(e)
            }
    
    def apply_compliance_fixes(self, content: IntelligentModuleContent, 
                             user_approved_fixes: Dict[str, str]) -> IntelligentModuleContent:
        """应用用户批准的合规修复
        
        Args:
            content: 原始内容
            user_approved_fixes: 用户批准的修复，格式为 {原文: 修复后文本}
            
        Returns:
            IntelligentModuleContent: 修复后的内容
        """
        try:
            logger.info(f"Applying user-approved compliance fixes for {content.module_type.value}")
            
            # 创建内容副本
            fixed_content = IntelligentModuleContent(
                module_type=content.module_type,
                title=content.title,
                description=content.description,
                key_points=content.key_points.copy(),
                generated_text=content.generated_text.copy(),
                material_requests=content.material_requests.copy(),
                language=content.language,
                generation_timestamp=datetime.now()
            )
            
            # 应用修复
            for original_text, fixed_text in user_approved_fixes.items():
                # 替换标题中的文本
                if original_text in fixed_content.title:
                    fixed_content.title = fixed_content.title.replace(original_text, fixed_text)
                
                # 替换描述中的文本
                if original_text in fixed_content.description:
                    fixed_content.description = fixed_content.description.replace(original_text, fixed_text)
                
                # 替换关键点中的文本
                for i, point in enumerate(fixed_content.key_points):
                    if original_text in point:
                        fixed_content.key_points[i] = point.replace(original_text, fixed_text)
                
                # 替换其他文本部分
                for section_name, section_content in fixed_content.generated_text.items():
                    if isinstance(section_content, str) and original_text in section_content:
                        fixed_content.generated_text[section_name] = section_content.replace(original_text, fixed_text)
            
            logger.info(f"Applied {len(user_approved_fixes)} compliance fixes for {content.module_type.value}")
            return fixed_content
            
        except Exception as e:
            logger.error(f"Failed to apply compliance fixes: {str(e)}")
            return content
    
    def generate_content_for_multiple_modules(self, contexts: List[GenerationContext], 
                                            enable_compliance_check: bool = True) -> Dict[ModuleType, IntelligentModuleContent]:
        """批量生成多个模块的内容
        
        Args:
            contexts: 生成上下文列表
            enable_compliance_check: 是否启用合规检查
            
        Returns:
            Dict[ModuleType, IntelligentModuleContent]: 模块类型到内容的映射
        """
        try:
            logger.info(f"Generating content for {len(contexts)} modules (compliance check: {enable_compliance_check})")
            
            results = {}
            compliance_summary = {
                "total_modules": len(contexts),
                "compliant_modules": 0,
                "issues_found": 0,
                "auto_fixes_applied": 0
            }
            
            for context in contexts:
                try:
                    content = self.generate_module_content(context)
                    
                    # 如果启用合规检查，进行额外的合规验证
                    if enable_compliance_check:
                        compliance_result = self.check_content_compliance_manual(content)
                        
                        if compliance_result["is_compliant"]:
                            compliance_summary["compliant_modules"] += 1
                        else:
                            compliance_summary["issues_found"] += compliance_result["total_issues"]
                    
                    results[context.module_type] = content
                    
                except Exception as e:
                    logger.error(f"Failed to generate content for {context.module_type.value}: {str(e)}")
                    # 继续处理其他模块，不中断整个批量生成
                    continue
            
            # 记录合规检查摘要
            if enable_compliance_check:
                logger.info(f"Compliance summary: {compliance_summary['compliant_modules']}/{compliance_summary['total_modules']} modules compliant, {compliance_summary['issues_found']} issues found")
            
            logger.info(f"Batch content generation completed: {len(results)}/{len(contexts)} successful")
            return results
            
        except Exception as e:
            logger.error(f"Batch content generation failed: {str(e)}")
            return {}
    
    def validate_generated_content(self, content: IntelligentModuleContent) -> Dict[str, Any]:
        """验证生成的内容质量
        
        Args:
            content: 要验证的模块内容
            
        Returns:
            Dict[str, Any]: 验证结果，包含质量分数和建议
        """
        try:
            validation_result = {
                "quality_score": 0.0,
                "issues": [],
                "suggestions": [],
                "is_valid": True
            }
            
            score = 1.0
            
            # 检查标题
            if not content.title or len(content.title) < 5:
                validation_result["issues"].append("标题过短或为空")
                score -= 0.2
            elif len(content.title) > 100:
                validation_result["issues"].append("标题过长")
                score -= 0.1
            
            # 检查描述
            if not content.description or len(content.description) < 10:
                validation_result["issues"].append("描述过短或为空")
                score -= 0.2
            
            # 检查关键点
            if len(content.key_points) < 2:
                validation_result["issues"].append("关键点数量不足")
                score -= 0.2
            elif len(content.key_points) > 6:
                validation_result["suggestions"].append("关键点数量较多，建议精简")
                score -= 0.05
            
            # 检查内容长度
            total_text_length = len(content.title) + len(content.description) + sum(len(point) for point in content.key_points)
            if total_text_length < 50:
                validation_result["issues"].append("内容总长度过短")
                score -= 0.3
            
            # 检查语言一致性
            if content.language == "zh":
                # 简单检查是否包含中文字符
                chinese_chars = sum(1 for char in content.title + content.description if '\u4e00' <= char <= '\u9fff')
                if chinese_chars < 5:
                    validation_result["issues"].append("中文内容不足")
                    score -= 0.1
            
            # 设置最终分数和状态
            validation_result["quality_score"] = max(score, 0.0)
            validation_result["is_valid"] = score >= 0.6
            
            if not validation_result["is_valid"]:
                validation_result["suggestions"].append("建议重新生成内容以提高质量")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Content validation failed: {str(e)}")
            return {
                "quality_score": 0.0,
                "issues": [f"验证过程出错: {str(e)}"],
                "suggestions": ["建议重新生成内容"],
                "is_valid": False
            }