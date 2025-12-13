# Scripts 工具脚本目录

本目录包含用于开发、测试和维护的工具脚本。

## 文件说明

### `optimize_ai_studio.py`
**AI Studio 性能优化脚本**

**用途：**
- 性能测试和基准测试
- 组件加载时间分析
- 内存使用优化验证
- 错误处理性能测试
- 生产环境准备检查

**功能：**
1. **状态管理性能测试** - 测试消息添加、状态获取的性能
2. **组件加载性能** - 测试UI组件的导入和初始化时间
3. **CSS注入性能** - 测试样式系统的性能
4. **内存使用分析** - 测试大量消息时的内存效率
5. **错误处理性能** - 测试错误处理系统的响应时间
6. **文件处理性能** - 测试文件验证的性能
7. **性能报告** - 生成详细的性能分析报告
8. **优化建议** - 提供基于测试结果的优化建议

**运行方式：**
```bash
# 从项目根目录运行
python scripts/optimize_ai_studio.py
```

**输出示例：**
```
🚀 AI Studio Performance Optimization
==================================================

=== Optimization 1: State Management ===
✓ Message addition performance: 0.023s for 100 messages
✓ State retrieval performance: 0.001s for 100 operations
✓ State management optimized

=== Optimization 2: Component Loading ===
✓ Component loading time: 0.156s
✓ UI controller initialized

📊 Performance Summary
==================================================
Total optimization time: 0.245s
Component loading: 0.156s
State operations: 0.024s
CSS injection: 0.008s
...

💡 Performance Recommendations:
  ✅ Component loading is optimal
  ✅ Message operations are optimal
  ✅ CSS injection is optimal

🎯 AI Studio is performance optimized!
```

**何时使用：**
- 开发新功能后验证性能影响
- 部署前的性能检查
- 性能问题排查
- 优化效果验证

## 使用指南

### 运行所有脚本
```bash
# 性能优化检查
python scripts/optimize_ai_studio.py
```

### 添加新脚本
当添加新的工具脚本时，请：
1. 使用描述性的文件名
2. 在文件顶部添加详细的文档字符串
3. 更新此README文档
4. 确保脚本可以从项目根目录运行

### 脚本开发规范
- 所有脚本应该可以独立运行
- 使用相对路径引用项目文件
- 提供清晰的输出和错误信息
- 包含适当的错误处理
- 在脚本顶部添加 `sys.path.append()` 来正确导入项目模块