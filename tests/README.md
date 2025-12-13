# AI Studio 测试文件组织结构

本目录包含了 AI Studio 功能的所有测试文件，按照功能分类进行组织。

## 文件分类说明

### 🎨 UI 组件测试 (UI Components)
- `test_ai_studio_ui_auto_resize.py` - 输入框自动调整大小测试
- `test_ai_studio_ui_auto_scroll.py` - 自动滚动行为测试
- `test_ai_studio_ui_file_upload.py` - 文件上传功能测试
- `test_ai_studio_ui_grid_layout.py` - 图片网格布局测试
- `test_ai_studio_ui_responsive_layout.py` - 响应式布局测试

### 🔄 交互行为测试 (Interaction Behaviors)
- `test_ai_studio_behavior_message_management.py` - 消息管理操作测试
- `test_ai_studio_behavior_message_submission.py` - 消息提交状态管理测试
- `test_ai_studio_behavior_navigation_efficiency.py` - 导航效率测试

### 🗃️ 状态管理测试 (State Management)
- `test_ai_studio_state_context_preservation.py` - 上下文保持测试
- `test_ai_studio_state_conversation_management.py` - 对话管理测试
- `test_ai_studio_state_model_configuration.py` - 模型配置状态测试

### 🔧 服务集成测试 (Service Integration)
- `test_ai_studio_service_vision.py` - 视觉服务集成测试

### ✨ 功能特性测试 (Feature Tests)
- `test_ai_studio_feature_image_generation.py` - 图像生成工作流测试

### 📋 属性测试 (Property-Based Tests)
- `test_ai_studio_property_message_styling.py` - 消息样式一致性属性测试
- `test_ai_studio_property_comprehensive.py` - 综合属性测试

## 命名规范

所有测试文件遵循以下命名规范：
```
test_ai_studio_{category}_{specific_feature}.py
```

其中：
- `category` 为功能分类：`ui`, `behavior`, `state`, `service`, `feature`, `property`
- `specific_feature` 为具体功能名称

## 运行测试

### 运行单个测试文件
```bash
python tests/test_ai_studio_ui_auto_scroll.py
```

### 运行特定分类的测试
```bash
# 运行所有 UI 测试
python -m pytest tests/test_ai_studio_ui_*.py

# 运行所有状态管理测试
python -m pytest tests/test_ai_studio_state_*.py
```

### 运行所有测试
```bash
python -m pytest tests/
```

## 测试覆盖的功能

### UI 组件 (5个测试文件)
- 自动调整大小
- 自动滚动
- 文件上传
- 网格布局
- 响应式设计

### 交互行为 (3个测试文件)
- 消息管理
- 消息提交
- 导航效率

### 状态管理 (3个测试文件)
- 上下文保持
- 对话管理
- 模型配置

### 服务集成 (1个测试文件)
- 视觉服务

### 功能特性 (1个测试文件)
- 图像生成

### 属性测试 (2个测试文件)
- 消息样式一致性
- 综合属性验证

## 总计
- **15个测试文件**，覆盖 AI Studio 的所有核心功能
- 按功能分类组织，便于维护和扩展
- 统一的命名规范，便于识别和管理