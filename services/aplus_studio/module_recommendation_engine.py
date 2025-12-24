"""
A+ 智能模块推荐引擎

该模块实现基于产品特征的智能模块推荐系统，包括：
- 基于产品特征的模块匹配逻辑
- 实现4个模块的推荐机制
- 添加推荐理由生成
- 技术产品推荐逻辑（功能解析、规格对比）
- 生活用品推荐逻辑（使用场景、问题解决）
- 其他产品类型的推荐规则
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import ModuleType, ProductCategory
from .intelligent_workflow import ProductAnalysis, ModuleRecommendation
from .performance_monitor import (
    PerformanceMonitor, performance_monitor, get_global_performance_monitor
)
from .error_handler import (
    ErrorHandler, error_handler, get_global_error_handler
)

logger = logging.getLogger(__name__)


class RecommendationStrategy(Enum):
    """推荐策略枚举"""
    CATEGORY_BASED = "category_based"  # 基于产品类别
    FEATURE_BASED = "feature_based"    # 基于产品特征
    HYBRID = "hybrid"                  # 混合策略
    CUSTOM = "custom"                  # 自定义策略


@dataclass
class ModuleScore:
    """模块评分"""
    module_type: ModuleType
    score: float
    reasons: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def add_reason(self, reason: str, score_boost: float = 0.0):
        """添加推荐理由"""
        self.reasons.append(reason)
        self.score += score_boost
        self.score = min(self.score, 1.0)  # 确保分数不超过1.0


@dataclass
class RecommendationContext:
    """推荐上下文"""
    product_analysis: ProductAnalysis
    strategy: RecommendationStrategy = RecommendationStrategy.HYBRID
    max_recommendations: int = 4
    min_confidence: float = 0.6
    include_alternatives: bool = True
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class ModuleRecommendationEngine:
    """模块推荐引擎"""
    
    def __init__(self):
        self.recommendation_rules = self._initialize_recommendation_rules()
        self.feature_weights = self._initialize_feature_weights()
        self.module_compatibility = self._initialize_module_compatibility()
        self.category_priorities = self._initialize_category_priorities()
        
        # 初始化性能监控和错误处理
        self._performance_monitor = get_global_performance_monitor()
        self._error_handler = get_global_error_handler()
        
        # 注册回退处理器
        self._register_fallback_handlers()
        
        logger.info("Module Recommendation Engine initialized")
    
    def _register_fallback_handlers(self):
        """注册回退处理器"""
        def recommendation_fallback(*args, **kwargs):
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
        
        self._error_handler.register_fallback_handler("recommend_modules", recommendation_fallback)
    
    def _initialize_recommendation_rules(self) -> Dict[ProductCategory, Dict[str, Any]]:
        """初始化推荐规则"""
        rules = {
            ProductCategory.TECHNOLOGY: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.FEATURE_ANALYSIS,
                    ModuleType.SPECIFICATION_COMPARISON,
                    ModuleType.INSTALLATION_GUIDE
                ],
                "secondary_modules": [
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.MAINTENANCE_CARE,
                    ModuleType.PACKAGE_CONTENTS,
                    ModuleType.SIZE_COMPATIBILITY
                ],
                "keywords": ["技术", "性能", "规格", "功能", "配置", "参数"],
                "focus": "technical_specifications",
                "complexity_preference": "high"
            },
            ProductCategory.HOME_LIVING: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.PROBLEM_SOLUTION,
                    ModuleType.SIZE_COMPATIBILITY
                ],
                "secondary_modules": [
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.MAINTENANCE_CARE,
                    ModuleType.CUSTOMER_REVIEWS,
                    ModuleType.QUALITY_ASSURANCE
                ],
                "keywords": ["家居", "生活", "使用", "场景", "便捷", "舒适"],
                "focus": "lifestyle_scenarios",
                "complexity_preference": "medium"
            },
            ProductCategory.FASHION: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.SIZE_COMPATIBILITY,
                    ModuleType.CUSTOMER_REVIEWS
                ],
                "secondary_modules": [
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.MAINTENANCE_CARE,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.PACKAGE_CONTENTS
                ],
                "keywords": ["时尚", "材质", "工艺", "设计", "风格", "品质"],
                "focus": "material_quality",
                "complexity_preference": "medium"
            },
            ProductCategory.SPORTS: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.MAINTENANCE_CARE
                ],
                "secondary_modules": [
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.SIZE_COMPATIBILITY,
                    ModuleType.FEATURE_ANALYSIS,
                    ModuleType.CUSTOMER_REVIEWS
                ],
                "keywords": ["运动", "健身", "户外", "耐用", "性能", "专业"],
                "focus": "performance_durability",
                "complexity_preference": "medium"
            },
            ProductCategory.HEALTH_BEAUTY: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.PROBLEM_SOLUTION,
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.CUSTOMER_REVIEWS
                ],
                "secondary_modules": [
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.MAINTENANCE_CARE,
                    ModuleType.PACKAGE_CONTENTS
                ],
                "keywords": ["健康", "美容", "护理", "效果", "安全", "天然"],
                "focus": "safety_effectiveness",
                "complexity_preference": "low"
            },
            ProductCategory.AUTOMOTIVE: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.INSTALLATION_GUIDE,
                    ModuleType.SIZE_COMPATIBILITY,
                    ModuleType.SPECIFICATION_COMPARISON
                ],
                "secondary_modules": [
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.MAINTENANCE_CARE,
                    ModuleType.FEATURE_ANALYSIS,
                    ModuleType.PACKAGE_CONTENTS
                ],
                "keywords": ["汽车", "安装", "兼容", "规格", "配件", "改装"],
                "focus": "compatibility_installation",
                "complexity_preference": "high"
            },
            ProductCategory.TOOLS: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.FEATURE_ANALYSIS,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.MAINTENANCE_CARE
                ],
                "secondary_modules": [
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.SPECIFICATION_COMPARISON,
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.PACKAGE_CONTENTS
                ],
                "keywords": ["工具", "功能", "实用", "耐用", "专业", "效率"],
                "focus": "functionality_durability",
                "complexity_preference": "medium"
            },
            ProductCategory.OTHER: {
                "primary_modules": [
                    ModuleType.PRODUCT_OVERVIEW,
                    ModuleType.PROBLEM_SOLUTION,
                    ModuleType.USAGE_SCENARIOS,
                    ModuleType.PACKAGE_CONTENTS
                ],
                "secondary_modules": [
                    ModuleType.QUALITY_ASSURANCE,
                    ModuleType.CUSTOMER_REVIEWS,
                    ModuleType.MATERIAL_CRAFTSMANSHIP,
                    ModuleType.MAINTENANCE_CARE
                ],
                "keywords": ["实用", "便捷", "品质", "功能"],
                "focus": "general_utility",
                "complexity_preference": "medium"
            }
        }
        return rules
    
    def _initialize_feature_weights(self) -> Dict[str, float]:
        """初始化特征权重"""
        return {
            "technical_complexity": 0.3,
            "material_emphasis": 0.2,
            "installation_required": 0.25,
            "size_critical": 0.2,
            "maintenance_needed": 0.15,
            "quality_focus": 0.2,
            "user_reviews_important": 0.15,
            "problem_solving": 0.25,
            "usage_variety": 0.2
        }
    
    def _initialize_module_compatibility(self) -> Dict[ModuleType, Set[ModuleType]]:
        """初始化模块兼容性矩阵"""
        compatibility = {}
        
        # 产品概览与所有模块兼容
        compatibility[ModuleType.PRODUCT_OVERVIEW] = set(ModuleType) - {ModuleType.PRODUCT_OVERVIEW}
        
        # 功能解析与技术相关模块兼容性高
        compatibility[ModuleType.FEATURE_ANALYSIS] = {
            ModuleType.SPECIFICATION_COMPARISON,
            ModuleType.INSTALLATION_GUIDE,
            ModuleType.QUALITY_ASSURANCE,
            ModuleType.MAINTENANCE_CARE
        }
        
        # 规格对比与技术模块兼容
        compatibility[ModuleType.SPECIFICATION_COMPARISON] = {
            ModuleType.FEATURE_ANALYSIS,
            ModuleType.SIZE_COMPATIBILITY,
            ModuleType.QUALITY_ASSURANCE
        }
        
        # 使用场景与生活化模块兼容
        compatibility[ModuleType.USAGE_SCENARIOS] = {
            ModuleType.PROBLEM_SOLUTION,
            ModuleType.SIZE_COMPATIBILITY,
            ModuleType.MAINTENANCE_CARE,
            ModuleType.CUSTOMER_REVIEWS
        }
        
        # 问题解决与实用模块兼容
        compatibility[ModuleType.PROBLEM_SOLUTION] = {
            ModuleType.USAGE_SCENARIOS,
            ModuleType.QUALITY_ASSURANCE,
            ModuleType.CUSTOMER_REVIEWS
        }
        
        # 安装指南与技术模块兼容
        compatibility[ModuleType.INSTALLATION_GUIDE] = {
            ModuleType.SIZE_COMPATIBILITY,
            ModuleType.PACKAGE_CONTENTS,
            ModuleType.MAINTENANCE_CARE
        }
        
        # 尺寸兼容与多数模块兼容
        compatibility[ModuleType.SIZE_COMPATIBILITY] = {
            ModuleType.INSTALLATION_GUIDE,
            ModuleType.SPECIFICATION_COMPARISON,
            ModuleType.USAGE_SCENARIOS,
            ModuleType.PACKAGE_CONTENTS
        }
        
        # 维护保养与质量相关模块兼容
        compatibility[ModuleType.MAINTENANCE_CARE] = {
            ModuleType.QUALITY_ASSURANCE,
            ModuleType.MATERIAL_CRAFTSMANSHIP,
            ModuleType.USAGE_SCENARIOS
        }
        
        # 材质工艺与质量模块兼容
        compatibility[ModuleType.MATERIAL_CRAFTSMANSHIP] = {
            ModuleType.QUALITY_ASSURANCE,
            ModuleType.MAINTENANCE_CARE,
            ModuleType.CUSTOMER_REVIEWS
        }
        
        # 品质保证与多数模块兼容
        compatibility[ModuleType.QUALITY_ASSURANCE] = {
            ModuleType.MATERIAL_CRAFTSMANSHIP,
            ModuleType.MAINTENANCE_CARE,
            ModuleType.CUSTOMER_REVIEWS,
            ModuleType.SPECIFICATION_COMPARISON
        }
        
        # 用户评价与体验相关模块兼容
        compatibility[ModuleType.CUSTOMER_REVIEWS] = {
            ModuleType.QUALITY_ASSURANCE,
            ModuleType.USAGE_SCENARIOS,
            ModuleType.PROBLEM_SOLUTION,
            ModuleType.MATERIAL_CRAFTSMANSHIP
        }
        
        # 包装内容与实用模块兼容
        compatibility[ModuleType.PACKAGE_CONTENTS] = {
            ModuleType.INSTALLATION_GUIDE,
            ModuleType.SIZE_COMPATIBILITY,
            ModuleType.QUALITY_ASSURANCE
        }
        
        return compatibility
    
    def _initialize_category_priorities(self) -> Dict[ProductCategory, Dict[ModuleType, float]]:
        """初始化类别优先级"""
        priorities = {}
        
        # 为每个产品类别设置模块优先级
        for category, rules in self.recommendation_rules.items():
            category_priorities = {}
            
            # 主要模块高优先级
            for i, module in enumerate(rules["primary_modules"]):
                category_priorities[module] = 1.0 - (i * 0.1)  # 1.0, 0.9, 0.8, 0.7
            
            # 次要模块中等优先级
            for i, module in enumerate(rules["secondary_modules"]):
                category_priorities[module] = 0.6 - (i * 0.05)  # 0.6, 0.55, 0.5, 0.45
            
            # 其他模块低优先级
            all_modules = set(ModuleType)
            covered_modules = set(rules["primary_modules"] + rules["secondary_modules"])
            for module in all_modules - covered_modules:
                category_priorities[module] = 0.3
            
            priorities[category] = category_priorities
        
        return priorities
    
    @performance_monitor("recommend_modules", cache_key_params={"context": 0}, cache_ttl=1800)
    @error_handler("recommend_modules", max_retries=2, enable_recovery=True)
    def recommend_modules(self, context: RecommendationContext) -> ModuleRecommendation:
        """推荐模块
        
        Args:
            context: 推荐上下文
            
        Returns:
            ModuleRecommendation: 模块推荐结果
        """
        try:
            logger.info(f"Starting module recommendation for {context.product_analysis.product_type}")
            
            # 计算所有模块的评分
            module_scores = self._calculate_module_scores(context)
            
            # 排序并选择前N个模块
            sorted_scores = sorted(module_scores, key=lambda x: x.score, reverse=True)
            
            # 选择推荐模块
            recommended_modules = []
            recommendation_reasons = {}
            confidence_scores = {}
            
            for score in sorted_scores[:context.max_recommendations]:
                if score.confidence >= context.min_confidence:
                    recommended_modules.append(score.module_type)
                    recommendation_reasons[score.module_type] = self._format_recommendation_reason(score)
                    confidence_scores[score.module_type] = score.confidence
            
            # 如果推荐数量不足，补充低置信度的模块
            if len(recommended_modules) < context.max_recommendations:
                remaining_needed = context.max_recommendations - len(recommended_modules)
                for score in sorted_scores[len(recommended_modules):]:
                    if len(recommended_modules) >= context.max_recommendations:
                        break
                    if score.module_type not in recommended_modules:
                        recommended_modules.append(score.module_type)
                        recommendation_reasons[score.module_type] = self._format_recommendation_reason(score)
                        confidence_scores[score.module_type] = max(score.confidence, context.min_confidence)
            
            # 生成替代模块
            alternative_modules = []
            if context.include_alternatives:
                used_modules = set(recommended_modules)
                for score in sorted_scores:
                    if score.module_type not in used_modules and len(alternative_modules) < 4:
                        alternative_modules.append(score.module_type)
            
            # 创建推荐结果
            recommendation = ModuleRecommendation(
                recommended_modules=recommended_modules,
                recommendation_reasons=recommendation_reasons,
                confidence_scores=confidence_scores,
                alternative_modules=alternative_modules
            )
            
            logger.info(f"Module recommendation completed: {len(recommended_modules)} modules recommended")
            return recommendation
            
        except Exception as e:
            logger.error(f"Module recommendation failed: {str(e)}")
            # 返回默认推荐
            return self._get_default_recommendation(context.product_analysis)
    
    def _calculate_module_scores(self, context: RecommendationContext) -> List[ModuleScore]:
        """计算模块评分"""
        analysis = context.product_analysis
        category = analysis.product_category
        
        module_scores = []
        
        for module_type in ModuleType:
            score = ModuleScore(module_type=module_type, score=0.0)
            
            # 基于类别的基础评分
            base_score = self.category_priorities.get(category, {}).get(module_type, 0.3)
            score.score = base_score
            score.confidence = base_score
            
            # 基于产品特征的评分调整
            self._adjust_score_by_features(score, analysis)
            
            # 基于关键词匹配的评分调整
            self._adjust_score_by_keywords(score, analysis, category)
            
            # 基于模块兼容性的评分调整
            self._adjust_score_by_compatibility(score, module_scores)
            
            # 计算最终置信度
            score.confidence = min(score.score * 0.9, 1.0)
            
            module_scores.append(score)
        
        return module_scores
    
    def _adjust_score_by_features(self, score: ModuleScore, analysis: ProductAnalysis):
        """基于产品特征调整评分"""
        module = score.module_type
        
        # 技术产品特征匹配
        if self._has_technical_features(analysis):
            if module in [ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON]:
                score.score += 0.2
                score.add_reason("产品具有技术特征，适合功能和规格展示")
        
        # 安装需求匹配
        if self._requires_installation(analysis):
            if module == ModuleType.INSTALLATION_GUIDE:
                score.score += 0.25
                score.add_reason("产品需要安装，安装指南很重要")
        
        # 尺寸敏感性匹配
        if self._is_size_critical(analysis):
            if module == ModuleType.SIZE_COMPATIBILITY:
                score.score += 0.2
                score.add_reason("产品对尺寸要求较高")
        
        # 材质重要性匹配
        if len(analysis.materials) > 2:
            if module == ModuleType.MATERIAL_CRAFTSMANSHIP:
                score.score += 0.15
                score.add_reason("产品材质丰富，适合展示工艺")
        
        # 问题解决导向匹配
        if self._is_problem_solving_focused(analysis):
            if module == ModuleType.PROBLEM_SOLUTION:
                score.score += 0.2
                score.add_reason("产品主要解决特定问题")
        
        # 使用场景多样性匹配
        if len(analysis.use_cases) > 2:
            if module == ModuleType.USAGE_SCENARIOS:
                score.score += 0.15
                score.add_reason("产品使用场景丰富")
        
        # 维护需求匹配
        if self._requires_maintenance(analysis):
            if module == ModuleType.MAINTENANCE_CARE:
                score.score += 0.15
                score.add_reason("产品需要定期维护")
    
    def _adjust_score_by_keywords(self, score: ModuleScore, analysis: ProductAnalysis, category: ProductCategory):
        """基于关键词匹配调整评分"""
        rules = self.recommendation_rules.get(category, {})
        keywords = rules.get("keywords", [])
        
        # 检查产品特征中的关键词
        all_text = " ".join(analysis.key_features + analysis.marketing_angles + analysis.use_cases)
        
        keyword_matches = sum(1 for keyword in keywords if keyword in all_text)
        if keyword_matches > 0:
            keyword_boost = min(keyword_matches * 0.05, 0.15)
            score.score += keyword_boost
            score.add_reason(f"产品特征与{category.value}类别高度匹配")
    
    def _adjust_score_by_compatibility(self, score: ModuleScore, existing_scores: List[ModuleScore]):
        """基于模块兼容性调整评分"""
        if len(existing_scores) == 0:
            return
        
        module = score.module_type
        compatible_modules = self.module_compatibility.get(module, set())
        
        # 检查与已有高分模块的兼容性
        high_score_modules = [s.module_type for s in existing_scores if s.score > 0.7]
        
        compatibility_count = sum(1 for m in high_score_modules if m in compatible_modules)
        if compatibility_count > 0:
            compatibility_boost = min(compatibility_count * 0.03, 0.1)
            score.score += compatibility_boost
            score.add_reason("与其他推荐模块兼容性好")
    
    def _has_technical_features(self, analysis: ProductAnalysis) -> bool:
        """判断是否有技术特征"""
        technical_keywords = ["技术", "性能", "规格", "参数", "配置", "功能", "处理器", "内存", "功率", "频率"]
        all_text = " ".join(analysis.key_features + analysis.marketing_angles)
        return any(keyword in all_text for keyword in technical_keywords)
    
    def _requires_installation(self, analysis: ProductAnalysis) -> bool:
        """判断是否需要安装"""
        installation_keywords = ["安装", "组装", "配置", "设置", "连接", "固定", "挂载"]
        all_text = " ".join(analysis.key_features + analysis.use_cases + analysis.marketing_angles)
        return any(keyword in all_text for keyword in installation_keywords)
    
    def _is_size_critical(self, analysis: ProductAnalysis) -> bool:
        """判断尺寸是否关键"""
        size_keywords = ["尺寸", "大小", "规格", "兼容", "适配", "空间", "紧凑", "小巧"]
        all_text = " ".join(analysis.key_features + analysis.use_cases + analysis.marketing_angles)
        return any(keyword in all_text for keyword in size_keywords)
    
    def _is_problem_solving_focused(self, analysis: ProductAnalysis) -> bool:
        """判断是否以问题解决为导向"""
        problem_keywords = ["解决", "改善", "优化", "提升", "减少", "避免", "防止", "消除"]
        all_text = " ".join(analysis.marketing_angles + analysis.use_cases)
        return any(keyword in all_text for keyword in problem_keywords)
    
    def _requires_maintenance(self, analysis: ProductAnalysis) -> bool:
        """判断是否需要维护"""
        maintenance_keywords = ["维护", "保养", "清洁", "更换", "检查", "保修", "耐用"]
        all_text = " ".join(analysis.key_features + analysis.marketing_angles)
        return any(keyword in all_text for keyword in maintenance_keywords)
    
    def _format_recommendation_reason(self, score: ModuleScore) -> str:
        """格式化推荐理由"""
        if score.reasons:
            return "；".join(score.reasons)
        else:
            # 生成默认理由
            return self._generate_default_reason(score.module_type)
    
    def _generate_default_reason(self, module_type: ModuleType) -> str:
        """生成默认推荐理由"""
        default_reasons = {
            ModuleType.PRODUCT_OVERVIEW: "展示产品整体特性和核心卖点",
            ModuleType.FEATURE_ANALYSIS: "详细解析产品功能特点",
            ModuleType.SPECIFICATION_COMPARISON: "突出产品技术优势",
            ModuleType.USAGE_SCENARIOS: "展示产品实际应用场景",
            ModuleType.PROBLEM_SOLUTION: "说明产品解决的具体问题",
            ModuleType.INSTALLATION_GUIDE: "提供产品安装指导",
            ModuleType.SIZE_COMPATIBILITY: "展示产品尺寸兼容性",
            ModuleType.MAINTENANCE_CARE: "介绍产品维护保养",
            ModuleType.MATERIAL_CRAFTSMANSHIP: "突出产品材质工艺",
            ModuleType.QUALITY_ASSURANCE: "展示产品品质保证",
            ModuleType.CUSTOMER_REVIEWS: "展示用户评价和反馈",
            ModuleType.PACKAGE_CONTENTS: "展示产品包装内容"
        }
        
        return default_reasons.get(module_type, "适合产品的专业展示")
    
    def _get_default_recommendation(self, analysis: ProductAnalysis) -> ModuleRecommendation:
        """获取默认推荐"""
        category = analysis.product_category
        rules = self.recommendation_rules.get(category, self.recommendation_rules[ProductCategory.OTHER])
        
        recommended_modules = rules["primary_modules"][:4]
        
        recommendation_reasons = {}
        confidence_scores = {}
        
        for module in recommended_modules:
            recommendation_reasons[module] = self._generate_default_reason(module)
            confidence_scores[module] = 0.7
        
        alternative_modules = rules["secondary_modules"][:4]
        
        return ModuleRecommendation(
            recommended_modules=recommended_modules,
            recommendation_reasons=recommendation_reasons,
            confidence_scores=confidence_scores,
            alternative_modules=alternative_modules
        )
    
    def get_recommendation_explanation(self, recommendation: ModuleRecommendation, analysis: ProductAnalysis) -> Dict[str, Any]:
        """获取推荐解释"""
        try:
            explanation = {
                "product_analysis_summary": {
                    "product_type": analysis.product_type,
                    "category": analysis.product_category.value,
                    "key_features": analysis.key_features[:3],
                    "confidence": analysis.confidence_score
                },
                "recommendation_strategy": {
                    "primary_focus": self.recommendation_rules.get(analysis.product_category, {}).get("focus", "general"),
                    "total_modules": len(recommendation.recommended_modules),
                    "avg_confidence": sum(recommendation.confidence_scores.values()) / len(recommendation.confidence_scores) if recommendation.confidence_scores else 0
                },
                "module_details": [],
                "alternatives_available": len(recommendation.alternative_modules)
            }
            
            # 添加每个推荐模块的详细信息
            for module in recommendation.recommended_modules:
                module_detail = {
                    "module_type": module.value,
                    "display_name": self._get_module_display_name(module),
                    "reason": recommendation.recommendation_reasons.get(module, ""),
                    "confidence": recommendation.confidence_scores.get(module, 0.0),
                    "category_fit": self._assess_category_fit(module, analysis.product_category)
                }
                explanation["module_details"].append(module_detail)
            
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to generate recommendation explanation: {str(e)}")
            return {"error": str(e)}
    
    def _get_module_display_name(self, module_type: ModuleType) -> str:
        """获取模块显示名称"""
        display_names = {
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
        return display_names.get(module_type, module_type.value)
    
    def _assess_category_fit(self, module_type: ModuleType, category: ProductCategory) -> str:
        """评估模块与类别的匹配度"""
        priority = self.category_priorities.get(category, {}).get(module_type, 0.3)
        
        if priority >= 0.8:
            return "excellent"
        elif priority >= 0.6:
            return "good"
        elif priority >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def validate_recommendation(self, recommendation: ModuleRecommendation) -> Dict[str, Any]:
        """验证推荐结果"""
        try:
            validation_result = {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "suggestions": []
            }
            
            # 检查推荐数量
            if len(recommendation.recommended_modules) != 4:
                validation_result["warnings"].append(f"推荐模块数量为{len(recommendation.recommended_modules)}，建议为4个")
            
            # 检查是否包含产品概览
            if ModuleType.PRODUCT_OVERVIEW not in recommendation.recommended_modules:
                validation_result["warnings"].append("建议包含产品概览模块作为基础展示")
            
            # 检查模块重复
            if len(set(recommendation.recommended_modules)) != len(recommendation.recommended_modules):
                validation_result["is_valid"] = False
                validation_result["issues"].append("推荐模块中存在重复")
            
            # 检查置信度
            low_confidence_modules = [
                module for module, confidence in recommendation.confidence_scores.items()
                if confidence < 0.6
            ]
            if low_confidence_modules:
                validation_result["warnings"].append(f"以下模块置信度较低: {[m.value for m in low_confidence_modules]}")
            
            # 检查模块兼容性
            compatibility_issues = self._check_module_compatibility(recommendation.recommended_modules)
            if compatibility_issues:
                validation_result["warnings"].extend(compatibility_issues)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Recommendation validation failed: {str(e)}")
            return {
                "is_valid": False,
                "issues": [f"验证过程出错: {str(e)}"],
                "warnings": [],
                "suggestions": []
            }
    
    def _check_module_compatibility(self, modules: List[ModuleType]) -> List[str]:
        """检查模块兼容性"""
        issues = []
        
        for i, module1 in enumerate(modules):
            compatible_modules = self.module_compatibility.get(module1, set())
            for j, module2 in enumerate(modules[i+1:], i+1):
                if module2 not in compatible_modules and module1 not in self.module_compatibility.get(module2, set()):
                    issues.append(f"{self._get_module_display_name(module1)}与{self._get_module_display_name(module2)}兼容性较低")
        
        return issues