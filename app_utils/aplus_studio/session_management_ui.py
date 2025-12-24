"""
A+ 智能工作流会话管理界面组件

该模块提供会话管理功能，包括自动保存用户操作和数据、
工作会话的加载和恢复、会话超时和数据清理等功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

from services.aplus_studio.models import WorkflowState, ModuleType, GenerationStatus
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowSession, IntelligentWorkflowController
from app_utils.aplus_studio.intelligent_state_manager import IntelligentWorkflowStateManager

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    """会话摘要信息"""
    session_id: str
    name: str
    current_state: WorkflowState
    progress_percentage: float
    selected_modules_count: int
    completed_modules_count: int
    creation_time: datetime
    last_updated: datetime
    is_current: bool = False
    is_recoverable: bool = True
    size_mb: float = 0.0
    tags: List[str] = None


@dataclass
class SessionBackup:
    """会话备份信息"""
    backup_id: str
    session_id: str
    backup_time: datetime
    backup_size: int
    backup_data: str
    is_auto_backup: bool = True
    description: str = ""


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    SAVED = "saved"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"


class SessionManagementUI:
    """会话管理界面组件"""
    
    def __init__(self, state_manager: IntelligentWorkflowStateManager):
        self.state_manager = state_manager
        self.workflow_controller = state_manager.workflow_controller
        
        # 会话管理配置
        self.max_sessions = 50
        self.session_timeout_hours = 24
        self.auto_save_interval_minutes = 5
        self.backup_retention_days = 30
        self.max_backup_size_mb = 10
        
        # 自动保存配置
        self.enable_auto_save = True
        self.save_on_state_change = True
        self.save_on_content_edit = True
        self.save_on_module_selection = True
        
        logger.info("Session Management UI initialized")
    
    def render_session_management_panel(self):
        """渲染会话管理面板"""
        try:
            st.markdown("### 💾 会话管理")
            
            # 创建标签页
            tab1, tab2, tab3, tab4 = st.tabs(["当前会话", "会话历史", "自动保存", "数据清理"])
            
            with tab1:
                self._render_current_session_panel()
            
            with tab2:
                self._render_session_history_panel()
            
            with tab3:
                self._render_auto_save_panel()
            
            with tab4:
                self._render_data_cleanup_panel()
                
        except Exception as e:
            logger.error(f"Error rendering session management panel: {str(e)}")
            st.error(f"会话管理面板渲染错误: {str(e)}")
    
    def _render_current_session_panel(self):
        """渲染当前会话面板"""
        try:
            session = self.state_manager.get_current_session()
            
            if not session:
                st.info("📝 当前没有活跃的工作流会话")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🚀 开始新会话", type="primary"):
                        new_session = self.state_manager.create_new_session()
                        st.success(f"新会话已创建: {new_session.session_id}")
                        st.rerun()
                
                with col2:
                    if st.button("📂 从历史加载"):
                        st.session_state.show_load_dialog = True
                        st.rerun()
                
                return
            
            # 显示当前会话信息
            st.markdown("#### 📊 当前会话详情")
            
            # 会话基本信息
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("会话ID", session.session_id[:12] + "...")
                st.metric("当前状态", session.current_state.value)
            
            with col2:
                progress = session.get_progress_percentage()
                st.metric("完成进度", f"{progress:.1f}%")
                st.metric("选定模块", len(session.selected_modules))
            
            with col3:
                age_hours = (datetime.now() - session.creation_time).total_seconds() / 3600
                st.metric("会话时长", f"{age_hours:.1f}小时")
                completed_count = len(session.get_completed_modules())
                st.metric("已完成模块", completed_count)
            
            # 会话操作
            st.markdown("#### 🛠️ 会话操作")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("💾 手动保存", help="立即保存当前会话到历史记录"):
                    self.state_manager.save_current_session_to_history()
                    st.success("会话已保存")
                    st.rerun()
            
            with col2:
                if st.button("📋 复制会话", help="创建当前会话的副本"):
                    new_session = self._duplicate_session(session)
                    if new_session:
                        st.success(f"会话已复制: {new_session.session_id}")
                        st.rerun()
                    else:
                        st.error("会话复制失败")
            
            with col3:
                if st.button("📤 导出会话", help="导出会话数据"):
                    export_data = self.state_manager.export_session_data()
                    if export_data:
                        st.download_button(
                            label="下载会话数据",
                            data=json.dumps(export_data, indent=2, ensure_ascii=False),
                            file_name=f"session_{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    else:
                        st.error("导出失败")
            
            with col4:
                if st.button("🔄 重置会话", help="重置当前会话，保留基本设置"):
                    if st.session_state.get("confirm_reset", False):
                        self.state_manager.reset_current_session()
                        st.success("会话已重置")
                        st.session_state.confirm_reset = False
                        st.rerun()
                    else:
                        st.session_state.confirm_reset = True
                        st.warning("确定要重置会话吗？点击再次确认。")
            
            # 会话详细信息
            with st.expander("🔍 详细信息", expanded=False):
                self._render_session_details(session)
            
            # 自动保存状态
            self._render_auto_save_status()
            
        except Exception as e:
            logger.error(f"Error rendering current session panel: {str(e)}")
            st.error(f"当前会话面板渲染错误: {str(e)}")
    
    def _render_session_details(self, session: IntelligentWorkflowSession):
        """渲染会话详细信息"""
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**基本信息**")
                st.text(f"完整ID: {session.session_id}")
                st.text(f"创建时间: {session.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.text(f"最后更新: {session.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
                st.text(f"用户编辑数: {len(session.user_edits)}")
                
                if session.product_analysis:
                    st.markdown("**产品分析**")
                    st.text(f"产品类型: {session.product_analysis.product_type}")
                    st.text(f"产品类别: {session.product_analysis.product_category.value}")
                    st.text(f"置信度: {session.product_analysis.confidence_score:.2%}")
            
            with col2:
                if session.selected_modules:
                    st.markdown("**选定模块**")
                    for module in session.selected_modules:
                        status = session.generation_status.get(module, GenerationStatus.NOT_STARTED)
                        status_icon = {
                            GenerationStatus.NOT_STARTED: "⚪",
                            GenerationStatus.IN_PROGRESS: "🔵",
                            GenerationStatus.COMPLETED: "🟢",
                            GenerationStatus.FAILED: "🔴",
                            GenerationStatus.CANCELLED: "⚫"
                        }.get(status, "❓")
                        
                        st.text(f"{status_icon} {module.value}")
                
                if session.selected_style_theme:
                    st.markdown("**风格主题**")
                    st.text(f"主题: {session.selected_style_theme.theme_name}")
                    st.text(f"设计风格: {session.selected_style_theme.design_style}")
                
                if session.compliance_results:
                    st.markdown("**合规检查**")
                    compliant_count = sum(1 for result in session.compliance_results.values() if result.is_compliant)
                    st.text(f"合规模块: {compliant_count}/{len(session.compliance_results)}")
            
        except Exception as e:
            logger.error(f"Error rendering session details: {str(e)}")
    
    def _render_auto_save_status(self):
        """渲染自动保存状态"""
        try:
            st.markdown("#### 🔄 自动保存状态")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                auto_save_enabled = self.state_manager.auto_save_enabled
                status_color = "🟢" if auto_save_enabled else "🔴"
                st.metric("自动保存", f"{status_color} {'启用' if auto_save_enabled else '禁用'}")
            
            with col2:
                last_backup = st.session_state.get('intelligent_workflow_last_backup')
                if last_backup:
                    backup_time = datetime.fromisoformat(last_backup)
                    time_diff = datetime.now() - backup_time
                    if time_diff.total_seconds() < 60:
                        backup_text = f"{time_diff.seconds}秒前"
                    elif time_diff.total_seconds() < 3600:
                        backup_text = f"{time_diff.seconds // 60}分钟前"
                    else:
                        backup_text = f"{time_diff.seconds // 3600}小时前"
                    st.metric("最后备份", backup_text)
                else:
                    st.metric("最后备份", "无")
            
            with col3:
                backup_available = st.session_state.get('intelligent_workflow_backup') is not None
                backup_status = "🟢 可用" if backup_available else "🔴 无"
                st.metric("备份状态", backup_status)
            
        except Exception as e:
            logger.error(f"Error rendering auto save status: {str(e)}")
    
    def _render_session_history_panel(self):
        """渲染会话历史面板"""
        try:
            st.markdown("#### 📚 会话历史记录")
            
            history = self.state_manager.get_session_history()
            
            if not history:
                st.info("暂无历史会话记录")
                return
            
            # 搜索和筛选
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_term = st.text_input("🔍 搜索会话", placeholder="输入会话ID或关键词")
            
            with col2:
                state_filter = st.selectbox(
                    "筛选状态",
                    options=["全部"] + [state.value for state in WorkflowState],
                    index=0
                )
            
            with col3:
                sort_by = st.selectbox(
                    "排序方式",
                    options=["最后更新", "创建时间", "进度", "模块数量"],
                    index=0
                )
            
            # 筛选和排序历史记录
            filtered_history = self._filter_and_sort_history(history, search_term, state_filter, sort_by)
            
            # 显示会话列表
            st.markdown(f"**找到 {len(filtered_history)} 个会话**")
            
            for i, session in enumerate(filtered_history[:20]):  # 限制显示20个
                self._render_session_card(session, i)
            
            if len(filtered_history) > 20:
                st.info(f"还有 {len(filtered_history) - 20} 个会话未显示")
            
        except Exception as e:
            logger.error(f"Error rendering session history panel: {str(e)}")
            st.error(f"会话历史面板渲染错误: {str(e)}")
    
    def _render_session_card(self, session: IntelligentWorkflowSession, index: int):
        """渲染会话卡片"""
        try:
            with st.container():
                # 创建会话卡片
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    # 会话基本信息
                    st.markdown(f"**🗂️ {session.session_id[:12]}...**")
                    st.text(f"状态: {session.current_state.value}")
                    st.text(f"创建: {session.creation_time.strftime('%m-%d %H:%M')}")
                
                with col2:
                    # 进度信息
                    progress = session.get_progress_percentage()
                    st.metric("进度", f"{progress:.1f}%")
                    if session.selected_modules:
                        st.text(f"模块: {len(session.selected_modules)}个")
                
                with col3:
                    # 状态信息
                    completed_count = len(session.get_completed_modules())
                    st.metric("已完成", completed_count)
                    
                    age_hours = (datetime.now() - session.last_updated).total_seconds() / 3600
                    if age_hours < 1:
                        age_text = f"{age_hours * 60:.0f}分钟前"
                    elif age_hours < 24:
                        age_text = f"{age_hours:.1f}小时前"
                    else:
                        age_text = f"{age_hours / 24:.1f}天前"
                    st.text(f"更新: {age_text}")
                
                with col4:
                    # 操作按钮
                    if st.button("📂 加载", key=f"load_session_{index}"):
                        loaded_session = self.state_manager.load_session_from_history(session.session_id)
                        if loaded_session:
                            st.success("会话已加载")
                            st.rerun()
                        else:
                            st.error("会话加载失败")
                    
                    if st.button("🗑️ 删除", key=f"delete_session_{index}"):
                        if st.session_state.get(f"confirm_delete_{index}", False):
                            self._delete_session_from_history(session.session_id)
                            st.success("会话已删除")
                            st.session_state[f"confirm_delete_{index}"] = False
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{index}"] = True
                            st.warning("确定删除？再次点击确认")
                
                st.markdown("---")
                
        except Exception as e:
            logger.error(f"Error rendering session card: {str(e)}")
    
    def _filter_and_sort_history(self, history: List[IntelligentWorkflowSession], 
                                search_term: str, state_filter: str, sort_by: str) -> List[IntelligentWorkflowSession]:
        """筛选和排序历史记录"""
        try:
            filtered = history.copy()
            
            # 搜索筛选
            if search_term:
                filtered = [
                    session for session in filtered
                    if search_term.lower() in session.session_id.lower()
                    or (session.product_analysis and search_term.lower() in session.product_analysis.product_type.lower())
                ]
            
            # 状态筛选
            if state_filter != "全部":
                filtered = [
                    session for session in filtered
                    if session.current_state.value == state_filter
                ]
            
            # 排序
            if sort_by == "最后更新":
                filtered.sort(key=lambda x: x.last_updated, reverse=True)
            elif sort_by == "创建时间":
                filtered.sort(key=lambda x: x.creation_time, reverse=True)
            elif sort_by == "进度":
                filtered.sort(key=lambda x: x.get_progress_percentage(), reverse=True)
            elif sort_by == "模块数量":
                filtered.sort(key=lambda x: len(x.selected_modules), reverse=True)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering and sorting history: {str(e)}")
            return history
    
    def _render_auto_save_panel(self):
        """渲染自动保存面板"""
        try:
            st.markdown("#### ⚙️ 自动保存设置")
            
            # 自动保存开关
            col1, col2 = st.columns(2)
            
            with col1:
                auto_save_enabled = st.checkbox(
                    "启用自动保存",
                    value=self.state_manager.auto_save_enabled,
                    help="自动保存会话数据到浏览器存储"
                )
                
                if auto_save_enabled != self.state_manager.auto_save_enabled:
                    self.state_manager.auto_save_enabled = auto_save_enabled
                    st.success(f"自动保存已{'启用' if auto_save_enabled else '禁用'}")
            
            with col2:
                backup_interval = st.slider(
                    "备份间隔（分钟）",
                    min_value=1,
                    max_value=30,
                    value=self.state_manager.backup_interval_minutes,
                    help="自动备份的时间间隔"
                )
                
                if backup_interval != self.state_manager.backup_interval_minutes:
                    self.state_manager.backup_interval_minutes = backup_interval
                    st.success(f"备份间隔已设置为 {backup_interval} 分钟")
            
            # 自动保存触发条件
            st.markdown("**自动保存触发条件**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                save_on_state_change = st.checkbox(
                    "状态变更时保存",
                    value=self.save_on_state_change,
                    help="工作流状态改变时自动保存"
                )
                self.save_on_state_change = save_on_state_change
            
            with col2:
                save_on_content_edit = st.checkbox(
                    "内容编辑时保存",
                    value=self.save_on_content_edit,
                    help="用户编辑内容时自动保存"
                )
                self.save_on_content_edit = save_on_content_edit
            
            with col3:
                save_on_module_selection = st.checkbox(
                    "模块选择时保存",
                    value=self.save_on_module_selection,
                    help="选择模块时自动保存"
                )
                self.save_on_module_selection = save_on_module_selection
            
            # 手动备份操作
            st.markdown("#### 🔧 手动备份操作")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 立即备份"):
                    self.state_manager._create_session_backup()
                    st.success("备份已创建")
            
            with col2:
                if st.button("🔄 恢复备份"):
                    self.state_manager._attempt_session_recovery()
                    st.success("已尝试从备份恢复")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ 清除备份"):
                    if st.session_state.get("confirm_clear_backup", False):
                        st.session_state.intelligent_workflow_backup = None
                        st.session_state.intelligent_workflow_last_backup = None
                        st.success("备份已清除")
                        st.session_state.confirm_clear_backup = False
                        st.rerun()
                    else:
                        st.session_state.confirm_clear_backup = True
                        st.warning("确定清除备份？再次点击确认")
            
        except Exception as e:
            logger.error(f"Error rendering auto save panel: {str(e)}")
            st.error(f"自动保存面板渲染错误: {str(e)}")
    
    def _render_data_cleanup_panel(self):
        """渲染数据清理面板"""
        try:
            st.markdown("#### 🧹 数据清理")
            
            # 存储使用情况
            storage_info = self._get_storage_info()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("历史会话数", storage_info["session_count"])
            
            with col2:
                st.metric("存储使用", f"{storage_info['storage_size_mb']:.1f} MB")
            
            with col3:
                st.metric("最老会话", storage_info["oldest_session_age"])
            
            # 清理选项
            st.markdown("**清理选项**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                cleanup_days = st.slider(
                    "清理天数前的数据",
                    min_value=1,
                    max_value=30,
                    value=7,
                    help="清理指定天数前的会话数据"
                )
                
                if st.button("🗑️ 清理旧数据"):
                    if st.session_state.get("confirm_cleanup", False):
                        self.state_manager.cleanup_old_data(cleanup_days)
                        st.success(f"已清理 {cleanup_days} 天前的数据")
                        st.session_state.confirm_cleanup = False
                        st.rerun()
                    else:
                        st.session_state.confirm_cleanup = True
                        st.warning(f"确定清理 {cleanup_days} 天前的数据？再次点击确认")
            
            with col2:
                if st.button("🔄 重置所有数据"):
                    if st.session_state.get("confirm_reset_all", False):
                        self._reset_all_data()
                        st.success("所有数据已重置")
                        st.session_state.confirm_reset_all = False
                        st.rerun()
                    else:
                        st.session_state.confirm_reset_all = True
                        st.error("⚠️ 这将删除所有会话数据！再次点击确认")
            
            # 会话超时设置
            st.markdown("**会话超时设置**")
            
            timeout_hours = st.slider(
                "会话超时时间（小时）",
                min_value=1,
                max_value=72,
                value=self.session_timeout_hours,
                help="会话在指定时间后自动过期"
            )
            
            if timeout_hours != self.session_timeout_hours:
                self.session_timeout_hours = timeout_hours
                self.state_manager.session_timeout_hours = timeout_hours
                st.success(f"会话超时时间已设置为 {timeout_hours} 小时")
            
        except Exception as e:
            logger.error(f"Error rendering data cleanup panel: {str(e)}")
            st.error(f"数据清理面板渲染错误: {str(e)}")
    
    def _get_storage_info(self) -> Dict[str, Any]:
        """获取存储使用信息"""
        try:
            history = self.state_manager.get_session_history()
            
            session_count = len(history)
            
            # 估算存储大小（简化计算）
            storage_size_mb = session_count * 0.1  # 假设每个会话约0.1MB
            
            # 最老会话年龄
            oldest_session_age = "无"
            if history:
                oldest_session = min(history, key=lambda x: x.creation_time)
                age_days = (datetime.now() - oldest_session.creation_time).days
                if age_days == 0:
                    oldest_session_age = "今天"
                elif age_days == 1:
                    oldest_session_age = "1天前"
                else:
                    oldest_session_age = f"{age_days}天前"
            
            return {
                "session_count": session_count,
                "storage_size_mb": storage_size_mb,
                "oldest_session_age": oldest_session_age
            }
            
        except Exception as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return {
                "session_count": 0,
                "storage_size_mb": 0.0,
                "oldest_session_age": "未知"
            }
    
    def _duplicate_session(self, session: IntelligentWorkflowSession) -> Optional[IntelligentWorkflowSession]:
        """复制会话"""
        try:
            # 创建新会话ID
            new_session_id = f"{session.session_id}_copy_{datetime.now().strftime('%H%M%S')}"
            
            # 创建会话副本
            new_session = IntelligentWorkflowSession(
                session_id=new_session_id,
                current_state=session.current_state,
                product_analysis=session.product_analysis,
                module_recommendation=session.module_recommendation,
                selected_modules=session.selected_modules.copy(),
                module_contents=session.module_contents.copy(),
                selected_style_theme=session.selected_style_theme,
                compliance_results=session.compliance_results.copy(),
                generation_results={},  # 不复制生成结果
                generation_status={module: GenerationStatus.NOT_STARTED for module in session.selected_modules},
                user_edits=session.user_edits.copy(),
                workflow_metadata=session.workflow_metadata.copy()
            )
            
            # 保存当前会话并加载新会话
            self.state_manager.save_current_session_to_history()
            self.state_manager.workflow_controller.load_session(new_session)
            st.session_state.intelligent_workflow_session = new_session
            
            logger.info(f"Session duplicated: {session.session_id} -> {new_session_id}")
            return new_session
            
        except Exception as e:
            logger.error(f"Error duplicating session: {str(e)}")
            return None
    
    def _delete_session_from_history(self, session_id: str):
        """从历史记录中删除会话"""
        try:
            history = st.session_state.get('intelligent_workflow_history', [])
            updated_history = [session for session in history if session.session_id != session_id]
            st.session_state.intelligent_workflow_history = updated_history
            
            logger.info(f"Session deleted from history: {session_id}")
            
        except Exception as e:
            logger.error(f"Error deleting session from history: {str(e)}")
    
    def _reset_all_data(self):
        """重置所有数据"""
        try:
            # 清除所有会话相关的状态
            st.session_state.intelligent_workflow_session = None
            st.session_state.intelligent_workflow_history = []
            st.session_state.intelligent_workflow_backup = None
            st.session_state.intelligent_workflow_last_backup = None
            st.session_state.intelligent_workflow_recovery_data = {}
            st.session_state.intelligent_workflow_user_edits = {}
            st.session_state.intelligent_workflow_temp_data = {}
            
            # 重置工作流控制器
            self.state_manager.workflow_controller.clear_current_session()
            
            logger.info("All session data has been reset")
            
        except Exception as e:
            logger.error(f"Error resetting all data: {str(e)}")
    
    def setup_auto_save_callbacks(self):
        """设置自动保存回调"""
        try:
            # 这个方法可以在主应用中调用，设置各种自动保存触发器
            if self.enable_auto_save:
                # 在状态管理器中启用自动保存
                self.state_manager.auto_save_enabled = True
                
                # 设置定期备份
                if 'last_auto_save' not in st.session_state:
                    st.session_state.last_auto_save = datetime.now()
                
                # 检查是否需要自动保存
                time_since_last_save = datetime.now() - st.session_state.last_auto_save
                if time_since_last_save.total_seconds() > (self.auto_save_interval_minutes * 60):
                    self.state_manager._create_session_backup()
                    st.session_state.last_auto_save = datetime.now()
                    logger.debug("Auto-save triggered by time interval")
            
        except Exception as e:
            logger.error(f"Error setting up auto save callbacks: {str(e)}")
    
    def handle_session_timeout(self):
        """处理会话超时"""
        try:
            session = self.state_manager.get_current_session()
            if not session:
                return
            
            # 检查会话是否超时
            session_age = datetime.now() - session.last_updated
            if session_age.total_seconds() > (self.session_timeout_hours * 3600):
                st.warning(f"⏰ 会话已超时（{self.session_timeout_hours}小时无活动）")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 继续使用"):
                        # 更新会话时间戳
                        session.last_updated = datetime.now()
                        self.state_manager._save_session(session)
                        st.success("会话已续期")
                        st.rerun()
                
                with col2:
                    if st.button("💾 保存并结束"):
                        self.state_manager.save_current_session_to_history()
                        self.state_manager.clear_current_session()
                        st.success("会话已保存并结束")
                        st.rerun()
                
                return True  # 表示会话已超时
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling session timeout: {str(e)}")
            return False