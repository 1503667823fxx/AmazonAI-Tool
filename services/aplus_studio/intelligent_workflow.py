"""
A+ 智能工作流控制器

该模块实现智能工作流系统的核心控制逻辑，管理从产品分析到最终生成的完整流程。
工作流程：产品分析 → 智能模块推荐 → 自动内容填充 → 统一风格生成
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .models import (
    ModuleType, GenerationStatus, ValidationStatus, 
    ProductInfo, AnalysisResult, GenerationResult,
    WorkflowState, ProductCategory, StyleTheme, Priority
)
from .error_handler import (
    ErrorHandler, error_handler, get_global_error_handler, ErrorContext
)

logger = logging.getLogger(__name__)


@dataclass
class ProductAnalysis:
    """产品分析结果"""
    product_id: str
    product_category: ProductCategory
    product_type: str
    key_features: List[str]
    materials: List[str]
    target_audience: str
    use_cases: List[str]
    marketing_angles: List[str]
    confidence_score: float
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'product_id': self.product_id,
            'product_category': self.product_category.value,
            'product_type': self.product_type,
            'key_features': self.key_features,
            'materials': self.materials,
            'target_audience': self.target_audience,
            'use_cases': self.use_cases,
            'marketing_angles': self.marketing_angles,
            'confidence_score': self.confidence_score,
            'analysis_timestamp': self.analysis_timestamp.isoformat()
        }


@dataclass
class ModuleRecommendation:
    """模块推荐结果"""
    recommended_modules: List[ModuleType]
    recommendation_reasons: Dict[ModuleType, str]
    confidence_scores: Dict[ModuleType, float]
    alternative_modules: List[ModuleType]
    recommendation_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'recommended_modules': [m.value for m in self.recommended_modules],
            'recommendation_reasons': {k.value: v for k, v in self.recommendation_reasons.items()},
            'confidence_scores': {k.value: v for k, v in self.confidence_scores.items()},
            'alternative_modules': [m.value for m in self.alternative_modules],
            'recommendation_timestamp': self.recommendation_timestamp.isoformat()
        }


@dataclass
class MaterialRequest:
    """素材需求"""
    request_id: str
    material_type: str  # IMAGE, DOCUMENT, TEXT, DATA
    description: str
    importance: Priority
    example: Optional[str] = None
    help_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'request_id': self.request_id,
            'material_type': self.material_type,
            'description': self.description,
            'importance': self.importance.value,
            'example': self.example,
            'help_text': self.help_text
        }


@dataclass
class ModuleContent:
    """模块内容"""
    module_type: ModuleType
    title: str
    description: str
    key_points: List[str]
    generated_text: Dict[str, str]
    material_requests: List[MaterialRequest]
    language: str
    generation_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'module_type': self.module_type.value,
            'title': self.title,
            'description': self.description,
            'key_points': self.key_points,
            'generated_text': self.generated_text,
            'material_requests': [req.to_dict() for req in self.material_requests],
            'language': self.language,
            'generation_timestamp': self.generation_timestamp.isoformat()
        }


@dataclass
class StyleThemeConfig:
    """风格主题配置"""
    theme_id: str
    theme_name: str
    color_palette: List[str]
    font_family: str
    design_style: str
    layout_preferences: Dict[str, Any]
    suitable_categories: List[ProductCategory]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'theme_id': self.theme_id,
            'theme_name': self.theme_name,
            'color_palette': self.color_palette,
            'font_family': self.font_family,
            'design_style': self.design_style,
            'layout_preferences': self.layout_preferences,
            'suitable_categories': [cat.value for cat in self.suitable_categories]
        }


@dataclass
class IntelligentMaterialRequest:
    """智能素材需求"""
    request_id: str
    material_type: str  # IMAGE, DOCUMENT, TEXT, DATA, SPECIFICATION, CUSTOM_PROMPT
    description: str
    importance: Priority
    example: Optional[str] = None
    help_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'request_id': self.request_id,
            'material_type': self.material_type,
            'description': self.description,
            'importance': self.importance.value,
            'example': self.example,
            'help_text': self.help_text
        }


@dataclass
class IntelligentModuleContent:
    """智能模块内容"""
    module_type: ModuleType
    title: str
    description: str
    key_points: List[str]
    generated_text: Dict[str, str]
    material_requests: List[IntelligentMaterialRequest]
    language: str
    generation_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'module_type': self.module_type.value,
            'title': self.title,
            'description': self.description,
            'key_points': self.key_points,
            'generated_text': self.generated_text,
            'material_requests': [req.to_dict() for req in self.material_requests],
            'language': self.language,
            'generation_timestamp': self.generation_timestamp.isoformat()
        }


@dataclass
class IntelligentWorkflowSession:
    """智能工作流会话"""
    session_id: str
    current_state: WorkflowState
    product_analysis: Optional[ProductAnalysis] = None
    module_recommendation: Optional[ModuleRecommendation] = None
    selected_modules: List[ModuleType] = field(default_factory=list)
    module_contents: Dict[ModuleType, ModuleContent] = field(default_factory=dict)
    selected_style_theme: Optional[StyleThemeConfig] = None
    compliance_results: Dict[ModuleType, ComplianceResult] = field(default_factory=dict)
    generation_results: Dict[ModuleType, GenerationResult] = field(default_factory=dict)
    generation_status: Dict[ModuleType, GenerationStatus] = field(default_factory=dict)
    user_edits: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保所有选定模块都有状态
        for module_type in self.selected_modules:
            if module_type not in self.generation_status:
                self.generation_status[module_type] = GenerationStatus.NOT_STARTED
    
    def update_state(self, new_state: WorkflowState):
        """更新工作流状态"""
        self.current_state = new_state
        self.last_updated = datetime.now()
        logger.info(f"Workflow state updated to: {new_state.value}")
    
    def add_selected_module(self, module_type: ModuleType):
        """添加选定模块"""
        if module_type not in self.selected_modules:
            self.selected_modules.append(module_type)
            self.generation_status[module_type] = GenerationStatus.NOT_STARTED
            self.last_updated = datetime.now()
    
    def remove_selected_module(self, module_type: ModuleType):
        """移除选定模块"""
        if module_type in self.selected_modules:
            self.selected_modules.remove(module_type)
            # 清理相关数据
            self.generation_status.pop(module_type, None)
            self.module_contents.pop(module_type, None)
            self.compliance_results.pop(module_type, None)
            self.generation_results.pop(module_type, None)
            self.last_updated = datetime.now()
    
    def get_progress_percentage(self) -> float:
        """获取整体进度百分比"""
        if not self.selected_modules:
            return 0.0
        
        completed_count = sum(
            1 for module in self.selected_modules
            if self.generation_status.get(module) == GenerationStatus.COMPLETED
        )
        
        return (completed_count / len(self.selected_modules)) * 100
    
    def get_completed_modules(self) -> List[ModuleType]:
        """获取已完成的模块"""
        return [
            module for module in self.selected_modules
            if self.generation_status.get(module) == GenerationStatus.COMPLETED
        ]
    
    def get_failed_modules(self) -> List[ModuleType]:
        """获取失败的模块"""
        return [
            module for module in self.selected_modules
            if self.generation_status.get(module) == GenerationStatus.FAILED
        ]
    
    def is_ready_for_generation(self) -> bool:
        """检查是否准备好进行图片生成"""
        return (
            self.current_state == WorkflowState.FINAL_CONFIRMATION and
            len(self.selected_modules) > 0 and
            self.selected_style_theme is not None and
            all(module in self.module_contents for module in self.selected_modules)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'session_id': self.session_id,
            'current_state': self.current_state.value,
            'product_analysis': self.product_analysis.to_dict() if self.product_analysis else None,
            'module_recommendation': self.module_recommendation.to_dict() if self.module_recommendation else None,
            'selected_modules': [m.value for m in self.selected_modules],
            'module_contents': {k.value: v.to_dict() for k, v in self.module_contents.items()},
            'selected_style_theme': self.selected_style_theme.to_dict() if self.selected_style_theme else None,
            'compliance_results': {k.value: v.to_dict() for k, v in self.compliance_results.items()},
            'generation_status': {k.value: v.value for k, v in self.generation_status.items()},
            'user_edits': self.user_edits,
            'workflow_metadata': self.workflow_metadata,
            'creation_time': self.creation_time.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'progress_percentage': self.get_progress_percentage()
        }


class IntelligentWorkflowController:
    """智能工作流控制器"""
    
    def __init__(self):
        self.current_session: Optional[IntelligentWorkflowSession] = None
        self.session_history: List[IntelligentWorkflowSession] = []
        
        # 添加state_manager属性以兼容UI组件
        self.state_manager = None  # 将在外部设置
        
        # 预定义的风格主题
        self.style_themes = self._initialize_style_themes()
        
        # 模块推荐规则
        self.recommendation_rules = self._initialize_recommendation_rules()
        
        # 初始化错误处理
        self._error_handler = get_global_error_handler()
        self._performance_monitor = get_global_performance_monitor()
        self._error_handler = get_global_error_handler()
        
        # 注册回退处理器
        self._register_fallback_handlers()
        
        logger.info("Intelligent Workflow Controller initialized")
    
    def _initialize_style_themes(self) -> Dict[StyleTheme, StyleThemeConfig]:
        """初始化风格主题配置"""
        themes = {}
        
        # 现代科技风
        themes[StyleTheme.MODERN_TECH] = StyleThemeConfig(
            theme_id="modern_tech",
            theme_name="现代科技风",
            color_palette=["#2563EB", "#1E40AF", "#3B82F6", "#60A5FA", "#93C5FD"],
            font_family="Inter, sans-serif",
            design_style="现代简约、科技感强",
            layout_preferences={
                "emphasis": "technical_specifications",
                "layout_style": "grid_based",
                "visual_hierarchy": "data_driven"
            },
            suitable_categories=[ProductCategory.TECHNOLOGY, ProductCategory.AUTOMOTIVE, ProductCategory.TOOLS]
        )
        
        # 温馨家居风
        themes[StyleTheme.WARM_HOME] = StyleThemeConfig(
            theme_id="warm_home",
            theme_name="温馨家居风",
            color_palette=["#DC2626", "#EF4444", "#F87171", "#FCA5A5", "#FECACA"],
            font_family="Georgia, serif",
            design_style="温馨、生活化",
            layout_preferences={
                "emphasis": "comfort_lifestyle",
                "layout_style": "organic_flow",
                "visual_hierarchy": "emotion_driven"
            },
            suitable_categories=[ProductCategory.HOME_LIVING, ProductCategory.HEALTH_BEAUTY]
        )
        
        # 奢华高端风
        themes[StyleTheme.LUXURY_PREMIUM] = StyleThemeConfig(
            theme_id="luxury_premium",
            theme_name="奢华高端风",
            color_palette=["#111827", "#374151", "#6B7280", "#D1D5DB", "#F9FAFB"],
            font_family="Playfair Display, serif",
            design_style="精致、奢华",
            layout_preferences={
                "emphasis": "premium_quality",
                "layout_style": "elegant_minimal",
                "visual_hierarchy": "luxury_focused"
            },
            suitable_categories=[ProductCategory.FASHION, ProductCategory.HEALTH_BEAUTY]
        )
        
        # 简洁功能风
        themes[StyleTheme.CLEAN_FUNCTIONAL] = StyleThemeConfig(
            theme_id="clean_functional",
            theme_name="简洁功能风",
            color_palette=["#059669", "#10B981", "#34D399", "#6EE7B7", "#A7F3D0"],
            font_family="Roboto, sans-serif",
            design_style="清晰、功能性强",
            layout_preferences={
                "emphasis": "practical_function",
                "layout_style": "structured_clean",
                "visual_hierarchy": "function_first"
            },
            suitable_categories=[ProductCategory.TOOLS, ProductCategory.SPORTS, ProductCategory.AUTOMOTIVE]
        )
        
        # 专业商务风
        themes[StyleTheme.PROFESSIONAL] = StyleThemeConfig(
            theme_id="professional",
            theme_name="专业商务风",
            color_palette=["#1F2937", "#374151", "#4B5563", "#9CA3AF", "#E5E7EB"],
            font_family="Source Sans Pro, sans-serif",
            design_style="专业、商务",
            layout_preferences={
                "emphasis": "professional_credibility",
                "layout_style": "corporate_structured",
                "visual_hierarchy": "authority_based"
            },
            suitable_categories=[ProductCategory.TECHNOLOGY, ProductCategory.TOOLS, ProductCategory.OTHER]
        )
        
        return themes
    
    def _initialize_recommendation_rules(self) -> Dict[ProductCategory, List[ModuleType]]:
        """初始化模块推荐规则"""
        rules = {
            ProductCategory.TECHNOLOGY: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.FEATURE_ANALYSIS,
                ModuleType.SPECIFICATION_COMPARISON,
                ModuleType.INSTALLATION_GUIDE
            ],
            ProductCategory.HOME_LIVING: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.USAGE_SCENARIOS,
                ModuleType.PROBLEM_SOLUTION,
                ModuleType.SIZE_COMPATIBILITY
            ],
            ProductCategory.FASHION: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.MATERIAL_CRAFTSMANSHIP,
                ModuleType.SIZE_COMPATIBILITY,
                ModuleType.CUSTOMER_REVIEWS
            ],
            ProductCategory.SPORTS: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.USAGE_SCENARIOS,
                ModuleType.QUALITY_ASSURANCE,
                ModuleType.MAINTENANCE_CARE
            ],
            ProductCategory.HEALTH_BEAUTY: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.PROBLEM_SOLUTION,
                ModuleType.QUALITY_ASSURANCE,
                ModuleType.CUSTOMER_REVIEWS
            ],
            ProductCategory.AUTOMOTIVE: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.INSTALLATION_GUIDE,
                ModuleType.SIZE_COMPATIBILITY,
                ModuleType.SPECIFICATION_COMPARISON
            ],
            ProductCategory.TOOLS: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.FEATURE_ANALYSIS,
                ModuleType.USAGE_SCENARIOS,
                ModuleType.MAINTENANCE_CARE
            ],
            ProductCategory.OTHER: [
                ModuleType.PRODUCT_OVERVIEW,
                ModuleType.PROBLEM_SOLUTION,
                ModuleType.USAGE_SCENARIOS,
                ModuleType.PACKAGE_CONTENTS
            ]
        }
        return rules
    
    def _register_fallback_handlers(self):
        """注册回退处理器"""
        # 产品分析回退处理器
        def product_analysis_fallback(*args, **kwargs):
            logger.info("Using fallback for product analysis")
            return ProductAnalysis(
                product_id=f"fallback_{int(datetime.now().timestamp())}",
                product_category=ProductCategory.OTHER,
                product_type="通用产品",
                key_features=["实用功能", "优质设计", "便捷操作"],
                materials=["优质材料"],
                target_audience="普通用户",
                use_cases=["日常使用"],
                marketing_angles=["实用便捷", "品质可靠"],
                confidence_score=0.5
            )
        
        # 模块推荐回退处理器
        def module_recommendation_fallback(*args, **kwargs):
            logger.info("Using fallback for module recommendation")
            return ModuleRecommendation(
                recommended_modules=[
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.PROBLEM_SOLUTION,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.QUALITY_ASSURANCE
                ],
                recommendation_reasons={
                    ModuleType.PRODUCT_OVERVIEW: "展示产品整体特性",
                    ModuleType.PROBLEM_SOLUTION: "说明产品解决的问题",
                    ModuleType.USAGE_SCENARIOS: "展示使用场景",
                    ModuleType.QUALITY_ASSURANCE: "展示品质保证"
                },
                confidence_scores={
                    ModuleType.PRODUCT_OVERVIEW: 0.8,
                    ModuleType.PROBLEM_SOLUTION: 0.7,
                    ModuleType.USAGE_SCENARIOS: 0.7,
                    ModuleType.QUALITY_ASSURANCE: 0.6
                },
                alternative_modules=[ModuleType.FEATURE_ANALYSIS, ModuleType.CUSTOMER_REVIEWS]
            )
        
        # 风格主题选择回退处理器
        def style_theme_fallback(*args, **kwargs):
            logger.info("Using fallback for style theme selection")
            return self.style_themes[StyleTheme.PROFESSIONAL]
        
        # 注册回退处理器
        self._error_handler.register_fallback_handler("product_analysis", product_analysis_fallback)
        self._error_handler.register_fallback_handler("module_recommendation", module_recommendation_fallback)
        self._error_handler.register_fallback_handler("style_theme_selection", style_theme_fallback)
    
    @error_handler("create_new_session", max_retries=2, enable_recovery=True)
    
    def create_new_session(self, session_id: Optional[str] = None) -> IntelligentWorkflowSession:
        """创建新的智能工作流会话"""
        if session_id is None:
            session_id = f"iw_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000:04d}"
        
        session = IntelligentWorkflowSession(
            session_id=session_id,
            current_state=WorkflowState.INITIAL
        )
        
        self.current_session = session
        logger.info(f"Created new intelligent workflow session: {session_id}")
        
        return session
    
    def get_current_session(self) -> Optional[IntelligentWorkflowSession]:
        """获取当前会话"""
        return self.current_session
    
    def load_session(self, session: IntelligentWorkflowSession):
        """加载会话"""
        self.current_session = session
        logger.info(f"Loaded intelligent workflow session: {session.session_id}")
    
    @error_handler("transition_to_state", max_retries=1, enable_recovery=True)
    def transition_to_state(self, target_state: WorkflowState) -> bool:
        """状态转换"""
        logger.info(f"Workflow controller transition_to_state called: {target_state.value}")
        
        if not self.current_session:
            logger.error("No active session for state transition")
            return False
        
        current_state = self.current_session.current_state
        logger.debug(f"Current session state: {current_state.value}")
        
        # 验证状态转换的合法性
        if not self._is_valid_transition(current_state, target_state):
            logger.error(f"Invalid state transition: {current_state.value} -> {target_state.value}")
            return False
        
        logger.debug(f"State transition is valid: {current_state.value} -> {target_state.value}")
        
        self.current_session.update_state(target_state)
        logger.info(f"State transition successful: {current_state.value} -> {target_state.value}")
        logger.debug(f"Session state after update: {self.current_session.current_state.value}")
        
        return True
    
    def _is_valid_transition(self, current: WorkflowState, target: WorkflowState) -> bool:
        """验证状态转换是否合法"""
        # 定义合法的状态转换
        valid_transitions = {
            WorkflowState.INITIAL: [WorkflowState.PRODUCT_ANALYSIS, WorkflowState.ERROR],
            WorkflowState.PRODUCT_ANALYSIS: [WorkflowState.MODULE_RECOMMENDATION, WorkflowState.ERROR],
            WorkflowState.MODULE_RECOMMENDATION: [WorkflowState.CONTENT_GENERATION, WorkflowState.PRODUCT_ANALYSIS, WorkflowState.ERROR],
            WorkflowState.CONTENT_GENERATION: [WorkflowState.CONTENT_EDITING, WorkflowState.MODULE_RECOMMENDATION, WorkflowState.ERROR],
            WorkflowState.CONTENT_EDITING: [WorkflowState.STYLE_SELECTION, WorkflowState.CONTENT_GENERATION, WorkflowState.ERROR],
            WorkflowState.STYLE_SELECTION: [WorkflowState.FINAL_CONFIRMATION, WorkflowState.CONTENT_EDITING, WorkflowState.ERROR],
            WorkflowState.FINAL_CONFIRMATION: [WorkflowState.IMAGE_GENERATION, WorkflowState.STYLE_SELECTION, WorkflowState.ERROR],
            WorkflowState.IMAGE_GENERATION: [WorkflowState.COMPLETED, WorkflowState.FINAL_CONFIRMATION, WorkflowState.ERROR],
            WorkflowState.COMPLETED: [WorkflowState.INITIAL],  # 可以重新开始
            WorkflowState.ERROR: [WorkflowState.INITIAL, WorkflowState.PRODUCT_ANALYSIS]  # 错误状态可以重新开始
        }
        
        return target in valid_transitions.get(current, [])
    
    def get_available_style_themes(self, product_category: Optional[ProductCategory] = None) -> List[StyleThemeConfig]:
        """获取可用的风格主题"""
        if product_category is None:
            return list(self.style_themes.values())
        
        # 根据产品类别筛选合适的主题
        suitable_themes = []
        for theme_config in self.style_themes.values():
            if product_category in theme_config.suitable_categories:
                suitable_themes.append(theme_config)
        
        # 如果没有特别合适的主题，返回专业商务风作为默认
        if not suitable_themes:
            suitable_themes = [self.style_themes[StyleTheme.PROFESSIONAL]]
        
        return suitable_themes
    
    @error_handler("recommend_style_theme", max_retries=1, enable_recovery=True)
    def recommend_style_theme(self, product_analysis: ProductAnalysis) -> StyleThemeConfig:
        """推荐风格主题"""
        category = product_analysis.product_category
        
        # 根据产品类别推荐主题
        theme_mapping = {
            ProductCategory.TECHNOLOGY: StyleTheme.MODERN_TECH,
            ProductCategory.HOME_LIVING: StyleTheme.WARM_HOME,
            ProductCategory.FASHION: StyleTheme.LUXURY_PREMIUM,
            ProductCategory.SPORTS: StyleTheme.CLEAN_FUNCTIONAL,
            ProductCategory.HEALTH_BEAUTY: StyleTheme.LUXURY_PREMIUM,
            ProductCategory.AUTOMOTIVE: StyleTheme.CLEAN_FUNCTIONAL,
            ProductCategory.TOOLS: StyleTheme.CLEAN_FUNCTIONAL,
            ProductCategory.OTHER: StyleTheme.PROFESSIONAL
        }
        
        recommended_theme = theme_mapping.get(category, StyleTheme.PROFESSIONAL)
        return self.style_themes[recommended_theme]
    
    @error_handler("get_module_recommendations", max_retries=2, enable_recovery=True)
    def get_module_recommendations(self, product_analysis: ProductAnalysis) -> ModuleRecommendation:
        """获取模块推荐"""
        category = product_analysis.product_category
        
        # 获取基础推荐
        base_recommendations = self.recommendation_rules.get(category, self.recommendation_rules[ProductCategory.OTHER])
        
        # 生成推荐理由
        reasons = {}
        confidence_scores = {}
        
        for module in base_recommendations:
            reasons[module] = self._generate_recommendation_reason(module, product_analysis)
            confidence_scores[module] = self._calculate_confidence_score(module, product_analysis)
        
        # 生成替代模块
        all_modules = list(ModuleType)
        alternative_modules = [m for m in all_modules if m not in base_recommendations][:4]
        
        return ModuleRecommendation(
            recommended_modules=base_recommendations,
            recommendation_reasons=reasons,
            confidence_scores=confidence_scores,
            alternative_modules=alternative_modules
        )
    
    def _generate_recommendation_reason(self, module: ModuleType, analysis: ProductAnalysis) -> str:
        """生成推荐理由"""
        reasons = {
            ModuleType.PRODUCT_OVERVIEW: f"展示{analysis.product_type}的整体特性和核心卖点",
            ModuleType.FEATURE_ANALYSIS: f"详细解析{analysis.product_type}的功能特点",
            ModuleType.SPECIFICATION_COMPARISON: f"突出{analysis.product_type}的技术优势",
            ModuleType.USAGE_SCENARIOS: f"展示{analysis.product_type}的实际应用场景",
            ModuleType.PROBLEM_SOLUTION: f"说明{analysis.product_type}解决的具体问题",
            ModuleType.INSTALLATION_GUIDE: f"提供{analysis.product_type}的安装指导",
            ModuleType.SIZE_COMPATIBILITY: f"展示{analysis.product_type}的尺寸兼容性",
            ModuleType.MAINTENANCE_CARE: f"介绍{analysis.product_type}的维护保养",
            ModuleType.MATERIAL_CRAFTSMANSHIP: f"突出{analysis.product_type}的材质工艺",
            ModuleType.QUALITY_ASSURANCE: f"展示{analysis.product_type}的品质保证",
            ModuleType.CUSTOMER_REVIEWS: f"展示{analysis.product_type}的用户评价",
            ModuleType.PACKAGE_CONTENTS: f"展示{analysis.product_type}的包装内容"
        }
        
        return reasons.get(module, f"适合{analysis.product_type}的专业展示")
    
    def _calculate_confidence_score(self, module: ModuleType, analysis: ProductAnalysis) -> float:
        """计算推荐置信度"""
        # 基础置信度
        base_confidence = 0.8
        
        # 根据产品特征调整置信度
        if "技术" in analysis.key_features and module in [ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON]:
            base_confidence += 0.1
        
        if "安装" in analysis.use_cases and module == ModuleType.INSTALLATION_GUIDE:
            base_confidence += 0.15
        
        if "材质" in analysis.materials and module == ModuleType.MATERIAL_CRAFTSMANSHIP:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def save_session_to_history(self):
        """保存当前会话到历史记录"""
        if self.current_session:
            # 创建会话副本
            session_copy = IntelligentWorkflowSession(
                session_id=self.current_session.session_id,
                current_state=self.current_session.current_state,
                product_analysis=self.current_session.product_analysis,
                module_recommendation=self.current_session.module_recommendation,
                selected_modules=self.current_session.selected_modules.copy(),
                module_contents=self.current_session.module_contents.copy(),
                selected_style_theme=self.current_session.selected_style_theme,
                compliance_results=self.current_session.compliance_results.copy(),
                generation_results=self.current_session.generation_results.copy(),
                generation_status=self.current_session.generation_status.copy(),
                user_edits=self.current_session.user_edits.copy(),
                workflow_metadata=self.current_session.workflow_metadata.copy(),
                creation_time=self.current_session.creation_time,
                last_updated=self.current_session.last_updated
            )
            
            self.session_history.append(session_copy)
            
            # 限制历史记录数量
            if len(self.session_history) > 20:
                self.session_history = self.session_history[-20:]
            
            logger.info(f"Session saved to history: {self.current_session.session_id}")
    
    def get_session_history(self) -> List[IntelligentWorkflowSession]:
        """获取会话历史"""
        return sorted(self.session_history, key=lambda x: x.last_updated, reverse=True)
    
    def clear_current_session(self):
        """清除当前会话"""
        if self.current_session:
            self.save_session_to_history()
            self.current_session = None
            logger.info("Current session cleared")
