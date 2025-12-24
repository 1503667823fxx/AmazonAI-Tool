"""
模块工厂

管理模块创建和发现的工厂类，提供统一的模块生成接口。
"""

import logging
from typing import Dict, List, Optional, Any
from .models import (
    ModuleType, ModuleInfo, MaterialSet, MaterialRequirements, 
    GeneratedModule, AnalysisResult
)
from .modules import ModuleRegistry, get_registry, BaseModuleGenerator

logger = logging.getLogger(__name__)


class ModuleFactory:
    """
    模块工厂类
    
    提供模块创建、验证和管理的统一接口。
    """
    
    def __init__(self):
        self.registry = get_registry()
        self._creation_stats = {
            'total_created': 0,
            'successful_creations': 0,
            'failed_creations': 0
        }
    
    def create_module(self, module_type: ModuleType, materials: MaterialSet) -> Optional[BaseModuleGenerator]:
        """
        创建模块生成器实例
        
        Args:
            module_type: 模块类型
            materials: 素材集合
            
        Returns:
            模块生成器实例，失败时返回None
        """
        try:
            self._creation_stats['total_created'] += 1
            
            # 检查模块是否已注册
            if not self.registry.is_registered(module_type):
                logger.error(f"Module {module_type.value} is not registered")
                self._creation_stats['failed_creations'] += 1
                return None
            
            # 验证素材需求
            validation_result = self.validate_module_materials(module_type, materials)
            if not validation_result['is_valid']:
                logger.warning(f"Material validation failed for {module_type.value}: {validation_result['issues']}")
                # 不阻止创建，但记录警告
            
            # 创建生成器实例
            generator = self.registry.get_generator(module_type)
            if generator:
                self._creation_stats['successful_creations'] += 1
                logger.info(f"Successfully created generator for {module_type.value}")
                return generator
            else:
                self._creation_stats['failed_creations'] += 1
                logger.error(f"Failed to create generator for {module_type.value}")
                return None
                
        except Exception as e:
            self._creation_stats['failed_creations'] += 1
            logger.error(f"Exception while creating module {module_type.value}: {str(e)}")
            return None
    
    def get_available_modules(self) -> List[ModuleInfo]:
        """
        获取所有可用模块的信息
        
        Returns:
            模块信息列表
        """
        available_modules = []
        
        for module_type in self.registry.get_available_modules():
            module_info = self.registry.get_module_info(module_type)
            if module_info:
                available_modules.append(module_info)
        
        return available_modules
    
    def validate_module_materials(self, module_type: ModuleType, materials: MaterialSet) -> Dict[str, Any]:
        """
        验证模块素材需求
        
        Args:
            module_type: 模块类型
            materials: 素材集合
            
        Returns:
            验证结果字典
        """
        return self.registry.validate_module_materials(module_type, materials)
    
    def get_module_requirements(self, module_type: ModuleType) -> Optional[MaterialRequirements]:
        """
        获取模块的素材需求
        
        Args:
            module_type: 模块类型
            
        Returns:
            素材需求，如果模块不存在则返回None
        """
        generator = self.registry.get_generator(module_type)
        if generator:
            try:
                return generator.get_material_requirements()
            except Exception as e:
                logger.error(f"Failed to get requirements for {module_type.value}: {str(e)}")
        
        return None
    
    def batch_validate_materials(self, 
                                module_types: List[ModuleType], 
                                materials_dict: Dict[ModuleType, MaterialSet]) -> Dict[ModuleType, Dict[str, Any]]:
        """
        批量验证多个模块的素材需求
        
        Args:
            module_types: 模块类型列表
            materials_dict: 模块类型到素材集合的映射
            
        Returns:
            模块类型到验证结果的映射
        """
        validation_results = {}
        
        for module_type in module_types:
            materials = materials_dict.get(module_type, MaterialSet())
            validation_results[module_type] = self.validate_module_materials(module_type, materials)
        
        return validation_results
    
    def get_module_dependencies(self, module_type: ModuleType) -> List[ModuleType]:
        """
        获取模块依赖关系
        
        Args:
            module_type: 模块类型
            
        Returns:
            依赖的模块类型列表
        """
        # 目前大多数模块都是独立的，但某些模块可能有依赖关系
        # 例如，某些高级模块可能需要基础分析结果
        dependencies = {
            # 示例：某些模块可能依赖产品概览模块的结果
            # ModuleType.FEATURE_ANALYSIS: [ModuleType.PRODUCT_OVERVIEW],
        }
        
        return dependencies.get(module_type, [])
    
    def suggest_module_combination(self, 
                                  product_category: str, 
                                  target_audience: str,
                                  available_materials: MaterialSet) -> List[ModuleType]:
        """
        根据产品类别和目标用户建议模块组合
        
        Args:
            product_category: 产品类别
            target_audience: 目标用户
            available_materials: 可用素材
            
        Returns:
            建议的模块类型列表
        """
        suggestions = []
        
        # 基础推荐：所有产品都建议的核心模块
        core_modules = [
            ModuleType.PRODUCT_OVERVIEW,
            ModuleType.FEATURE_ANALYSIS,
            ModuleType.USAGE_SCENARIOS
        ]
        suggestions.extend(core_modules)
        
        # 根据产品类别添加特定模块
        category_specific = {
            'electronics': [
                ModuleType.SPECIFICATION_COMPARISON,
                ModuleType.INSTALLATION_GUIDE,
                ModuleType.SIZE_COMPATIBILITY
            ],
            'home_garden': [
                ModuleType.MAINTENANCE_CARE,
                ModuleType.MATERIAL_CRAFTSMANSHIP,
                ModuleType.USAGE_SCENARIOS
            ],
            'health_beauty': [
                ModuleType.PROBLEM_SOLUTION,
                ModuleType.CUSTOMER_REVIEWS,
                ModuleType.QUALITY_ASSURANCE
            ],
            'sports_outdoors': [
                ModuleType.MATERIAL_CRAFTSMANSHIP,
                ModuleType.USAGE_SCENARIOS,
                ModuleType.MAINTENANCE_CARE
            ]
        }
        
        category_modules = category_specific.get(product_category.lower(), [])
        suggestions.extend(category_modules)
        
        # 根据可用素材过滤建议
        filtered_suggestions = []
        for module_type in suggestions:
            validation_result = self.validate_module_materials(module_type, available_materials)
            # 如果有必需素材缺失，降低优先级但不完全排除
            if validation_result['is_valid'] or len(validation_result['warnings']) <= 2:
                filtered_suggestions.append(module_type)
        
        # 去重并限制数量
        unique_suggestions = list(dict.fromkeys(filtered_suggestions))
        return unique_suggestions[:8]  # 最多推荐8个模块
    
    def estimate_generation_time(self, module_types: List[ModuleType]) -> Dict[str, Any]:
        """
        估算生成时间
        
        Args:
            module_types: 模块类型列表
            
        Returns:
            时间估算信息
        """
        # 基础生成时间（秒）
        base_times = {
            ModuleType.PRODUCT_OVERVIEW: 45,
            ModuleType.PROBLEM_SOLUTION: 50,
            ModuleType.FEATURE_ANALYSIS: 60,
            ModuleType.SPECIFICATION_COMPARISON: 40,
            ModuleType.USAGE_SCENARIOS: 55,
            ModuleType.INSTALLATION_GUIDE: 65,
            ModuleType.SIZE_COMPATIBILITY: 35,
            ModuleType.MAINTENANCE_CARE: 45,
            ModuleType.MATERIAL_CRAFTSMANSHIP: 50,
            ModuleType.QUALITY_ASSURANCE: 40,
            ModuleType.CUSTOMER_REVIEWS: 35,
            ModuleType.PACKAGE_CONTENTS: 30,
            # 旧模块
            ModuleType.IDENTITY: 60,
            ModuleType.SENSORY: 55,
            ModuleType.EXTENSION: 120,  # 4张图片
            ModuleType.TRUST: 50
        }
        
        total_time = sum(base_times.get(mt, 60) for mt in module_types)
        
        # 并行生成可以减少总时间
        parallel_time = max(base_times.get(mt, 60) for mt in module_types) if module_types else 0
        
        return {
            'sequential_time': total_time,
            'parallel_time': parallel_time,
            'estimated_time': min(total_time, parallel_time * 1.5),  # 考虑并行效率
            'module_count': len(module_types),
            'per_module_breakdown': {
                mt.value: base_times.get(mt, 60) for mt in module_types
            }
        }
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        获取工厂统计信息
        
        Returns:
            统计信息字典
        """
        registry_stats = self.registry.get_registry_stats()
        
        return {
            'creation_stats': self._creation_stats.copy(),
            'registry_stats': registry_stats,
            'success_rate': (
                self._creation_stats['successful_creations'] / 
                max(1, self._creation_stats['total_created'])
            )
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        registry_health = self.registry.health_check()
        factory_stats = self.get_factory_stats()
        
        return {
            'factory_status': 'healthy',
            'registry_health': registry_health,
            'creation_success_rate': factory_stats['success_rate'],
            'available_modules': len(self.get_available_modules())
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._creation_stats = {
            'total_created': 0,
            'successful_creations': 0,
            'failed_creations': 0
        }