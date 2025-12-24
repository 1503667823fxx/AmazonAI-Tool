"""
A+ Studio 控制器

协调模块生成过程的主控制器，负责：
- 模块选择处理逻辑
- 素材上传协调
- 生成工作流程编排
- 合规验证集成
- 错误处理和恢复机制
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from .models import (
    ModuleType, MaterialSet, GenerationConfig, GeneratedModule,
    GenerationStatus, ComplianceStatus, ValidationStatus, APlusSession
)
from .module_factory import ModuleFactory
from .material_processor import MaterialProcessor
from .session_manager import SessionManager
from .batch_processor import BatchProcessor
from .modules import BaseModuleGenerator

logger = logging.getLogger(__name__)


class APlusStudioController:
    """
    A+ Studio 主控制器
    
    协调所有系统组件，提供统一的A+内容生成接口。
    """
    
    def __init__(self):
        """初始化控制器"""
        self.module_factory = ModuleFactory()
        self.material_processor = MaterialProcessor()
        self.session_manager = SessionManager()
        self.batch_processor = BatchProcessor()
        
        # 控制器状态
        self._is_initialized = False
        self._active_generations = {}  # session_id -> generation_info
        self._generation_stats = {
            'total_sessions': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'total_modules_generated': 0
        }
        
        # 初始化控制器
        self._initialize()
    
    def _initialize(self):
        """初始化控制器组件"""
        try:
            # 验证模块工厂状态
            factory_health = self.module_factory.health_check()
            if factory_health.get('factory_status') != 'healthy':
                logger.warning("Module factory health check failed")
            
            # 初始化会话管理器
            self.session_manager.initialize()
            
            # 初始化批处理器
            self.batch_processor.initialize()
            
            self._is_initialized = True
            logger.info("A+ Studio Controller initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize controller: {str(e)}")
            self._is_initialized = False
    
    def create_session(self, 
                      selected_modules: List[ModuleType],
                      generation_config: Optional[GenerationConfig] = None) -> str:
        """
        创建新的A+制作会话
        
        Args:
            selected_modules: 选中的模块类型列表
            generation_config: 生成配置参数
            
        Returns:
            会话ID
        """
        try:
            if not self._is_initialized:
                raise RuntimeError("Controller not properly initialized")
            
            # 验证模块选择
            if not selected_modules:
                raise ValueError("No modules selected")
            
            # 验证模块可用性
            available_modules = self.module_factory.get_available_modules()
            available_types = [m.module_type for m in available_modules]
            
            invalid_modules = [m for m in selected_modules if m not in available_types]
            if invalid_modules:
                raise ValueError(f"Invalid modules selected: {[m.value for m in invalid_modules]}")
            
            # 创建默认配置
            if generation_config is None:
                generation_config = GenerationConfig(
                    selected_modules=selected_modules,
                    language="zh",
                    compliance_level="strict",
                    batch_mode=len(selected_modules) > 3,
                    quality_threshold=0.8
                )
            
            # 创建会话
            session_id = self.session_manager.create_session(
                selected_modules=selected_modules,
                generation_config=generation_config
            )
            
            # 更新统计
            self._generation_stats['total_sessions'] += 1
            
            logger.info(f"Created session {session_id} with {len(selected_modules)} modules")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise
    
    def upload_materials(self, 
                        session_id: str,
                        module_type: ModuleType,
                        materials: MaterialSet) -> Dict[str, Any]:
        """
        为指定模块上传素材
        
        Args:
            session_id: 会话ID
            module_type: 模块类型
            materials: 素材集合
            
        Returns:
            上传结果信息
        """
        try:
            # 验证会话
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if module_type not in session.selected_modules:
                raise ValueError(f"Module {module_type.value} not selected in session")
            
            # 处理素材
            processed_materials = self.material_processor.process_materials(materials)
            
            # 验证素材需求
            validation_result = self.module_factory.validate_module_materials(
                module_type, processed_materials
            )
            
            # 保存素材到会话
            self.session_manager.update_session_materials(
                session_id, module_type, processed_materials
            )
            
            result = {
                'status': 'success',
                'module_type': module_type.value,
                'materials_count': {
                    'images': len(processed_materials.images),
                    'documents': len(processed_materials.documents),
                    'text_inputs': len(processed_materials.text_inputs),
                    'custom_prompts': len(processed_materials.custom_prompts)
                },
                'validation': validation_result,
                'total_size': processed_materials.get_total_file_size()
            }
            
            logger.info(f"Uploaded materials for {module_type.value} in session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload materials: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'module_type': module_type.value if module_type else None
            }
    
    def generate_module(self, 
                       session_id: str,
                       module_type: ModuleType,
                       force_regenerate: bool = False) -> Dict[str, Any]:
        """
        生成单个模块
        
        Args:
            session_id: 会话ID
            module_type: 模块类型
            force_regenerate: 是否强制重新生成
            
        Returns:
            生成结果信息
        """
        try:
            # 验证会话和模块
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if module_type not in session.selected_modules:
                raise ValueError(f"Module {module_type.value} not selected")
            
            # 检查是否已生成
            current_status = session.generation_status.get(module_type, GenerationStatus.NOT_STARTED)
            if current_status == GenerationStatus.COMPLETED and not force_regenerate:
                return {
                    'status': 'already_completed',
                    'module_type': module_type.value,
                    'message': 'Module already generated'
                }
            
            # 更新状态为进行中
            self.session_manager.update_generation_status(
                session_id, module_type, GenerationStatus.IN_PROGRESS
            )
            
            # 获取素材
            materials = session.material_sets.get(module_type, MaterialSet())
            
            # 创建模块生成器
            generator = self.module_factory.create_module(module_type, materials)
            if not generator:
                raise RuntimeError(f"Failed to create generator for {module_type.value}")
            
            # 执行生成
            start_time = datetime.now()
            
            try:
                # 这里应该调用实际的生成逻辑
                # 目前使用模拟生成
                generated_module = self._simulate_module_generation(
                    generator, module_type, materials, session.generation_config
                )
                
                generation_time = (datetime.now() - start_time).total_seconds()
                generated_module.generation_time = generation_time
                
                # 合规验证
                compliance_result = self._validate_compliance(generated_module)
                generated_module.compliance_status = compliance_result['status']
                
                # 保存结果
                self.session_manager.save_generated_module(
                    session_id, module_type, generated_module
                )
                
                # 更新状态
                self.session_manager.update_generation_status(
                    session_id, module_type, GenerationStatus.COMPLETED
                )
                
                # 更新统计
                self._generation_stats['successful_generations'] += 1
                self._generation_stats['total_modules_generated'] += 1
                
                result = {
                    'status': 'success',
                    'module_type': module_type.value,
                    'generation_time': generation_time,
                    'quality_score': generated_module.quality_score,
                    'compliance_status': generated_module.compliance_status.value,
                    'validation_status': generated_module.validation_status.value
                }
                
                logger.info(f"Successfully generated {module_type.value} in {generation_time:.2f}s")
                return result
                
            except Exception as gen_error:
                # 生成失败，更新状态
                self.session_manager.update_generation_status(
                    session_id, module_type, GenerationStatus.FAILED
                )
                
                self._generation_stats['failed_generations'] += 1
                
                raise gen_error
                
        except Exception as e:
            logger.error(f"Failed to generate module {module_type.value}: {str(e)}")
            return {
                'status': 'error',
                'module_type': module_type.value,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def batch_generate_modules(self, 
                              session_id: str,
                              module_types: Optional[List[ModuleType]] = None,
                              max_concurrent: int = 3) -> Dict[str, Any]:
        """
        批量生成模块
        
        Args:
            session_id: 会话ID
            module_types: 要生成的模块类型列表，None表示生成所有选中的模块
            max_concurrent: 最大并发数
            
        Returns:
            批量生成结果
        """
        try:
            # 验证会话
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # 确定要生成的模块
            if module_types is None:
                module_types = session.selected_modules
            else:
                # 验证模块是否在选中列表中
                invalid_modules = [m for m in module_types if m not in session.selected_modules]
                if invalid_modules:
                    raise ValueError(f"Modules not selected: {[m.value for m in invalid_modules]}")
            
            # 过滤已完成的模块
            pending_modules = [
                m for m in module_types 
                if session.generation_status.get(m, GenerationStatus.NOT_STARTED) != GenerationStatus.COMPLETED
            ]
            
            if not pending_modules:
                return {
                    'status': 'all_completed',
                    'message': 'All modules already generated',
                    'total_modules': len(module_types),
                    'completed_modules': len(module_types)
                }
            
            # 记录批量生成开始
            batch_id = f"batch_{session_id}_{int(datetime.now().timestamp())}"
            self._active_generations[session_id] = {
                'batch_id': batch_id,
                'start_time': datetime.now(),
                'total_modules': len(pending_modules),
                'completed_modules': 0,
                'failed_modules': 0,
                'status': 'running'
            }
            
            # 使用批处理器执行生成
            batch_result = self.batch_processor.process_batch(
                session_id=session_id,
                module_types=pending_modules,
                max_concurrent=max_concurrent,
                progress_callback=self._batch_progress_callback
            )
            
            # 更新活跃生成状态
            if session_id in self._active_generations:
                self._active_generations[session_id]['status'] = 'completed'
                self._active_generations[session_id]['end_time'] = datetime.now()
            
            return batch_result
            
        except Exception as e:
            # 更新失败状态
            if session_id in self._active_generations:
                self._active_generations[session_id]['status'] = 'failed'
                self._active_generations[session_id]['error'] = str(e)
            
            logger.error(f"Batch generation failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'session_id': session_id
            }
    
    def get_generation_progress(self, session_id: str) -> Dict[str, Any]:
        """
        获取生成进度
        
        Args:
            session_id: 会话ID
            
        Returns:
            进度信息
        """
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # 计算进度统计
            total_modules = len(session.selected_modules)
            completed_modules = len([
                m for m, status in session.generation_status.items()
                if m in session.selected_modules and status == GenerationStatus.COMPLETED
            ])
            
            in_progress_modules = len([
                m for m, status in session.generation_status.items()
                if m in session.selected_modules and status == GenerationStatus.IN_PROGRESS
            ])
            
            failed_modules = len([
                m for m, status in session.generation_status.items()
                if m in session.selected_modules and status == GenerationStatus.FAILED
            ])
            
            progress_percentage = (completed_modules / total_modules * 100) if total_modules > 0 else 0
            
            # 获取活跃生成信息
            active_generation = self._active_generations.get(session_id)
            
            result = {
                'session_id': session_id,
                'total_modules': total_modules,
                'completed_modules': completed_modules,
                'in_progress_modules': in_progress_modules,
                'failed_modules': failed_modules,
                'progress_percentage': progress_percentage,
                'module_status': {
                    module_type.value: status.value 
                    for module_type, status in session.generation_status.items()
                    if module_type in session.selected_modules
                },
                'active_generation': active_generation,
                'estimated_completion': self._estimate_completion_time(session_id)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get progress: {str(e)}")
            return {'error': str(e)}
    
    def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话生成结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话结果信息
        """
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # 收集生成结果
            results = {}
            for module_type in session.selected_modules:
                if module_type in session.module_results:
                    result = session.module_results[module_type]
                    results[module_type.value] = {
                        'status': session.generation_status.get(module_type, GenerationStatus.NOT_STARTED).value,
                        'quality_score': result.quality_score,
                        'compliance_status': result.compliance_status.value,
                        'validation_status': result.validation_status.value,
                        'generation_time': result.generation_time,
                        'generation_timestamp': result.generation_timestamp.isoformat(),
                        'has_image_data': result.image_data is not None,
                        'image_path': result.image_path
                    }
                else:
                    results[module_type.value] = {
                        'status': session.generation_status.get(module_type, GenerationStatus.NOT_STARTED).value
                    }
            
            return {
                'session_id': session_id,
                'creation_time': session.creation_time.isoformat(),
                'last_updated': session.last_updated.isoformat(),
                'selected_modules': [m.value for m in session.selected_modules],
                'results': results,
                'overall_progress': session.get_progress_percentage()
            }
            
        except Exception as e:
            logger.error(f"Failed to get session results: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        清理会话资源
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功清理
        """
        try:
            # 停止活跃的生成任务
            if session_id in self._active_generations:
                self._active_generations[session_id]['status'] = 'cancelled'
                del self._active_generations[session_id]
            
            # 清理会话
            success = self.session_manager.cleanup_session(session_id)
            
            # 清理临时文件
            self.material_processor.cleanup_session_files(session_id)
            
            logger.info(f"Cleaned up session {session_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        Returns:
            系统健康信息
        """
        try:
            # 检查各组件健康状态
            factory_health = self.module_factory.health_check()
            processor_health = self.material_processor.health_check()
            session_health = self.session_manager.health_check()
            batch_health = self.batch_processor.health_check()
            
            # 计算整体健康状态
            component_statuses = [
                factory_health.get('factory_status') == 'healthy',
                processor_health.get('status') == 'healthy',
                session_health.get('status') == 'healthy',
                batch_health.get('status') == 'healthy'
            ]
            
            if all(component_statuses):
                overall_status = 'healthy'
            elif any(component_statuses):
                overall_status = 'degraded'
            else:
                overall_status = 'unhealthy'
            
            return {
                'overall_status': overall_status,
                'controller_initialized': self._is_initialized,
                'active_sessions': len(self.session_manager.get_active_sessions()),
                'active_generations': len(self._active_generations),
                'generation_stats': self._generation_stats.copy(),
                'components': {
                    'module_factory': factory_health,
                    'material_processor': processor_health,
                    'session_manager': session_health,
                    'batch_processor': batch_health
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _simulate_module_generation(self, 
                                   generator: BaseModuleGenerator,
                                   module_type: ModuleType,
                                   materials: MaterialSet,
                                   config: Optional[GenerationConfig]) -> GeneratedModule:
        """
        模拟模块生成（实际实现中应该调用真实的生成逻辑）
        
        Args:
            generator: 模块生成器
            module_type: 模块类型
            materials: 素材集合
            config: 生成配置
            
        Returns:
            生成的模块
        """
        import time
        import random
        
        # 模拟生成时间
        generation_time = random.uniform(1.0, 3.0)
        time.sleep(generation_time)
        
        # 创建模拟结果
        result = GeneratedModule(
            module_type=module_type,
            image_data=None,  # 实际应该有图片数据
            image_path=f"generated/{module_type.value}_{int(datetime.now().timestamp())}.png",
            compliance_status=ComplianceStatus.PENDING_REVIEW,
            generation_timestamp=datetime.now(),
            materials_used=materials,
            quality_score=random.uniform(0.7, 0.95),
            validation_status=ValidationStatus.PASSED,
            prompt_used=f"Generated prompt for {module_type.value}",
            generation_time=generation_time
        )
        
        return result
    
    def _validate_compliance(self, module: GeneratedModule) -> Dict[str, Any]:
        """
        验证A+合规性
        
        Args:
            module: 生成的模块
            
        Returns:
            合规验证结果
        """
        # 模拟合规验证
        # 实际实现中应该检查图片尺寸、文件大小、色彩空间等
        
        compliance_score = module.quality_score * 0.9  # 模拟合规分数
        
        if compliance_score >= 0.8:
            status = ComplianceStatus.COMPLIANT
        elif compliance_score >= 0.6:
            status = ComplianceStatus.NEEDS_OPTIMIZATION
        else:
            status = ComplianceStatus.NON_COMPLIANT
        
        return {
            'status': status,
            'score': compliance_score,
            'issues': [],
            'recommendations': []
        }
    
    def _batch_progress_callback(self, session_id: str, progress_info: Dict[str, Any]):
        """
        批量生成进度回调
        
        Args:
            session_id: 会话ID
            progress_info: 进度信息
        """
        if session_id in self._active_generations:
            self._active_generations[session_id].update(progress_info)
    
    def _estimate_completion_time(self, session_id: str) -> Optional[str]:
        """
        估算完成时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            预计完成时间（ISO格式字符串）
        """
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                return None
            
            # 获取时间估算
            remaining_modules = [
                m for m in session.selected_modules
                if session.generation_status.get(m, GenerationStatus.NOT_STARTED) == GenerationStatus.NOT_STARTED
            ]
            
            if not remaining_modules:
                return None
            
            # 使用模块工厂的时间估算
            time_estimate = self.module_factory.estimate_generation_time(remaining_modules)
            estimated_seconds = time_estimate.get('estimated_time', 60)
            
            estimated_completion = datetime.now().timestamp() + estimated_seconds
            return datetime.fromtimestamp(estimated_completion).isoformat()
            
        except Exception as e:
            logger.error(f"Failed to estimate completion time: {str(e)}")
            return None