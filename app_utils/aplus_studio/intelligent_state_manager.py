"""
A+ 智能工作流状态管理器

该模块管理智能工作流的会话状态，包括持久化存储、状态恢复和数据完整性验证。
支持浏览器刷新后的状态恢复和自动备份功能。
"""

import streamlit as st
import json
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from services.aplus_studio.intelligent_workflow import (
    IntelligentWorkflowSession, IntelligentWorkflowController,
    ProductAnalysis, ModuleRecommendation,
    ModuleContent, StyleThemeConfig, ComplianceResult
)
from services.aplus_studio.models import (
    WorkflowState, ProductCategory, ModuleType, Priority,
    GenerationStatus, GenerationResult
)

logger = logging.getLogger(__name__)


class IntelligentWorkflowStateManager:
    """智能工作流状态管理器"""
    
    def __init__(self):
        self.session_timeout_hours = 24
        self.max_history_sessions = 15
        self.auto_save_enabled = True
        self.backup_interval_minutes = 3
        
        # 初始化工作流控制器
        self.workflow_controller = IntelligentWorkflowController()
        
        # 设置双向引用
        self.workflow_controller.state_manager = self
        
        self._init_session_state()
        self._setup_auto_backup()
        
        logger.info("Intelligent Workflow State Manager initialized")
    
    def _init_session_state(self):
        """初始化Streamlit会话状态"""
        try:
            # 智能工作流相关状态
            if 'intelligent_workflow_session' not in st.session_state:
                st.session_state.intelligent_workflow_session = None
            
            if 'intelligent_workflow_history' not in st.session_state:
                st.session_state.intelligent_workflow_history = []
            
            if 'intelligent_workflow_backup' not in st.session_state:
                st.session_state.intelligent_workflow_backup = None
            
            if 'intelligent_workflow_last_backup' not in st.session_state:
                st.session_state.intelligent_workflow_last_backup = None
            
            if 'intelligent_workflow_recovery_data' not in st.session_state:
                st.session_state.intelligent_workflow_recovery_data = {}
            
            # 用户编辑缓存
            if 'intelligent_workflow_user_edits' not in st.session_state:
                st.session_state.intelligent_workflow_user_edits = {}
            
            # 临时数据存储
            if 'intelligent_workflow_temp_data' not in st.session_state:
                st.session_state.intelligent_workflow_temp_data = {}
            
            # 尝试从备份恢复
            self._attempt_session_recovery()
            
            logger.info("Intelligent workflow session state initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize intelligent workflow session state: {str(e)}")
            # 确保基本状态存在
            st.session_state.intelligent_workflow_session = None
            st.session_state.intelligent_workflow_history = []
    
    def _setup_auto_backup(self):
        """设置自动备份"""
        try:
            if self.auto_save_enabled:
                last_backup = st.session_state.get('intelligent_workflow_last_backup')
                if last_backup:
                    last_backup_time = datetime.fromisoformat(last_backup)
                    if datetime.now() - last_backup_time > timedelta(minutes=self.backup_interval_minutes):
                        self._create_session_backup()
                else:
                    self._create_session_backup()
        except Exception as e:
            logger.warning(f"Auto backup setup failed: {str(e)}")
    
    def _attempt_session_recovery(self):
        """尝试从备份恢复会话"""
        try:
            backup_data = st.session_state.get('intelligent_workflow_backup')
            if backup_data and not st.session_state.get('intelligent_workflow_session'):
                logger.info("Attempting to recover intelligent workflow session from backup")
                
                recovered_session = self._deserialize_session(backup_data)
                if recovered_session and self._validate_recovered_session(recovered_session):
                    st.session_state.intelligent_workflow_session = recovered_session
                    self.workflow_controller.load_session(recovered_session)
                    logger.info(f"Successfully recovered intelligent workflow session: {recovered_session.session_id}")
                    
                    if hasattr(st, 'success'):
                        st.success("已从上次智能工作流会话恢复数据")
                else:
                    logger.warning("Intelligent workflow session recovery validation failed")
                    
        except Exception as e:
            logger.error(f"Intelligent workflow session recovery failed: {str(e)}")
    
    def _validate_recovered_session(self, session: IntelligentWorkflowSession) -> bool:
        """验证恢复的会话是否有效"""
        try:
            if not session.session_id or not session.creation_time:
                return False
            
            # 检查会话是否过期
            if datetime.now() - session.creation_time > timedelta(hours=self.session_timeout_hours):
                logger.info(f"Recovered intelligent workflow session {session.session_id} is expired")
                return False
            
            # 检查状态有效性
            if not isinstance(session.current_state, WorkflowState):
                return False
            
            # 验证数据完整性
            if not hasattr(session, 'generation_status') or not isinstance(session.generation_status, dict):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Intelligent workflow session validation failed: {str(e)}")
            return False
    
    def create_new_session(self, session_id: Optional[str] = None) -> IntelligentWorkflowSession:
        """创建新的智能工作流会话"""
        try:
            # 保存当前会话到历史
            if self.has_active_session():
                self.save_current_session_to_history()
            
            # 创建新会话
            session = self.workflow_controller.create_new_session(session_id)
            
            # 保存到状态
            st.session_state.intelligent_workflow_session = session
            
            # 创建初始备份
            self._create_session_backup()
            
            logger.info(f"Created new intelligent workflow session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create new intelligent workflow session: {str(e)}")
            raise
    
    def get_current_session(self) -> Optional[IntelligentWorkflowSession]:
        """获取当前会话"""
        try:
            session = st.session_state.get('intelligent_workflow_session')
            logger.debug(f"get_current_session: session from st.session_state: {session is not None}")
            
            if session:
                logger.debug(f"Found session: {session.session_id}, state: {session.current_state.value}")
            
            # 如果没有会话但有备份，尝试恢复
            if not session:
                logger.debug("No session found, checking for backup")
                backup_data = st.session_state.get('intelligent_workflow_backup')
                if backup_data:
                    logger.debug("Backup data found, attempting recovery")
                    session = self._deserialize_session(backup_data)
                    if session and self._validate_recovered_session(session):
                        logger.info(f"Auto-recovered session from backup: {session.session_id}")
                        st.session_state.intelligent_workflow_session = session
                        self.workflow_controller.load_session(session)
                        logger.info("Auto-recovered intelligent workflow session from backup")
                    else:
                        logger.warning("Session recovery from backup failed")
                else:
                    logger.debug("No backup data available")
            
            # 验证会话完整性
            if session and not self._validate_session_integrity(session):
                logger.warning("Current intelligent workflow session failed integrity check")
                return None
            
            return session
            
        except Exception as e:
            logger.error(f"Error getting current intelligent workflow session: {str(e)}")
            return None
    
    def _validate_session_integrity(self, session: IntelligentWorkflowSession) -> bool:
        """验证会话完整性"""
        try:
            if not session or not session.session_id:
                return False
            
            # 检查会话是否过期
            if datetime.now() - session.creation_time > timedelta(hours=self.session_timeout_hours):
                return False
            
            # 检查必需的属性
            required_attrs = ['current_state', 'creation_time', 'last_updated', 'generation_status']
            for attr in required_attrs:
                if not hasattr(session, attr):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Intelligent workflow session integrity validation failed: {str(e)}")
            return False
    
    def has_active_session(self) -> bool:
        """检查是否有活跃会话"""
        return st.session_state.get('intelligent_workflow_session') is not None
    
    def get_current_state(self) -> WorkflowState:
        """获取当前工作流状态"""
        try:
            session = self.get_current_session()
            if session:
                current_state = session.current_state
                logger.debug(f"get_current_state returning: {current_state.value}")
                return current_state
            else:
                # 如果没有会话，返回初始状态
                logger.debug("get_current_state: no session found, returning INITIAL")
                return WorkflowState.INITIAL
        except Exception as e:
            logger.error(f"Failed to get current workflow state: {str(e)}")
            return WorkflowState.INITIAL
    
    def transition_to_state(self, target_state: WorkflowState) -> bool:
        """转换到指定状态"""
        try:
            session = self.get_current_session()
            if not session:
                # 如果没有会话，创建新会话
                session = self.create_new_session()
            
            # 更新状态
            session.update_state(target_state)
            self._save_session(session)
            
            logger.info(f"Transitioned to state: {target_state.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition to state {target_state.value}: {str(e)}")
            return False
    
    # 便捷方法用于主应用调用
    def set_analysis_result(self, analysis_result):
        """设置分析结果"""
        try:
            session = self.get_current_session()
            if session:
                # 这里应该转换为ProductAnalysis对象，暂时存储原始数据
                session.workflow_metadata['analysis_result'] = analysis_result
                self._save_session(session)
        except Exception as e:
            logger.error(f"Failed to set analysis result: {str(e)}")
    
    def get_analysis_result(self):
        """获取分析结果"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('analysis_result')
            return None
        except Exception as e:
            logger.error(f"Failed to get analysis result: {str(e)}")
            return None
    
    def set_module_recommendation(self, recommendation):
        """设置模块推荐"""
        try:
            session = self.get_current_session()
            if session:
                # 验证推荐数据结构
                if isinstance(recommendation, dict):
                    logger.debug(f"Saving module recommendation with keys: {list(recommendation.keys())}")
                    
                    # 处理ModuleType对象，转换为字符串以便序列化
                    processed_recommendation = {}
                    for key, value in recommendation.items():
                        if key == 'selected_modules' and isinstance(value, list):
                            # 转换ModuleType对象为字符串
                            processed_recommendation[key] = [
                                m.value if hasattr(m, 'value') else str(m) for m in value
                            ]
                            logger.debug(f"Processed selected_modules: {processed_recommendation[key]}")
                        elif key in ['recommended_modules', 'alternative_modules'] and isinstance(value, list):
                            # 转换ModuleType对象为字符串
                            processed_recommendation[key] = [
                                m.value if hasattr(m, 'value') else str(m) for m in value
                            ]
                        else:
                            processed_recommendation[key] = value
                    
                    session.workflow_metadata['module_recommendation'] = processed_recommendation
                else:
                    session.workflow_metadata['module_recommendation'] = recommendation
                
                self._save_session(session)
                logger.info("Module recommendation saved successfully")
        except Exception as e:
            logger.error(f"Failed to set module recommendation: {str(e)}")
            # 重新抛出异常以便上层处理
            raise
    
    def get_module_recommendation(self):
        """获取模块推荐"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('module_recommendation')
            return None
        except Exception as e:
            logger.error(f"Failed to get module recommendation: {str(e)}")
            return None
    
    def set_generated_content(self, content):
        """设置生成的内容"""
        try:
            session = self.get_current_session()
            if session:
                session.workflow_metadata['generated_content'] = content
                self._save_session(session)
        except Exception as e:
            logger.error(f"Failed to set generated content: {str(e)}")
    
    def get_generated_content(self):
        """获取生成的内容"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('generated_content')
            return None
        except Exception as e:
            logger.error(f"Failed to get generated content: {str(e)}")
            return None
    
    def set_final_content(self, content):
        """设置最终内容"""
        try:
            session = self.get_current_session()
            if session:
                session.workflow_metadata['final_content'] = content
                self._save_session(session)
        except Exception as e:
            logger.error(f"Failed to set final content: {str(e)}")
    
    def get_final_content(self):
        """获取最终内容"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('final_content')
            return None
        except Exception as e:
            logger.error(f"Failed to get final content: {str(e)}")
            return None
    
    def set_style_theme(self, theme):
        """设置风格主题"""
        try:
            session = self.get_current_session()
            if session:
                session.workflow_metadata['style_theme'] = theme
                self._save_session(session)
        except Exception as e:
            logger.error(f"Failed to set style theme: {str(e)}")
    
    def get_style_theme(self):
        """获取风格主题"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('style_theme')
            return None
        except Exception as e:
            logger.error(f"Failed to get style theme: {str(e)}")
            return None
    
    def set_generated_images(self, images):
        """设置生成的图片"""
        try:
            session = self.get_current_session()
            if session:
                session.workflow_metadata['generated_images'] = images
                self._save_session(session)
        except Exception as e:
            logger.error(f"Failed to set generated images: {str(e)}")
    
    def get_generated_images(self):
        """获取生成的图片"""
        try:
            session = self.get_current_session()
            if session:
                return session.workflow_metadata.get('generated_images')
            return None
        except Exception as e:
            logger.error(f"Failed to get generated images: {str(e)}")
            return None
    
    def reset_workflow(self):
        """重置工作流"""
        try:
            self.clear_current_session()
            # 创建新会话
            self.create_new_session()
        except Exception as e:
            logger.error(f"Failed to reset workflow: {str(e)}")
    
    def update_product_analysis(self, product_analysis: ProductAnalysis):
        """更新产品分析结果"""
        try:
            session = self.get_current_session()
            if session:
                session.product_analysis = product_analysis
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info("Product analysis updated in intelligent workflow")
        except Exception as e:
            logger.error(f"Failed to update product analysis: {str(e)}")
            raise
    
    def update_module_recommendation(self, recommendation: ModuleRecommendation):
        """更新模块推荐结果"""
        try:
            session = self.get_current_session()
            if session:
                session.module_recommendation = recommendation
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info("Module recommendation updated in intelligent workflow")
        except Exception as e:
            logger.error(f"Failed to update module recommendation: {str(e)}")
            raise
    
    def update_selected_modules(self, selected_modules: List[ModuleType]):
        """更新选定的模块"""
        try:
            session = self.get_current_session()
            if session:
                # 清除旧的选择
                session.selected_modules.clear()
                session.generation_status.clear()
                
                # 添加新的选择
                for module_type in selected_modules:
                    session.add_selected_module(module_type)
                
                session.last_updated = datetime.now()
                self._save_session(session)
                
                # 触发自动保存（如果启用）
                if hasattr(self, 'save_on_module_selection') and getattr(self, 'save_on_module_selection', True):
                    self._create_session_backup()
                    logger.debug("Auto-save triggered by module selection")
                
                logger.info(f"Selected modules updated: {[m.value for m in selected_modules]}")
        except Exception as e:
            logger.error(f"Failed to update selected modules: {str(e)}")
            raise
    
    def update_module_content(self, module_type: ModuleType, content: ModuleContent):
        """更新模块内容"""
        try:
            session = self.get_current_session()
            if session:
                session.module_contents[module_type] = content
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info(f"Module content updated for {module_type.value}")
        except Exception as e:
            logger.error(f"Failed to update module content: {str(e)}")
            raise
    
    def update_style_theme(self, style_theme: StyleThemeConfig):
        """更新风格主题"""
        try:
            session = self.get_current_session()
            if session:
                session.selected_style_theme = style_theme
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info(f"Style theme updated: {style_theme.theme_name}")
        except Exception as e:
            logger.error(f"Failed to update style theme: {str(e)}")
            raise
    
    def update_compliance_result(self, module_type: ModuleType, compliance_result: ComplianceResult):
        """更新合规检查结果"""
        try:
            session = self.get_current_session()
            if session:
                session.compliance_results[module_type] = compliance_result
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info(f"Compliance result updated for {module_type.value}")
        except Exception as e:
            logger.error(f"Failed to update compliance result: {str(e)}")
            raise
    
    def update_generation_status(self, module_type: ModuleType, status: GenerationStatus):
        """更新生成状态"""
        try:
            session = self.get_current_session()
            if session:
                old_status = session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
                session.generation_status[module_type] = status
                session.last_updated = datetime.now()
                
                self._save_session(session)
                logger.info(f"Generation status updated for {module_type.value}: {old_status.value} -> {status.value}")
        except Exception as e:
            logger.error(f"Failed to update generation status: {str(e)}")
            raise
    
    def update_generation_result(self, module_type: ModuleType, result: GenerationResult):
        """更新生成结果"""
        try:
            session = self.get_current_session()
            if session:
                session.generation_results[module_type] = result
                session.generation_status[module_type] = GenerationStatus.COMPLETED
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info(f"Generation result updated for {module_type.value}")
        except Exception as e:
            logger.error(f"Failed to update generation result: {str(e)}")
            raise
    
    def transition_workflow_state(self, target_state: WorkflowState) -> bool:
        """转换工作流状态"""
        try:
            logger.info(f"Starting workflow state transition to: {target_state.value}")
            
            session = self.get_current_session()
            if not session:
                logger.error("No active session for workflow state transition")
                return False
            
            logger.debug(f"Current session state: {session.current_state.value}")
            logger.debug(f"Session ID: {session.session_id}")
            
            success = self.workflow_controller.transition_to_state(target_state)
            logger.debug(f"Workflow controller transition result: {success}")
            
            if success:
                # 更新会话状态
                logger.debug("Updating session state in st.session_state")
                st.session_state.intelligent_workflow_session = self.workflow_controller.current_session
                
                logger.debug("Saving session")
                self._save_session(session)
                
                # 触发自动保存（如果启用）
                if hasattr(self, 'save_on_state_change') and getattr(self, 'save_on_state_change', True):
                    logger.debug("Creating session backup")
                    self._create_session_backup()
                    logger.debug(f"Auto-save triggered by state transition to {target_state.value}")
                
                logger.info(f"Workflow state transition completed successfully: {target_state.value}")
            else:
                logger.error(f"Workflow controller transition failed for: {target_state.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to transition workflow state: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return False
    
    def save_user_edit(self, edit_key: str, edit_value: Any):
        """保存用户编辑"""
        try:
            session = self.get_current_session()
            if session:
                session.user_edits[edit_key] = edit_value
                session.last_updated = datetime.now()
                
                # 同时保存到临时编辑缓存
                user_edits = st.session_state.get('intelligent_workflow_user_edits', {})
                user_edits[edit_key] = edit_value
                st.session_state.intelligent_workflow_user_edits = user_edits
                
                self._save_session(session)
                
                # 触发自动保存（如果启用）
                if hasattr(self, 'save_on_content_edit') and getattr(self, 'save_on_content_edit', True):
                    self._create_session_backup()
                    logger.debug(f"Auto-save triggered by user edit: {edit_key}")
                
                logger.debug(f"User edit saved: {edit_key}")
        except Exception as e:
            logger.error(f"Failed to save user edit: {str(e)}")
    
    def get_user_edit(self, edit_key: str, default_value: Any = None) -> Any:
        """获取用户编辑"""
        try:
            session = self.get_current_session()
            if session:
                return session.user_edits.get(edit_key, default_value)
            
            # 从临时缓存获取
            user_edits = st.session_state.get('intelligent_workflow_user_edits', {})
            return user_edits.get(edit_key, default_value)
            
        except Exception as e:
            logger.error(f"Failed to get user edit: {str(e)}")
            return default_value
    
    def _save_session(self, session: IntelligentWorkflowSession):
        """保存会话到状态"""
        try:
            logger.debug(f"Saving session to st.session_state: {session.session_id}")
            logger.debug(f"Session state being saved: {session.current_state.value}")
            
            st.session_state.intelligent_workflow_session = session
            
            # 验证保存是否成功
            saved_session = st.session_state.get('intelligent_workflow_session')
            if saved_session:
                logger.debug(f"Session saved successfully, state: {saved_session.current_state.value}")
            else:
                logger.error("Session save failed - session not found in st.session_state")
            
            # 自动备份
            if self.auto_save_enabled:
                logger.debug("Creating automatic backup")
                self._create_session_backup()
                
        except Exception as e:
            logger.error(f"Failed to save intelligent workflow session: {str(e)}")
            raise
    
    def _create_session_backup(self):
        """创建会话备份"""
        try:
            session = st.session_state.get('intelligent_workflow_session')
            if session:
                backup_data = self._serialize_session(session)
                st.session_state.intelligent_workflow_backup = backup_data
                st.session_state.intelligent_workflow_last_backup = datetime.now().isoformat()
                logger.debug("Intelligent workflow session backup created")
        except Exception as e:
            logger.warning(f"Failed to create intelligent workflow session backup: {str(e)}")
    
    def _serialize_session(self, session: IntelligentWorkflowSession) -> str:
        """序列化会话数据"""
        try:
            # 创建可序列化的数据结构
            session_data = {
                'session_id': session.session_id,
                'current_state': session.current_state.value,
                'creation_time': session.creation_time.isoformat(),
                'last_updated': session.last_updated.isoformat(),
                'selected_modules': [m.value for m in session.selected_modules],
                'generation_status': {k.value: v.value for k, v in session.generation_status.items()},
                'has_product_analysis': session.product_analysis is not None,
                'has_module_recommendation': session.module_recommendation is not None,
                'has_style_theme': session.selected_style_theme is not None,
                'module_contents_count': len(session.module_contents),
                'compliance_results_count': len(session.compliance_results),
                'generation_results_count': len(session.generation_results),
                'user_edits_count': len(session.user_edits),
                'workflow_metadata': self._serialize_workflow_metadata(session.workflow_metadata)
            }
            
            # 使用base64编码
            json_str = json.dumps(session_data)
            return base64.b64encode(json_str.encode()).decode()
            
        except Exception as e:
            logger.error(f"Intelligent workflow session serialization failed: {str(e)}")
            return ""
    
    def _serialize_workflow_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """序列化工作流元数据，处理ModuleType等不可序列化对象"""
        try:
            serialized_metadata = {}
            
            for key, value in metadata.items():
                if key == 'module_recommendation' and isinstance(value, dict):
                    # 处理模块推荐数据中的ModuleType对象
                    serialized_recommendation = {}
                    for rec_key, rec_value in value.items():
                        if rec_key in ['recommended_modules', 'selected_modules', 'alternative_modules'] and isinstance(rec_value, list):
                            # 转换ModuleType列表为字符串列表
                            serialized_recommendation[rec_key] = [
                                m.value if hasattr(m, 'value') else str(m) for m in rec_value
                            ]
                        elif rec_key in ['recommendation_reasons', 'confidence_scores'] and isinstance(rec_value, dict):
                            # 转换以ModuleType为键的字典
                            serialized_recommendation[rec_key] = {
                                (k.value if hasattr(k, 'value') else str(k)): v 
                                for k, v in rec_value.items()
                            }
                        else:
                            # 其他数据直接复制
                            serialized_recommendation[rec_key] = rec_value
                    
                    serialized_metadata[key] = serialized_recommendation
                    
                elif key == 'generated_content' and isinstance(value, dict):
                    # 处理生成内容中的ModuleType键
                    serialized_metadata[key] = {
                        (k.value if hasattr(k, 'value') else str(k)): v 
                        for k, v in value.items()
                    }
                    
                elif key == 'final_content' and isinstance(value, dict):
                    # 处理最终内容中的ModuleType键
                    serialized_metadata[key] = {
                        (k.value if hasattr(k, 'value') else str(k)): v 
                        for k, v in value.items()
                    }
                    
                elif key == 'generated_images' and isinstance(value, dict):
                    # 处理生成图片中的ModuleType键
                    serialized_metadata[key] = {
                        (k.value if hasattr(k, 'value') else str(k)): v 
                        for k, v in value.items()
                    }
                    
                else:
                    # 其他数据直接复制
                    serialized_metadata[key] = value
            
            return serialized_metadata
            
        except Exception as e:
            logger.warning(f"Failed to serialize workflow metadata: {str(e)}")
            # 返回空字典作为fallback
            return {}
    
    def _deserialize_session(self, backup_data: str) -> Optional[IntelligentWorkflowSession]:
        """反序列化会话数据"""
        try:
            # 解码数据
            json_str = base64.b64decode(backup_data.encode()).decode()
            session_data = json.loads(json_str)
            
            # 重建会话对象（简化版本）
            session = IntelligentWorkflowSession(
                session_id=session_data['session_id'],
                current_state=WorkflowState(session_data['current_state']),
                selected_modules=[ModuleType(m) for m in session_data.get('selected_modules', [])],
                generation_status={
                    ModuleType(k): GenerationStatus(v) 
                    for k, v in session_data.get('generation_status', {}).items()
                },
                workflow_metadata=self._deserialize_workflow_metadata(session_data.get('workflow_metadata', {}))
            )
            
            # 设置时间戳
            session.creation_time = datetime.fromisoformat(session_data['creation_time'])
            session.last_updated = datetime.fromisoformat(session_data['last_updated'])
            
            return session
            
        except Exception as e:
            logger.error(f"Intelligent workflow session deserialization failed: {str(e)}")
            return None
    
    def _deserialize_workflow_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化工作流元数据，恢复ModuleType等对象"""
        try:
            deserialized_metadata = {}
            
            for key, value in metadata.items():
                if key == 'module_recommendation' and isinstance(value, dict):
                    # 处理模块推荐数据中的ModuleType对象
                    deserialized_recommendation = {}
                    for rec_key, rec_value in value.items():
                        if rec_key in ['recommended_modules', 'selected_modules', 'alternative_modules'] and isinstance(rec_value, list):
                            # 转换字符串列表为ModuleType列表
                            try:
                                deserialized_recommendation[rec_key] = [
                                    ModuleType(m) for m in rec_value
                                ]
                            except:
                                deserialized_recommendation[rec_key] = rec_value
                        elif rec_key in ['recommendation_reasons', 'confidence_scores'] and isinstance(rec_value, dict):
                            # 转换以字符串为键的字典为以ModuleType为键的字典
                            try:
                                deserialized_recommendation[rec_key] = {
                                    ModuleType(k): v for k, v in rec_value.items()
                                }
                            except:
                                deserialized_recommendation[rec_key] = rec_value
                        else:
                            # 其他数据直接复制
                            deserialized_recommendation[rec_key] = rec_value
                    
                    deserialized_metadata[key] = deserialized_recommendation
                    
                elif key in ['generated_content', 'final_content', 'generated_images'] and isinstance(value, dict):
                    # 处理以ModuleType为键的字典
                    try:
                        deserialized_metadata[key] = {
                            ModuleType(k): v for k, v in value.items()
                        }
                    except:
                        # 如果转换失败，保持原样
                        deserialized_metadata[key] = value
                        
                else:
                    # 其他数据直接复制
                    deserialized_metadata[key] = value
            
            return deserialized_metadata
            
        except Exception as e:
            logger.warning(f"Failed to deserialize workflow metadata: {str(e)}")
            # 返回原始数据作为fallback
            return metadata
    
    def save_current_session_to_history(self):
        """保存当前会话到历史记录"""
        try:
            session = self.get_current_session()
            if session:
                history = st.session_state.get('intelligent_workflow_history', [])
                
                # 检查是否已存在
                existing_index = None
                for i, hist_session in enumerate(history):
                    if hist_session.session_id == session.session_id:
                        existing_index = i
                        break
                
                if existing_index is not None:
                    history[existing_index] = session
                else:
                    history.append(session)
                    
                    # 限制历史记录数量
                    if len(history) > self.max_history_sessions:
                        history.sort(key=lambda x: x.last_updated)
                        history = history[-(self.max_history_sessions-1):]
                
                st.session_state.intelligent_workflow_history = history
                logger.info(f"Intelligent workflow session saved to history: {session.session_id}")
                
        except Exception as e:
            logger.warning(f"Failed to save intelligent workflow session to history: {str(e)}")
    
    def get_session_history(self) -> List[IntelligentWorkflowSession]:
        """获取会话历史记录"""
        try:
            history = st.session_state.get('intelligent_workflow_history', [])
            return sorted(history, key=lambda x: x.last_updated, reverse=True)
        except Exception as e:
            logger.error(f"Failed to get intelligent workflow session history: {str(e)}")
            return []
    
    def load_session_from_history(self, session_id: str) -> Optional[IntelligentWorkflowSession]:
        """从历史记录加载会话"""
        try:
            history = self.get_session_history()
            
            for session in history:
                if session.session_id == session_id:
                    if self._validate_session_integrity(session):
                        # 保存当前会话到历史
                        if self.has_active_session():
                            self.save_current_session_to_history()
                        
                        # 加载选定的会话
                        st.session_state.intelligent_workflow_session = session
                        self.workflow_controller.load_session(session)
                        self._create_session_backup()
                        
                        logger.info(f"Loaded intelligent workflow session from history: {session_id}")
                        return session
                    else:
                        logger.warning(f"Intelligent workflow session {session_id} failed integrity check")
                        break
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load intelligent workflow session from history: {str(e)}")
            return None
    
    def clear_current_session(self):
        """清除当前会话"""
        try:
            if self.has_active_session():
                self.save_current_session_to_history()
            
            st.session_state.intelligent_workflow_session = None
            st.session_state.intelligent_workflow_backup = None
            st.session_state.intelligent_workflow_last_backup = None
            st.session_state.intelligent_workflow_user_edits = {}
            
            self.workflow_controller.clear_current_session()
            
            logger.info("Current intelligent workflow session cleared")
        except Exception as e:
            logger.error(f"Failed to clear current intelligent workflow session: {str(e)}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要信息"""
        try:
            session = self.get_current_session()
            if not session:
                return {
                    "has_session": False,
                    "message": "没有活跃的智能工作流会话",
                    "backup_available": st.session_state.get('intelligent_workflow_backup') is not None
                }
            
            progress_percentage = session.get_progress_percentage()
            completed_modules = len(session.get_completed_modules())
            failed_modules = len(session.get_failed_modules())
            
            return {
                "has_session": True,
                "session_id": session.session_id,
                "current_state": session.current_state.value,
                "progress_percentage": progress_percentage,
                "selected_modules_count": len(session.selected_modules),
                "completed_modules_count": completed_modules,
                "failed_modules_count": failed_modules,
                "has_product_analysis": session.product_analysis is not None,
                "has_module_recommendation": session.module_recommendation is not None,
                "has_style_theme": session.selected_style_theme is not None,
                "creation_time": session.creation_time.isoformat(),
                "last_updated": session.last_updated.isoformat(),
                "session_age_hours": (datetime.now() - session.creation_time).total_seconds() / 3600,
                "backup_available": st.session_state.get('intelligent_workflow_backup') is not None,
                "last_backup_time": st.session_state.get('intelligent_workflow_last_backup'),
                "auto_save_enabled": self.auto_save_enabled,
                "ready_for_generation": session.is_ready_for_generation()
            }
            
        except Exception as e:
            logger.error(f"Failed to get intelligent workflow session summary: {str(e)}")
            return {
                "has_session": False,
                "error": str(e)
            }
    
    def export_session_data(self) -> Optional[Dict[str, Any]]:
        """导出会话数据"""
        try:
            session = self.get_current_session()
            if not session:
                return None
            
            return session.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to export intelligent workflow session data: {str(e)}")
            return None
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """清理旧数据"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # 清理旧的会话历史
            history = st.session_state.get('intelligent_workflow_history', [])
            cleaned_history = [
                session for session in history 
                if session.last_updated > cutoff_time
            ]
            st.session_state.intelligent_workflow_history = cleaned_history
            
            logger.info(f"Cleaned up intelligent workflow data older than {days_to_keep} days")
            
        except Exception as e:
            logger.error(f"Intelligent workflow data cleanup failed: {str(e)}")
    
    def reset_current_session(self):
        """重置当前会话"""
        try:
            session = self.get_current_session()
            if session:
                # 保存到历史
                self.save_current_session_to_history()
                
                # 创建新会话，保持相同ID
                new_session = self.workflow_controller.create_new_session(session.session_id + "_reset")
                st.session_state.intelligent_workflow_session = new_session
                self._create_session_backup()
                
                logger.info(f"Reset intelligent workflow session: {session.session_id}")
                
        except Exception as e:
            logger.error(f"Failed to reset intelligent workflow session: {str(e)}")
            raise
