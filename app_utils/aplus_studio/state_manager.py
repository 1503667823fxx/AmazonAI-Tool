"""
A+ Studio State Manager.

This module manages session state for the A+ image workflow system,
handling persistence and recovery across browser refreshes with enhanced
data integrity and recovery mechanisms.
"""

import streamlit as st
import json
import pickle
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid
import logging

from services.aplus_studio.models import (
    APlusSession, ProductInfo, AnalysisResult, ModuleType,
    GenerationResult, GenerationStatus, VisualStyle
)

# 配置日志
logger = logging.getLogger(__name__)


class APlusStateManager:
    """A+ Studio状态管理器 - 管理会话状态和持久化，支持浏览器刷新后的状态恢复"""
    
    def __init__(self):
        self.session_timeout_hours = 24
        self.max_history_sessions = 20
        self.auto_save_enabled = True
        self.backup_interval_minutes = 5
        
        self._init_session_state()
        self._setup_auto_backup()
    
    def _init_session_state(self):
        """初始化Streamlit会话状态，包含持久化支持"""
        try:
            # 基本会话状态
            if 'aplus_session' not in st.session_state:
                st.session_state.aplus_session = None
            
            if 'aplus_sessions_history' not in st.session_state:
                st.session_state.aplus_sessions_history = []
            
            if 'aplus_version_histories' not in st.session_state:
                st.session_state.aplus_version_histories = {}
            
            # 持久化相关状态
            if 'aplus_session_backup' not in st.session_state:
                st.session_state.aplus_session_backup = None
            
            if 'aplus_last_backup_time' not in st.session_state:
                st.session_state.aplus_last_backup_time = None
            
            if 'aplus_recovery_data' not in st.session_state:
                st.session_state.aplus_recovery_data = {}
            
            # 尝试从备份恢复
            self._attempt_session_recovery()
            
            logger.info("Session state initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize session state: {str(e)}")
            # 确保基本状态存在
            st.session_state.aplus_session = None
            st.session_state.aplus_sessions_history = []
    
    def _setup_auto_backup(self):
        """设置自动备份"""
        try:
            if self.auto_save_enabled:
                # 检查是否需要备份
                last_backup = st.session_state.get('aplus_last_backup_time')
                if last_backup:
                    last_backup_time = datetime.fromisoformat(last_backup)
                    if datetime.now() - last_backup_time > timedelta(minutes=self.backup_interval_minutes):
                        self._create_session_backup()
                else:
                    # 首次运行，创建备份
                    self._create_session_backup()
        except Exception as e:
            logger.warning(f"Auto backup setup failed: {str(e)}")
    
    def _attempt_session_recovery(self):
        """尝试从备份恢复会话"""
        try:
            # 检查是否有备份数据
            backup_data = st.session_state.get('aplus_session_backup')
            if backup_data and not st.session_state.get('aplus_session'):
                logger.info("Attempting to recover session from backup")
                
                # 尝试恢复会话
                recovered_session = self._deserialize_session(backup_data)
                if recovered_session and self._validate_recovered_session(recovered_session):
                    st.session_state.aplus_session = recovered_session
                    logger.info(f"Successfully recovered session: {recovered_session.session_id}")
                    
                    # 显示恢复通知
                    if hasattr(st, 'success'):
                        st.success("已从上次会话恢复数据")
                else:
                    logger.warning("Session recovery validation failed")
                    
        except Exception as e:
            logger.error(f"Session recovery failed: {str(e)}")
    
    def _validate_recovered_session(self, session: APlusSession) -> bool:
        """验证恢复的会话是否有效"""
        try:
            # 检查基本属性
            if not session.session_id or not session.creation_time:
                return False
            
            # 检查会话是否过期
            if datetime.now() - session.creation_time > timedelta(hours=self.session_timeout_hours):
                logger.info(f"Recovered session {session.session_id} is expired")
                return False
            
            # 检查数据完整性
            if not hasattr(session, 'generation_status') or not isinstance(session.generation_status, dict):
                return False
            
            # 验证模块状态
            expected_modules = set(ModuleType)
            actual_modules = set(session.generation_status.keys())
            if not expected_modules.issubset(actual_modules):
                logger.warning("Recovered session has incomplete module status")
                # 修复缺失的模块状态
                for module_type in expected_modules - actual_modules:
                    session.generation_status[module_type] = GenerationStatus.NOT_STARTED
            
            return True
            
        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            return False
    
    def create_new_session(self) -> APlusSession:
        """创建新的A+制作会话，包含持久化支持"""
        try:
            session_id = str(uuid.uuid4())
            
            new_session = APlusSession(
                session_id=session_id,
                product_info=None,
                analysis_result=None,
                visual_style=None,
                module_results={},
                generation_status={
                    ModuleType.IDENTITY: GenerationStatus.NOT_STARTED,
                    ModuleType.SENSORY: GenerationStatus.NOT_STARTED,
                    ModuleType.EXTENSION: GenerationStatus.NOT_STARTED,
                    ModuleType.TRUST: GenerationStatus.NOT_STARTED
                }
            )
            
            st.session_state.aplus_session = new_session
            
            # 创建初始备份
            self._create_session_backup()
            
            logger.info(f"Created new session: {session_id}")
            return new_session
            
        except Exception as e:
            logger.error(f"Failed to create new session: {str(e)}")
            raise
    
    def get_current_session(self) -> Optional[APlusSession]:
        """获取当前会话，包含自动恢复机制"""
        try:
            session = st.session_state.get('aplus_session')
            
            # 如果没有会话但有备份，尝试恢复
            if not session:
                backup_data = st.session_state.get('aplus_session_backup')
                if backup_data:
                    session = self._deserialize_session(backup_data)
                    if session and self._validate_recovered_session(session):
                        st.session_state.aplus_session = session
                        logger.info("Auto-recovered session from backup")
            
            # 验证会话有效性
            if session and not self._validate_session_integrity(session):
                logger.warning("Current session failed integrity check")
                return None
            
            return session
            
        except Exception as e:
            logger.error(f"Error getting current session: {str(e)}")
            return None
    
    def _validate_session_integrity(self, session: APlusSession) -> bool:
        """验证会话完整性"""
        try:
            if not session or not session.session_id:
                return False
            
            # 检查会话是否过期
            if datetime.now() - session.creation_time > timedelta(hours=self.session_timeout_hours):
                return False
            
            # 检查必需的属性
            required_attrs = ['generation_status', 'module_results', 'creation_time', 'last_updated']
            for attr in required_attrs:
                if not hasattr(session, attr):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Session integrity validation failed: {str(e)}")
            return False
    
    def has_active_session(self) -> bool:
        """检查是否有活跃会话"""
        return st.session_state.get('aplus_session') is not None
    
    def update_product_info(self, product_info: ProductInfo):
        """更新产品信息，包含自动备份"""
        try:
            session = self.get_current_session()
            if session:
                session.product_info = product_info
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info("Product info updated successfully")
        except Exception as e:
            logger.error(f"Failed to update product info: {str(e)}")
            raise
    
    def update_analysis_result(self, analysis_result: AnalysisResult):
        """更新分析结果，包含自动备份"""
        try:
            session = self.get_current_session()
            if session:
                session.analysis_result = analysis_result
                session.visual_style = analysis_result.visual_style
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info("Analysis result updated successfully")
        except Exception as e:
            logger.error(f"Failed to update analysis result: {str(e)}")
            raise
    
    def update_module_result(self, module_type: ModuleType, result: GenerationResult):
        """更新模块生成结果，包含版本历史管理"""
        try:
            session = self.get_current_session()
            if session:
                # 保存旧版本到历史记录
                if module_type in session.module_results:
                    self._archive_module_version(session.session_id, module_type, session.module_results[module_type])
                
                session.module_results[module_type] = result
                session.last_updated = datetime.now()
                self._save_session(session)
                logger.info(f"Module result updated for {module_type.value}")
        except Exception as e:
            logger.error(f"Failed to update module result: {str(e)}")
            raise
    
    def update_generation_status(self, module_type: ModuleType, status: GenerationStatus):
        """更新模块生成状态，包含状态变更日志"""
        try:
            session = self.get_current_session()
            if session:
                old_status = session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
                session.generation_status[module_type] = status
                session.last_updated = datetime.now()
                
                # 记录状态变更
                self._log_status_change(session.session_id, module_type, old_status, status)
                
                self._save_session(session)
                logger.info(f"Generation status updated for {module_type.value}: {old_status.value} -> {status.value}")
        except Exception as e:
            logger.error(f"Failed to update generation status: {str(e)}")
            raise
    
    def _save_session(self, session: APlusSession):
        """保存会话到状态，包含自动备份"""
        try:
            st.session_state.aplus_session = session
            
            # 添加到历史记录
            self._add_to_history(session)
            
            # 自动备份
            if self.auto_save_enabled:
                self._create_session_backup()
                
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            raise
    
    def _create_session_backup(self):
        """创建会话备份"""
        try:
            session = st.session_state.get('aplus_session')
            if session:
                # 序列化会话数据
                backup_data = self._serialize_session(session)
                st.session_state.aplus_session_backup = backup_data
                st.session_state.aplus_last_backup_time = datetime.now().isoformat()
                logger.debug("Session backup created")
        except Exception as e:
            logger.warning(f"Failed to create session backup: {str(e)}")
    
    def _serialize_session(self, session: APlusSession) -> str:
        """序列化会话数据"""
        try:
            # 创建可序列化的数据结构
            session_data = {
                'session_id': session.session_id,
                'creation_time': session.creation_time.isoformat(),
                'last_updated': session.last_updated.isoformat(),
                'generation_status': {k.value: v.value for k, v in session.generation_status.items()},
                'has_product_info': session.product_info is not None,
                'has_analysis_result': session.analysis_result is not None,
                'has_visual_style': session.visual_style is not None,
                'module_results_count': len(session.module_results),
                'module_results_keys': [k.value for k in session.module_results.keys()]
            }
            
            # 使用base64编码
            json_str = json.dumps(session_data)
            return base64.b64encode(json_str.encode()).decode()
            
        except Exception as e:
            logger.error(f"Session serialization failed: {str(e)}")
            return ""
    
    def _deserialize_session(self, backup_data: str) -> Optional[APlusSession]:
        """反序列化会话数据"""
        try:
            # 解码数据
            json_str = base64.b64decode(backup_data.encode()).decode()
            session_data = json.loads(json_str)
            
            # 重建会话对象（简化版本，只包含基本信息）
            session = APlusSession(
                session_id=session_data['session_id'],
                product_info=None,  # 需要重新输入
                analysis_result=None,  # 需要重新分析
                visual_style=None,
                module_results={},  # 需要重新生成
                generation_status={
                    ModuleType(k): GenerationStatus(v) 
                    for k, v in session_data['generation_status'].items()
                }
            )
            
            # 设置时间戳
            session.creation_time = datetime.fromisoformat(session_data['creation_time'])
            session.last_updated = datetime.fromisoformat(session_data['last_updated'])
            
            return session
            
        except Exception as e:
            logger.error(f"Session deserialization failed: {str(e)}")
            return None
    
    def _archive_module_version(self, session_id: str, module_type: ModuleType, result: GenerationResult):
        """归档模块版本到历史记录"""
        try:
            if 'aplus_module_archives' not in st.session_state:
                st.session_state.aplus_module_archives = {}
            
            archives = st.session_state.aplus_module_archives
            key = f"{session_id}_{module_type.value}"
            
            if key not in archives:
                archives[key] = []
            
            # 添加版本信息（简化）
            version_info = {
                'timestamp': datetime.now().isoformat(),
                'quality_score': result.quality_score,
                'validation_status': result.validation_status.value,
                'generation_time': result.generation_time
            }
            
            archives[key].append(version_info)
            
            # 限制历史记录数量
            if len(archives[key]) > 10:
                archives[key] = archives[key][-10:]
            
            st.session_state.aplus_module_archives = archives
            
        except Exception as e:
            logger.warning(f"Failed to archive module version: {str(e)}")
    
    def _log_status_change(self, session_id: str, module_type: ModuleType, old_status: GenerationStatus, new_status: GenerationStatus):
        """记录状态变更日志"""
        try:
            if 'aplus_status_logs' not in st.session_state:
                st.session_state.aplus_status_logs = []
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id,
                'module_type': module_type.value,
                'old_status': old_status.value,
                'new_status': new_status.value
            }
            
            st.session_state.aplus_status_logs.append(log_entry)
            
            # 限制日志数量
            if len(st.session_state.aplus_status_logs) > 100:
                st.session_state.aplus_status_logs = st.session_state.aplus_status_logs[-100:]
                
        except Exception as e:
            logger.warning(f"Failed to log status change: {str(e)}")
    
    def get_module_result(self, module_type: ModuleType) -> Optional[GenerationResult]:
        """获取指定模块的生成结果"""
        try:
            session = self.get_current_session()
            if session:
                return session.module_results.get(module_type)
            return None
        except Exception as e:
            logger.error(f"Failed to get module result: {str(e)}")
            return None
    
    def get_generation_status(self, module_type: ModuleType) -> GenerationStatus:
        """获取指定模块的生成状态"""
        try:
            session = self.get_current_session()
            if session:
                return session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
            return GenerationStatus.NOT_STARTED
        except Exception as e:
            logger.error(f"Failed to get generation status: {str(e)}")
            return GenerationStatus.NOT_STARTED
    
    def _add_to_history(self, session: APlusSession):
        """添加会话到历史记录，包含智能去重"""
        try:
            history = st.session_state.aplus_sessions_history
            
            # 检查是否已存在
            existing_index = None
            for i, hist_session in enumerate(history):
                if hist_session.session_id == session.session_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # 更新现有记录
                history[existing_index] = session
            else:
                # 添加新记录
                history.append(session)
                
                # 限制历史记录数量
                if len(history) > self.max_history_sessions:
                    # 移除最旧的记录
                    history.sort(key=lambda x: x.last_updated)
                    history = history[-(self.max_history_sessions-1):]
            
            st.session_state.aplus_sessions_history = history
            
        except Exception as e:
            logger.warning(f"Failed to add session to history: {str(e)}")
    
    def get_sessions_history(self) -> List[APlusSession]:
        """获取会话历史记录，按时间排序"""
        try:
            history = st.session_state.get('aplus_sessions_history', [])
            # 按最后更新时间倒序排列
            return sorted(history, key=lambda x: x.last_updated, reverse=True)
        except Exception as e:
            logger.error(f"Failed to get sessions history: {str(e)}")
            return []
    
    def load_session(self, session_id: str) -> Optional[APlusSession]:
        """从历史记录加载会话，包含完整性验证"""
        try:
            history = self.get_sessions_history()
            
            for session in history:
                if session.session_id == session_id:
                    # 验证会话完整性
                    if self._validate_session_integrity(session):
                        st.session_state.aplus_session = session
                        self._create_session_backup()  # 创建备份
                        logger.info(f"Loaded session from history: {session_id}")
                        return session
                    else:
                        logger.warning(f"Session {session_id} failed integrity check")
                        break
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return None
    
    def clear_current_session(self):
        """清除当前会话，包含清理备份"""
        try:
            st.session_state.aplus_session = None
            st.session_state.aplus_session_backup = None
            st.session_state.aplus_last_backup_time = None
            logger.info("Current session cleared")
        except Exception as e:
            logger.error(f"Failed to clear current session: {str(e)}")
    
    def export_session_data(self) -> Optional[Dict[str, Any]]:
        """导出会话数据（用于持久化存储），包含完整的会话信息"""
        try:
            session = self.get_current_session()
            if not session:
                return None
            
            export_data = {
                "session_id": session.session_id,
                "creation_time": session.creation_time.isoformat(),
                "last_updated": session.last_updated.isoformat(),
                "has_product_info": session.product_info is not None,
                "has_analysis": session.analysis_result is not None,
                "module_count": len(session.module_results),
                "generation_status": {k.value: v.value for k, v in session.generation_status.items()},
                "completed_modules": [
                    k.value for k, v in session.generation_status.items() 
                    if v == GenerationStatus.COMPLETED
                ],
                "failed_modules": [
                    k.value for k, v in session.generation_status.items() 
                    if v == GenerationStatus.FAILED
                ],
                "backup_available": st.session_state.get('aplus_session_backup') is not None,
                "export_timestamp": datetime.now().isoformat()
            }
            
            # 添加模块结果摘要
            module_summaries = {}
            for module_type, result in session.module_results.items():
                module_summaries[module_type.value] = {
                    "quality_score": result.quality_score,
                    "validation_status": result.validation_status.value,
                    "generation_time": result.generation_time,
                    "has_image": result.image_data is not None or result.image_path is not None
                }
            export_data["module_summaries"] = module_summaries
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export session data: {str(e)}")
            return None
    
    def import_session_data(self, session_data: Dict[str, Any]) -> bool:
        """导入会话数据（从持久化存储恢复），包含数据验证"""
        try:
            # 验证导入数据的完整性
            required_fields = ['session_id', 'creation_time', 'generation_status']
            for field in required_fields:
                if field not in session_data:
                    logger.error(f"Import data missing required field: {field}")
                    return False
            
            # 创建新会话
            session = APlusSession(
                session_id=session_data['session_id'],
                product_info=None,  # 需要重新输入
                analysis_result=None,  # 需要重新分析
                visual_style=None,
                module_results={},
                generation_status={
                    ModuleType(k): GenerationStatus(v) 
                    for k, v in session_data['generation_status'].items()
                }
            )
            
            # 设置时间戳
            session.creation_time = datetime.fromisoformat(session_data['creation_time'])
            session.last_updated = datetime.fromisoformat(session_data.get('last_updated', session_data['creation_time']))
            
            # 保存会话
            st.session_state.aplus_session = session
            self._create_session_backup()
            
            logger.info(f"Successfully imported session: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import session data: {str(e)}")
            return False
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要信息，包含详细的状态统计"""
        try:
            session = self.get_current_session()
            if not session:
                return {
                    "has_session": False,
                    "message": "没有活跃的会话",
                    "backup_available": st.session_state.get('aplus_session_backup') is not None
                }
            
            completed_modules = sum(
                1 for status in session.generation_status.values()
                if status == GenerationStatus.COMPLETED
            )
            
            in_progress_modules = sum(
                1 for status in session.generation_status.values()
                if status == GenerationStatus.IN_PROGRESS
            )
            
            failed_modules = sum(
                1 for status in session.generation_status.values()
                if status == GenerationStatus.FAILED
            )
            
            # 计算会话健康度
            total_modules = len(ModuleType)
            health_score = (completed_modules / total_modules) * 100 if total_modules > 0 else 0
            
            # 检查数据完整性
            data_integrity = {
                "has_product_info": session.product_info is not None,
                "has_analysis": session.analysis_result is not None,
                "has_visual_style": session.visual_style is not None,
                "module_results_count": len(session.module_results)
            }
            
            return {
                "has_session": True,
                "session_id": session.session_id,
                "health_score": health_score,
                "data_integrity": data_integrity,
                "total_modules": total_modules,
                "completed_modules": completed_modules,
                "in_progress_modules": in_progress_modules,
                "failed_modules": failed_modules,
                "creation_time": session.creation_time.isoformat(),
                "last_updated": session.last_updated.isoformat(),
                "session_age_hours": (datetime.now() - session.creation_time).total_seconds() / 3600,
                "backup_available": st.session_state.get('aplus_session_backup') is not None,
                "last_backup_time": st.session_state.get('aplus_last_backup_time'),
                "auto_save_enabled": self.auto_save_enabled
            }
            
        except Exception as e:
            logger.error(f"Failed to get session summary: {str(e)}")
            return {
                "has_session": False,
                "error": str(e)
            }
    
    def reset_module(self, module_type: ModuleType):
        """重置指定模块的状态，包含历史记录清理"""
        try:
            session = self.get_current_session()
            if session:
                # 归档当前结果
                if module_type in session.module_results:
                    self._archive_module_version(session.session_id, module_type, session.module_results[module_type])
                    del session.module_results[module_type]
                
                # 重置状态
                session.generation_status[module_type] = GenerationStatus.NOT_STARTED
                session.last_updated = datetime.now()
                
                self._save_session(session)
                logger.info(f"Reset module {module_type.value}")
        except Exception as e:
            logger.error(f"Failed to reset module: {str(e)}")
            raise
    
    def reset_all_modules(self):
        """重置所有模块的状态，包含完整的状态清理"""
        try:
            session = self.get_current_session()
            if session:
                # 归档所有现有结果
                for module_type, result in session.module_results.items():
                    self._archive_module_version(session.session_id, module_type, result)
                
                # 重置所有状态
                session.module_results = {}
                session.generation_status = {
                    ModuleType.IDENTITY: GenerationStatus.NOT_STARTED,
                    ModuleType.SENSORY: GenerationStatus.NOT_STARTED,
                    ModuleType.EXTENSION: GenerationStatus.NOT_STARTED,
                    ModuleType.TRUST: GenerationStatus.NOT_STARTED
                }
                session.last_updated = datetime.now()
                
                self._save_session(session)
                logger.info("Reset all modules")
        except Exception as e:
            logger.error(f"Failed to reset all modules: {str(e)}")
            raise
    
    def save_version_history(self, session_id: str, version_histories: Dict[str, Any]):
        """保存版本历史记录，包含数据验证"""
        try:
            if 'aplus_version_histories' not in st.session_state:
                st.session_state.aplus_version_histories = {}
            
            # 验证数据格式
            if not isinstance(version_histories, dict):
                raise ValueError("Version histories must be a dictionary")
            
            st.session_state.aplus_version_histories[session_id] = version_histories
            logger.info(f"Saved version history for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save version history: {str(e)}")
            raise
    
    def get_version_history(self, session_id: str) -> Dict[str, Any]:
        """获取版本历史记录"""
        try:
            version_histories = st.session_state.get('aplus_version_histories', {})
            return version_histories.get(session_id, {})
        except Exception as e:
            logger.error(f"Failed to get version history: {str(e)}")
            return {}
    
    def clear_version_history(self, session_id: str):
        """清除指定会话的版本历史"""
        try:
            if 'aplus_version_histories' in st.session_state:
                version_histories = st.session_state.aplus_version_histories
                if session_id in version_histories:
                    del version_histories[session_id]
                    st.session_state.aplus_version_histories = version_histories
                    logger.info(f"Cleared version history for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear version history: {str(e)}")
    
    # Enhanced Recovery and Maintenance Methods
    
    def emergency_save(self):
        """紧急保存当前状态"""
        try:
            session = self.get_current_session()
            if session:
                # 创建紧急备份
                emergency_backup = self._serialize_session(session)
                st.session_state.aplus_emergency_backup = emergency_backup
                st.session_state.aplus_emergency_backup_time = datetime.now().isoformat()
                
                # 保存到恢复数据
                recovery_data = st.session_state.get('aplus_recovery_data', {})
                recovery_data['emergency_session'] = emergency_backup
                recovery_data['emergency_timestamp'] = datetime.now().isoformat()
                st.session_state.aplus_recovery_data = recovery_data
                
                logger.info("Emergency save completed")
                return True
        except Exception as e:
            logger.error(f"Emergency save failed: {str(e)}")
            return False
    
    def recover_from_emergency_backup(self) -> bool:
        """从紧急备份恢复"""
        try:
            emergency_backup = st.session_state.get('aplus_emergency_backup')
            if emergency_backup:
                recovered_session = self._deserialize_session(emergency_backup)
                if recovered_session and self._validate_recovered_session(recovered_session):
                    st.session_state.aplus_session = recovered_session
                    self._create_session_backup()
                    logger.info("Successfully recovered from emergency backup")
                    return True
            
            logger.warning("No valid emergency backup found")
            return False
            
        except Exception as e:
            logger.error(f"Emergency recovery failed: {str(e)}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """清理旧数据"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # 清理旧的会话历史
            history = st.session_state.get('aplus_sessions_history', [])
            cleaned_history = [
                session for session in history 
                if session.last_updated > cutoff_time
            ]
            st.session_state.aplus_sessions_history = cleaned_history
            
            # 清理旧的状态日志
            status_logs = st.session_state.get('aplus_status_logs', [])
            cleaned_logs = [
                log for log in status_logs 
                if datetime.fromisoformat(log['timestamp']) > cutoff_time
            ]
            st.session_state.aplus_status_logs = cleaned_logs
            
            # 清理旧的模块归档
            archives = st.session_state.get('aplus_module_archives', {})
            cleaned_archives = {}
            for key, archive_list in archives.items():
                cleaned_list = [
                    archive for archive in archive_list 
                    if datetime.fromisoformat(archive['timestamp']) > cutoff_time
                ]
                if cleaned_list:
                    cleaned_archives[key] = cleaned_list
            st.session_state.aplus_module_archives = cleaned_archives
            
            logger.info(f"Cleaned up data older than {days_to_keep} days")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            stats = {
                "sessions_history_count": len(st.session_state.get('aplus_sessions_history', [])),
                "version_histories_count": len(st.session_state.get('aplus_version_histories', {})),
                "status_logs_count": len(st.session_state.get('aplus_status_logs', [])),
                "module_archives_count": len(st.session_state.get('aplus_module_archives', {})),
                "has_current_session": st.session_state.get('aplus_session') is not None,
                "has_backup": st.session_state.get('aplus_session_backup') is not None,
                "has_emergency_backup": st.session_state.get('aplus_emergency_backup') is not None,
                "last_backup_time": st.session_state.get('aplus_last_backup_time'),
                "auto_save_enabled": self.auto_save_enabled,
                "session_timeout_hours": self.session_timeout_hours,
                "max_history_sessions": self.max_history_sessions
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {str(e)}")
            return {"error": str(e)}
    
    def configure_persistence(self, 
                            auto_save: bool = True, 
                            backup_interval_minutes: int = 5,
                            session_timeout_hours: int = 24,
                            max_history_sessions: int = 20):
        """配置持久化设置"""
        try:
            self.auto_save_enabled = auto_save
            self.backup_interval_minutes = max(1, min(60, backup_interval_minutes))
            self.session_timeout_hours = max(1, min(168, session_timeout_hours))  # 最多7天
            self.max_history_sessions = max(5, min(100, max_history_sessions))
            
            logger.info(f"Persistence configuration updated: auto_save={auto_save}, "
                       f"backup_interval={self.backup_interval_minutes}min, "
                       f"timeout={self.session_timeout_hours}h, "
                       f"max_history={self.max_history_sessions}")
            
        except Exception as e:
            logger.error(f"Failed to configure persistence: {str(e)}")
            raise