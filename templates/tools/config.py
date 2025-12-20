"""
模板库管理系统配置
"""

import os
from pathlib import Path

# 获取项目根目录
def get_project_root() -> Path:
    """获取项目根目录路径"""
    # 从tools目录向上两级到达项目根目录
    current_file = Path(__file__).resolve()
    tools_dir = current_file.parent  # templates/tools/
    templates_dir = tools_dir.parent  # templates/
    project_root = templates_dir.parent  # 项目根目录
    return project_root

# 项目根目录
PROJECT_ROOT = get_project_root()

# 模板库相关路径
TEMPLATES_ROOT = PROJECT_ROOT / "templates"
TEMPLATES_BY_CATEGORY = TEMPLATES_ROOT / "by_category"
TEMPLATES_CONFIG = TEMPLATES_ROOT / "config"
TEMPLATES_INDEX = TEMPLATES_ROOT / "index"
TEMPLATES_TOOLS = TEMPLATES_ROOT / "tools"

# 其他重要路径
DOCS_ROOT = PROJECT_ROOT / "docs"
TESTS_ROOT = PROJECT_ROOT / "tests"

# 配置文件路径
CATEGORIES_CONFIG = TEMPLATES_CONFIG / "categories.yaml"
TEMPLATE_TYPES_CONFIG = TEMPLATES_CONFIG / "template_types.yaml"
VALIDATION_RULES_CONFIG = TEMPLATES_CONFIG / "validation_rules.yaml"
GLOBAL_SETTINGS_CONFIG = TEMPLATES_CONFIG / "global_settings.yaml"

# 索引文件路径
SEARCH_INDEX = TEMPLATES_INDEX / "search_index.json"
CATEGORY_INDEX = TEMPLATES_INDEX / "category_index.json"
TAG_INDEX = TEMPLATES_INDEX / "tag_index.json"
TEMPLATE_REGISTRY = TEMPLATES_INDEX / "template_registry.json"

# 默认设置
DEFAULT_TEMPLATE_TYPE = "standard"
DEFAULT_CATEGORY = "electronics"
DEFAULT_STATUS = "draft"

# 图片尺寸配置
IMAGE_SIZES = {
    "preview": {"width": 300, "height": 200},
    "desktop": {"width": 1464, "height": 600},
    "mobile": {"width": 600, "height": 450}
}

# 支持的文件格式
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".webp"]
SUPPORTED_CONFIG_FORMATS = [".json", ".yaml", ".yml"]

# 质量检查配置
QUALITY_THRESHOLDS = {
    "completeness_score": 80,
    "design_quality": 75,
    "usability_score": 70,
    "performance_score": 80,
    "accessibility_score": 65
}

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def ensure_directories():
    """确保所有必要的目录存在"""
    directories = [
        TEMPLATES_BY_CATEGORY,
        TEMPLATES_CONFIG,
        TEMPLATES_INDEX,
        TEMPLATES_TOOLS,
        DOCS_ROOT,
        TESTS_ROOT
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_template_path(template_name: str, category: str = None) -> Path:
    """获取模板的完整路径"""
    if category:
        return TEMPLATES_BY_CATEGORY / category / template_name
    else:
        # 搜索所有分类目录
        for category_dir in TEMPLATES_BY_CATEGORY.iterdir():
            if category_dir.is_dir():
                template_path = category_dir / template_name
                if template_path.exists():
                    return template_path
        raise FileNotFoundError(f"Template '{template_name}' not found in any category")

def get_relative_path(absolute_path: Path) -> str:
    """获取相对于项目根目录的相对路径"""
    try:
        return str(absolute_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(absolute_path)