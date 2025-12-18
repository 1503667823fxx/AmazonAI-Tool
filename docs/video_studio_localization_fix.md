# Video Studio 本地化修复说明

## 问题描述

在自动格式化后，Video Studio 页面出现 `AttributeError: 'TemplateCategory' object has no attribute 'chinese_name'` 错误。

## 解决方案

### 1. 创建独立的本地化工具模块

创建了 `app_utils/video_studio/localization.py` 文件，提供：

- **安全的中文名称获取函数**
- **完整的中英文映射字典**
- **容错机制**，即使枚举类没有 `chinese_name` 属性也能正常工作

### 2. 核心函数

```python
# 分类中文名称
get_category_chinese_name(category) -> str

# 风格中文名称  
get_style_chinese_name(style) -> str

# 模型中文名称
get_model_chinese_name(model) -> str

# 质量中文名称
get_quality_chinese_name(quality) -> str

# 模板显示名称格式化
format_template_display_name(template) -> str
```

### 3. 容错机制

每个函数都包含多层容错：

1. **优先使用对象的 `chinese_name` 属性**（如果存在）
2. **使用对象的 `value` 属性查找映射**
3. **直接字符串查找映射**
4. **返回原始值作为备用**

### 4. 更新的文件

#### `pages/4_🎬_Video_Studio.py`
- 使用 `format_template_display_name()` 格式化模板选项
- 使用本地化函数显示模板详情
- 使用本地化函数显示模型和质量选项

#### `app_utils/video_studio/ui_components.py`
- 更新分类选择器使用本地化工具

#### `app_utils/video_studio/__init__.py`
- 导出本地化函数供外部使用

## 中文映射表

### 分类映射
| 英文 | 中文 |
|------|------|
| product_showcase | 商品展示 |
| promotional | 推广宣传 |
| social_media | 社交媒体 |
| storytelling | 故事叙述 |
| educational | 教育培训 |
| custom | 自定义 |

### 风格映射
| 英文 | 中文 |
|------|------|
| cinematic | 电影风格 |
| dynamic | 动感活力 |
| minimal | 简约风格 |
| energetic | 高能激情 |
| elegant | 优雅精致 |
| modern | 现代时尚 |
| vintage | 复古怀旧 |
| professional | 专业商务 |

### 模型映射
| 英文 | 中文 |
|------|------|
| luma | Luma Dream Machine (梦境机器) |
| runway | Runway ML (跑道实验室) |
| pika | Pika Labs (皮卡实验室) |

### 质量映射
| 英文 | 中文 |
|------|------|
| 720p | 720p (高清) |
| 1080p | 1080p (全高清) |
| 4k | 4K (超高清) |

## 优势

1. **健壮性**：即使枚举类属性缺失也能正常工作
2. **可维护性**：集中管理所有中文映射
3. **扩展性**：易于添加新的映射关系
4. **一致性**：确保整个应用的中文显示一致

## 使用示例

```python
from app_utils.video_studio.localization import (
    get_category_chinese_name,
    format_template_display_name
)

# 安全获取分类中文名称
category_name = get_category_chinese_name(template.metadata.category)

# 格式化模板显示名称
display_name = format_template_display_name(template)
```

这个解决方案确保了 Video Studio 的中文界面能够稳定工作，不受代码格式化或其他变更的影响。
