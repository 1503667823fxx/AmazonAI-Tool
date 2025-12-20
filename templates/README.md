# 模板库目录结构说明

## 目录组织

本目录包含APlus Studio的所有模板资源，按照以下结构组织：

### config/
全局配置文件目录，包含：
- `categories.yaml` - 分类定义配置
- `template_types.yaml` - 模板类型配置
- `validation_rules.yaml` - 验证规则配置
- `global_settings.yaml` - 全局系统设置

### by_category/
按分类组织的模板存储目录：
- `electronics/` - 电子产品类模板
- `beauty/` - 美妆护肤类模板
- `home/` - 家居用品类模板
- `seasonal/` - 季节性模板

## 模板目录结构

每个模板应遵循以下标准结构：

```
template_name/
├── template.json          # 模板配置文件 (必需)
├── README.md             # 模板说明文档 (必需)
├── preview.jpg           # 预览缩略图 300x200px (必需)
├── desktop/              # 桌面版模板 (必需)
│   ├── header.jpg        # 1464x600px
│   ├── features.jpg      # 1464x600px
│   └── ...
├── mobile/               # 移动版模板 (必需)
│   ├── header.jpg        # 600x450px
│   ├── features.jpg      # 600x450px
│   └── ...
├── docs/                 # 文档目录 (可选)
└── metadata/             # 元数据目录 (自动生成)
```

## 命名规范

- 模板ID: 使用kebab-case格式，如 `tech_modern`
- 文件名: 小写字母、数字和下划线，如 `header.jpg`
- 目录名: 小写字母、数字和下划线

## 图片尺寸要求

- 预览图: 300x200px
- 桌面版: 1464x600px
- 移动版: 600x450px

## 使用说明

请参考 `/tools/` 目录下的CLI工具来管理模板。

更多详细信息，请查看项目文档。
