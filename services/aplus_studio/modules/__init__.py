"""
A+ Studio 模块生成器包

这个包包含了所有A+模块的生成器实现，包括：
- 基础模块框架
- 12个专业模块生成器
- 模块注册和发现系统
"""

from .base_module import BaseModuleGenerator, ModuleGenerationError
from .module_registry import ModuleRegistry, register_module, get_module_generator, get_registry
from .product_overview import ProductOverviewGenerator
from .problem_solution import ProblemSolutionGenerator
from .feature_analysis import FeatureAnalysisGenerator
from .specification_comparison import SpecificationComparisonGenerator
from .usage_scenarios import UsageScenariosGenerator
from .installation_guide import InstallationGuideGenerator
from .size_compatibility import SizeCompatibilityGenerator
from .maintenance_care import MaintenanceCareGenerator
from .material_craftsmanship import MaterialCraftsmanshipGenerator
from .quality_assurance import QualityAssuranceGenerator
from .customer_reviews import CustomerReviewsGenerator
from .package_contents import PackageContentsGenerator
from ..models import ModuleType

# 注册已实现的模块 - Phase 2 (核心模块)
register_module(ModuleType.PRODUCT_OVERVIEW, ProductOverviewGenerator)
register_module(ModuleType.PROBLEM_SOLUTION, ProblemSolutionGenerator)
register_module(ModuleType.FEATURE_ANALYSIS, FeatureAnalysisGenerator)
register_module(ModuleType.SPECIFICATION_COMPARISON, SpecificationComparisonGenerator)
register_module(ModuleType.USAGE_SCENARIOS, UsageScenariosGenerator)
register_module(ModuleType.INSTALLATION_GUIDE, InstallationGuideGenerator)

# 注册已实现的模块 - Phase 3 (次要模块)
register_module(ModuleType.SIZE_COMPATIBILITY, SizeCompatibilityGenerator)
register_module(ModuleType.MAINTENANCE_CARE, MaintenanceCareGenerator)
register_module(ModuleType.MATERIAL_CRAFTSMANSHIP, MaterialCraftsmanshipGenerator)
register_module(ModuleType.QUALITY_ASSURANCE, QualityAssuranceGenerator)
register_module(ModuleType.CUSTOMER_REVIEWS, CustomerReviewsGenerator)
register_module(ModuleType.PACKAGE_CONTENTS, PackageContentsGenerator)

__all__ = [
    'BaseModuleGenerator',
    'ModuleGenerationError', 
    'ModuleRegistry',
    'register_module',
    'get_module_generator',
    'get_registry',
    'ProductOverviewGenerator',
    'ProblemSolutionGenerator',
    'FeatureAnalysisGenerator',
    'SpecificationComparisonGenerator',
    'UsageScenariosGenerator',
    'InstallationGuideGenerator',
    'SizeCompatibilityGenerator',
    'MaintenanceCareGenerator',
    'MaterialCraftsmanshipGenerator',
    'QualityAssuranceGenerator',
    'CustomerReviewsGenerator',
    'PackageContentsGenerator'
]