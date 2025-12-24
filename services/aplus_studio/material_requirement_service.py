"""
A+ 智能工作流素材需求识别系统

该模块实现素材需求识别功能，包括：
- 识别AI无法生成的内容项
- 生成具体的素材需求提示
- 实现素材与内容的关联更新
- 管理素材优先级和类型
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import ModuleType, Priority, ProductCategory
from .intelligent_workflow import (
    ProductAnalysis, IntelligentMaterialRequest, IntelligentModuleContent
)

logger = logging.getLogger(__name__)


class MaterialType(Enum):
    """素材类型枚举"""
    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    DATA = "data"
    SPECIFICATION = "specification"
    CUSTOM_PROMPT = "custom_prompt"
    VIDEO = "video"
    AUDIO = "audio"


class MaterialComplexity(Enum):
    """素材复杂度"""
    SIMPLE = "simple"      # 简单素材，AI可以生成
    MODERATE = "moderate"  # 中等复杂度，需要用户输入
    COMPLEX = "complex"    # 复杂素材，必须用户提供
    IMPOSSIBLE = "impossible"  # AI无法生成，必须用户提供


@dataclass
class MaterialRequirementRule:
    """素材需求规则"""
    module_type: ModuleType
    material_type: MaterialType
    priority: Priority
    complexity: MaterialComplexity
    description: str
    examples: List[str]
    help_text: str
    conditions: List[str] = field(default_factory=list)  # 触发条件
    file_formats: List[str] = field(default_factory=list)
    max_file_size: Optional[int] = None  # bytes
    min_quality_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """判断规则是否适用于当前上下文"""
        if not self.conditions:
            return True
        
        for condition in self.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估单个条件"""
        try:
            # 简单的条件评估逻辑
            if "category=" in condition:
                required_category = condition.split("category=")[1].strip()
                return context.get("product_category") == required_category
            
            if "has_technical_features" in condition:
                return context.get("has_technical_features", False)
            
            if "complexity=" in condition:
                required_complexity = condition.split("complexity=")[1].strip()
                return context.get("product_complexity") == required_complexity
            
            return True
            
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {str(e)}")
            return True


@dataclass
class MaterialGap:
    """素材缺口"""
    gap_id: str
    module_type: ModuleType
    content_section: str
    missing_material_type: MaterialType
    impact_level: str  # HIGH, MEDIUM, LOW
    description: str
    suggested_solution: str
    ai_generation_possible: bool
    user_action_required: bool


@dataclass
class MaterialAnalysisResult:
    """素材分析结果"""
    total_requirements: int
    ai_generatable: int
    user_required: int
    optional_materials: int
    critical_gaps: List[MaterialGap]
    recommendations: List[str]
    estimated_completion_time: int  # minutes


class MaterialRequirementService:
    """素材需求识别服务"""
    
    def __init__(self):
        self.requirement_rules = self._initialize_requirement_rules()
        self.ai_generation_capabilities = self._initialize_ai_capabilities()
        self.material_templates = self._initialize_material_templates()
        logger.info("Material Requirement Service initialized")
    
    def _initialize_requirement_rules(self) -> List[MaterialRequirementRule]:
        """初始化素材需求规则"""
        rules = []
        
        # 产品概览模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.PRODUCT_OVERVIEW,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="产品主图和多角度展示图",
                examples=["正面图", "侧面图", "细节特写", "包装图"],
                help_text="提供产品的多角度高清图片，有助于生成更准确的概览内容。建议至少3张不同角度的图片。",
                file_formats=["JPG", "PNG", "WEBP"],
                max_file_size=10 * 1024 * 1024,  # 10MB
                min_quality_requirements={"min_resolution": "800x600", "min_dpi": 72}
            ),
            MaterialRequirementRule(
                module_type=ModuleType.PRODUCT_OVERVIEW,
                material_type=MaterialType.TEXT,
                priority=Priority.OPTIONAL,
                complexity=MaterialComplexity.SIMPLE,
                description="产品核心卖点描述",
                examples=["独特功能", "主要优势", "使用价值"],
                help_text="如果有特殊的产品卖点需要强调，可以提供文字描述。"
            )
        ])
        
        # 问题解决模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.PROBLEM_SOLUTION,
                material_type=MaterialType.TEXT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.COMPLEX,
                description="用户痛点和问题描述",
                examples=["传统方案的不足", "用户遇到的困难", "市场现状问题"],
                help_text="详细描述目标用户在使用类似产品时遇到的具体问题，这是生成有效解决方案内容的关键。",
                conditions=["module_selected=problem_solution"]
            ),
            MaterialRequirementRule(
                module_type=ModuleType.PROBLEM_SOLUTION,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="问题场景对比图",
                examples=["使用前后对比", "问题现象图片", "解决效果展示"],
                help_text="提供展示问题和解决效果的对比图片，增强说服力。",
                file_formats=["JPG", "PNG"]
            )
        ])
        
        # 功能解析模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.FEATURE_ANALYSIS,
                material_type=MaterialType.SPECIFICATION,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="详细技术规格和功能参数",
                examples=["功能列表", "技术参数表", "性能指标", "操作说明"],
                help_text="提供产品的详细技术规格和功能参数，这些信息AI无法准确生成，必须由用户提供。",
                conditions=["has_technical_features=true"]
            ),
            MaterialRequirementRule(
                module_type=ModuleType.FEATURE_ANALYSIS,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="功能展示和操作界面图",
                examples=["功能界面截图", "操作演示图", "内部结构图", "工作原理图"],
                help_text="提供展示产品功能的图片，帮助用户更直观地理解功能特点。",
                file_formats=["JPG", "PNG", "GIF"]
            )
        ])
        
        # 规格对比模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.SPECIFICATION_COMPARISON,
                material_type=MaterialType.DATA,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="竞品对比数据和参数表",
                examples=["性能参数对比", "功能差异表", "价格对比", "规格对比表"],
                help_text="提供与竞品的详细对比数据，这些市场信息AI无法获取，必须由用户提供。",
                conditions=["module_selected=specification_comparison"]
            ),
            MaterialRequirementRule(
                module_type=ModuleType.SPECIFICATION_COMPARISON,
                material_type=MaterialType.SPECIFICATION,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="完整产品规格表",
                examples=["技术参数", "尺寸重量", "兼容性信息", "认证标准"],
                help_text="提供完整的产品规格信息，确保对比内容的准确性。"
            )
        ])
        
        # 使用场景模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.USAGE_SCENARIOS,
                material_type=MaterialType.TEXT,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="具体使用场景和应用案例",
                examples=["办公场景应用", "家庭使用情况", "户外使用案例", "专业应用场景"],
                help_text="描述产品在不同场景下的具体应用方式，帮助生成更真实的场景展示。"
            ),
            MaterialRequirementRule(
                module_type=ModuleType.USAGE_SCENARIOS,
                material_type=MaterialType.IMAGE,
                priority=Priority.OPTIONAL,
                complexity=MaterialComplexity.MODERATE,
                description="实际使用环境照片",
                examples=["工作环境照片", "家庭使用场景", "户外应用图片"],
                help_text="提供产品在实际环境中使用的照片，增强场景真实感。",
                file_formats=["JPG", "PNG"]
            )
        ])
        
        # 安装指南模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.INSTALLATION_GUIDE,
                material_type=MaterialType.DOCUMENT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="官方安装说明文档",
                examples=["安装步骤说明", "工具清单", "注意事项", "故障排除"],
                help_text="提供官方的安装说明文档，确保安装指南的准确性和安全性。这些信息AI无法生成。",
                file_formats=["PDF", "DOC", "DOCX", "TXT"],
                conditions=["requires_installation=true"]
            ),
            MaterialRequirementRule(
                module_type=ModuleType.INSTALLATION_GUIDE,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="安装过程图片和示意图",
                examples=["安装步骤图", "工具使用图", "连接示意图", "完成效果图"],
                help_text="提供安装过程的图片说明，提高安装指南的可理解性。",
                file_formats=["JPG", "PNG", "GIF"]
            )
        ])
        
        # 尺寸兼容模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.SIZE_COMPATIBILITY,
                material_type=MaterialType.SPECIFICATION,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="精确尺寸数据和兼容性信息",
                examples=["产品尺寸图", "安装尺寸要求", "兼容设备列表", "空间要求"],
                help_text="提供精确的尺寸数据和兼容性信息，这些技术数据AI无法准确生成。"
            )
        ])
        
        # 维护保养模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.MAINTENANCE_CARE,
                material_type=MaterialType.DOCUMENT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="官方维护保养说明",
                examples=["保养周期", "清洁方法", "维护步骤", "注意事项"],
                help_text="提供官方的维护保养说明，确保用户正确维护产品。",
                file_formats=["PDF", "DOC", "TXT"]
            )
        ])
        
        # 材质工艺模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.MATERIAL_CRAFTSMANSHIP,
                material_type=MaterialType.TEXT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.COMPLEX,
                description="材质详细信息和工艺说明",
                examples=["材料成分", "制造工艺", "质量标准", "认证信息"],
                help_text="提供详细的材质信息和制造工艺说明，这些专业信息需要准确描述。"
            ),
            MaterialRequirementRule(
                module_type=ModuleType.MATERIAL_CRAFTSMANSHIP,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="材质细节和工艺展示图",
                examples=["材质纹理图", "工艺细节图", "制造过程图", "质量检测图"],
                help_text="提供展示材质和工艺细节的高清图片。",
                file_formats=["JPG", "PNG"],
                min_quality_requirements={"min_resolution": "1200x800"}
            )
        ])
        
        # 品质保证模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.QUALITY_ASSURANCE,
                material_type=MaterialType.DOCUMENT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="质量认证和保证文档",
                examples=["认证证书", "质量标准", "测试报告", "保修政策"],
                help_text="提供官方的质量认证文档和保证信息，这些权威信息必须由用户提供。",
                file_formats=["PDF", "JPG", "PNG"]
            )
        ])
        
        # 用户评价模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.CUSTOMER_REVIEWS,
                material_type=MaterialType.TEXT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="真实用户评价和反馈",
                examples=["用户评论", "使用体验", "评分数据", "推荐理由"],
                help_text="提供真实的用户评价和反馈，这些信息AI无法生成，必须基于实际用户数据。"
            ),
            MaterialRequirementRule(
                module_type=ModuleType.CUSTOMER_REVIEWS,
                material_type=MaterialType.IMAGE,
                priority=Priority.OPTIONAL,
                complexity=MaterialComplexity.MODERATE,
                description="用户使用照片",
                examples=["用户晒图", "使用场景照片", "效果展示图"],
                help_text="用户提供的真实使用照片，增强评价可信度。",
                file_formats=["JPG", "PNG"]
            )
        ])
        
        # 包装内容模块规则
        rules.extend([
            MaterialRequirementRule(
                module_type=ModuleType.PACKAGE_CONTENTS,
                material_type=MaterialType.TEXT,
                priority=Priority.REQUIRED,
                complexity=MaterialComplexity.IMPOSSIBLE,
                description="完整包装清单",
                examples=["主要产品", "配件列表", "说明书", "保修卡"],
                help_text="提供完整的包装内容清单，确保信息准确无误。"
            ),
            MaterialRequirementRule(
                module_type=ModuleType.PACKAGE_CONTENTS,
                material_type=MaterialType.IMAGE,
                priority=Priority.RECOMMENDED,
                complexity=MaterialComplexity.MODERATE,
                description="开箱和内容展示图",
                examples=["开箱图", "内容物摆放图", "配件展示图"],
                help_text="提供开箱和包装内容的展示图片。",
                file_formats=["JPG", "PNG"]
            )
        ])
        
        return rules
    
    def _initialize_ai_capabilities(self) -> Dict[MaterialType, Dict[str, Any]]:
        """初始化AI生成能力配置"""
        return {
            MaterialType.TEXT: {
                "can_generate": True,
                "quality_level": "high",
                "limitations": ["无法生成特定技术参数", "无法获取实时市场数据", "无法生成真实用户评价"],
                "best_for": ["产品描述", "功能介绍", "使用建议"]
            },
            MaterialType.IMAGE: {
                "can_generate": True,
                "quality_level": "medium",
                "limitations": ["无法生成真实产品照片", "无法生成特定品牌标识", "无法生成实际使用场景"],
                "best_for": ["概念图", "示意图", "装饰性图片"]
            },
            MaterialType.SPECIFICATION: {
                "can_generate": False,
                "quality_level": "none",
                "limitations": ["无法生成准确技术参数", "无法获取官方规格数据"],
                "best_for": []
            },
            MaterialType.DATA: {
                "can_generate": False,
                "quality_level": "none",
                "limitations": ["无法获取市场数据", "无法生成竞品对比", "无法获取实时价格"],
                "best_for": []
            },
            MaterialType.DOCUMENT: {
                "can_generate": False,
                "quality_level": "none",
                "limitations": ["无法生成官方文档", "无法获取认证信息", "无法生成法律文件"],
                "best_for": []
            }
        }
    
    def _initialize_material_templates(self) -> Dict[str, str]:
        """初始化素材模板"""
        return {
            "image_request_zh": "请提供{description}。建议格式：{formats}，文件大小不超过{max_size}MB。{help_text}",
            "image_request_en": "Please provide {description}. Recommended formats: {formats}, file size under {max_size}MB. {help_text}",
            "text_request_zh": "请提供{description}。例如：{examples}。{help_text}",
            "text_request_en": "Please provide {description}. Examples: {examples}. {help_text}",
            "document_request_zh": "请上传{description}。支持格式：{formats}。{help_text}",
            "document_request_en": "Please upload {description}. Supported formats: {formats}. {help_text}",
            "data_request_zh": "请提供{description}。这些数据信息AI无法生成，需要您提供准确信息。{help_text}",
            "data_request_en": "Please provide {description}. This data cannot be generated by AI and requires accurate information from you. {help_text}"
        }
    
    def identify_material_requirements(self, module_types: List[ModuleType], 
                                     product_analysis: ProductAnalysis,
                                     language: str = "zh") -> List[IntelligentMaterialRequest]:
        """识别素材需求
        
        Args:
            module_types: 选定的模块类型列表
            product_analysis: 产品分析结果
            language: 语言
            
        Returns:
            List[IntelligentMaterialRequest]: 素材需求列表
        """
        try:
            logger.info(f"Identifying material requirements for {len(module_types)} modules")
            
            # 构建分析上下文
            context = self._build_analysis_context(product_analysis)
            
            material_requests = []
            processed_combinations = set()  # 避免重复需求
            
            for module_type in module_types:
                # 获取适用的规则
                applicable_rules = self._get_applicable_rules(module_type, context)
                
                for rule in applicable_rules:
                    # 避免重复的素材需求
                    combination_key = (module_type, rule.material_type, rule.description)
                    if combination_key in processed_combinations:
                        continue
                    
                    processed_combinations.add(combination_key)
                    
                    # 创建素材请求
                    request = self._create_material_request(rule, module_type, language)
                    material_requests.append(request)
            
            # 按优先级排序
            material_requests.sort(key=lambda x: self._get_priority_weight(x.importance))
            
            logger.info(f"Identified {len(material_requests)} material requirements")
            return material_requests
            
        except Exception as e:
            logger.error(f"Material requirement identification failed: {str(e)}")
            return []
    
    def _build_analysis_context(self, product_analysis: ProductAnalysis) -> Dict[str, Any]:
        """构建分析上下文"""
        context = {
            "product_category": product_analysis.product_category.value,
            "product_type": product_analysis.product_type,
            "has_technical_features": self._has_technical_features(product_analysis),
            "product_complexity": self._assess_product_complexity(product_analysis),
            "requires_installation": self._requires_installation(product_analysis),
            "has_multiple_materials": len(product_analysis.materials) > 2,
            "confidence_score": product_analysis.confidence_score
        }
        
        return context
    
    def _has_technical_features(self, analysis: ProductAnalysis) -> bool:
        """判断是否有技术特征"""
        technical_keywords = ["技术", "性能", "参数", "规格", "配置", "功率", "频率", "容量"]
        all_text = " ".join(analysis.key_features + analysis.marketing_angles)
        return any(keyword in all_text for keyword in technical_keywords)
    
    def _assess_product_complexity(self, analysis: ProductAnalysis) -> str:
        """评估产品复杂度"""
        complexity_score = 0
        
        # 基于特征数量
        if len(analysis.key_features) > 5:
            complexity_score += 2
        elif len(analysis.key_features) > 3:
            complexity_score += 1
        
        # 基于材料种类
        if len(analysis.materials) > 3:
            complexity_score += 1
        
        # 基于使用场景
        if len(analysis.use_cases) > 3:
            complexity_score += 1
        
        # 基于产品类别
        if analysis.product_category in [ProductCategory.TECHNOLOGY, ProductCategory.AUTOMOTIVE]:
            complexity_score += 2
        elif analysis.product_category in [ProductCategory.TOOLS, ProductCategory.HEALTH_BEAUTY]:
            complexity_score += 1
        
        if complexity_score >= 4:
            return "high"
        elif complexity_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _requires_installation(self, analysis: ProductAnalysis) -> bool:
        """判断是否需要安装"""
        installation_keywords = ["安装", "组装", "设置", "配置", "连接", "固定"]
        all_text = " ".join(analysis.key_features + analysis.use_cases + analysis.marketing_angles)
        return any(keyword in all_text for keyword in installation_keywords)
    
    def _get_applicable_rules(self, module_type: ModuleType, context: Dict[str, Any]) -> List[MaterialRequirementRule]:
        """获取适用的规则"""
        applicable_rules = []
        
        for rule in self.requirement_rules:
            if rule.module_type == module_type and rule.is_applicable(context):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _create_material_request(self, rule: MaterialRequirementRule, 
                               module_type: ModuleType, language: str) -> IntelligentMaterialRequest:
        """创建素材请求"""
        # 格式化描述
        formatted_description = self._format_material_description(rule, language)
        
        # 格式化示例
        examples_text = ", ".join(rule.examples) if rule.examples else ""
        
        # 格式化帮助文本
        help_text = rule.help_text
        if rule.file_formats:
            formats_text = ", ".join(rule.file_formats)
            if language == "zh":
                help_text += f" 支持格式：{formats_text}。"
            else:
                help_text += f" Supported formats: {formats_text}."
        
        if rule.max_file_size:
            max_size_mb = rule.max_file_size / (1024 * 1024)
            if language == "zh":
                help_text += f" 文件大小不超过{max_size_mb:.0f}MB。"
            else:
                help_text += f" File size under {max_size_mb:.0f}MB."
        
        return IntelligentMaterialRequest(
            request_id=str(uuid.uuid4()),
            material_type=rule.material_type.value,
            description=formatted_description,
            importance=rule.priority,
            example=examples_text if examples_text else None,
            help_text=help_text
        )
    
    def _format_material_description(self, rule: MaterialRequirementRule, language: str) -> str:
        """格式化素材描述"""
        description = rule.description
        
        # 根据复杂度添加标识
        if rule.complexity == MaterialComplexity.IMPOSSIBLE:
            if language == "zh":
                description = f"[必需] {description}"
            else:
                description = f"[Required] {description}"
        elif rule.complexity == MaterialComplexity.COMPLEX:
            if language == "zh":
                description = f"[重要] {description}"
            else:
                description = f"[Important] {description}"
        
        return description
    
    def _get_priority_weight(self, priority: Priority) -> int:
        """获取优先级权重（用于排序）"""
        weights = {
            Priority.REQUIRED: 1,
            Priority.RECOMMENDED: 2,
            Priority.OPTIONAL: 3
        }
        return weights.get(priority, 3)
    
    def analyze_material_gaps(self, module_content: IntelligentModuleContent,
                            provided_materials: Dict[str, Any]) -> MaterialAnalysisResult:
        """分析素材缺口
        
        Args:
            module_content: 模块内容
            provided_materials: 用户提供的素材
            
        Returns:
            MaterialAnalysisResult: 素材分析结果
        """
        try:
            logger.info(f"Analyzing material gaps for {module_content.module_type.value}")
            
            total_requirements = len(module_content.material_requests)
            ai_generatable = 0
            user_required = 0
            optional_materials = 0
            critical_gaps = []
            recommendations = []
            
            for request in module_content.material_requests:
                material_type = MaterialType(request.material_type)
                
                # 检查AI生成能力
                ai_capability = self.ai_generation_capabilities.get(material_type, {})
                can_generate = ai_capability.get("can_generate", False)
                
                if can_generate:
                    ai_generatable += 1
                else:
                    user_required += 1
                
                if request.importance == Priority.OPTIONAL:
                    optional_materials += 1
                
                # 检查是否提供了素材
                material_provided = provided_materials.get(request.material_type, False)
                
                if not material_provided and request.importance == Priority.REQUIRED:
                    # 创建关键缺口
                    gap = MaterialGap(
                        gap_id=str(uuid.uuid4()),
                        module_type=module_content.module_type,
                        content_section="main",
                        missing_material_type=material_type,
                        impact_level="HIGH" if request.importance == Priority.REQUIRED else "MEDIUM",
                        description=f"缺少{request.description}",
                        suggested_solution=self._suggest_gap_solution(request, can_generate),
                        ai_generation_possible=can_generate,
                        user_action_required=not can_generate
                    )
                    critical_gaps.append(gap)
            
            # 生成建议
            recommendations = self._generate_material_recommendations(
                module_content, provided_materials, critical_gaps
            )
            
            # 估算完成时间
            estimated_time = self._estimate_completion_time(critical_gaps, user_required)
            
            result = MaterialAnalysisResult(
                total_requirements=total_requirements,
                ai_generatable=ai_generatable,
                user_required=user_required,
                optional_materials=optional_materials,
                critical_gaps=critical_gaps,
                recommendations=recommendations,
                estimated_completion_time=estimated_time
            )
            
            logger.info(f"Material gap analysis completed: {len(critical_gaps)} critical gaps found")
            return result
            
        except Exception as e:
            logger.error(f"Material gap analysis failed: {str(e)}")
            return MaterialAnalysisResult(
                total_requirements=0,
                ai_generatable=0,
                user_required=0,
                optional_materials=0,
                critical_gaps=[],
                recommendations=["分析过程出错，请重试"],
                estimated_completion_time=0
            )
    
    def _suggest_gap_solution(self, request: IntelligentMaterialRequest, ai_can_generate: bool) -> str:
        """建议缺口解决方案"""
        if ai_can_generate:
            return f"可以使用AI生成{request.description}，但用户提供的素材质量更好"
        else:
            return f"需要用户提供{request.description}，AI无法生成此类素材"
    
    def _generate_material_recommendations(self, module_content: IntelligentModuleContent,
                                         provided_materials: Dict[str, Any],
                                         critical_gaps: List[MaterialGap]) -> List[str]:
        """生成素材建议"""
        recommendations = []
        
        if len(critical_gaps) > 0:
            recommendations.append(f"发现{len(critical_gaps)}个关键素材缺口，建议优先补充")
        
        # 检查图片素材
        has_image_request = any(req.material_type == MaterialType.IMAGE.value 
                              for req in module_content.material_requests)
        has_image_provided = MaterialType.IMAGE.value in provided_materials
        
        if has_image_request and not has_image_provided:
            recommendations.append("建议提供产品图片以提升内容质量")
        
        # 检查技术规格
        has_spec_request = any(req.material_type == MaterialType.SPECIFICATION.value 
                             for req in module_content.material_requests)
        has_spec_provided = MaterialType.SPECIFICATION.value in provided_materials
        
        if has_spec_request and not has_spec_provided:
            recommendations.append("技术规格信息对于准确的内容生成至关重要")
        
        # 检查文档素材
        has_doc_request = any(req.material_type == MaterialType.DOCUMENT.value 
                            for req in module_content.material_requests)
        has_doc_provided = MaterialType.DOCUMENT.value in provided_materials
        
        if has_doc_request and not has_doc_provided:
            recommendations.append("官方文档能确保信息的权威性和准确性")
        
        if not recommendations:
            recommendations.append("素材提供充分，可以开始生成高质量内容")
        
        return recommendations
    
    def _estimate_completion_time(self, critical_gaps: List[MaterialGap], user_required: int) -> int:
        """估算完成时间（分钟）"""
        base_time = 5  # 基础时间
        
        # 每个关键缺口增加时间
        gap_time = len(critical_gaps) * 10
        
        # 用户需要提供的素材增加时间
        user_time = user_required * 5
        
        return base_time + gap_time + user_time
    
    def generate_material_collection_guide(self, material_requests: List[IntelligentMaterialRequest],
                                         language: str = "zh") -> Dict[str, Any]:
        """生成素材收集指南
        
        Args:
            material_requests: 素材需求列表
            language: 语言
            
        Returns:
            Dict[str, Any]: 素材收集指南
        """
        try:
            logger.info(f"Generating material collection guide for {len(material_requests)} requests")
            
            guide = {
                "overview": self._generate_guide_overview(material_requests, language),
                "categories": self._organize_requests_by_category(material_requests, language),
                "priority_order": self._generate_priority_order(material_requests, language),
                "tips": self._generate_collection_tips(material_requests, language),
                "estimated_time": self._estimate_collection_time(material_requests)
            }
            
            return guide
            
        except Exception as e:
            logger.error(f"Material collection guide generation failed: {str(e)}")
            return {"error": str(e)}
    
    def _generate_guide_overview(self, requests: List[IntelligentMaterialRequest], language: str) -> str:
        """生成指南概述"""
        total = len(requests)
        required = len([r for r in requests if r.importance == Priority.REQUIRED])
        recommended = len([r for r in requests if r.importance == Priority.RECOMMENDED])
        optional = len([r for r in requests if r.importance == Priority.OPTIONAL])
        
        if language == "zh":
            return f"共需要收集{total}项素材，其中必需{required}项，推荐{recommended}项，可选{optional}项。建议按优先级顺序收集，以确保内容生成质量。"
        else:
            return f"Total {total} materials needed: {required} required, {recommended} recommended, {optional} optional. Collect by priority order for best content quality."
    
    def _organize_requests_by_category(self, requests: List[IntelligentMaterialRequest], 
                                     language: str) -> Dict[str, List[Dict[str, Any]]]:
        """按类别组织需求"""
        categories = {}
        
        for request in requests:
            material_type = request.material_type
            
            if material_type not in categories:
                categories[material_type] = []
            
            categories[material_type].append({
                "description": request.description,
                "priority": request.importance.value,
                "example": request.example,
                "help_text": request.help_text
            })
        
        return categories
    
    def _generate_priority_order(self, requests: List[IntelligentMaterialRequest], 
                               language: str) -> List[Dict[str, Any]]:
        """生成优先级顺序"""
        # 按优先级排序
        sorted_requests = sorted(requests, key=lambda x: self._get_priority_weight(x.importance))
        
        priority_order = []
        for i, request in enumerate(sorted_requests, 1):
            priority_order.append({
                "order": i,
                "description": request.description,
                "priority": request.importance.value,
                "reason": self._get_priority_reason(request, language)
            })
        
        return priority_order
    
    def _get_priority_reason(self, request: IntelligentMaterialRequest, language: str) -> str:
        """获取优先级原因"""
        if request.importance == Priority.REQUIRED:
            return "必需素材，影响内容准确性" if language == "zh" else "Required material, affects content accuracy"
        elif request.importance == Priority.RECOMMENDED:
            return "推荐素材，提升内容质量" if language == "zh" else "Recommended material, improves content quality"
        else:
            return "可选素材，增强内容丰富度" if language == "zh" else "Optional material, enhances content richness"
    
    def _generate_collection_tips(self, requests: List[IntelligentMaterialRequest], 
                                language: str) -> List[str]:
        """生成收集提示"""
        tips = []
        
        # 检查是否有图片需求
        has_images = any(req.material_type == MaterialType.IMAGE.value for req in requests)
        if has_images:
            if language == "zh":
                tips.append("图片素材建议使用高分辨率（至少800x600），清晰展示产品特征")
            else:
                tips.append("Use high resolution images (at least 800x600) that clearly show product features")
        
        # 检查是否有文档需求
        has_docs = any(req.material_type == MaterialType.DOCUMENT.value for req in requests)
        if has_docs:
            if language == "zh":
                tips.append("文档素材请使用官方版本，确保信息准确性和权威性")
            else:
                tips.append("Use official documents to ensure information accuracy and authority")
        
        # 检查是否有规格需求
        has_specs = any(req.material_type == MaterialType.SPECIFICATION.value for req in requests)
        if has_specs:
            if language == "zh":
                tips.append("技术规格请提供完整详细的参数表，包含所有关键指标")
            else:
                tips.append("Provide complete detailed specification tables with all key metrics")
        
        # 通用提示
        if language == "zh":
            tips.extend([
                "优先收集必需素材，确保基础内容质量",
                "素材文件命名清晰，便于识别和使用",
                "如有疑问，可参考示例和帮助说明"
            ])
        else:
            tips.extend([
                "Prioritize required materials to ensure basic content quality",
                "Use clear file names for easy identification and use",
                "Refer to examples and help text if you have questions"
            ])
        
        return tips
    
    def _estimate_collection_time(self, requests: List[IntelligentMaterialRequest]) -> int:
        """估算收集时间（分钟）"""
        base_time = 10  # 基础时间
        
        # 每个需求增加时间
        per_request_time = len(requests) * 3
        
        # 复杂素材增加时间
        complex_requests = [r for r in requests if r.material_type in [
            MaterialType.SPECIFICATION.value, MaterialType.DOCUMENT.value, MaterialType.DATA.value
        ]]
        complex_time = len(complex_requests) * 5
        
        return base_time + per_request_time + complex_time