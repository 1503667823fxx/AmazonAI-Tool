"""
A+ 工作流管理服务
负责工作流状态管理和步骤处理
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json
import os

from app_utils.aplus_studio.interfaces import IWorkflowEngine, IStepProcessor
from app_utils.aplus_studio.models.core_models import WorkflowSession, WorkflowStatus, ProductData


class WorkflowService(IWorkflowEngine):
    """A+ 工作流管理服务"""
    
    def __init__(self, sessions_dir: str = "data/workflow_sessions"):
        self.sessions_dir = sessions_dir
        self._sessions_cache: Dict[str, WorkflowSession] = {}
        self._ensure_sessions_dir()
    
    def _ensure_sessions_dir(self):
        """确保会话目录存在"""
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    def create_session(self, user_id: str, template_id: str, total_steps: int = 5) -> WorkflowSession:
        """创建新的工作流会话"""
        session_id = str(uuid.uuid4())
        
        session = WorkflowSession(
            session_id=session_id,
            user_id=user_id,
            template_id=template_id,
            current_step=0,
            total_steps=total_steps,
            step_data={},
            product_data=None,
            customization_options={},
            status=WorkflowStatus.NOT_STARTED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存到缓存和文件
        self._sessions_cache[session_id] = session
        self._save_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        """获取工作流会话"""
        # 先从缓存中查找
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]
        
        # 从文件中加载
        session = self._load_session(session_id)
        if session:
            self._sessions_cache[session_id] = session
        
        return session
    
    def update_session(self, session: WorkflowSession) -> bool:
        """更新工作流会话"""
        try:
            session.updated_at = datetime.now()
            
            # 更新缓存
            self._sessions_cache[session.session_id] = session
            
            # 保存到文件
            self._save_session(session)
            
            return True
        except Exception as e:
            print(f"更新会话失败: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """删除工作流会话"""
        try:
            # 从缓存中删除
            if session_id in self._sessions_cache:
                del self._sessions_cache[session_id]
            
            # 删除文件
            session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                os.remove(session_file)
            
            return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False
    
    def next_step(self, session_id: str) -> bool:
        """进入下一步"""
        return self.advance_step(session_id)
    
    def previous_step(self, session_id: str) -> bool:
        """返回上一步"""
        return self.go_back_step(session_id)
    
    def complete_workflow(self, session_id: str) -> bool:
        """完成工作流"""
        return self.complete_session(session_id)
    
    def save_progress(self, session_id: str) -> bool:
        """保存进度"""
        session = self.get_session(session_id)
        if not session:
            return False
        return self.update_session(session)
    
    def advance_step(self, session_id: str) -> bool:
        """推进到下一步"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.current_step < session.total_steps:
            session.current_step += 1
            session.status = WorkflowStatus.IN_PROGRESS
            return self.update_session(session)
        
        return False
    
    def go_back_step(self, session_id: str) -> bool:
        """回退到上一步"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.current_step > 0:
            session.current_step -= 1
            session.status = WorkflowStatus.IN_PROGRESS
            return self.update_session(session)
        
        return False
    
    def complete_session(self, session_id: str) -> bool:
        """完成工作流会话"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = WorkflowStatus.COMPLETED
        session.current_step = session.total_steps
        return self.update_session(session)
    
    def pause_session(self, session_id: str) -> bool:
        """暂停工作流会话"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = WorkflowStatus.PAUSED
        return self.update_session(session)
    
    def resume_session(self, session_id: str) -> bool:
        """恢复工作流会话"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = WorkflowStatus.IN_PROGRESS
        return self.update_session(session)
    
    def fail_session(self, session_id: str, error_message: str = "") -> bool:
        """标记会话失败"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = WorkflowStatus.FAILED
        if error_message:
            session.step_data["error_message"] = error_message
        return self.update_session(session)
    
    def update_step_data(self, session_id: str, step_key: str, step_value: Any) -> bool:
        """更新步骤数据"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.step_data[step_key] = step_value
        return self.update_session(session)
    
    def update_product_data(self, session_id: str, product_data: ProductData) -> bool:
        """更新产品数据"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.product_data = product_data
        return self.update_session(session)
    
    def update_customization_options(self, session_id: str, options: Dict[str, Any]) -> bool:
        """更新定制选项"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.customization_options.update(options)
        return self.update_session(session)
    
    def get_user_sessions(self, user_id: str) -> List[WorkflowSession]:
        """获取用户的所有会话"""
        user_sessions = []
        
        # 从缓存中查找
        for session in self._sessions_cache.values():
            if session.user_id == user_id:
                user_sessions.append(session)
        
        # 从文件中加载（如果缓存中没有）
        try:
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # 移除.json后缀
                    if session_id not in self._sessions_cache:
                        session = self._load_session(session_id)
                        if session and session.user_id == user_id:
                            user_sessions.append(session)
                            self._sessions_cache[session_id] = session
        except Exception as e:
            print(f"加载用户会话失败: {e}")
        
        # 按创建时间排序
        user_sessions.sort(key=lambda x: x.created_at, reverse=True)
        return user_sessions
    
    def get_active_sessions(self) -> List[WorkflowSession]:
        """获取所有活跃会话"""
        active_sessions = []
        
        # 从缓存中查找
        for session in self._sessions_cache.values():
            if session.status in [WorkflowStatus.IN_PROGRESS, WorkflowStatus.PAUSED]:
                active_sessions.append(session)
        
        return active_sessions
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """清理旧会话"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
        
        cleaned_count = 0
        
        try:
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]
                    session = self._load_session(session_id)
                    
                    if session and session.created_at < cutoff_date:
                        if session.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                            self.delete_session(session_id)
                            cleaned_count += 1
        except Exception as e:
            print(f"清理旧会话失败: {e}")
        
        return cleaned_count
    
    def _save_session(self, session: WorkflowSession) -> None:
        """保存会话到文件"""
        session_file = os.path.join(self.sessions_dir, f"{session.session_id}.json")
        
        try:
            session_data = session.to_dict()
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"保存会话文件失败: {e}")
    
    def _load_session(self, session_id: str) -> Optional[WorkflowSession]:
        """从文件加载会话"""
        session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
        
        if not os.path.exists(session_file):
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            return WorkflowSession.from_dict(session_data)
        except Exception as e:
            print(f"加载会话文件失败: {e}")
            return None


class StepProcessorService(IStepProcessor):
    """A+ 工作流步骤处理服务"""
    
    def __init__(self):
        self.step_handlers = {
            0: self._handle_template_selection,
            1: self._handle_product_input,
            2: self._handle_customization,
            3: self._handle_ai_processing,
            4: self._handle_result_generation
        }
    
    def process_step(self, session: WorkflowSession, step_data: Dict[str, Any]) -> bool:
        """处理工作流步骤"""
        current_step = session.current_step
        
        if current_step in self.step_handlers:
            result = self.step_handlers[current_step](session, step_data)
            return result.get("success", False)
        else:
            return False
    
    def validate_step(self, session: WorkflowSession, step_number: int) -> bool:
        """验证步骤完成条件"""
        if step_number == 0:  # 模板选择
            return bool(session.template_id)
        elif step_number == 1:  # 产品输入
            return bool(session.product_data and 
                       session.product_data.name and 
                       session.product_data.category)
        elif step_number == 2:  # 定制选项
            return bool(session.customization_options.get("color_scheme"))
        elif step_number == 3:  # AI处理
            return bool(session.step_data.get("ai_processing_started"))
        elif step_number == 4:  # 结果生成
            return bool(session.step_data.get("result_generated"))
        else:
            return False
    
    def process_step_detailed(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流步骤"""
        current_step = session.current_step
        
        if current_step in self.step_handlers:
            return self.step_handlers[current_step](session, step_data)
        else:
            return {
                "success": False,
                "message": f"未知步骤: {current_step}",
                "next_step": current_step
            }
    
    def validate_step_data(self, step: int, data: Dict[str, Any]) -> List[str]:
        """验证步骤数据"""
        errors = []
        
        if step == 0:  # 模板选择
            if not data.get("template_id"):
                errors.append("请选择模板")
        
        elif step == 1:  # 产品输入
            if not data.get("product_name"):
                errors.append("请输入产品名称")
            if not data.get("product_category"):
                errors.append("请选择产品分类")
            if not data.get("product_images"):
                errors.append("请上传产品图片")
        
        elif step == 2:  # 定制选项
            if not data.get("color_scheme"):
                errors.append("请选择配色方案")
        
        elif step == 3:  # AI处理
            if not data.get("processing_options"):
                errors.append("请配置AI处理选项")
        
        return errors
    
    def get_step_requirements(self, step: int) -> Dict[str, Any]:
        """获取步骤要求"""
        requirements = {
            0: {
                "title": "选择模板",
                "description": "从模板库中选择适合的A+页面模板",
                "required_fields": ["template_id"],
                "optional_fields": ["preview_mode"]
            },
            1: {
                "title": "产品信息",
                "description": "填写产品详细信息和上传产品图片",
                "required_fields": ["product_name", "product_category", "product_images"],
                "optional_fields": ["product_features", "brand_info", "additional_info"]
            },
            2: {
                "title": "定制选项",
                "description": "选择配色方案和布局样式",
                "required_fields": ["color_scheme"],
                "optional_fields": ["layout_style", "font_style", "custom_elements"]
            },
            3: {
                "title": "AI处理",
                "description": "配置AI处理选项并开始生成",
                "required_fields": ["processing_options"],
                "optional_fields": ["quality_settings", "output_format"]
            },
            4: {
                "title": "结果生成",
                "description": "查看生成结果并下载文件",
                "required_fields": [],
                "optional_fields": ["download_format", "feedback"]
            }
        }
        
        return requirements.get(step, {})
    
    def _handle_template_selection(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理模板选择步骤"""
        template_id = step_data.get("template_id")
        
        if not template_id:
            return {
                "success": False,
                "message": "请选择模板",
                "next_step": 0
            }
        
        # 更新会话数据
        session.template_id = template_id
        session.step_data["selected_template"] = template_id
        
        return {
            "success": True,
            "message": "模板选择成功",
            "next_step": 1,
            "data": {"template_id": template_id}
        }
    
    def _handle_product_input(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理产品输入步骤"""
        required_fields = ["product_name", "product_category"]
        
        for field in required_fields:
            if not step_data.get(field):
                return {
                    "success": False,
                    "message": f"请填写{field}",
                    "next_step": 1
                }
        
        # 创建产品数据对象
        from app_utils.aplus_studio.models.core_models import ProductData, UploadedFile
        
        product_data = ProductData(
            name=step_data["product_name"],
            category=step_data["product_category"],
            features=step_data.get("product_features", []),
            brand_name=step_data.get("brand_name", ""),
            brand_color=step_data.get("brand_color", "#000000"),
            images=step_data.get("product_images", []),
            additional_info=step_data.get("additional_info", {})
        )
        
        # 更新会话数据
        session.product_data = product_data
        session.step_data["product_input_completed"] = True
        
        return {
            "success": True,
            "message": "产品信息录入成功",
            "next_step": 2,
            "data": {"product_data": product_data.to_dict()}
        }
    
    def _handle_customization(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理定制选项步骤"""
        color_scheme = step_data.get("color_scheme")
        
        if not color_scheme:
            return {
                "success": False,
                "message": "请选择配色方案",
                "next_step": 2
            }
        
        # 更新定制选项
        customization_options = {
            "color_scheme": color_scheme,
            "layout_style": step_data.get("layout_style", "标准布局"),
            "font_style": step_data.get("font_style", "默认字体"),
            "custom_elements": step_data.get("custom_elements", {})
        }
        
        session.customization_options.update(customization_options)
        session.step_data["customization_completed"] = True
        
        return {
            "success": True,
            "message": "定制选项配置成功",
            "next_step": 3,
            "data": {"customization_options": customization_options}
        }
    
    def _handle_ai_processing(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理AI处理步骤"""
        processing_options = step_data.get("processing_options", {})
        
        # 更新处理选项
        session.step_data["ai_processing_options"] = processing_options
        session.step_data["ai_processing_started"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "AI处理已开始",
            "next_step": 4,
            "data": {
                "processing_options": processing_options,
                "estimated_time": "2-3分钟"
            }
        }
    
    def _handle_result_generation(self, session: WorkflowSession, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理结果生成步骤"""
        # 标记处理完成
        session.step_data["result_generated"] = True
        session.step_data["generation_completed"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "A+页面生成完成",
            "next_step": 4,
            "data": {
                "result_ready": True,
                "download_available": True
            }
        }
