# Video Studio 依赖安装指南

## 概述

Video Studio 需要一些额外的 Python 包来支持其完整功能，特别是 AI 模型适配器和性能监控功能。

## 必需依赖

### 核心依赖
这些依赖对于 Video Studio 的基本功能是必需的：

```bash
pip install aiohttp psutil
```

- **aiohttp**: 异步 HTTP 客户端，用于与 AI 模型 API 通信
- **psutil**: 系统性能监控，用于资源管理和性能优化

### 可选依赖
这些依赖用于增强功能，但不是必需的：

```bash
pip install hypothesis pytest
```

- **hypothesis**: 属性测试框架，用于运行属性测试
- **pytest**: 测试框架，用于运行单元测试

## 快速安装

### 方法 1: 使用 requirements.txt
```bash
pip install -r requirements.txt
```

### 方法 2: 手动安装核心依赖
```bash
pip install aiohttp psutil
```

## 依赖说明

### aiohttp
- **用途**: 所有 AI 模型适配器（Luma、Runway、Pika）都需要此库来进行异步 HTTP 请求
- **版本要求**: >= 3.8.0
- **如果缺失**: 模型适配器将不可用，但其他功能正常工作

### psutil
- **用途**: 系统性能监控、资源管理、性能优化
- **版本要求**: >= 5.8.0
- **如果缺失**: 性能监控和资源管理功能将降级或不可用

## 故障排除

### 常见错误

#### ModuleNotFoundError: No module named 'aiohttp'
```bash
# 解决方案
pip install aiohttp
```

#### ModuleNotFoundError: No module named 'psutil'
```bash
# 解决方案
pip install psutil
```

### 安装失败

#### 在某些系统上 psutil 安装失败
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# CentOS/RHEL
sudo yum install python3-devel

# 然后重新安装
pip install psutil
```

#### 在 Windows 上安装失败
```bash
# 使用预编译的轮子
pip install --only-binary=all psutil
```

## 功能降级

如果某些依赖不可用，Video Studio 会优雅地降级：

### 缺少 aiohttp
- ❌ AI 模型适配器不可用
- ❌ 无法生成视频
- ✅ UI 界面正常显示
- ✅ 模板系统可用
- ✅ 配置管理可用

### 缺少 psutil
- ❌ 性能监控不可用
- ❌ 资源管理功能受限
- ✅ 基本视频生成功能可用
- ✅ 模型适配器可用
- ✅ 工作流管理可用

## 开发环境设置

### 完整开发环境
```bash
# 安装所有依赖
pip install -r requirements.txt

# 验证安装
python -c "import aiohttp, psutil; print('All dependencies installed successfully')"
```

### 最小运行环境
```bash
# 仅安装核心依赖
pip install aiohttp psutil

# 验证核心功能
python -c "from app_utils.video_studio import LumaAdapter; print('Core adapters available')"
```

## 版本兼容性

### Python 版本
- **最低要求**: Python 3.8+
- **推荐版本**: Python 3.9+

### 依赖版本
- **aiohttp**: >= 3.8.0, < 4.0.0
- **psutil**: >= 5.8.0
- **hypothesis**: >= 6.0.0 (测试用)
- **pytest**: >= 6.0.0 (测试用)

## 生产部署

### Docker 环境
```dockerfile
# 在 Dockerfile 中添加
RUN pip install aiohttp psutil
```

### 云平台部署
确保在部署配置中包含所需依赖：

```yaml
# requirements.txt 应包含
aiohttp>=3.8.0
psutil>=5.8.0
```

## 验证安装

### 检查脚本
创建一个简单的检查脚本来验证所有依赖：

```python
#!/usr/bin/env python3
"""验证 Video Studio 依赖安装"""

def check_dependencies():
    missing = []
    
    try:
        import aiohttp
        print("✅ aiohttp available")
    except ImportError:
        missing.append("aiohttp")
        print("❌ aiohttp missing")
    
    try:
        import psutil
        print("✅ psutil available")
    except ImportError:
        missing.append("psutil")
        print("❌ psutil missing")
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("请运行: pip install " + " ".join(missing))
        return False
    else:
        print("\n🎉 所有依赖都已正确安装！")
        return True

if __name__ == "__main__":
    check_dependencies()
```

### 功能测试
```python
# 测试适配器可用性
from app_utils.video_studio.adapters import (
    LUMA_AVAILABLE, 
    RUNWAY_AVAILABLE, 
    PIKA_AVAILABLE
)

print(f"Luma Adapter: {'✅' if LUMA_AVAILABLE else '❌'}")
print(f"Runway Adapter: {'✅' if RUNWAY_AVAILABLE else '❌'}")
print(f"Pika Adapter: {'✅' if PIKA_AVAILABLE else '❌'}")
```
