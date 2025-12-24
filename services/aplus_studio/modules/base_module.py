"""
基础模块生成器框架

所有专业模块生成器都继承自这个基础类，提供统一的接口和标准工作流程。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import (
    ModuleType, MaterialSet, MaterialRequirements, GeneratedModule,
    ComplianceStatus, ValidationStatus, AnalysisResult
)

logger = logging.getLogger(__name__)


class ModuleGenerationError(Exception):
    """模块生成错误"""
    def __init__(self, message: str, module_type: ModuleType, error_code: str = None):
        self.module_type = module_type
        self.error_code = error_code
        super().__init__(f"[{module_type.value}] {message}")


class BaseModuleGenerator(ABC):
    """
    基础模块生成器抽象类
    
    所有专业模块生成器都必须继承这个类并实现抽象方法。
    提供标准的生成工作流程、素材验证、错误处理等功能。
    """
    
    def __init__(self, module_type: ModuleType):
        self.module_type = module_type
        self.logger = logging.getLogger(f"{__name__}.{module_type.value}")
        self._generation_stats = {
            'total_generations': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'average_generation_time': 0.0
        }
    
    @abstractmethod
    def get_module_info(self) -> Dict[str, Any]:
        """
        获取模块信息和元数据
        
        Returns:
            包含模块名称、描述、用例等信息的字典
        """
        pass
    
    @abstractmethod
    def get_material_requirements(self) -> MaterialRequirements:
        """
        获取模块的素材需求
        
        Returns:
            MaterialRequirements: 模块所需的素材要求
        """
        pass
    
    @abstractmethod
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        生成模块布局配置
        
        Args:
            materials: 用户提供的素材
            analysis_result: 产品分析结果
            
        Returns:
            布局配置字典
        """
        pass
    
    @abstractmethod
    async def generate_content(self, 
                             materials: MaterialSet, 
                             layout_config: Dict[str, Any],
                             analysis_result: AnalysisResult) -> GeneratedModule:
        """
        生成模块内容
        
        Args:
            materials: 用户提供的素材
            layout_config: 布局配置
            analysis_result: 产品分析结果
            
        Returns:
            GeneratedModule: 生成的模块结果
        """
        pass
    
    async def generate(self, 
                      materials: MaterialSet, 
                      analysis_result: AnalysisResult,
                      custom_params: Optional[Dict[str, Any]] = None) -> GeneratedModule:
        """
        标准模块生成工作流程
        
        这是主要的生成入口点，协调整个生成过程。
        
        Args:
            materials: 用户提供的素材
            analysis_result: 产品分析结果
            custom_params: 自定义参数
            
        Returns:
            GeneratedModule: 生成的模块结果
            
        Raises:
            ModuleGenerationError: 生成过程中的错误
        """
        start_time = datetime.now()
        self._generation_stats['total_generations'] += 1
        
        try:
            self.logger.info(f"Starting generation for {self.module_type.value} module")
            
            # 1. 验证输入
            self._validate_inputs(materials, analysis_result)
            
            # 2. 验证素材需求
            validation_result = self.validate_materials(materials)
            if not validation_result['is_valid']:
                raise ModuleGenerationError(
                    f"Material validation failed: {', '.join(validation_result['issues'])}",
                    self.module_type,
                    "MATERIAL_VALIDATION_FAILED"
                )
            
            # 3. 应用自定义参数
            if custom_params:
                materials = self._apply_custom_params(materials, custom_params)
            
            # 4. 生成布局
            self.logger.info("Generating layout configuration")
            layout_config = await self.generate_layout(materials, analysis_result)
            
            # 5. 生成内容
            self.logger.info("Generating module content")
            generated_module = await self.generate_content(materials, layout_config, analysis_result)
            
            # 6. 验证生成结果
            self._validate_generation_result(generated_module)
            
            # 7. 合规性检查
            compliance_status = await self._check_compliance(generated_module)
            generated_module.compliance_status = compliance_status
            
            # 8. 更新统计信息
            generation_time = (datetime.now() - start_time).total_seconds()
            generated_module.generation_time = generation_time
            self._update_generation_stats(generation_time, True)
            
            self.logger.info(f"Successfully generated {self.module_type.value} module in {generation_time:.2f}s")
            return generated_module
            
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            self._update_generation_stats(generation_time, False)
            
            if isinstance(e, ModuleGenerationError):
                raise
            else:
                raise ModuleGenerationError(
                    f"Unexpected error during generation: {str(e)}",
                    self.module_type,
                    "UNEXPECTED_ERROR"
                ) from e
    
    def validate_materials(self, materials: MaterialSet) -> Dict[str, Any]:
        """
        验证素材是否满足模块需求
        
        Args:
            materials: 用户提供的素材
            
        Returns:
            验证结果字典
        """
        requirements = self.get_material_requirements()
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
        
        # 检查必需素材
        required_materials = requirements.get_required_materials()
        for req in required_materials:
            if not self._check_material_availability(materials, req):
                validation_result['is_valid'] = False
                validation_result['issues'].append(
                    f"Missing required material: {req.description}"
                )
        
        # 检查推荐素材
        recommended_materials = requirements.get_recommended_materials()
        for req in recommended_materials:
            if not self._check_material_availability(materials, req):
                validation_result['warnings'].append(
                    f"Missing recommended material: {req.description}"
                )
                validation_result['suggestions'].append(
                    f"Consider adding {req.description} for better results"
                )
        
        return validation_result
    
    def _validate_inputs(self, materials: MaterialSet, analysis_result: AnalysisResult):
        """验证输入参数"""
        if not materials:
            raise ModuleGenerationError(
                "Materials cannot be None",
                self.module_type,
                "INVALID_INPUT"
            )
        
        if not analysis_result:
            raise ModuleGenerationError(
                "Analysis result cannot be None", 
                self.module_type,
                "INVALID_INPUT"
            )
    
    def _check_material_availability(self, materials: MaterialSet, requirement) -> bool:
        """检查特定素材是否可用"""
        from ..models import MaterialType
        
        if requirement.material_type == MaterialType.IMAGE:
            return len(materials.images) > 0
        elif requirement.material_type == MaterialType.DOCUMENT:
            return len(materials.documents) > 0
        elif requirement.material_type == MaterialType.TEXT:
            return len(materials.text_inputs) > 0
        elif requirement.material_type == MaterialType.CUSTOM_PROMPT:
            return len(materials.custom_prompts) > 0
        
        return False
    
    def _apply_custom_params(self, materials: MaterialSet, custom_params: Dict[str, Any]) -> MaterialSet:
        """应用自定义参数到素材"""
        # 这里可以根据自定义参数修改素材
        # 暂时返回原始素材
        return materials
    
    def _validate_generation_result(self, generated_module: GeneratedModule):
        """验证生成结果"""
        if not generated_module:
            raise ModuleGenerationError(
                "Generated module is None",
                self.module_type,
                "GENERATION_FAILED"
            )
        
        if not generated_module.image_data and not generated_module.image_path:
            raise ModuleGenerationError(
                "Generated module has no image data",
                self.module_type,
                "NO_IMAGE_DATA"
            )
        
        if generated_module.module_type != self.module_type:
            raise ModuleGenerationError(
                f"Module type mismatch: expected {self.module_type}, got {generated_module.module_type}",
                self.module_type,
                "MODULE_TYPE_MISMATCH"
            )
    
    async def _check_compliance(self, generated_module: GeneratedModule) -> ComplianceStatus:
        """检查亚马逊A+合规性"""
        try:
            # 这里应该实现具体的合规性检查逻辑
            # 暂时返回待审核状态
            return ComplianceStatus.PENDING_REVIEW
        except Exception as e:
            self.logger.warning(f"Compliance check failed: {str(e)}")
            return ComplianceStatus.PENDING_REVIEW
    
    def _update_generation_stats(self, generation_time: float, success: bool):
        """更新生成统计信息"""
        if success:
            self._generation_stats['successful_generations'] += 1
        else:
            self._generation_stats['failed_generations'] += 1
        
        # 更新平均生成时间
        total_successful = self._generation_stats['successful_generations']
        if total_successful > 0:
            current_avg = self._generation_stats['average_generation_time']
            self._generation_stats['average_generation_time'] = (
                (current_avg * (total_successful - 1) + generation_time) / total_successful
            )
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        return self._generation_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._generation_stats = {
            'total_generations': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'average_generation_time': 0.0
        }
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self._generation_stats['total_generations']
        if total == 0:
            return 0.0
        return self._generation_stats['successful_generations'] / total
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'module_type': self.module_type.value,
            'status': 'healthy',
            'success_rate': self.get_success_rate(),
            'stats': self.get_generation_stats()
        }