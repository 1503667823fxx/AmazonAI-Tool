# A+Studio工作流系统

## 概述

A+Studio工作流系统是一个基于Streamlit的云端图片制作平台，专门用于创建专业的Amazon A+页面图片。系统采用模块化架构，集成Google Gemini 3 Pro Image Preview API，提供智能模板搜索、分步工作流引导和AI辅助图片合成功能。

## 项目结构

```
app_utils/aplus_studio/
├── __init__.py                 # 主模块初始化
├── README.md                   # 项目文档
├── interfaces.py               # 核心接口定义
├── models/                     # 数据模型模块
│   ├── __init__.py
│   └── core_models.py         # 核心数据模型
├── workflow/                   # 工作流引擎模块
│   ├── __init__.py
│   └── engine.py              # 工作流引擎实现
├── ai_processors/              # AI处理器模块
│   ├── __init__.py
│   └── gemini_client.py       # Gemini API客户端
├── file_management/            # 文件管理模块
│   ├── __init__.py
│   └── upload_handler.py      # 文件上传处理器
├── template_manager.py         # 模板管理器（现有）
└── search_engine.py           # 搜索引擎（现有）
```

## 核心组件

### 1. 数据模型 (models/)

- **Template**: 模板数据模型，包含模板信息、可替换区域等
- **WorkflowSession**: 工作流会话模型，管理用户工作流状态
- **ProductData**: 产品数据模型，存储用户产品信息
- **Category**: 分类模型，支持多级分类管理
- **UploadedFile**: 上传文件模型
- **Area**: 可替换区域模型

### 2. 核心接口 (interfaces.py)

定义了系统各组件的抽象接口：
- `ITemplateManager`: 模板管理接口
- `ISearchEngine`: 搜索引擎接口
- `ICategoryManager`: 分类管理接口
- `IWorkflowEngine`: 工作流引擎接口
- `IGeminiAPIClient`: Gemini API客户端接口
- `IFileUploadHandler`: 文件上传处理接口

### 3. 工作流引擎 (workflow/)

- **WorkflowEngine**: 管理分步工作流的状态和转换
- 支持工作流创建、步骤前进/后退、进度保存
- 提供会话管理和状态持久化

### 4. AI处理器 (ai_processors/)

- **GeminiAPIClient**: Gemini API客户端实现
- 支持图片生成、图片合成、文本增强
- 包含速率限制和错误重试机制

### 5. 文件管理 (file_management/)

- **FileUploadHandler**: 文件上传和验证处理
- 支持多种图片格式验证
- 提供图片尺寸调整和优化功能

## 测试框架

### 配置文件

- `pytest.ini`: pytest配置
- `tests/conftest.py`: 测试夹具和Hypothesis策略
- `tests/test_core_models.py`: 核心模型单元测试

### 测试策略

系统使用双重测试方法：

1. **单元测试**: 使用pytest验证具体功能和边界条件
2. **属性测试**: 使用Hypothesis进行属性基础测试，每个属性测试运行至少100次

### Hypothesis策略

提供了以下数据生成策略：
- `template_strategy()`: 生成随机模板数据
- `product_data_strategy()`: 生成随机产品数据
- `workflow_session_strategy()`: 生成随机工作流会话
- `category_strategy()`: 生成随机分类数据

## 使用示例

### 创建工作流会话

```python
from app_utils.aplus_studio.workflow.engine import WorkflowEngine

engine = WorkflowEngine()
session = engine.create_session("user_001", "template_001")

# 前进到下一步
engine.next_step(session.session_id)

# 获取会话状态
current_session = engine.get_session(session.session_id)
```

### 处理文件上传

```python
from app_utils.aplus_studio.file_management.upload_handler import FileUploadHandler
from app_utils.aplus_studio.models.core_models import UploadedFile

handler = FileUploadHandler()

# 创建上传文件
file = UploadedFile(
    filename="product.jpg",
    content_type="image/jpeg", 
    size=1024000,
    data=image_bytes
)

# 验证文件
errors = handler.validate_file(file)
if not errors:
    success = handler.process_upload(file)
```

### 使用Gemini API

```python
from app_utils.aplus_studio.ai_processors.gemini_client import GeminiAPIClient

client = GeminiAPIClient(api_key="your_api_key")

# 验证API密钥
if client.validate_api_key():
    # 增强文本
    enhanced_text = client.enhance_text(
        "产品特色文案",
        {"category": "电子产品", "brand_name": "TechPro"}
    )
```

## 数据验证

系统提供了完整的数据验证功能：

```python
from app_utils.aplus_studio.models.core_models import validate_template, validate_product_data

# 验证模板
errors = validate_template(template)
if errors:
    print("模板验证失败:", errors)

# 验证产品数据
errors = validate_product_data(product_data)
if errors:
    print("产品数据验证失败:", errors)
```

## 序列化支持

所有数据模型都支持JSON序列化：

```python
# 转换为字典
template_dict = template.to_dict()

# 从字典恢复
restored_template = Template.from_dict(template_dict)
```

## 开发指南

### 添加新组件

1. 在相应模块目录下创建新文件
2. 实现对应的接口
3. 添加单元测试和属性测试
4. 更新文档

### 测试运行

```bash
# 运行所有测试
python -m pytest

# 运行特定测试文件
python -m pytest tests/test_core_models.py -v

# 运行属性测试
python -m pytest -m property
```

### 验证设置

```bash
# 运行设置验证脚本
python validate_setup.py
```

## 依赖项

- `streamlit`: Web应用框架
- `pytest`: 测试框架
- `hypothesis`: 属性测试库
- `pillow`: 图片处理
- `requests`: HTTP客户端
- `google-generativeai`: Gemini API客户端

## 注意事项

1. **API密钥安全**: 确保Gemini API密钥的安全存储
2. **文件大小限制**: 默认最大文件大小为10MB
3. **速率限制**: API客户端包含速率限制机制
4. **错误处理**: 所有组件都包含完整的错误处理
5. **数据验证**: 在处理用户输入前始终进行验证

## 后续开发

根据任务列表，后续需要实现：
- 模板管理系统增强
- 分类管理器
- 图片合成器
- 用户界面组件
- 管理员功能
- 系统集成和优化