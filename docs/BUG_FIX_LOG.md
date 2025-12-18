# 🔧 Bug 修复记录

## 2024-12-16: Magic Canvas 涂抹数据粘贴后消失问题

### 问题描述
在 Magic Canvas 页面中，用户复制涂抹数据（base64 图片码）粘贴到输入框后，点击确认按钮时数据会消失。

### 根本原因
1. **Streamlit rerun 机制**: 当粘贴大量数据（如 base64 图片数据，通常几万字符）时，Streamlit 会触发页面重新渲染
2. **动态 key 问题**: `text_area` 的 `key` 使用了 `canvas_key` 变量，导致每次 rerun 时组件被视为新组件
3. **数据未持久化**: 输入的数据没有及时保存到 `session_state`，在 rerun 时丢失

### 解决方案

#### 修改文件: `pages/3_🖌️_Magic_Canvas.py`

1. **添加持久化存储变量**
```python
if "pending_mask_input" not in st.session_state:
    st.session_state.pending_mask_input = ""
```

2. **使用 on_change 回调立即保存数据**
```python
def save_mask_input():
    """回调函数：在输入变化时立即保存到 session_state"""
    input_value = st.session_state.get("mask_input_widget", "")
    if input_value:
        st.session_state.pending_mask_input = input_value
```

3. **使用固定的 key 并从 session_state 恢复数据**
```python
mask_data_input = st.text_area(
    "将复制的涂抹数据粘贴到这里",
    value=st.session_state.pending_mask_input,  # 从 session_state 恢复数据
    height=120,
    key="mask_input_widget",  # 使用固定的 key（不随 canvas_key 变化）
    on_change=save_mask_input  # 输入变化时立即保存
)
```

4. **清除数据时同步清空临时输入**
```python
if st.button("🗑️ 清除数据"):
    st.session_state.confirmed_mask_data = ""
    st.session_state.mask_data = None
    st.session_state.pending_mask_input = ""  # 同时清空临时输入
    st.rerun()
```

### 关键技术点

| 问题 | 解决方法 |
|------|----------|
| 动态 key 导致组件重置 | 使用固定的 key |
| rerun 时数据丢失 | 使用 `on_change` 回调立即保存 |
| 组件值不持久 | 使用 `value` 参数从 session_state 恢复 |

### 补充修复 v2 (同日)

**问题**: 确认按钮点击仍然无效

**根本原因**: Streamlit 的 `st.button` + `disabled` 参数组合存在时序问题。当按钮被点击时触发 rerun，但在 rerun 过程中 `disabled` 状态可能已经变化，导致按钮的点击事件没有被正确处理。

**最终解决方案**: 使用 `st.form` 组件
```python
with st.form(key="mask_data_form", clear_on_submit=False):
    mask_data_input = st.text_area(...)
    submitted = st.form_submit_button("✅ 确认数据", type="primary")
    
    if submitted:
        if mask_data_input and mask_data_input.strip():
            data = mask_data_input.strip()
            if data.startswith('data:image/png;base64,'):
                st.session_state.confirmed_mask_data = data
                st.rerun()
```

**为什么 st.form 有效**:
1. Form 内的输入不会触发 rerun，直到点击 submit 按钮
2. Submit 时，所有 form 内的数据会一起提交
3. 避免了 `disabled` 状态和数据同步的时序问题

### 补充修复 v3 (同日) - st.form 也失败

**问题**: 使用 st.form 后，点击确认数据能看到预览，但点击「开始重绘」后数据又丢失

**根本原因**: 
1. st.form 提交后调用 `st.rerun()` 会导致问题
2. 不调用 `st.rerun()` 时，当前页面能显示预览
3. 但点击其他按钮（如「开始重绘」）触发新的 rerun 时，`confirmed_mask_data` 被重置

**尝试过但失败的方案**:
1. ❌ `on_change` 回调 - 回调执行时 session_state 中的输入值可能还没更新
2. ❌ `st.form` + `st.rerun()` - rerun 后数据丢失
3. ❌ `st.form` 不调用 rerun - 当前页面正常，但下次 rerun 时数据丢失
4. ❌ `confirm_clicked` 标记 + 延迟处理 - pending_mask_data 在 rerun 时被清空
5. ❌ `on_click` 回调 - 回调执行时无法获取 text_area 的当前值

**当前尝试**: 简化方案，直接在按钮点击时处理，不使用复杂的状态管理

### 补充修复 v4 (同日) - 找到真正的根本原因！

**问题**: 点击「确认数据」后能看到预览，但点击「开始重绘」后数据丢失

**真正的根本原因**: `st.file_uploader` 的状态持久化问题！

```python
uploaded_file = st.file_uploader("📁 上传原图", ...)
if uploaded_file:  # 每次 rerun 时这个条件都为 True！
    ...
    st.session_state.confirmed_mask_data = ""  # 每次都被重置！
```

`st.file_uploader` 在 rerun 时会保持其状态，所以 `uploaded_file` 在每次 rerun 时都不是 `None`，导致 `confirmed_mask_data` 每次都被清空。

**解决方案**: 通过文件标识判断是否是新上传的文件
```python
if uploaded_file:
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    
    # 只在上传新文件时才重置数据
    if st.session_state.get("last_uploaded_file_id") != file_id:
        st.session_state.uploaded_image = image
        st.session_state.confirmed_mask_data = ""  # 只在新文件时重置
        st.session_state.last_uploaded_file_id = file_id
```

**关键教训**: 
- `st.file_uploader` 返回值在 rerun 时会保持，不是只在上传时才有值
- 需要额外的标识来判断是否是"新"上传的文件
- 不要在 `if uploaded_file:` 块中无条件重置其他状态

---

## 2024-12-16: Gemini API response_mime_type 错误

### 问题描述
调用 Gemini API 进行图像重绘时报错：
```
400 * GenerateContentRequest.generation_config.response_mime_type: 
allowed mimetypes are text/plain, application/json, application/xml, application/yaml and text/x.enum
```

### 根本原因
1. 原代码使用了 `response_mime_type="image/png"`，但 Gemini API 不支持图片作为 response_mime_type
2. 尝试使用 `response_modalities=['IMAGE', 'TEXT']` 也失败，可能是 SDK 版本不支持或参数被错误解析

### 解决方案
1. **完全移除 generation_config 参数**，让模型自动决定返回格式
2. **使用正确的模型**：`models/gemini-2.5-flash-image`（用户提供的可用模型）

```python
# 错误的写法
response = model.generate_content(
    [prompt, image],
    generation_config=genai.GenerationConfig(
        response_mime_type="image/png"  # ❌ 不支持
    )
)

# 正确的写法
response = model.generate_content([prompt, image])  # ✅ 不设置 generation_config
```

### 可用的模型列表
- `models/gemini-2.5-flash-image` - 支持图像生成
- `models/gemini-3-pro-image-preview` - 支持图像编辑 (Imagen API)
- `models/gemini-3-pro-preview` - 文本模型

### 关键教训
- Gemini API 的 `response_mime_type` 只支持文本格式，不支持图片
- 图像生成模型会自动返回图像，不需要指定输出格式
- 不同版本的 SDK 支持的参数可能不同，遇到错误时先尝试移除可选参数

---

### 预防措施

1. **Streamlit 输入组件最佳实践**:
   - 对于需要持久化的输入，始终使用固定的 `key`
   - 使用 `on_change` 回调而不是依赖返回值
   - 大数据输入场景要考虑 rerun 的影响

2. **session_state 使用规范**:
   - 临时输入数据使用 `pending_xxx` 命名
   - 确认后的数据使用 `confirmed_xxx` 命名
   - 清除操作要同时清理相关的所有状态

---

## 常见 Streamlit 问题速查

### 输入框数据丢失
- 检查 `key` 是否动态变化
- 添加 `on_change` 回调保存数据
- 使用 `value` 参数恢复数据

### 组件状态重置
- 避免在条件语句中创建组件
- 使用 `session_state` 管理状态
- 确保 `key` 在 rerun 间保持一致

### 大数据处理
- 考虑分块处理
- 使用文件上传代替文本粘贴
- 添加加载状态提示
