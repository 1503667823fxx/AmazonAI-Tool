"""
A+ 智能工作流简化状态管理器

简化版本：删除复杂的持久化、备份、恢复等过度工程功能
保留基本的状态管理，直接使用 session_state
"""

import streamlit as st
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from services.aplus_studio.models import WorkflowState, ModuleType

logger = logging.getLogger(__name__)


class SimpleWorkflowStateManager:
    """简化的工作流状态管理器"""
    
    def __init__(self):
        self._init_session_state()
        logger.info("Simple Workflow State Manager initialized")
    
    def _init_session_state(self):
        """初始化基本的会话状态"""
        # 基本工作流状态
        if 'workflow_current_state' not in st.session_state:
            st.session_state.workflow_current_state = WorkflowState.INITIAL
        
        # 工作流数据
        if 'workflow_data' not in st.session_state:
            st.session_state.workflow_data = {}
    
    def get_current_state(self) -> WorkflowState:
        """获取当前工作流状态"""
        return st.session_state.get('workflow_current_state', WorkflowState.INITIAL)
    
    def set_current_state(self, state: WorkflowState):
        """设置当前工作流状态"""
        st.session_state.workflow_current_state = state
        logger.info(f"Workflow state changed to: {state.value}")
    
    def get_workflow_data(self, key: str, default=None):
        """获取工作流数据"""
        return st.session_state.workflow_data.get(key, default)
    
    def set_workflow_data(self, key: str, value: Any):
        """设置工作流数据"""
        st.session_state.workflow_data[key] = value
    
    def clear_workflow_data(self):
        """清除所有工作流数据"""
        st.session_state.workflow_data = {}
        st.session_state.workflow_current_state = WorkflowState.INITIAL
        logger.info("Workflow data cleared")
    
    # 便捷方法
    def get_analysis_result(self):
        """获取分析结果"""
        return self.get_workflow_data('analysis_result')
    
    def set_analysis_result(self, result):
        """设置分析结果"""
        self.set_workflow_data('analysis_result', result)
    
    def get_module_recommendation(self):
        """获取模块推荐"""
        return self.get_workflow_data('module_recommendation')
    
    def set_module_recommendation(self, recommendation):
        """设置模块推荐"""
        self.set_workflow_data('module_recommendation', recommendation)
    
    def get_selected_modules(self) -> List[ModuleType]:
        """获取选中的模块"""
        modules = self.get_workflow_data('selected_modules', [])
        if modules and isinstance(modules[0], str):
            return [ModuleType(m) for m in modules]
        return modules
    
    def set_selected_modules(self, modules: List[ModuleType]):
        """设置选中的模块"""
        # 存储为字符串以便序列化
        self.set_workflow_data('selected_modules', [m.value for m in modules])
    
    def get_generated_content(self):
        """获取生成的内容"""
        return self.get_workflow_data('generated_content', {})
    
    def set_generated_content(self, content):
        """设置生成的内容"""
        self.set_workflow_data('generated_content', content)
    
    def get_final_content(self):
        """获取最终内容"""
        return self.get_workflow_data('final_content', {})
    
    def set_final_content(self, content):
        """设置最终内容"""
        self.set_workflow_data('final_content', content)
    
    def get_style_theme(self):
        """获取风格主题"""
        return self.get_workflow_data('style_theme')
    
    def set_style_theme(self, theme):
        """设置风格主题"""
        self.set_workflow_data('style_theme', theme)
    
    def get_generated_images(self):
        """获取生成的图片"""
        return self.get_workflow_data('generated_images', {})
    
    def set_generated_images(self, images):
        """设置生成的图片"""
        # 简化版本：直接存储，不做复杂的序列化处理
        self.set_workflow_data('generated_images', images)
    
    def transition_workflow_state(self, target_state: WorkflowState) -> bool:
        """转换工作流状态"""
        try:
            current_state = self.get_current_state()
            logger.info(f"Transitioning from {current_state.value} to {target_state.value}")
            
            # 简化版本：直接设置状态，不做复杂验证
            self.set_current_state(target_state)
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition workflow state: {str(e)}")
            return False
    
    def has_active_session(self) -> bool:
        """检查是否有活跃会话"""
        return bool(st.session_state.workflow_data)
    
    def get_workflow_progress(self) -> Dict[str, Any]:
        """获取工作流进度"""
        current_state = self.get_current_state()
        
        # 定义状态顺序
        states = [
            WorkflowState.INITIAL,
            WorkflowState.PRODUCT_ANALYSIS,
            WorkflowState.MODULE_RECOMMENDATION,
            WorkflowState.CONTENT_GENERATION,
            WorkflowState.CONTENT_EDITING,
            WorkflowState.STYLE_SELECTION,
            WorkflowState.IMAGE_GENERATION,
            WorkflowState.COMPLETED
        ]
        
        try:
            current_index = states.index(current_state)
        except ValueError:
            current_index = 0
        
        return {
            'current_state': current_state,
            'current_index': current_index,
            'total_steps': len(states),
            'progress_percentage': (current_index / (len(states) - 1)) * 100 if len(states) > 1 else 0,
            'completed_steps': states[:current_index + 1],
            'remaining_steps': states[current_index + 1:]
        }


# 为了兼容性，创建一个别名
IntelligentWorkflowStateManager = SimpleWorkflowStateManager