"""
Video Studio 本地化工具

提供中英文映射和安全的本地化函数
"""

from typing import Any

# 分类中文映射
CATEGORY_CHINESE_NAMES = {
    "product_showcase": "商品展示",
    "promotional": "推广宣传",
    "social_media": "社交媒体",
    "storytelling": "故事叙述",
    "educational": "教育培训",
    "custom": "自定义"
}

# 风格中文映射
STYLE_CHINESE_NAMES = {
    "cinematic": "电影风格",
    "dynamic": "动感活力",
    "minimal": "简约风格",
    "energetic": "高能激情",
    "elegant": "优雅精致",
    "modern": "现代时尚",
    "vintage": "复古怀旧",
    "professional": "专业商务"
}

# 模型中文映射
MODEL_CHINESE_NAMES = {
    "luma": "Luma Dream Machine (梦境机器)",
    "runway": "Runway ML (跑道实验室)",
    "pika": "Pika Labs (皮卡实验室)"
}

# 质量中文映射
QUALITY_CHINESE_NAMES = {
    "720p": "720p (高清)",
    "1080p": "1080p (全高清)",
    "4k": "4K (超高清)"
}


def get_category_chinese_name(category: Any) -> str:
    """
    安全获取分类中文名称
    
    Args:
        category: TemplateCategory 枚举或字符串
        
    Returns:
        str: 中文名称
    """
    try:
        # 尝试使用对象的chinese_name属性
        if hasattr(category, 'chinese_name'):
            return category.chinese_name
        
        # 尝试使用对象的value属性
        if hasattr(category, 'value'):
            return CATEGORY_CHINESE_NAMES.get(category.value, category.value)
        
        # 如果是字符串，直接查找
        if isinstance(category, str):
            return CATEGORY_CHINESE_NAMES.get(category, category)
        
        # 其他情况返回字符串表示
        return str(category)
        
    except Exception:
        return str(category)


def get_style_chinese_name(style: Any) -> str:
    """
    安全获取风格中文名称
    
    Args:
        style: VideoStyle 枚举或字符串
        
    Returns:
        str: 中文名称
    """
    try:
        # 尝试使用对象的chinese_name属性
        if hasattr(style, 'chinese_name'):
            return style.chinese_name
        
        # 尝试使用对象的value属性
        if hasattr(style, 'value'):
            return STYLE_CHINESE_NAMES.get(style.value, style.value)
        
        # 如果是字符串，直接查找
        if isinstance(style, str):
            return STYLE_CHINESE_NAMES.get(style, style)
        
        # 其他情况返回字符串表示
        return str(style)
        
    except Exception:
        return str(style)


def get_model_chinese_name(model: str) -> str:
    """
    获取模型中文名称
    
    Args:
        model: 模型名称字符串
        
    Returns:
        str: 中文名称
    """
    return MODEL_CHINESE_NAMES.get(model, model)


def get_quality_chinese_name(quality: str) -> str:
    """
    获取质量中文名称
    
    Args:
        quality: 质量字符串
        
    Returns:
        str: 中文名称
    """
    return QUALITY_CHINESE_NAMES.get(quality, quality)


def format_template_display_name(template) -> str:
    """
    格式化模板显示名称
    
    Args:
        template: VideoTemplate 对象
        
    Returns:
        str: 格式化的显示名称
    """
    try:
        category_name = get_category_chinese_name(template.metadata.category)
        return f"{template.metadata.name} ({category_name})"
    except Exception:
        return template.metadata.name if hasattr(template, 'metadata') else str(template)
