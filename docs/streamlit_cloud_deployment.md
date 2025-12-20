# Streamlit Cloud 部署指南

## 概述

本指南专门针对在 Streamlit Cloud 上部署 Video Studio 应用的配置和故障排除。

## 云端部署要求

### 1. requirements.txt 配置

确保 `requirements.txt` 包含所有必需的依赖：

```txt
streamlit
google-generativeai
replicate
pillow
numpy
requests
streamlit-drawable-canvas
watchdog
feedparser

moviepy==1.0.3
pydub
opencv-python-headless
imageio
proglog
hypothesis
pytest

# Video Studio 依赖
aiohttp>=3.8.0
psutil>=5.8.0
```

### 2. 云端环境特殊配置

#### Python 版本
- Streamlit Cloud 默认使用 Python 3.9+
- 确保代码兼容 Python 3.9+

#### 内存限制
- Streamlit Cloud 有内存限制
- Video Studio 会自动检测并适配资源限制

## 常见云端问题及解决方案

### 1. 模块导入错误

#### 问题: `ModuleNotFoundError: No module named 'aiohttp'`
```
解决方案:
1. 确认 requirements.txt 包含 aiohttp
2. 重新部署应用
3. 检查 Streamlit Cloud 的构建日志
```

#### 问题: `SyntaxError: 'await' outside async function`
```
解决方案:
已修复 - 更新到最新版本的代码
```

### 2. 依赖安装失败

#### psutil 安装失败
```bash
# 在 requirements.txt 中指定版本
psutil>=5.8.0,<6.0.0
```

#### aiohttp 安装失败
```bash
# 在 requirements.txt 中指定版本
aiohttp>=3.8.0,<4.0.0
```

### 3. 性能相关问题

#### 内存不足
- Video Studio 会自动检测可用内存
- 在云端环境中会自动降级某些功能

#### 处理超时
- 云端环境可能有请求超时限制
- Video Studio 会自动调整超时设置

## 部署检查清单

### 部署前检查

- [ ] `requirements.txt` 包含所有必需依赖
- [ ] 代码中没有语法错误
- [ ] 本地测试通过
- [ ] 依赖版本兼容

### 部署后验证

- [ ] 应用启动成功
- [ ] Video Studio 页面可以访问
- [ ] 适配器状态正常
- [ ] 核心功能可用

## 云端环境适配

### 自动降级功能

Video Studio 在云端环境中会自动适配：

1. **内存限制适配**
   - 自动检测可用内存
   - 调整缓存大小
   - 优化资源使用

2. **依赖缺失处理**
   - 优雅降级不可用功能
   - 显示清晰的错误信息
   - 提供安装指导

3. **性能优化**
   - 自动调整并发数
   - 优化请求超时
   - 智能资源管理

### 环境变量配置

可以通过 Streamlit Cloud 的环境变量配置：

```bash
# 可选的环境变量
VIDEO_STUDIO_LOG_LEVEL=INFO
VIDEO_STUDIO_MAX_CONCURRENT_TASKS=2
VIDEO_STUDIO_CACHE_SIZE=100MB
```

## 故障排除

### 1. 应用启动失败

#### 检查构建日志
1. 在 Streamlit Cloud 控制台查看构建日志
2. 查找依赖安装错误
3. 检查 Python 版本兼容性

#### 常见错误模式
```bash
# 依赖安装失败
ERROR: Could not install packages due to an EnvironmentError

# Python 版本不兼容
SyntaxError: invalid syntax

# 内存不足
MemoryError: Unable to allocate array
```

### 2. 运行时错误

#### 导入错误
```python
# 检查适配器可用性
from app_utils.video_studio.adapters import (
    LUMA_AVAILABLE, RUNWAY_AVAILABLE, PIKA_AVAILABLE
)
print(f"Adapters: Luma={LUMA_AVAILABLE}, Runway={RUNWAY_AVAILABLE}, Pika={PIKA_AVAILABLE}")
```

#### 功能降级
```python
# Video Studio 会自动处理功能降级
# 检查系统状态
from app_utils.video_studio import get_system_status
status = get_system_status()
```

### 3. 性能问题

#### 响应缓慢
- 检查网络连接
- 验证 API 密钥配置
- 查看资源使用情况

#### 内存使用过高
- Video Studio 会自动优化内存使用
- 检查是否有内存泄漏
- 考虑减少并发任务数

## 监控和日志

### 应用监控

```python
# 在 Streamlit 应用中添加状态监控
import streamlit as st
from app_utils.video_studio import get_system_metrics

# 显示系统状态
if st.sidebar.button("系统状态"):
    metrics = get_system_metrics()
    st.sidebar.json(metrics)
```

### 日志配置

```python
# 配置日志级别
import logging
logging.basicConfig(level=logging.INFO)

# Video Studio 会自动配置日志
from app_utils.video_studio.logging_config import setup_logging
setup_logging(level="INFO")
```

## 最佳实践

### 1. 代码优化

- 使用异步操作减少阻塞
- 实现适当的错误处理
- 优化内存使用

### 2. 用户体验

- 提供清晰的状态反馈
- 实现优雅的错误处理
- 显示有用的错误信息

### 3. 资源管理

- 自动清理临时文件
- 优化缓存策略
- 监控资源使用

## 支持和帮助

### 获取帮助

1. **检查文档**
   - `docs/video_studio_dependencies.md`
   - `docs/video_studio_template_system.md`

2. **运行诊断**
   ```bash
   python check_dependencies.py
   python test_video_studio_import.py
   ```

3. **查看日志**
   - Streamlit Cloud 控制台
   - 应用运行时日志

### 常用调试命令

```python
# 检查依赖状态
from app_utils.video_studio.adapters import *
print(f"Luma: {LUMA_AVAILABLE}, Runway: {RUNWAY_AVAILABLE}, Pika: {PIKA_AVAILABLE}")

# 检查系统资源
import psutil
print(f"Memory: {psutil.virtual_memory().percent}%")
print(f"CPU: {psutil.cpu_percent()}%")

# 测试基本功能
from app_utils.video_studio import VideoConfig
config = VideoConfig(template_id="test", input_images=[], duration=10, 
                    aspect_ratio="16:9", style="test", quality="720p")
print("VideoConfig created successfully")
```