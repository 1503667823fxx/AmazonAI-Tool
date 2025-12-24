"""
会话管理器

跟踪用户状态和素材的会话管理系统，负责：
- 模块选择的会话状态跟踪
- 临时素材存储系统
- 生成进度状态管理
- 会话清理和持久化
- 会话恢复机制
"""

import logging
import json
import os
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import threading
from dataclasses import asdict

from .models import (
    ModuleType, MaterialSet, GenerationConfig, GeneratedModule,
    GenerationStatus, APlusSession, ProductInfo, AnalysisResult
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器
    
    管理用户会话的生命周期，包括状态跟踪、数据持久化和资源清理。
    """
    
    def __init__(self, 
                 session_dir: str = "temp/aplus_sessions",
                 session_timeout_hours: int = 24,
                 max_concurrent_sessions: int = 100):
        """
        初始化会话管理器
        
        Args:
            session_dir: 会话数据存储目录
            session_timeout_hours: 会话超时时间（小时）
            max_concurrent_sessions: 最大并发会话数
        """
        self.session_dir = Path(session_dir)
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.max_concurrent_sessions = max_concurrent_sessions
        
        # 内存中的会话缓存
        self._active_sessions: Dict[str, APlusSession] = {}
        self._session_lock = threading.RLock()
        
        # 管理器状态
        self._is_initialized = False
        self._cleanup_stats = {
            'sessions_cleaned': 0,
            'files_cleaned': 0,
            'last_cleanup': None
        }
        
        # 确保目录存在
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self):
        """初始化会话管理器"""
        try:
            # 加载现有会话
            self._load_existing_sessions()
            
            # 清理过期会话
            self._cleanup_expired_sessions()
            
            self._is_initialized = True
            logger.info(f"Session manager initialized with {len(self._active_sessions)} active sessions")
            
        except Exception as e:
            logger.error(f"Failed to initialize session manager: {str(e)}")
            self._is_initialized = False
    
    def create_session(self, 
                      selected_modules: List[ModuleType],
                      generation_config: Optional[GenerationConfig] = None,
                      product_info: Optional[ProductInfo] = None) -> str:
        """
        创建新的会话
        
        Args:
            selected_modules: 选中的模块类型列表
            generation_config: 生成配置
            product_info: 产品信息
            
        Returns:
            会话ID
        """
        try:
            with self._session_lock:
                # 检查会话数量限制
                if len(self._active_sessions) >= self.max_concurrent_sessions:
                    # 清理最旧的会话
                    self._cleanup_oldest_sessions(1)
                
                # 生成会话ID
                session_id = str(uuid.uuid4())
                
                # 创建会话对象
                session = APlusSession(
                    session_id=session_id,
                    product_info=product_info,
                    analysis_result=None,
                    visual_style=None,
                    selected_modules=selected_modules,
                    generation_config=generation_config,
                    creation_time=datetime.now(),
                    last_updated=datetime.now()
                )
                
                # 初始化生成状态
                for module_type in selected_modules:
                    session.generation_status[module_type] = GenerationStatus.NOT_STARTED
                
                # 保存到内存和磁盘
                self._active_sessions[session_id] = session
                self._persist_session(session)
                
                logger.info(f"Created session {session_id} with {len(selected_modules)} modules")
                return session_id
                
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[APlusSession]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话对象，如果不存在则返回None
        """
        try:
            with self._session_lock:
                session = self._active_sessions.get(session_id)
                
                if session:
                    # 检查会话是否过期
                    if self._is_session_expired(session):
                        self._cleanup_session_internal(session_id)
                        return None
                    
                    # 更新最后访问时间
                    session.last_updated = datetime.now()
                    return session
                
                # 尝试从磁盘加载
                session = self._load_session_from_disk(session_id)
                if session and not self._is_session_expired(session):
                    self._active_sessions[session_id] = session
                    session.last_updated = datetime.now()
                    return session
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None
    
    def update_session_materials(self, 
                                session_id: str,
                                module_type: ModuleType,
                                materials: MaterialSet) -> bool:
        """
        更新会话的素材
        
        Args:
            session_id: 会话ID
            module_type: 模块类型
            materials: 素材集合
            
        Returns:
            是否成功更新
        """
        try:
            with self._session_lock:
                session = self.get_session(session_id)
                if not session:
                    return False
                
                # 更新素材
                session.material_sets[module_type] = materials
                session.last_updated = datetime.now()
                
                # 持久化
                self._persist_session(session)
                
                logger.debug(f"Updated materials for {module_type.value} in session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update session materials: {str(e)}")
            return False
    
    def update_generation_status(self, 
                                session_id: str,
                                module_type: ModuleType,
                                status: GenerationStatus) -> bool:
        """
        更新生成状态
        
        Args:
            session_id: 会话ID
            module_type: 模块类型
            status: 新状态
            
        Returns:
            是否成功更新
        """
        try:
            with self._session_lock:
                session = self.get_session(session_id)
                if not session:
                    return False
                
                # 更新状态
                old_status = session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
                session.generation_status[module_type] = status
                session.last_updated = datetime.now()
                
                # 持久化
                self._persist_session(session)
                
                logger.debug(f"Updated {module_type.value} status: {old_status.value} -> {status.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update generation status: {str(e)}")
            return False
    
    def save_generated_module(self, 
                             session_id: str,
                             module_type: ModuleType,
                             generated_module: GeneratedModule) -> bool:
        """
        保存生成的模块
        
        Args:
            session_id: 会话ID
            module_type: 模块类型
            generated_module: 生成的模块
            
        Returns:
            是否成功保存
        """
        try:
            with self._session_lock:
                session = self.get_session(session_id)
                if not session:
                    return False
                
                # 保存模块结果
                session.module_results[module_type] = generated_module
                session.last_updated = datetime.now()
                
                # 如果有图片数据，保存到文件
                if generated_module.image_data:
                    image_path = self._save_module_image(session_id, module_type, generated_module.image_data)
                    generated_module.image_path = image_path
                
                # 持久化
                self._persist_session(session)
                
                logger.info(f"Saved generated module {module_type.value} for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save generated module: {str(e)}")
            return False
    
    def get_active_sessions(self) -> List[str]:
        """
        获取活跃会话列表
        
        Returns:
            活跃会话ID列表
        """
        try:
            with self._session_lock:
                # 清理过期会话
                expired_sessions = [
                    sid for sid, session in self._active_sessions.items()
                    if self._is_session_expired(session)
                ]
                
                for sid in expired_sessions:
                    self._cleanup_session_internal(sid)
                
                return list(self._active_sessions.keys())
                
        except Exception as e:
            logger.error(f"Failed to get active sessions: {str(e)}")
            return []
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        清理指定会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功清理
        """
        try:
            with self._session_lock:
                return self._cleanup_session_internal(session_id)
                
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理所有过期会话
        
        Returns:
            清理的会话数量
        """
        try:
            with self._session_lock:
                return self._cleanup_expired_sessions()
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with self._session_lock:
                active_count = len(self._active_sessions)
                
                # 统计各状态的会话数
                status_counts = {}
                total_modules = 0
                completed_modules = 0
                
                for session in self._active_sessions.values():
                    total_modules += len(session.selected_modules)
                    
                    for module_type in session.selected_modules:
                        status = session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
                        status_counts[status.value] = status_counts.get(status.value, 0) + 1
                        
                        if status == GenerationStatus.COMPLETED:
                            completed_modules += 1
                
                return {
                    'active_sessions': active_count,
                    'total_modules': total_modules,
                    'completed_modules': completed_modules,
                    'completion_rate': (completed_modules / total_modules * 100) if total_modules > 0 else 0,
                    'status_distribution': status_counts,
                    'cleanup_stats': self._cleanup_stats.copy(),
                    'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
                    'max_concurrent_sessions': self.max_concurrent_sessions
                }
                
        except Exception as e:
            logger.error(f"Failed to get session statistics: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        try:
            # 检查目录访问权限
            test_file = self.session_dir / "health_check.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            # 获取统计信息
            stats = self.get_session_statistics()
            
            # 检查会话数量是否正常
            active_sessions = stats.get('active_sessions', 0)
            if active_sessions > self.max_concurrent_sessions * 0.9:
                status = 'warning'
                message = 'High session count'
            elif not self._is_initialized:
                status = 'error'
                message = 'Not initialized'
            else:
                status = 'healthy'
                message = 'All systems operational'
            
            return {
                'status': status,
                'message': message,
                'initialized': self._is_initialized,
                'session_dir_accessible': True,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session manager health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'initialized': self._is_initialized,
                'session_dir_accessible': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def _load_existing_sessions(self):
        """加载现有会话"""
        try:
            if not self.session_dir.exists():
                return
            
            loaded_count = 0
            for session_file in self.session_dir.glob("*.json"):
                try:
                    session = self._load_session_from_file(session_file)
                    if session and not self._is_session_expired(session):
                        self._active_sessions[session.session_id] = session
                        loaded_count += 1
                    else:
                        # 删除过期会话文件
                        session_file.unlink(missing_ok=True)
                        
                except Exception as e:
                    logger.warning(f"Failed to load session from {session_file}: {str(e)}")
            
            logger.info(f"Loaded {loaded_count} existing sessions")
            
        except Exception as e:
            logger.error(f"Failed to load existing sessions: {str(e)}")
    
    def _load_session_from_disk(self, session_id: str) -> Optional[APlusSession]:
        """从磁盘加载会话"""
        try:
            session_file = self.session_dir / f"{session_id}.json"
            if session_file.exists():
                return self._load_session_from_file(session_file)
            return None
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id} from disk: {str(e)}")
            return None
    
    def _load_session_from_file(self, session_file: Path) -> Optional[APlusSession]:
        """从文件加载会话"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重建会话对象
            session = self._deserialize_session(data)
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session from file {session_file}: {str(e)}")
            return None
    
    def _persist_session(self, session: APlusSession):
        """持久化会话到磁盘"""
        try:
            session_file = self.session_dir / f"{session.session_id}.json"
            
            # 序列化会话数据
            session_data = self._serialize_session(session)
            
            # 写入文件
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {str(e)}")
    
    def _serialize_session(self, session: APlusSession) -> Dict[str, Any]:
        """序列化会话对象"""
        try:
            # 转换为字典
            data = asdict(session)
            
            # 处理特殊字段
            data['selected_modules'] = [m.value for m in session.selected_modules]
            data['generation_status'] = {
                m.value: status.value for m, status in session.generation_status.items()
            }
            
            # 处理模块结果（不保存图片数据到JSON）
            if session.module_results:
                data['module_results'] = {}
                for module_type, result in session.module_results.items():
                    result_data = asdict(result)
                    result_data['module_type'] = module_type.value
                    result_data['compliance_status'] = result.compliance_status.value
                    result_data['validation_status'] = result.validation_status.value
                    # 不保存图片数据，只保存路径
                    result_data['image_data'] = None
                    data['module_results'][module_type.value] = result_data
            
            # 处理素材集合（不保存实际文件内容）
            if session.material_sets:
                data['material_sets'] = {}
                for module_type, materials in session.material_sets.items():
                    materials_data = asdict(materials)
                    # 只保存文件元数据，不保存内容
                    materials_data['images'] = [
                        {
                            'filename': f.filename,
                            'file_type': f.file_type.value,
                            'file_size': f.file_size,
                            'upload_timestamp': f.upload_timestamp.isoformat(),
                            'validation_status': f.validation_status.value
                        } for f in materials.images
                    ]
                    materials_data['documents'] = [
                        {
                            'filename': f.filename,
                            'file_type': f.file_type.value,
                            'file_size': f.file_size,
                            'upload_timestamp': f.upload_timestamp.isoformat(),
                            'validation_status': f.validation_status.value
                        } for f in materials.documents
                    ]
                    data['material_sets'][module_type.value] = materials_data
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to serialize session: {str(e)}")
            raise
    
    def _deserialize_session(self, data: Dict[str, Any]) -> APlusSession:
        """反序列化会话对象"""
        try:
            # 重建基本字段
            session = APlusSession(
                session_id=data['session_id'],
                product_info=None,  # 简化处理
                analysis_result=None,  # 简化处理
                visual_style=None,  # 简化处理
                selected_modules=[ModuleType(m) for m in data.get('selected_modules', [])],
                creation_time=datetime.fromisoformat(data['creation_time']),
                last_updated=datetime.fromisoformat(data['last_updated'])
            )
            
            # 重建生成状态
            if 'generation_status' in data:
                session.generation_status = {
                    ModuleType(m): GenerationStatus(status)
                    for m, status in data['generation_status'].items()
                }
            
            # 重建模块结果（简化版本，不包含实际图片数据）
            if 'module_results' in data:
                from .models import GeneratedModule, ComplianceStatus, ValidationStatus
                session.module_results = {}
                for module_str, result_data in data['module_results'].items():
                    module_type = ModuleType(module_str)
                    result = GeneratedModule(
                        module_type=module_type,
                        image_data=None,
                        image_path=result_data.get('image_path'),
                        compliance_status=ComplianceStatus(result_data.get('compliance_status', 'pending_review')),
                        generation_timestamp=datetime.fromisoformat(result_data['generation_timestamp']),
                        quality_score=result_data.get('quality_score', 0.0),
                        validation_status=ValidationStatus(result_data.get('validation_status', 'pending')),
                        prompt_used=result_data.get('prompt_used', ''),
                        generation_time=result_data.get('generation_time', 0.0)
                    )
                    session.module_results[module_type] = result
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to deserialize session: {str(e)}")
            raise
    
    def _is_session_expired(self, session: APlusSession) -> bool:
        """检查会话是否过期"""
        return datetime.now() - session.last_updated > self.session_timeout
    
    def _cleanup_session_internal(self, session_id: str) -> bool:
        """内部会话清理方法"""
        try:
            # 从内存中移除
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            
            # 删除会话文件
            session_file = self.session_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            # 删除会话相关的文件目录
            session_files_dir = self.session_dir / session_id
            if session_files_dir.exists():
                shutil.rmtree(session_files_dir)
            
            self._cleanup_stats['sessions_cleaned'] += 1
            logger.debug(f"Cleaned up session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
            return False
    
    def _cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            expired_sessions = [
                sid for sid, session in self._active_sessions.items()
                if self._is_session_expired(session)
            ]
            
            cleaned_count = 0
            for session_id in expired_sessions:
                if self._cleanup_session_internal(session_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self._cleanup_stats['last_cleanup'] = datetime.now().isoformat()
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0
    
    def _cleanup_oldest_sessions(self, count: int) -> int:
        """清理最旧的会话"""
        try:
            # 按最后更新时间排序
            sorted_sessions = sorted(
                self._active_sessions.items(),
                key=lambda x: x[1].last_updated
            )
            
            cleaned_count = 0
            for session_id, _ in sorted_sessions[:count]:
                if self._cleanup_session_internal(session_id):
                    cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup oldest sessions: {str(e)}")
            return 0
    
    def _save_module_image(self, session_id: str, module_type: ModuleType, image_data: bytes) -> str:
        """保存模块图片"""
        try:
            # 创建会话文件目录
            session_files_dir = self.session_dir / session_id
            session_files_dir.mkdir(exist_ok=True)
            
            # 生成图片文件名
            timestamp = int(datetime.now().timestamp())
            image_filename = f"{module_type.value}_{timestamp}.png"
            image_path = session_files_dir / image_filename
            
            # 保存图片
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            return str(image_path)
            
        except Exception as e:
            logger.error(f"Failed to save module image: {str(e)}")
            return ""