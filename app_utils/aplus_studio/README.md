# APlus Studio 应用工具

## 📁 文件结构

```
app_utils/aplus_studio/
├── __init__.py                 # 模块初始化
├── template_manager.py         # 模板管理器
├── search_engine.py           # 智能搜索引擎
└── README.md                  # 说明文档
```

## 🎯 功能模块

### 1. TemplateManager (template_manager.py)
负责模板的加载、管理和基础处理功能：
- 加载模板配置文件
- 获取可用模板列表
- 按类别筛选模板
- 加载指定模板资源

### 2. AITemplateProcessor (template_manager.py)
AI 驱动的模板处理器：
- 产品内容智能替换
- 配色方案自动适配
- 布局智能优化
- AI 增强处理

### 3. TemplateSearchEngine (search_engine.py)
智能搜索引擎核心：
- 多维度搜索索引构建
- 关键词、标签、节日匹配
- 相关性评分算法
- 搜索建议生成

### 4. SmartTemplateRecommender (search_engine.py)
智能推荐系统：
- 基于产品信息的模板推荐
- 推荐原因生成
- 匹配度评估

## 🔧 使用方式

### 基础导入
```python
from app_utils.aplus_studio.template_manager import TemplateManager, AITemplateProcessor
from app_utils.aplus_studio.search_engine import TemplateSearchEngine, SmartTemplateRecommender
```

### 模板管理
```python
# 初始化模板管理器
template_manager = TemplateManager()

# 获取所有可用模板
templates = template_manager.get_available_templates()

# 按类别获取模板
tech_templates = template_manager.get_template_by_category("电子产品")

# 加载指定模板
template = template_manager.load_template("tech_modern")
```

### 智能搜索
```python
# 初始化搜索引擎
search_engine = TemplateSearchEngine()

# 搜索模板
results = search_engine.search_templates("南瓜服")

# 获取搜索建议
suggestions = search_engine.get_search_suggestions("万圣")

# 获取相似模板
similar = search_engine.get_similar_templates("halloween_spooky")
```

### 智能推荐
```python
# 初始化推荐器
recommender = SmartTemplateRecommender(search_engine)

# 根据产品信息推荐
recommendations = recommender.recommend_by_product_info(
    product_name="万圣节南瓜服装",
    product_category="服装配饰", 
    features=["派对装扮", "恐怖造型"]
)
```

## 🎨 模板配置

模板配置文件位于 `templates/templates_config.json`，包含：
- 模板基本信息 (名称、类别、描述)
- 搜索关键词和标签
- 风格属性定义
- 节日和季节标记
- 可替换区域坐标

## 🔍 搜索功能特性

### 多维度匹配
- **节日匹配**: 15分 (最高权重)
- **关键词匹配**: 10分
- **标签匹配**: 8分
- **类别匹配**: 7分
- **季节匹配**: 6分
- **风格属性**: 5分
- **文本相似度**: 3分
- **部分词匹配**: 2分

### 搜索示例
```python
# 节日主题搜索
search_engine.search_templates("万圣节")
# 返回: 万圣节恐怖风模板 (高匹配度)

# 产品搜索
search_engine.search_templates("南瓜服")
# 返回: 万圣节恐怖风模板 (关键词匹配)

# 组合搜索
search_engine.search_templates("万圣节 服装 派对")
# 返回: 多个相关模板，按匹配度排序
```

## 🚀 扩展性

### 添加新模板
1. 在 `templates/` 文件夹中创建模板文件夹
2. 添加模板图片文件
3. 在 `templates_config.json` 中添加配置
4. 系统自动索引新模板

### 自定义搜索算法
可以通过修改 `_calculate_relevance_score` 方法调整搜索权重和算法。

### 集成外部AI服务
`AITemplateProcessor` 类预留了AI服务集成接口，可以轻松接入：
- OpenAI GPT API
- Stable Diffusion
- Google Vision API
- 其他图像处理服务

## 📊 性能优化

- 搜索索引预构建，提升搜索速度
- 模板配置缓存，减少文件读取
- 相似度计算优化，支持大量模板
- 搜索结果分页，控制内存使用

## 🔗 与页面集成

在 `pages/5_🧩_APlus_Studio.py` 中：
```python
# 导入工具模块
from app_utils.aplus_studio.template_manager import TemplateManager
from app_utils.aplus_studio.search_engine import TemplateSearchEngine

# 在页面中使用
search_engine = TemplateSearchEngine()
results = search_engine.search_templates(user_query)
```

## 📝 开发规范

### 代码风格
- 遵循 PEP 8 编码规范
- 使用类型提示 (Type Hints)
- 完整的文档字符串
- 异常处理和错误日志

### 测试覆盖
- 单元测试覆盖核心功能
- 搜索算法准确性测试
- 模板加载性能测试
- 边界条件处理测试

---

*该模块是 AmazonAI-Tool 项目的核心组件，负责 A+ 页面的智能模板管理和搜索功能。*