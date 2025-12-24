"""
模块注册和发现系统

提供模块的动态注册、发现和创建功能。
"""

import logging
from typing import Dict, Type, Optional, List
from ..models import ModuleType, ModuleInfo
from .base_module import BaseModuleGenerator

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    模块注册表
    
    管理所有可用的模块生成器，提供注册、发现和创建功能。
    """
    
    def __init__(self):
        self._generators: Dict[ModuleType, Type[BaseModuleGenerator]] = {}
        self._module_info_cache: Dict[ModuleType, ModuleInfo] = {}
    
    def register(self, module_type: ModuleType, generator_class: Type[BaseModuleGenerator]):
        """
        注册模块生成器
        
        Args:
            module_type: 模块类型
            generator_class: 生成器类
        """
        if not issubclass(generator_class, BaseModuleGenerator):
            raise ValueError(f"Generator class must inherit from BaseModuleGenerator")
        
        self._generators[module_type] = generator_class
        logger.info(f"Registered generator for {module_type.value}: {generator_class.__name__}")
    
    def unregister(self, module_type: ModuleType):
        """
        取消注册模块生成器
        
        Args:
            module_type: 模块类型
        """
        if module_type in self._generators:
            del self._generators[module_type]
            if module_type in self._module_info_cache:
                del self._module_info_cache[module_type]
            logger.info(f"Unregistered generator for {module_type.value}")
    
    def is_registered(self, module_type: ModuleType) -> bool:
        """
        检查模块是否已注册
        
        Args:
            module_type: 模块类型
            
        Returns:
            是否已注册
        """
        return module_type in self._generators
    
    def get_generator(self, module_type: ModuleType) -> Optional[BaseModuleGenerator]:
        """
        获取模块生成器实例
        
        Args:
            module_type: 模块类型
            
        Returns:
            生成器实例，如果未注册则返回None
        """
        generator_class = self._generators.get(module_type)
        if generator_class:
            try:
                return generator_class(module_type)
            except Exception as e:
                logger.error(f"Failed to create generator for {module_type.value}: {str(e)}")
                return None
        return None
    
    def get_available_modules(self) -> List[ModuleType]:
        """
        获取所有可用的模块类型
        
        Returns:
            可用模块类型列表
        """
        return list(self._generators.keys())
    
    def get_module_info(self, module_type: ModuleType) -> Optional[ModuleInfo]:
        """
        获取模块信息
        
        Args:
            module_type: 模块类型
            
        Returns:
            模块信息，如果未注册则返回None
        """
        # 检查缓存
        if module_type in self._module_info_cache:
            return self._module_info_cache[module_type]
        
        # 创建生成器实例获取信息
        generator = self.get_generator(module_type)
        if generator:
            try:
                info_dict = generator.get_module_info()
                # 这里可以将字典转换为ModuleInfo对象
                # 暂时返回基本信息
                from ..models import get_module_info_by_type
                module_info = get_module_info_by_type(module_type)
                self._module_info_cache[module_type] = module_info
                return module_info
            except Exception as e:
                logger.error(f"Failed to get module info for {module_type.value}: {str(e)}")
        
        return None
    
    def validate_module_materials(self, module_type: ModuleType, materials) -> Dict[str, Any]:
        """
        验证模块素材
        
        Args:
            module_type: 模块类型
            materials: 素材集合
            
        Returns:
            验证结果
        """
        generator = self.get_generator(module_type)
        if generator:
            return generator.validate_materials(materials)
        
        return {
            'is_valid': False,
            'issues': [f'Module {module_type.value} is not registered'],
            'warnings': [],
            'suggestions': []
        }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_registered': len(self._generators),
            'registered_modules': [mt.value for mt in self._generators.keys()],
            'cache_size': len(self._module_info_cache)
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        healthy_modules = []
        unhealthy_modules = []
        
        for module_type in self._generators.keys():
            try:
                generator = self.get_generator(module_type)
                if generator:
                    health = generator.health_check()
                    if health.get('status') == 'healthy':
                        healthy_modules.append(module_type.value)
                    else:
                        unhealthy_modules.append(module_type.value)
                else:
                    unhealthy_modules.append(module_type.value)
            except Exception as e:
                logger.error(f"Health check failed for {module_type.value}: {str(e)}")
                unhealthy_modules.append(module_type.value)
        
        return {
            'overall_status': 'healthy' if not unhealthy_modules else 'degraded',
            'healthy_modules': healthy_modules,
            'unhealthy_modules': unhealthy_modules,
            'total_modules': len(self._generators)
        }


# 全局注册表实例
_global_registry = ModuleRegistry()


def register_module(module_type: ModuleType, generator_class: Type[BaseModuleGenerator]):
    """
    注册模块生成器到全局注册表
    
    Args:
        module_type: 模块类型
        generator_class: 生成器类
    """
    _global_registry.register(module_type, generator_class)


def get_module_generator(module_type: ModuleType) -> Optional[BaseModuleGenerator]:
    """
    从全局注册表获取模块生成器
    
    Args:
        module_type: 模块类型
        
    Returns:
        生成器实例
    """
    return _global_registry.get_generator(module_type)


def get_registry() -> ModuleRegistry:
    """
    获取全局注册表实例
    
    Returns:
        全局注册表
    """
    return _global_registry


def is_module_available(module_type: ModuleType) -> bool:
    """
    检查模块是否可用
    
    Args:
        module_type: 模块类型
        
    Returns:
        是否可用
    """
    return _global_registry.is_registered(module_type)


def get_available_modules() -> List[ModuleType]:
    """
    获取所有可用模块
    
    Returns:
        可用模块列表
    """
    return _global_registry.get_available_modules()