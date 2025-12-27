"""
A+ 智能工作流导航界面组件

该模块提供工作流程导航系统，包括步骤导航组件、进度跟踪、
步骤间跳转功能、工作进度保存和恢复等功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

from services.aplus_studio.models import WorkflowState, ModuleType, GenerationStatus
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowController, IntelligentWorkflowSession
from app_utils.aplus_studio.intelligent_state_manager import IntelligentWorkflowStateManager

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    state: WorkflowState
    name: str
    icon: str
    description: str
    is_completed: bool = False
    is_current: bool = False
    is_accessible: bool = True
    completion_percentage: float = 0.0
    estimated_time: int = 0  # 预估时间（秒）
    key_data: Optional[Dict[str, Any]] = None


@dataclass
class NavigationAction:
    """导航操作"""
    action_type: str  # "next", "previous", "jump", "save", "load"
    target_state: Optional[WorkflowState] = None
    callback: Optional[Callable] = None
    confirmation_required: bool = False
    confirmation_message: str = ""


class WorkflowNavigationUI:
    """工作流导航界面组件"""
    
    def __init__(self, state_manager: IntelligentWorkflowStateManager):
        self.state_manager = state_manager
        self.workflow_controller = state_manager.workflow_controller
        
        # 步骤定义
        self.workflow_steps = self._initialize_workflow_steps()
        
        # 导航配置
        self.show_progress_bar = True
        self.show_step_details = True
        self.enable_step_jumping = True
        self.auto_save_enabled = True
        self.save_interval_seconds = 30
        
        logger.info("Workflow Navigation UI initialized")
    
    def _initialize_workflow_steps(self) -> Dict[WorkflowState, WorkflowStep]:
        """初始化工作流步骤定义"""
        steps = {
            WorkflowState.INITIAL: WorkflowStep(
                state=WorkflowState.INITIAL,
                name="开始",
                icon="🚀",
                description="开始智能工作流程",
                estimated_time=0
            ),
            WorkflowState.PRODUCT_ANALYSIS: WorkflowStep(
                state=WorkflowState.PRODUCT_ANALYSIS,
                name="产品分析",
                icon="🔍",
                description="上传产品图片，AI分析产品特性",
                estimated_time=60
            ),
            WorkflowState.MODULE_RECOMMENDATION: WorkflowStep(
                state=WorkflowState.MODULE_RECOMMENDATION,
                name="模块推荐",
                icon="🎯",
                description="AI推荐最适合的4个模块组合",
                estimated_time=10
            ),
            WorkflowState.CONTENT_GENERATION: WorkflowStep(
                state=WorkflowState.CONTENT_GENERATION,
                name="内容生成",
                icon="✍️",
                description="AI自动生成模块文案内容",
                estimated_time=30
            ),
            WorkflowState.CONTENT_EDITING: WorkflowStep(
                state=WorkflowState.CONTENT_EDITING,
                name="内容编辑",
                icon="📝",
                description="查看和编辑生成的内容",
                estimated_time=300
            ),
            WorkflowState.STYLE_SELECTION: WorkflowStep(
                state=WorkflowState.STYLE_SELECTION,
                name="风格选择",
                icon="🎨",
                description="选择统一的视觉风格主题",
                estimated_time=60
            ),
            WorkflowState.FINAL_CONFIRMATION: WorkflowStep(
                state=WorkflowState.FINAL_CONFIRMATION,
                name="最终确认",
                icon="✅",
                description="确认所有设置，准备生成",
                estimated_time=30
            ),
            WorkflowState.IMAGE_GENERATION: WorkflowStep(
                state=WorkflowState.IMAGE_GENERATION,
                name="图片生成",
                icon="🖼️",
                description="批量生成A+模块图片",
                estimated_time=180
            ),
            WorkflowState.COMPLETED: WorkflowStep(
                state=WorkflowState.COMPLETED,
                name="完成",
                icon="🎉",
                description="工作流程完成，查看结果",
                estimated_time=0
            )
        }
        return steps
    
    def render_navigation_header(self) -> Optional[NavigationAction]:
        """渲染导航头部
        
        Returns:
            NavigationAction: 用户触发的导航操作，如果没有则返回None
        """
        try:
            session = self.state_manager.get_current_session()
            if not session:
                st.warning("⚠️ 没有活跃的工作流会话")
                if st.button("🚀 开始新的工作流程", type="primary"):
                    return NavigationAction(
                        action_type="start_new",
                        target_state=WorkflowState.PRODUCT_ANALYSIS
                    )
                return None
            
            # 更新步骤状态
            self._update_step_states(session)
            
            # 渲染步骤导航
            action = self._render_step_navigation(session)
            
            # 渲染进度信息
            if self.show_progress_bar:
                self._render_progress_bar(session)
            
            # 渲染会话信息
            self._render_session_info(session)
            
            return action
            
        except Exception as e:
            logger.error(f"Error rendering navigation header: {str(e)}")
            st.error(f"导航渲染错误: {str(e)}")
            return None
    
    def _update_step_states(self, session: IntelligentWorkflowSession):
        """更新步骤状态"""
        try:
            current_state = session.current_state
            
            # 重置所有步骤状态
            for step in self.workflow_steps.values():
                step.is_current = False
                step.is_completed = False
                step.is_accessible = False
                step.completion_percentage = 0.0
                step.key_data = None
            
            # 设置当前步骤
            if current_state in self.workflow_steps:
                self.workflow_steps[current_state].is_current = True
            
            # 设置已完成和可访问的步骤
            step_order = [
                WorkflowState.INITIAL,
                WorkflowState.PRODUCT_ANALYSIS,
                WorkflowState.MODULE_RECOMMENDATION,
                WorkflowState.CONTENT_GENERATION,
                WorkflowState.CONTENT_EDITING,
                WorkflowState.STYLE_SELECTION,
                WorkflowState.FINAL_CONFIRMATION,
                WorkflowState.IMAGE_GENERATION,
                WorkflowState.COMPLETED
            ]
            
            current_index = step_order.index(current_state) if current_state in step_order else 0
            
            # 标记已完成的步骤
            for i, state in enumerate(step_order):
                if i < current_index:
                    self.workflow_steps[state].is_completed = True
                    self.workflow_steps[state].is_accessible = True
                    self.workflow_steps[state].completion_percentage = 100.0
                elif i == current_index:
                    self.workflow_steps[state].is_accessible = True
                    # 计算当前步骤的完成百分比
                    self.workflow_steps[state].completion_percentage = self._calculate_step_completion(session, state)
                elif i == current_index + 1:
                    # 下一步可能可访问（如果当前步骤有足够进度）
                    if self.workflow_steps[step_order[current_index]].completion_percentage > 50:
                        self.workflow_steps[state].is_accessible = True
            
            # 设置步骤关键数据
            self._set_step_key_data(session)
            
        except Exception as e:
            logger.error(f"Error updating step states: {str(e)}")
    
    def _calculate_step_completion(self, session: IntelligentWorkflowSession, state: WorkflowState) -> float:
        """计算步骤完成百分比"""
        try:
            if state == WorkflowState.PRODUCT_ANALYSIS:
                return 100.0 if session.product_analysis else 0.0
            
            elif state == WorkflowState.MODULE_RECOMMENDATION:
                return 100.0 if session.module_recommendation else 0.0
            
            elif state == WorkflowState.CONTENT_GENERATION:
                if not session.selected_modules:
                    return 0.0
                generated_count = len(session.module_contents)
                return (generated_count / len(session.selected_modules)) * 100.0
            
            elif state == WorkflowState.CONTENT_EDITING:
                # 基于用户编辑的数量来估算
                if not session.selected_modules:
                    return 0.0
                # 如果有用户编辑记录，认为已经开始编辑
                return 50.0 if session.user_edits else 0.0
            
            elif state == WorkflowState.STYLE_SELECTION:
                return 100.0 if session.selected_style_theme else 0.0
            
            elif state == WorkflowState.FINAL_CONFIRMATION:
                return 100.0 if session.is_ready_for_generation() else 0.0
            
            elif state == WorkflowState.IMAGE_GENERATION:
                if not session.selected_modules:
                    return 0.0
                completed_count = len(session.get_completed_modules())
                return (completed_count / len(session.selected_modules)) * 100.0
            
            elif state == WorkflowState.COMPLETED:
                return 100.0 if len(session.get_completed_modules()) == len(session.selected_modules) else 0.0
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating step completion for {state.value}: {str(e)}")
            return 0.0
    
    def _set_step_key_data(self, session: IntelligentWorkflowSession):
        """设置步骤关键数据"""
        try:
            # 产品分析步骤
            if session.product_analysis:
                self.workflow_steps[WorkflowState.PRODUCT_ANALYSIS].key_data = {
                    "product_type": session.product_analysis.product_type,
                    "category": session.product_analysis.product_category.value,
                    "confidence": f"{session.product_analysis.confidence_score:.1%}"
                }
            
            # 模块推荐步骤
            if session.module_recommendation:
                self.workflow_steps[WorkflowState.MODULE_RECOMMENDATION].key_data = {
                    "recommended_count": len(session.module_recommendation.recommended_modules),
                    "selected_count": len(session.selected_modules)
                }
            
            # 内容生成步骤
            if session.selected_modules:
                self.workflow_steps[WorkflowState.CONTENT_GENERATION].key_data = {
                    "total_modules": len(session.selected_modules),
                    "generated_modules": len(session.module_contents)
                }
            
            # 风格选择步骤
            if session.selected_style_theme:
                self.workflow_steps[WorkflowState.STYLE_SELECTION].key_data = {
                    "theme_name": session.selected_style_theme.theme_name
                }
            
            # 图片生成步骤
            if session.selected_modules:
                completed_modules = session.get_completed_modules()
                failed_modules = session.get_failed_modules()
                self.workflow_steps[WorkflowState.IMAGE_GENERATION].key_data = {
                    "total_modules": len(session.selected_modules),
                    "completed_modules": len(completed_modules),
                    "failed_modules": len(failed_modules),
                    "progress": f"{len(completed_modules)}/{len(session.selected_modules)}"
                }
            
        except Exception as e:
            logger.error(f"Error setting step key data: {str(e)}")
    
    def _render_step_navigation(self, session: IntelligentWorkflowSession) -> Optional[NavigationAction]:
        """渲染步骤导航"""
        try:
            st.markdown("### 🧭 工作流程导航")
            
            # 创建步骤导航容器
            nav_container = st.container()
            
            with nav_container:
                # 创建列布局
                cols = st.columns(len(self.workflow_steps))
                
                action = None
                
                for i, (state, step) in enumerate(self.workflow_steps.items()):
                    with cols[i]:
                        # 步骤状态样式
                        if step.is_completed:
                            status_color = "🟢"
                            status_text = "已完成"
                        elif step.is_current:
                            status_color = "🔵"
                            status_text = "进行中"
                        elif step.is_accessible:
                            status_color = "⚪"
                            status_text = "可访问"
                        else:
                            status_color = "⚫"
                            status_text = "未开始"
                        
                        # 渲染步骤卡片
                        step_html = f"""
                        <div style="
                            border: 2px solid {'#28a745' if step.is_completed else '#007bff' if step.is_current else '#6c757d'};
                            border-radius: 10px;
                            padding: 10px;
                            text-align: center;
                            background-color: {'#f8f9fa' if step.is_current else 'white'};
                            margin-bottom: 10px;
                        ">
                            <div style="font-size: 24px;">{step.icon}</div>
                            <div style="font-weight: bold; margin: 5px 0;">{step.name}</div>
                            <div style="font-size: 12px; color: #6c757d;">{status_color} {status_text}</div>
                            {f'<div style="font-size: 10px; color: #28a745;">{step.completion_percentage:.0f}%</div>' if step.completion_percentage > 0 else ''}
                        </div>
                        """
                        
                        st.markdown(step_html, unsafe_allow_html=True)
                        
                        # 步骤跳转按钮
                        if self.enable_step_jumping and step.is_accessible and not step.is_current:
                            if st.button(f"跳转到{step.name}", key=f"jump_to_{state.value}"):
                                action = NavigationAction(
                                    action_type="jump",
                                    target_state=state,
                                    confirmation_required=True,
                                    confirmation_message=f"确定要跳转到\"{step.name}\"步骤吗？当前进度将被保存。"
                                )
                                # 立即返回action，不要继续循环
                                return action
                        
                        # 显示步骤详细信息
                        if self.show_step_details and step.key_data:
                            with st.expander(f"📊 {step.name}详情", expanded=False):
                                for key, value in step.key_data.items():
                                    st.text(f"{key}: {value}")
                
                return action
                
        except Exception as e:
            logger.error(f"Error rendering step navigation: {str(e)}")
            st.error(f"步骤导航渲染错误: {str(e)}")
            return None
    
    def _render_progress_bar(self, session: IntelligentWorkflowSession):
        """渲染进度条"""
        try:
            # 计算整体进度
            total_progress = self._calculate_overall_progress(session)
            
            st.markdown("#### 📈 整体进度")
            
            # 进度条
            progress_bar = st.progress(total_progress / 100.0)
            
            # 进度文本
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("整体进度", f"{total_progress:.1f}%")
            
            with col2:
                if session.selected_modules:
                    completed_count = len(session.get_completed_modules())
                    total_count = len(session.selected_modules)
                    st.metric("模块进度", f"{completed_count}/{total_count}")
                else:
                    st.metric("模块进度", "0/0")
            
            with col3:
                # 预估剩余时间
                remaining_time = self._estimate_remaining_time(session)
                if remaining_time > 0:
                    if remaining_time < 60:
                        time_text = f"{remaining_time:.0f}秒"
                    elif remaining_time < 3600:
                        time_text = f"{remaining_time/60:.0f}分钟"
                    else:
                        time_text = f"{remaining_time/3600:.1f}小时"
                    st.metric("预估剩余", time_text)
                else:
                    st.metric("预估剩余", "已完成")
            
        except Exception as e:
            logger.error(f"Error rendering progress bar: {str(e)}")
    
    def _calculate_overall_progress(self, session: IntelligentWorkflowSession) -> float:
        """计算整体进度百分比"""
        try:
            # 步骤权重
            step_weights = {
                WorkflowState.PRODUCT_ANALYSIS: 15,
                WorkflowState.MODULE_RECOMMENDATION: 10,
                WorkflowState.CONTENT_GENERATION: 20,
                WorkflowState.CONTENT_EDITING: 15,
                WorkflowState.STYLE_SELECTION: 10,
                WorkflowState.FINAL_CONFIRMATION: 5,
                WorkflowState.IMAGE_GENERATION: 20,
                WorkflowState.COMPLETED: 5
            }
            
            total_weight = sum(step_weights.values())
            weighted_progress = 0.0
            
            for state, weight in step_weights.items():
                if state in self.workflow_steps:
                    step_progress = self.workflow_steps[state].completion_percentage
                    weighted_progress += (step_progress * weight) / total_weight
            
            return min(weighted_progress, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating overall progress: {str(e)}")
            return 0.0
    
    def _estimate_remaining_time(self, session: IntelligentWorkflowSession) -> float:
        """预估剩余时间（秒）"""
        try:
            remaining_time = 0.0
            current_state = session.current_state
            
            # 获取步骤顺序
            step_order = [
                WorkflowState.PRODUCT_ANALYSIS,
                WorkflowState.MODULE_RECOMMENDATION,
                WorkflowState.CONTENT_GENERATION,
                WorkflowState.CONTENT_EDITING,
                WorkflowState.STYLE_SELECTION,
                WorkflowState.FINAL_CONFIRMATION,
                WorkflowState.IMAGE_GENERATION,
                WorkflowState.COMPLETED
            ]
            
            current_index = step_order.index(current_state) if current_state in step_order else 0
            
            # 计算当前步骤剩余时间
            if current_state in self.workflow_steps:
                current_step = self.workflow_steps[current_state]
                current_progress = current_step.completion_percentage
                if current_progress < 100:
                    remaining_progress = (100 - current_progress) / 100.0
                    remaining_time += current_step.estimated_time * remaining_progress
            
            # 计算后续步骤时间
            for i in range(current_index + 1, len(step_order)):
                state = step_order[i]
                if state in self.workflow_steps:
                    remaining_time += self.workflow_steps[state].estimated_time
            
            return remaining_time
            
        except Exception as e:
            logger.error(f"Error estimating remaining time: {str(e)}")
            return 0.0
    
    def _render_session_info(self, session: IntelligentWorkflowSession):
        """渲染会话信息"""
        try:
            with st.expander("📋 会话信息", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text(f"会话ID: {session.session_id}")
                    st.text(f"创建时间: {session.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.text(f"最后更新: {session.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    st.text(f"当前状态: {session.current_state.value}")
                    if session.selected_modules:
                        module_names = [m.value for m in session.selected_modules]
                        st.text(f"选定模块: {', '.join(module_names)}")
                    
                    # 会话操作按钮
                    if st.button("💾 保存会话", key="save_session"):
                        self.state_manager.save_current_session_to_history()
                        st.success("会话已保存到历史记录")
                        st.rerun()
            
        except Exception as e:
            logger.error(f"Error rendering session info: {str(e)}")
    
    def render_navigation_actions(self) -> Optional[NavigationAction]:
        """渲染导航操作按钮
        
        Returns:
            NavigationAction: 用户触发的导航操作
        """
        try:
            session = self.state_manager.get_current_session()
            if not session:
                return None
            
            st.markdown("---")
            
            # 创建操作按钮布局
            col1, col2, col3, col4 = st.columns(4)
            
            action = None
            current_state = session.current_state
            
            # 上一步按钮
            with col1:
                if self._can_go_previous(current_state):
                    if st.button("⬅️ 上一步", key="nav_previous"):
                        previous_state = self._get_previous_state(current_state)
                        if previous_state:
                            action = NavigationAction(
                                action_type="previous",
                                target_state=previous_state,
                                confirmation_required=True,
                                confirmation_message="确定要返回上一步吗？当前进度将被保存。"
                            )
            
            # 下一步按钮
            with col2:
                if self._can_go_next(session, current_state):
                    if st.button("➡️ 下一步", key="nav_next"):
                        next_state = self._get_next_state(current_state)
                        if next_state:
                            action = NavigationAction(
                                action_type="next",
                                target_state=next_state
                            )
            
            # 保存进度按钮
            with col3:
                if st.button("💾 保存进度", key="nav_save"):
                    action = NavigationAction(action_type="save")
            
            # 重新开始按钮
            with col4:
                if st.button("🔄 重新开始", key="nav_restart"):
                    action = NavigationAction(
                        action_type="restart",
                        target_state=WorkflowState.INITIAL,
                        confirmation_required=True,
                        confirmation_message="确定要重新开始吗？当前所有进度将被清除。"
                    )
            
            return action
            
        except Exception as e:
            logger.error(f"Error rendering navigation actions: {str(e)}")
            return None
    
    def _can_go_previous(self, current_state: WorkflowState) -> bool:
        """检查是否可以返回上一步"""
        return current_state != WorkflowState.INITIAL
    
    def _can_go_next(self, session: IntelligentWorkflowSession, current_state: WorkflowState) -> bool:
        """检查是否可以进入下一步"""
        if current_state == WorkflowState.COMPLETED:
            return False
        
        # 检查当前步骤是否满足进入下一步的条件
        if current_state == WorkflowState.PRODUCT_ANALYSIS:
            return session.product_analysis is not None
        elif current_state == WorkflowState.MODULE_RECOMMENDATION:
            return session.module_recommendation is not None and len(session.selected_modules) > 0
        elif current_state == WorkflowState.CONTENT_GENERATION:
            return len(session.module_contents) > 0
        elif current_state == WorkflowState.CONTENT_EDITING:
            return len(session.module_contents) == len(session.selected_modules)
        elif current_state == WorkflowState.STYLE_SELECTION:
            return session.selected_style_theme is not None
        elif current_state == WorkflowState.FINAL_CONFIRMATION:
            return session.is_ready_for_generation()
        elif current_state == WorkflowState.IMAGE_GENERATION:
            return len(session.get_completed_modules()) == len(session.selected_modules)
        
        return True
    
    def _get_previous_state(self, current_state: WorkflowState) -> Optional[WorkflowState]:
        """获取上一个状态"""
        state_order = [
            WorkflowState.INITIAL,
            WorkflowState.PRODUCT_ANALYSIS,
            WorkflowState.MODULE_RECOMMENDATION,
            WorkflowState.CONTENT_GENERATION,
            WorkflowState.CONTENT_EDITING,
            WorkflowState.STYLE_SELECTION,
            WorkflowState.FINAL_CONFIRMATION,
            WorkflowState.IMAGE_GENERATION,
            WorkflowState.COMPLETED
        ]
        
        try:
            current_index = state_order.index(current_state)
            if current_index > 0:
                return state_order[current_index - 1]
        except ValueError:
            pass
        
        return None
    
    def _get_next_state(self, current_state: WorkflowState) -> Optional[WorkflowState]:
        """获取下一个状态"""
        state_order = [
            WorkflowState.INITIAL,
            WorkflowState.PRODUCT_ANALYSIS,
            WorkflowState.MODULE_RECOMMENDATION,
            WorkflowState.CONTENT_GENERATION,
            WorkflowState.CONTENT_EDITING,
            WorkflowState.STYLE_SELECTION,
            WorkflowState.FINAL_CONFIRMATION,
            WorkflowState.IMAGE_GENERATION,
            WorkflowState.COMPLETED
        ]
        
        try:
            current_index = state_order.index(current_state)
            if current_index < len(state_order) - 1:
                return state_order[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def handle_navigation_action(self, action: NavigationAction) -> bool:
        """处理导航操作
        
        Args:
            action: 导航操作
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if action.confirmation_required:
                # 显示确认对话框
                if not st.session_state.get(f"confirm_{action.action_type}", False):
                    st.warning(action.confirmation_message)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("确认", key=f"confirm_{action.action_type}_yes"):
                            st.session_state[f"confirm_{action.action_type}"] = True
                            st.rerun()
                    with col2:
                        if st.button("取消", key=f"confirm_{action.action_type}_no"):
                            return False
                    return False
                else:
                    # 清除确认状态
                    st.session_state[f"confirm_{action.action_type}"] = False
            
            # 执行操作
            if action.action_type == "jump" or action.action_type == "next" or action.action_type == "previous":
                if action.target_state:
                    success = self.state_manager.transition_workflow_state(action.target_state)
                    if success:
                        st.success(f"已跳转到{self.workflow_steps[action.target_state].name}步骤")
                        st.rerun()
                    else:
                        st.error("状态转换失败")
                    return success
            
            elif action.action_type == "save":
                self.state_manager.save_current_session_to_history()
                st.success("进度已保存")
                return True
            
            elif action.action_type == "restart":
                self.state_manager.clear_current_session()
                self.state_manager.create_new_session()
                st.success("已重新开始工作流程")
                st.rerun()
                return True
            
            elif action.action_type == "start_new":
                if action.target_state:
                    session = self.state_manager.create_new_session()
                    success = self.state_manager.transition_workflow_state(action.target_state)
                    if success:
                        st.success("新的工作流程已开始")
                        st.rerun()
                    return success
            
            # 执行回调函数
            if action.callback:
                return action.callback()
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling navigation action: {str(e)}")
            st.error(f"导航操作失败: {str(e)}")
            return False
    
    def render_session_history_sidebar(self):
        """在侧边栏渲染会话历史"""
        try:
            with st.sidebar:
                st.markdown("### 📚 会话历史")
                
                history = self.state_manager.get_session_history()
                
                if not history:
                    st.info("暂无历史会话")
                    return
                
                for session in history[:10]:  # 显示最近10个会话
                    with st.expander(f"🗂️ {session.session_id[:8]}...", expanded=False):
                        st.text(f"状态: {session.current_state.value}")
                        st.text(f"创建: {session.creation_time.strftime('%m-%d %H:%M')}")
                        st.text(f"更新: {session.last_updated.strftime('%m-%d %H:%M')}")
                        
                        if session.selected_modules:
                            st.text(f"模块: {len(session.selected_modules)}个")
                        
                        progress = session.get_progress_percentage()
                        st.text(f"进度: {progress:.1f}%")
                        
                        if st.button(f"加载", key=f"load_{session.session_id}"):
                            loaded_session = self.state_manager.load_session_from_history(session.session_id)
                            if loaded_session:
                                st.success("会话已加载")
                                st.rerun()
                            else:
                                st.error("会话加载失败")
                
        except Exception as e:
            logger.error(f"Error rendering session history sidebar: {str(e)}")
