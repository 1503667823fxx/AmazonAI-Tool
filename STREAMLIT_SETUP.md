# APlus Studio 模板库管理系统 - Streamlit云端环境设置

## 概述

本文档说明如何在Streamlit云端环境中设置和使用模板库管理系统。

## 环境要求

- Python 3.8+
- Streamlit Cloud环境
- 必需的Python包（见requirements.txt）

## 已完成的环境配置

### 1. 依赖管理
- ✅ 更新了 `requirements.txt` 添加模板库管理系统依赖
- ✅ 包含所有必需的Python包：pydantic, PyYAML, jsonschema, rich, click等

### 2. Streamlit配置
- ✅ 创建了 `.streamlit/config.toml` - Streamlit应用配置
- ✅ 创建了 `.streamlit/secrets.toml` - 系统密钥和环境变量配置

### 3. 核心工具模块
- ✅ `tools/config.py` - 配置管理模块，适配Streamlit环境
- ✅ `tools/streamlit_utils.py` - Streamlit专用工具函数
- ✅ `tools/validators/` - 配置、结构、图片验证器
- ✅ `tools/cli/template_cli.py` - 命令行工具（基础框架）

### 4. 构建工具
- ✅ 更新了 `Makefile` 适配Streamlit云端环境
- ✅ 移除了不适用的本地开发配置（pyproject.toml, .pre-commit-config.yaml等）

## 使用方法

### 在Streamlit Cloud中部署

1. **上传项目到GitHub**
   ```bash
   git add .
   git commit -m "添加模板库管理系统"
   git push origin main
   ```

2. **在Streamlit Cloud中部署**
   - 访问 [share.streamlit.io](https://share.streamlit.io)
   - 连接GitHub仓库
   - 选择主文件：`Home.py`
   - 部署应用

### 本地开发（可选）

如果需要本地开发，可以：

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行应用**
   ```bash
   streamlit run Home.py
   ```

3. **验证环境**
   ```bash
   python validate_streamlit_env.py
   ```

## 配置说明

### Streamlit配置 (.streamlit/config.toml)
- 服务器端口：8501
- 文件上传限制：200MB
- 主题配色：红色主色调
- 启用缓存和快速重新运行

### 系统配置 (.streamlit/secrets.toml)
- 调试模式：启用
- 图片尺寸：桌面版1464x600，移动版600x450
- 文件大小限制：5MB
- 缓存设置：启用，100MB限制

## 验证工具

系统提供了多个验证工具：

1. **环境验证**
   ```bash
   python validate_streamlit_env.py
   ```

2. **配置验证**
   ```bash
   make validate-configs
   ```

3. **结构验证**
   ```bash
   make validate-structure
   ```

4. **完整验证**
   ```bash
   make validate-all
   ```

## 目录结构

```
├── .streamlit/              # Streamlit配置
│   ├── config.toml         # 应用配置
│   └── secrets.toml        # 密钥配置
├── tools/                  # 工具模块
│   ├── config.py          # 配置管理
│   ├── streamlit_utils.py # Streamlit工具
│   ├── validators/        # 验证器
│   ├── cli/              # CLI工具
│   └── models/           # 数据模型
├── templates/             # 模板库
│   ├── config/           # 配置文件
│   └── by_category/      # 分类模板
├── requirements.txt       # Python依赖
├── Makefile              # 构建工具
└── Home.py               # 主应用文件
```

## 下一步

环境设置完成后，可以继续实现：

1. **任务2**: 模板生成和配置管理核心功能
2. **任务3**: 元数据生成和智能分析功能
3. **任务4**: 分类管理和组织系统
4. **任务5**: 命令行工具和用户界面

## 故障排除

### 常见问题

1. **依赖包安装失败**
   - 检查requirements.txt文件
   - 确保Python版本3.8+

2. **Streamlit配置问题**
   - 检查.streamlit/目录下的配置文件
   - 验证config.toml和secrets.toml格式

3. **模块导入错误**
   - 确保tools/目录下的__init__.py文件存在
   - 检查Python路径设置

### 获取帮助

- 查看Makefile命令：`make help`
- 运行环境验证：`python validate_streamlit_env.py`
- 检查项目结构：`make check-structure`