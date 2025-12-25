"""
A+ 智能工作流模块推荐界面组件

该模块提供模块推荐阶段的用户界面，包括推荐结果展示、理由说明、
用户确认和手动调整选项、替代模块建议显示等功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from services.aplus_studio.models import ModuleType, WorkflowState
from services.aplus_studio.module_recommendation_engine import ModuleRecommendationEngine
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowController

logger = logging.getLogger(__name__)


@dataclass
class ModuleRecommendationDisplay:
    """模块推荐显示信息"""
    module_type: ModuleType
    name: str
    icon: str
    description: str
    reason: str
    confidence: float
    is_recommended: bool
    is_selected: bool
    preview_image: Optional[str] = None
    estimated_time: int = 30
    complexity: str = "中等"


class RecommendationMode(Enum):
    """推荐模式"""
    AI_RECOMMENDED = "ai_recommended"  # AI推荐模式
    MANUAL_SELECTION = "manual_selection"  # 手动选择模式
    HYBRID = "hybrid"  # 混合模式


class ModuleRecommendationUI:
    """模块推荐界面组件"""
    
    def __init__(self, workflow_controller: IntelligentWorkflowController):
        self.workflow_controller = workflow_controller
        self.recommendation_engine = ModuleRecommendationEngine()
        
        # 模块配置信息
        self.module_configs = {
            ModuleType.PRODUCT_OVERVIEW: {
                "name": "产品概览",
                "icon": "🎯",
                "description": "展示产品整体外观和核心特性，使用英雄式布局突出产品价值",
                "complexity": "简单",
                "estimated_time": 25,
                "suitable_for": ["所有产品", "新品发布", "品牌展示"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["产品主图", "核心卖点", "品牌标识"]
            },
            ModuleType.FEATURE_ANALYSIS: {
                "name": "功能解析",
                "icon": "🔍",
                "description": "使用图表、标注和分解图展示产品功能细节和技术特性",
                "complexity": "中等",
                "estimated_time": 35,
                "suitable_for": ["技术产品", "复杂功能", "专业设备"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["功能标注", "技术图解", "特性说明"]
            },
            ModuleType.SPECIFICATION_COMPARISON: {
                "name": "规格对比",
                "icon": "📊",
                "description": "创建清晰的对比表格和数据可视化，突出产品规格优势",
                "complexity": "中等",
                "estimated_time": 30,
                "suitable_for": ["技术产品", "系列产品", "竞品对比"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["规格表格", "数据对比", "优势标注"]
            },
            ModuleType.USAGE_SCENARIOS: {
                "name": "使用场景",
                "icon": "🏠",
                "description": "展示产品在实际使用环境中的应用和效果",
                "complexity": "简单",
                "estimated_time": 30,
                "suitable_for": ["生活用品", "家居产品", "日用品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["使用环境", "应用场景", "效果展示"]
            },
            ModuleType.PROBLEM_SOLUTION: {
                "name": "问题解决",
                "icon": "💡",
                "description": "展示产品如何解决用户痛点和实际问题",
                "complexity": "中等",
                "estimated_time": 35,
                "suitable_for": ["功能性产品", "解决方案", "创新产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["问题描述", "解决方案", "效果对比"]
            },
            ModuleType.MATERIAL_CRAFTSMANSHIP: {
                "name": "材质工艺",
                "icon": "✨",
                "description": "突出产品材质、工艺和制造品质",
                "complexity": "中等",
                "estimated_time": 40,
                "suitable_for": ["高端产品", "工艺品", "品质产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["材质展示", "工艺细节", "品质认证"]
            },
            ModuleType.INSTALLATION_GUIDE: {
                "name": "安装指南",
                "icon": "🔧",
                "description": "提供清晰的安装步骤和使用指导",
                "complexity": "复杂",
                "estimated_time": 45,
                "suitable_for": ["需要安装的产品", "复杂产品", "DIY产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["安装步骤", "工具说明", "注意事项"]
            },
            ModuleType.SIZE_COMPATIBILITY: {
                "name": "尺寸兼容",
                "icon": "📐",
                "description": "展示产品尺寸信息和兼容性说明",
                "complexity": "简单",
                "estimated_time": 25,
                "suitable_for": ["配件产品", "尺寸敏感产品", "兼容性产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["尺寸标注", "兼容性图表", "适配说明"]
            },
            ModuleType.PACKAGE_CONTENTS: {
                "name": "包装内容",
                "icon": "📦",
                "description": "展示产品包装内容和配件清单",
                "complexity": "简单",
                "estimated_time": 20,
                "suitable_for": ["套装产品", "配件丰富产品", "礼品套装"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["内容清单", "配件展示", "包装说明"]
            },
            ModuleType.QUALITY_ASSURANCE: {
                "name": "品质保证",
                "icon": "🏆",
                "description": "展示产品认证、保修和品质保证信息",
                "complexity": "简单",
                "estimated_time": 25,
                "suitable_for": ["品牌产品", "认证产品", "保修产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["认证标识", "保修信息", "品质承诺"]
            },
            ModuleType.CUSTOMER_REVIEWS: {
                "name": "客户评价",
                "icon": "⭐",
                "description": "展示客户评价和使用反馈",
                "complexity": "中等",
                "estimated_time": 30,
                "suitable_for": ["热销产品", "好评产品", "用户推荐"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["评价展示", "用户反馈", "评分统计"]
            },
            ModuleType.MAINTENANCE_CARE: {
                "name": "维护保养",
                "icon": "🧽",
                "description": "提供产品维护和保养指导",
                "complexity": "中等",
                "estimated_time": 35,
                "suitable_for": ["需要保养的产品", "长期使用产品", "精密产品"],
                "output_format": "单张图片 (600×450)",
                "key_elements": ["保养步骤", "维护提示", "注意事项"]
            }
        }
    
    def render_recommendation_interface(self, analysis_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        渲染完整的模块推荐界面
        
        Args:
            analysis_result: 产品分析结果（可选，如果不提供则从session获取）
        
        Returns:
            Dict: 包含用户操作和选择结果的字典
        """
        st.subheader("🎯 智能模块推荐")
        
        # 检查前置条件 - 优先使用传入的analysis_result
        if analysis_result is None:
            session = self.workflow_controller.state_manager.get_current_session()
            if not session or not session.product_analysis:
                st.warning("⚠️ 请先完成产品分析")
                return {"action": None}
            # 从session获取分析结果
            analysis_result = session.product_analysis
        
        # 确保analysis_result不为空
        if not analysis_result:
            st.warning("⚠️ 请先完成产品分析")
            return {"action": None}
        
        # 如果已有推荐结果，显示推荐界面
        existing_recommendation = self.workflow_controller.state_manager.get_module_recommendation()
        if existing_recommendation:
            return self._render_recommendation_results(existing_recommendation)
        
        # 否则显示推荐生成界面
        return self._render_recommendation_generation(analysis_result)
    
    def _render_recommendation_generation(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """渲染推荐生成界面"""
        
        st.write("**🤖 AI正在分析您的产品，生成最佳模块推荐...**")
        
        # 调试信息
        logger.debug(f"Rendering recommendation generation interface with analysis_result keys: {list(analysis_result.keys()) if analysis_result else 'None'}")
        
        # 显示分析摘要
        with st.expander("📋 产品分析摘要", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                product_type = analysis_result.get('product_type', '未识别')
                st.metric("产品类别", product_type)
            
            with col2:
                confidence_score = analysis_result.get('confidence_score', 0)
                st.metric("置信度", f"{confidence_score:.1%}")
            
            with col3:
                key_features = analysis_result.get('key_features', [])
                st.metric("特征数量", len(key_features))
            
            # 核心特征
            if key_features:
                st.write("**核心特征：**")
                for feature in key_features[:3]:
                    st.write(f"• {feature}")
        
        # 推荐选项
        with st.expander("⚙️ 推荐选项", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                recommendation_count = st.selectbox(
                    "推荐模块数量",
                    [3, 4, 5, 6],
                    index=1,  # 默认4个
                    help="AI将推荐指定数量的最适合模块"
                )
                
                include_alternatives = st.checkbox(
                    "包含替代建议",
                    value=True,
                    help="为每个推荐模块提供替代选项"
                )
            
            with col2:
                recommendation_style = st.selectbox(
                    "推荐风格",
                    ["平衡推荐", "营销导向", "技术导向", "用户导向"],
                    help="不同风格会影响模块选择偏好"
                )
                
                prioritize_simplicity = st.checkbox(
                    "优先简单模块",
                    value=False,
                    help="优先推荐制作简单、效果明显的模块"
                )
        
        # 生成推荐按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        # 调试信息
        if st.checkbox("显示调试信息", value=False):
            st.write("**调试信息:**")
            st.write(f"- recommendation_count: {recommendation_count}")
            st.write(f"- include_alternatives: {include_alternatives}")
            st.write(f"- recommendation_style: {recommendation_style}")
            st.write(f"- prioritize_simplicity: {prioritize_simplicity}")
            st.write(f"- analysis_result keys: {list(analysis_result.keys()) if analysis_result else 'None'}")
        
        with col1:
            if st.button("🚀 生成AI推荐", type="primary", use_container_width=True):
                logger.debug("Generate AI recommendation button clicked")
                st.write("🔄 按钮已点击，正在处理...")  # 临时调试信息
                return {
                    "action": "generate_recommendation",
                    "analysis_result": analysis_result,
                    "options": {
                        "count": recommendation_count,
                        "include_alternatives": include_alternatives,
                        "style": recommendation_style,
                        "prioritize_simplicity": prioritize_simplicity
                    }
                }
        
        with col2:
            if st.button("🎯 手动选择", use_container_width=True):
                return {"action": "manual_selection"}
        
        with col3:
            if st.button("📖 模块说明", use_container_width=True):
                return {"action": "show_module_guide"}
        
        return {"action": None}
    
    def _render_recommendation_results(self, recommendation) -> Dict[str, Any]:
        """渲染推荐结果界面"""
        
        st.write("**✅ AI推荐完成**")
        
        # 推荐摘要
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            recommended_modules = recommendation.get('recommended_modules', [])
            st.metric("推荐模块", len(recommended_modules))
        
        with col2:
            confidence_scores = recommendation.get('confidence_scores', {})
            if confidence_scores:
                avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                st.metric("平均置信度", f"{avg_confidence:.1%}")
            else:
                st.metric("平均置信度", "N/A")
        
        with col3:
            total_time = 0
            for module in recommended_modules:
                if hasattr(module, 'value'):
                    module_key = module
                else:
                    # 如果是字符串，转换为ModuleType
                    from services.aplus_studio.models import ModuleType
                    try:
                        module_key = ModuleType(module)
                    except:
                        continue
                
                if module_key in self.module_configs:
                    total_time += self.module_configs[module_key]["estimated_time"]
            
            st.metric("预计制作时间", f"{total_time}分钟")
        
        with col4:
            alternative_modules = recommendation.get('alternative_modules', [])
            st.metric("替代选项", f"{len(alternative_modules)}个")
        
        # 推荐模式选择
        recommendation_mode = self._render_mode_selection()
        
        if recommendation_mode == RecommendationMode.AI_RECOMMENDED:
            return self._render_ai_recommended_mode(recommendation)
        elif recommendation_mode == RecommendationMode.MANUAL_SELECTION:
            return self._render_manual_selection_mode(recommendation)
        else:  # HYBRID
            return self._render_hybrid_mode(recommendation)
    
    def _render_mode_selection(self) -> RecommendationMode:
        """渲染推荐模式选择"""
        
        st.write("**选择模式**")
        
        # 模式说明
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("🤖 **AI推荐**\n直接使用AI推荐的模块，快速高效")
        
        with col2:
            st.info("🎯 **手动选择**\n完全自由选择，适合有明确需求")
        
        with col3:
            st.info("🔄 **混合模式**\n在AI推荐基础上调整，平衡效率与个性化")
        
        mode_options = {
            "🤖 AI推荐": RecommendationMode.AI_RECOMMENDED,
            "🎯 手动选择": RecommendationMode.MANUAL_SELECTION,
            "🔄 混合模式": RecommendationMode.HYBRID
        }
        
        selected_mode = st.radio(
            "选择推荐模式",
            list(mode_options.keys()),
            horizontal=True,
            label_visibility="collapsed"
        )
        
        return mode_options[selected_mode]
    
    def _render_ai_recommended_mode(self, recommendation) -> Dict[str, Any]:
        """渲染AI推荐模式"""
        
        st.write("**🤖 AI推荐模块**")
        
        selected_modules = []
        
        # 获取推荐数据
        recommended_modules = recommendation.get('recommended_modules', [])
        recommendation_reasons = recommendation.get('recommendation_reasons', {})
        confidence_scores = recommendation.get('confidence_scores', {})
        
        # 显示推荐模块
        for i, module_type in enumerate(recommended_modules, 1):
            # 确保module_type是ModuleType对象
            if isinstance(module_type, str):
                from services.aplus_studio.models import ModuleType
                try:
                    module_type = ModuleType(module_type)
                except:
                    continue
            
            config = self.module_configs.get(module_type, {})
            if not config:
                continue
                
            reason = recommendation_reasons.get(module_type, "AI推荐此模块")
            confidence = confidence_scores.get(module_type, 0.8)
            
            with st.container():
                # 模块卡片
                col1, col2, col3 = st.columns([1, 4, 1])
                
                with col1:
                    st.write(f"**{i}.**")
                    st.write(f"{config['icon']}")
                
                with col2:
                    # 模块选择复选框
                    is_selected = st.checkbox(
                        f"**{config['name']}**",
                        value=True,  # AI推荐的默认选中
                        key=f"ai_rec_{module_type.value}",
                        help=f"置信度: {confidence:.1%}"
                    )
                    
                    if is_selected:
                        selected_modules.append(module_type)
                    
                    # 模块描述
                    st.write(config["description"])
                    
                    # 推荐理由
                    st.info(f"💡 **推荐理由：** {reason}")
                
                with col3:
                    # 置信度指示器
                    confidence_color = "green" if confidence > 0.8 else "orange" if confidence > 0.6 else "red"
                    st.markdown(f"<div style='text-align: center; color: {confidence_color}; font-weight: bold;'>{confidence:.0%}</div>", 
                              unsafe_allow_html=True)
                    
                    # 详情按钮
                    if st.button("ℹ️", key=f"info_ai_{module_type.value}", help="查看详情"):
                        self._show_module_details(module_type)
                
                # 模块详细信息
                with st.expander(f"📋 {config['name']} 详细信息", expanded=False):
                    self._render_module_details(module_type, config)
                
                st.divider()
        
        # 替代建议
        alternative_modules = recommendation.get('alternative_modules', [])
        if alternative_modules:
            self._render_alternative_suggestions(alternative_modules)
        
        # 操作按钮
        return self._render_action_buttons(selected_modules, "ai_recommended")
    
    def _render_manual_selection_mode(self, recommendation) -> Dict[str, Any]:
        """渲染手动选择模式"""
        
        st.write("**🎯 手动选择模块**")
        st.info("💡 **使用说明：** 选择您需要的模块类型，然后点击下方的"确认选择"按钮继续")
        
        # 确保 ModuleType 在当前作用域可用
        from services.aplus_studio.models import ModuleType
        
        # 按类别组织模块
        module_categories = {
            "核心展示": [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON],
            "使用场景": [ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.INSTALLATION_GUIDE],
            "品质保证": [ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
            "产品信息": [ModuleType.SIZE_COMPATIBILITY, ModuleType.PACKAGE_CONTENTS, ModuleType.MAINTENANCE_CARE]
        }
        
        selected_modules = []
        recommended_modules = recommendation.get('recommended_modules', [])
        
        # 确保recommended_modules是ModuleType对象列表
        if recommended_modules and isinstance(recommended_modules[0], str):
            from services.aplus_studio.models import ModuleType
            recommended_modules = [ModuleType(m) for m in recommended_modules if m in [mt.value for mt in ModuleType]]
        
        # 显示分类选择
        for category_name, modules in module_categories.items():
            st.write(f"**{category_name}**")
            
            cols = st.columns(len(modules))
            
            for i, module_type in enumerate(modules):
                config = self.module_configs[module_type]
                
                with cols[i]:
                    # 模块选择卡片
                    is_recommended = module_type in recommended_modules
                    
                    # 卡片样式
                    card_style = "border: 2px solid #28a745;" if is_recommended else "border: 1px solid #dee2e6;"
                    
                    with st.container():
                        st.markdown(f"<div style='{card_style} padding: 10px; border-radius: 5px; margin-bottom: 10px;'>", 
                                  unsafe_allow_html=True)
                        
                        # 模块图标和名称
                        st.write(f"<div style='text-align: center; font-size: 24px;'>{config['icon']}</div>", 
                               unsafe_allow_html=True)
                        
                        # 选择复选框
                        is_selected = st.checkbox(
                            config["name"],
                            value=is_recommended,  # AI推荐的默认选中
                            key=f"manual_{module_type.value}",
                            label_visibility="visible"
                        )
                        
                        if is_selected:
                            selected_modules.append(module_type)
                        
                        # 推荐标识
                        if is_recommended:
                            st.success("🤖 AI推荐")
                        
                        # 复杂度和时间
                        st.caption(f"复杂度: {config['complexity']}")
                        st.caption(f"时间: {config['estimated_time']}分钟")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("")  # 添加间距
        
        # 选择统计
        if selected_modules:
            total_time = sum(self.module_configs[m]["estimated_time"] for m in selected_modules)
            complexity_counts = {}
            for module in selected_modules:
                complexity = self.module_configs[module]["complexity"]
                complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            
            # 显示选择摘要
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("已选择", f"{len(selected_modules)} 个模块")
            with col2:
                st.metric("预计时间", f"{total_time} 分钟")
            with col3:
                complexity_text = ", ".join([f"{k}:{v}" for k, v in complexity_counts.items()])
                st.metric("复杂度", complexity_text)
        else:
            st.info("👆 请选择您需要的模块类型")
        
        # 操作按钮
        return self._render_action_buttons(selected_modules, "manual")
    
    def _render_hybrid_mode(self, recommendation) -> Dict[str, Any]:
        """渲染混合模式"""
        
        st.write("**🔄 混合模式 - 在AI推荐基础上调整**")
        
        # AI推荐区域
        st.write("**🤖 AI推荐模块**")
        
        selected_modules = []
        recommended_modules = recommendation.get('recommended_modules', [])
        recommendation_reasons = recommendation.get('recommendation_reasons', {})
        confidence_scores = recommendation.get('confidence_scores', {})
        
        # 确保recommended_modules是ModuleType对象列表
        if recommended_modules and isinstance(recommended_modules[0], str):
            from services.aplus_studio.models import ModuleType
            recommended_modules = [ModuleType(m) for m in recommended_modules if m in [mt.value for mt in ModuleType]]
        
        # 显示AI推荐的模块
        for module_type in recommended_modules:
            config = self.module_configs.get(module_type, {})
            if not config:
                continue
                
            reason = recommendation_reasons.get(module_type, "AI推荐此模块")
            confidence = confidence_scores.get(module_type, 0.8)
            
            col1, col2, col3 = st.columns([1, 5, 1])
            
            with col1:
                st.write(config['icon'])
            
            with col2:
                is_selected = st.checkbox(
                    f"**{config['name']}** (AI推荐)",
                    value=True,
                    key=f"hybrid_rec_{module_type.value}",
                    help=f"推荐理由: {reason}"
                )
                
                if is_selected:
                    selected_modules.append(module_type)
                
                st.caption(config["description"])
            
            with col3:
                st.write(f"{confidence:.0%}")
        
        st.divider()
        
        # 其他可选模块
        st.write("**➕ 其他可选模块**")
        
        other_modules = [m for m in self.module_configs.keys() if m not in recommended_modules]
        
        if other_modules:
            # 按行显示其他模块
            cols_per_row = 3
            rows = (len(other_modules) + cols_per_row - 1) // cols_per_row
            
            for row in range(rows):
                cols = st.columns(cols_per_row)
                
                for col_idx in range(cols_per_row):
                    module_idx = row * cols_per_row + col_idx
                    
                    if module_idx < len(other_modules):
                        module_type = other_modules[module_idx]
                        config = self.module_configs[module_type]
                        
                        with cols[col_idx]:
                            is_selected = st.checkbox(
                                f"{config['icon']} {config['name']}",
                                value=False,
                                key=f"hybrid_other_{module_type.value}",
                                help=config["description"]
                            )
                            
                            if is_selected:
                                selected_modules.append(module_type)
                            
                            st.caption(f"{config['complexity']} • {config['estimated_time']}分钟")
        
        # 选择统计
        if selected_modules:
            ai_count = sum(1 for m in selected_modules if m in recommended_modules)
            manual_count = len(selected_modules) - ai_count
            total_time = sum(self.module_configs[m]["estimated_time"] for m in selected_modules)
            
            st.info(f"已选择 {len(selected_modules)} 个模块 (AI推荐: {ai_count}, 手动添加: {manual_count})，预计时间: {total_time} 分钟")
        
        # 操作按钮
        return self._render_action_buttons(selected_modules, "hybrid")
    
    def _render_alternative_suggestions(self, alternative_modules: List[ModuleType]) -> None:
        """渲染替代建议"""
        
        with st.expander("🔄 替代建议", expanded=False):
            st.write("**如果您对推荐不满意，可以考虑以下替代模块：**")
            st.info("💡 这些是基于产品分析的其他可选模块，您可以在混合模式或手动模式中选择它们")
            
            # 按行显示替代模块，每行3个
            cols_per_row = 3
            rows = (len(alternative_modules) + cols_per_row - 1) // cols_per_row
            
            for row in range(rows):
                cols = st.columns(cols_per_row)
                
                for col_idx in range(cols_per_row):
                    module_idx = row * cols_per_row + col_idx
                    
                    if module_idx < len(alternative_modules):
                        module_type = alternative_modules[module_idx]
                        config = self.module_configs[module_type]
                        
                        with cols[col_idx]:
                            # 模块卡片展示
                            with st.container():
                                st.markdown(
                                    f"""
                                    <div style='border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; text-align: center; height: 120px; display: flex; flex-direction: column; justify-content: space-between;'>
                                        <div style='font-size: 24px;'>{config['icon']}</div>
                                        <div style='font-weight: bold; margin: 5px 0;'>{config['name']}</div>
                                        <div style='font-size: 12px; color: #666;'>{config['complexity']} • {config['estimated_time']}分钟</div>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                                
                                # 详细描述
                                with st.expander("查看详情", expanded=False):
                                    st.write(config["description"])
                                    st.write(f"**适用于：** {', '.join(config.get('suitable_for', []))}")
            
            st.caption("💡 提示：您可以切换到"混合模式"或"手动选择"来选择这些替代模块")
    
    def _render_module_details(self, module_type: ModuleType, config: Dict[str, Any]) -> None:
        """渲染模块详细信息"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本信息**")
            st.write(f"• 复杂度: {config['complexity']}")
            st.write(f"• 预计时间: {config['estimated_time']} 分钟")
            st.write(f"• 输出格式: {config['output_format']}")
        
        with col2:
            st.write("**适用场景**")
            for scenario in config["suitable_for"]:
                st.write(f"• {scenario}")
        
        st.write("**关键要素**")
        for element in config["key_elements"]:
            st.write(f"• {element}")
    
    def _render_action_buttons(self, selected_modules: List[ModuleType], mode: str) -> Dict[str, Any]:
        """渲染操作按钮"""
        
        st.write("**操作选项**")
        
        # 验证选择
        if not selected_modules:
            st.warning("⚠️ 请至少选择一个模块后再进行操作")
            return {"action": None}
        
        if len(selected_modules) > 6:
            st.error("❌ 最多只能选择6个模块，请取消一些选择")
            return {"action": None}
        
        # 显示选择摘要
        total_time = sum(self.module_configs[m]["estimated_time"] for m in selected_modules)
        complexity_counts = {}
        
        for module in selected_modules:
            complexity = self.module_configs[module]["complexity"]
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("选择模块", len(selected_modules))
        
        with col2:
            st.metric("预计时间", f"{total_time}分钟")
        
        with col3:
            complexity_text = ", ".join([f"{k}:{v}" for k, v in complexity_counts.items()])
            st.metric("复杂度分布", complexity_text)
        
        # 操作按钮
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            if st.button("✅ 确认选择", type="primary", use_container_width=True):
                return {
                    "action": "confirm_selection",
                    "selected_modules": selected_modules,
                    "mode": mode
                }
        
        with col2:
            if st.button("🔄 重新推荐", use_container_width=True):
                return {"action": "regenerate_recommendation"}
        
        with col3:
            if st.button("💾 保存草稿", use_container_width=True):
                self._save_selection_draft(selected_modules, mode)
                st.success("草稿已保存")
        
        with col4:
            if st.button("📖 使用指南", use_container_width=True):
                return {"action": "show_usage_guide"}
        
        return {"action": None}
    
    def _show_module_details(self, module_type: ModuleType) -> None:
        """显示模块详细信息（弹窗或侧边栏）"""
        
        # 在实际实现中，这可能会打开一个模态框或侧边栏
        # 这里我们使用session state来标记显示详情
        st.session_state[f"show_module_details_{module_type.value}"] = True
    
    def render_module_guide(self) -> None:
        """渲染模块使用指南"""
        
        st.subheader("📖 A+模块使用指南")
        
        # 确保 ModuleType 在当前作用域可用
        from services.aplus_studio.models import ModuleType
        
        # 模块分类说明
        st.write("**模块分类**")
        
        categories = {
            "🎯 核心展示模块": {
                "description": "展示产品核心价值和特性的基础模块",
                "modules": [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON],
                "recommendation": "每个产品都应该包含至少一个核心展示模块"
            },
            "🏠 使用场景模块": {
                "description": "展示产品实际应用和解决方案的模块",
                "modules": [ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.INSTALLATION_GUIDE],
                "recommendation": "生活用品和功能性产品建议包含使用场景模块"
            },
            "✨ 品质保证模块": {
                "description": "突出产品品质、工艺和用户认可的模块",
                "modules": [ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
                "recommendation": "高端产品和品牌产品建议包含品质保证模块"
            },
            "📊 产品信息模块": {
                "description": "提供详细产品信息和使用指导的模块",
                "modules": [ModuleType.SIZE_COMPATIBILITY, ModuleType.PACKAGE_CONTENTS, ModuleType.MAINTENANCE_CARE],
                "recommendation": "复杂产品和需要详细说明的产品建议包含信息模块"
            }
        }
        
        for category_name, category_info in categories.items():
            with st.expander(category_name, expanded=False):
                st.write(category_info["description"])
                st.info(f"💡 **建议：** {category_info['recommendation']}")
                
                for module_type in category_info["modules"]:
                    config = self.module_configs[module_type]
                    st.write(f"**{config['icon']} {config['name']}**")
                    st.write(f"• {config['description']}")
                    st.write(f"• 复杂度: {config['complexity']} | 时间: {config['estimated_time']}分钟")
                    st.write("")
        
        # 选择建议
        st.write("**选择建议**")
        
        recommendations = [
            "🎯 **新产品发布**: 产品概览 + 功能解析 + 使用场景 + 品质保证",
            "🔧 **技术产品**: 功能解析 + 规格对比 + 安装指南 + 维护保养",
            "🏠 **家居用品**: 产品概览 + 使用场景 + 材质工艺 + 尺寸兼容",
            "🎁 **礼品套装**: 产品概览 + 包装内容 + 使用场景 + 客户评价",
            "⚡ **快速上线**: 产品概览 + 使用场景 + 品质保证 (3个简单模块)"
        ]
        
        for recommendation in recommendations:
            st.write(recommendation)
    
    def render_recommendation_summary(self) -> Dict[str, Any]:
        """渲染推荐摘要"""
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.module_recommendation:
            return {"has_recommendation": False}
        
        recommendation = session.module_recommendation
        
        return {
            "has_recommendation": True,
            "recommended_count": len(recommendation.recommended_modules),
            "selected_count": len(session.selected_modules) if session.selected_modules else 0,
            "avg_confidence": sum(recommendation.confidence_scores.values()) / len(recommendation.confidence_scores),
            "total_estimated_time": sum(self.module_configs[m]["estimated_time"] for m in recommendation.recommended_modules),
            "recommendation_timestamp": recommendation.recommendation_timestamp.isoformat() if hasattr(recommendation, 'recommendation_timestamp') else None
        }
    
    def _save_selection_draft(self, selected_modules: List[ModuleType], mode: str) -> None:
        """保存选择草稿"""
        
        try:
            draft_data = {
                "selected_modules": [m.value for m in selected_modules],
                "mode": mode,
                "saved_at": st.session_state.get("current_time", "unknown")
            }
            
            st.session_state["module_selection_draft"] = draft_data
            logger.info(f"Module selection draft saved: {len(selected_modules)} modules")
            
        except Exception as e:
            logger.error(f"Failed to save selection draft: {str(e)}")
            st.error("草稿保存失败")
    
    def load_selection_draft(self) -> Optional[Dict[str, Any]]:
        """加载选择草稿"""
        
        return st.session_state.get("module_selection_draft")
    
    def clear_selection_draft(self) -> None:
        """清除选择草稿"""
        
        if "module_selection_draft" in st.session_state:
            del st.session_state.module_selection_draft
    
    def validate_module_selection(self, selected_modules: List[ModuleType]) -> Dict[str, Any]:
        """验证模块选择"""
        
        # 确保 ModuleType 在当前作用域可用
        from services.aplus_studio.models import ModuleType
        
        errors = []
        warnings = []
        suggestions = []
        
        # 检查数量
        if not selected_modules:
            errors.append("至少需要选择一个模块")
        elif len(selected_modules) > 6:
            errors.append("最多只能选择6个模块")
        
        # 检查组合合理性
        if len(selected_modules) >= 2:
            # 检查是否有核心展示模块
            core_modules = [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON]
            has_core = any(m in selected_modules for m in core_modules)
            
            if not has_core:
                warnings.append("建议至少包含一个核心展示模块（产品概览、功能解析或规格对比）")
            
            # 检查复杂度平衡
            complexity_counts = {}
            for module in selected_modules:
                complexity = self.module_configs[module]["complexity"]
                complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            
            if complexity_counts.get("复杂", 0) > len(selected_modules) // 2:
                warnings.append("复杂模块较多，可能会增加制作时间和难度")
            
            # 时间估算
            total_time = sum(self.module_configs[m]["estimated_time"] for m in selected_modules)
            if total_time > 180:  # 3小时
                warnings.append(f"预计制作时间较长（{total_time}分钟），建议分批制作")
        
        # 提供优化建议
        if len(selected_modules) == 1:
            suggestions.append("单个模块制作快速，建议考虑添加1-2个互补模块以提升效果")
        elif len(selected_modules) >= 5:
            suggestions.append("模块数量较多，建议优先制作核心模块，其他模块可后续添加")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    def get_module_config(self, module_type: ModuleType) -> Dict[str, Any]:
        """获取模块配置信息"""
        
        return self.module_configs.get(module_type, {})
    
    def get_all_module_types(self) -> List[ModuleType]:
        """获取所有可用的模块类型"""
        
        return list(self.module_configs.keys())
    
    def get_recommended_modules_for_category(self, product_category: str) -> List[ModuleType]:
        """根据产品类别获取推荐模块"""
        
        # 确保 ModuleType 在当前作用域可用
        from services.aplus_studio.models import ModuleType
        
        # 基于产品类别的推荐逻辑
        category_recommendations = {
            "电子产品": [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON, ModuleType.INSTALLATION_GUIDE],
            "家居用品": [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.SIZE_COMPATIBILITY],
            "服装配饰": [ModuleType.PRODUCT_OVERVIEW, ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.SIZE_COMPATIBILITY, ModuleType.CUSTOMER_REVIEWS],
            "美容护理": [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.QUALITY_ASSURANCE],
            "运动户外": [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.USAGE_SCENARIOS, ModuleType.MATERIAL_CRAFTSMANSHIP],
            "汽车用品": [ModuleType.PRODUCT_OVERVIEW, ModuleType.INSTALLATION_GUIDE, ModuleType.SIZE_COMPATIBILITY, ModuleType.QUALITY_ASSURANCE],
            "母婴用品": [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
            "食品饮料": [ModuleType.PRODUCT_OVERVIEW, ModuleType.PACKAGE_CONTENTS, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
            "图书文具": [ModuleType.PRODUCT_OVERVIEW, ModuleType.PACKAGE_CONTENTS, ModuleType.USAGE_SCENARIOS, ModuleType.SIZE_COMPATIBILITY],
            "工具设备": [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.INSTALLATION_GUIDE, ModuleType.MAINTENANCE_CARE]
        }
        
        return category_recommendations.get(product_category, [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.USAGE_SCENARIOS, ModuleType.QUALITY_ASSURANCE])


# 全局实例，便于访问
def create_module_recommendation_ui(workflow_controller: IntelligentWorkflowController) -> ModuleRecommendationUI:
    """创建模块推荐UI实例"""
    return ModuleRecommendationUI(workflow_controller)
