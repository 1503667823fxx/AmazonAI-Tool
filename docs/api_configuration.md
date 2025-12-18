# Video Studio API 配置指南

## 概述

Video Studio 使用多种 AI API 来提供完整的视频生成功能。本指南说明如何配置这些 API。

## 当前 API 配置

### 文本生成 API

**使用**: Google Gemini API  
**模型**: `gemini-3.0-flash-preview`  
**用途**: 生成视频脚本和场景描述

#### 配置方法
1. 在 Streamlit Secrets 中添加：
   ```toml
   [secrets]
   GOOGLE_API_KEY = "your_google_api_key_here"
   ```

2. 或在本地 `.streamlit/secrets.toml` 中添加：
   ```toml
   GOOGLE_API_KEY = "your_google_api_key_here"
   ```

#### 获取 API 密钥
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建新的 API 密钥
3. 复制密钥到配置文件

### 视频生成 API

**当前支持的模型**:
- Luma Dream Machine
- Runway ML
- Pika Labs

**状态**: 待配置 (根据需要选择)

#### Luma Dream Machine
```toml
LUMA_API_KEY = "your_luma_api_key"
```

#### Runway ML
```toml
RUNWAY_API_KEY = "your_runway_api_key"
```

#### Pika Labs
```toml
PIKA_API_KEY = "your_pika_api_key"
```

## API 使用说明

### 脚本生成 (Script Engine)

**文件**: `services/video_studio/script_engine.py`  
**API**: Google Gemini  
**功能**: 根据商品信息生成视频脚本

```python
from services.video_studio.script_engine import generate_video_script

# 使用示例
script = generate_video_script(
    api_key=st.secrets["GOOGLE_API_KEY"],
    product_info="商品描述",
    video_duration=15,
    style="Amazon Minimalist"
)
```

### 视频生成 (Visual Engine)

**文件**: `services/video_studio/visual_engine.py`  
**API**: Luma Dream Machine (默认)  
**功能**: 根据脚本生成视频片段

```python
from services.video_studio.visual_engine import batch_generate_videos

# 使用示例
videos = batch_generate_videos(
    scenes=script_data["scenes"],
    api_key=st.secrets["LUMA_API_KEY"]
)
```

## 错误处理

### API 不可用时的降级处理

Video Studio 提供了优雅的降级处理：

1. **脚本生成不可用**
   - 显示警告信息
   - 提供手动输入脚本的选项
   - 返回错误信息而不是崩溃

2. **视频生成不可用**
   - 显示警告信息
   - 提供模拟生成结果
   - 允许用户上传自己的视频

### 常见错误及解决方案

#### API 密钥无效
```
错误: Authentication failed
解决: 检查 API 密钥是否正确配置
```

#### API 配额超限
```
错误: Quota exceeded
解决: 检查 API 使用配额，升级计划或等待重置
```

#### 网络连接问题
```
错误: Connection timeout
解决: 检查网络连接，重试请求
```

## 成本优化

### Gemini API 成本优化

1. **选择合适的模型**
   - `gemini-3.0-flash-preview`: 快速且经济
   - `gemini-pro`: 更高质量但成本更高

2. **优化提示词**
   - 使用简洁明确的提示词
   - 避免不必要的长文本生成

3. **缓存结果**
   - 对相似的商品信息缓存脚本
   - 避免重复生成相同内容

### 视频 API 成本优化

1. **批量处理**
   - 一次性生成多个场景
   - 利用批量折扣

2. **质量设置**
   - 根据需要选择合适的质量
   - 预览时使用较低质量

3. **时长控制**
   - 控制视频时长以降低成本
   - 优化场景数量

## 开发和测试

### 本地开发配置

1. 创建 `.streamlit/secrets.toml`:
   ```toml
   GOOGLE_API_KEY = "your_development_key"
   LUMA_API_KEY = "your_luma_key"
   # 其他 API 密钥...
   ```

2. 使用测试模式:
   ```python
   # 在开发时使用模拟 API
   if st.secrets.get("DEVELOPMENT_MODE", False):
       # 使用模拟响应
       pass
   ```

### 测试 API 连接

```python
# 测试 Gemini API
import google.generativeai as genai

def test_gemini_api(api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.0-flash-preview')
        response = model.generate_content("Hello, world!")
        return True, response.text
    except Exception as e:
        return False, str(e)

# 在 Streamlit 中使用
if st.button("测试 Gemini API"):
    success, result = test_gemini_api(st.secrets["GOOGLE_API_KEY"])
    if success:
        st.success("API 连接成功!")
        st.write(result)
    else:
        st.error(f"API 连接失败: {result}")
```

## 安全最佳实践

### API 密钥安全

1. **永远不要在代码中硬编码 API 密钥**
2. **使用 Streamlit Secrets 管理密钥**
3. **定期轮换 API 密钥**
4. **限制 API 密钥的权限范围**

### 访问控制

1. **实施速率限制**
2. **监控 API 使用情况**
3. **设置使用配额警告**
4. **记录 API 调用日志**

## 故障排除

### 检查清单

- [ ] API 密钥是否正确配置
- [ ] 网络连接是否正常
- [ ] API 配额是否充足
- [ ] 依赖包是否正确安装
- [ ] 错误日志是否有详细信息

### 调试工具

```python
# API 状态检查工具
def check_api_status():
    status = {}
    
    # 检查 Gemini API
    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        status["gemini"] = "✅ 可用"
    except Exception as e:
        status["gemini"] = f"❌ 不可用: {e}"
    
    # 检查其他 API...
    
    return status

# 在 Streamlit 中显示状态
if st.sidebar.button("检查 API 状态"):
    status = check_api_status()
    for api, state in status.items():
        st.sidebar.write(f"{api}: {state}")
```

## 更新日志

- **2024-12-17**: 从 OpenAI 迁移到 Google Gemini API
- **2024-12-17**: 添加优雅的 API 错误处理
- **2024-12-17**: 创建 API 配置指南
