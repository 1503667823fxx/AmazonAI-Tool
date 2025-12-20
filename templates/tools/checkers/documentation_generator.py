#!/usr/bin/env python3
"""
文档生成器
开发自动文档生成功能，创建模板使用指南和API文档，支持多种输出格式(HTML, Markdown, PDF)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import click
from rich.console import Console
from rich.markdown import Markdown
import jinja2

console = Console()


@dataclass
class TemplateDocumentation:
    """模板文档数据"""
    template_id: str
    template_name: str
    template_path: str
    category: str
    description: str
    
    # 基本信息
    version: str
    status: str
    created_at: str
    updated_at: str
    
    # 设计属性
    style_tags: List[str]
    keywords: List[str]
    sections: List[str]
    color_schemes: List[Dict[str, str]]
    
    # 技术规格
    supported_formats: Dict[str, Dict[str, Any]]
    replaceable_areas: Dict[str, Dict[str, Any]]
    assets: Dict[str, Any]
    
    # 使用指南
    usage_instructions: str = ""
    customization_guide: str = ""
    best_practices: List[str] = None
    
    def __post_init__(self):
        if self.best_practices is None:
            self.best_practices = []


class DocumentationGenerator:
    """文档生成器"""
    
    def __init__(self):
        """初始化文档生成器"""
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # 设置默认模板
        self._setup_default_templates()
    
    def generate_template_documentation(self, template_path: Path, output_format: str = "markdown") -> str:
        """为单个模板生成文档
        
        Args:
            template_path: 模板目录路径
            output_format: 输出格式 (markdown, html, json)
            
        Returns:
            生成的文档内容
        """
        # 提取模板信息
        doc_data = self._extract_template_info(template_path)
        
        # 根据格式生成文档
        if output_format == "markdown":
            return self._generate_markdown_doc(doc_data)
        elif output_format == "html":
            return self._generate_html_doc(doc_data)
        elif output_format == "json":
            return self._generate_json_doc(doc_data)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def generate_library_documentation(self, templates_root: Path, output_format: str = "markdown") -> str:
        """为整个模板库生成文档
        
        Args:
            templates_root: 模板库根目录
            output_format: 输出格式
            
        Returns:
            生成的文档内容
        """
        # 收集所有模板信息
        templates_data = []
        categories = {}
        
        for category_dir in templates_root.iterdir():
            if category_dir.is_dir() and category_dir.name != "config":
                category_name = category_dir.name
                categories[category_name] = []
                
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir():
                        try:
                            doc_data = self._extract_template_info(template_dir)
                            templates_data.append(doc_data)
                            categories[category_name].append(doc_data)
                        except Exception as e:
                            console.print(f"[yellow]警告: 无法处理模板 {template_dir}: {e}[/yellow]")
        
        # 生成库级文档
        library_data = {
            "title": "模板库文档",
            "generated_at": datetime.now().isoformat(),
            "total_templates": len(templates_data),
            "categories": categories,
            "templates": templates_data
        }
        
        if output_format == "markdown":
            return self._generate_library_markdown(library_data)
        elif output_format == "html":
            return self._generate_library_html(library_data)
        elif output_format == "json":
            return json.dumps(library_data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def generate_api_documentation(self, output_format: str = "markdown") -> str:
        """生成API文档
        
        Args:
            output_format: 输出格式
            
        Returns:
            API文档内容
        """
        api_data = {
            "title": "模板库管理系统 API 文档",
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "endpoints": self._get_api_endpoints(),
            "models": self._get_api_models(),
            "examples": self._get_api_examples()
        }
        
        if output_format == "markdown":
            return self._generate_api_markdown(api_data)
        elif output_format == "html":
            return self._generate_api_html(api_data)
        elif output_format == "json":
            return json.dumps(api_data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def _extract_template_info(self, template_path: Path) -> TemplateDocumentation:
        """提取模板信息"""
        config_path = template_path / "template.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 读取README内容
        readme_path = template_path / "README.md"
        usage_instructions = ""
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                usage_instructions = f.read()
        
        # 提取分类信息
        classification = config.get("classification", {})
        design_attributes = config.get("design_attributes", {})
        
        return TemplateDocumentation(
            template_id=config.get("id", template_path.name),
            template_name=config.get("name", template_path.name),
            template_path=str(template_path),
            category=config.get("category", "未分类"),
            description=config.get("description", ""),
            version=config.get("version", "1.0.0"),
            status=config.get("status", "draft"),
            created_at=config.get("metadata", {}).get("created_at", ""),
            updated_at=config.get("metadata", {}).get("updated_at", ""),
            style_tags=classification.get("style_tags", []),
            keywords=classification.get("keyword_tags", []),
            sections=config.get("layout_structure", {}).get("sections", []),
            color_schemes=config.get("customization_options", {}).get("color_schemes", []),
            supported_formats=config.get("layout_structure", {}).get("supported_formats", {}),
            replaceable_areas=config.get("replaceable_areas", {}),
            assets=config.get("assets", {}),
            usage_instructions=usage_instructions,
            customization_guide=self._generate_customization_guide(config),
            best_practices=self._generate_best_practices(config)
        )
    
    def _generate_customization_guide(self, config: Dict[str, Any]) -> str:
        """生成定制指南"""
        guide_parts = []
        
        # 可替换区域说明
        replaceable_areas = config.get("replaceable_areas", {})
        if replaceable_areas:
            guide_parts.append("## 可替换区域\n")
            for format_type, areas in replaceable_areas.items():
                guide_parts.append(f"### {format_type.title()}版\n")
                for area_name, area_info in areas.items():
                    guide_parts.append(f"- **{area_name}**: {area_info.get('description', '')}")
                    if 'constraints' in area_info:
                        constraints = area_info['constraints']
                        guide_parts.append(f"  - 约束: {', '.join(f'{k}: {v}' for k, v in constraints.items())}")
                guide_parts.append("")
        
        # 配色方案说明
        color_schemes = config.get("customization_options", {}).get("color_schemes", [])
        if color_schemes:
            guide_parts.append("## 配色方案\n")
            for scheme in color_schemes:
                guide_parts.append(f"### {scheme.get('name', '未命名')}")
                guide_parts.append(f"- 主色: {scheme.get('primary', '')}")
                guide_parts.append(f"- 辅色: {scheme.get('secondary', '')}")
                guide_parts.append(f"- 强调色: {scheme.get('accent', '')}")
                guide_parts.append("")
        
        return "\n".join(guide_parts)
    
    def _generate_best_practices(self, config: Dict[str, Any]) -> List[str]:
        """生成最佳实践建议"""
        practices = []
        
        # 根据模板类型添加建议
        template_type = config.get("template_type", "")
        category = config.get("category", "")
        
        if template_type == "premium":
            practices.append("使用高质量图片以充分展现产品特色")
            practices.append("确保品牌元素与整体设计风格协调")
        
        if category == "electronics":
            practices.append("突出产品的技术规格和创新特性")
            practices.append("使用清晰的产品图片展示细节")
        elif category == "beauty":
            practices.append("注重色彩搭配和视觉美感")
            practices.append("展示产品使用效果和成分信息")
        
        # 通用建议
        practices.extend([
            "保持文字内容简洁明了",
            "确保图片分辨率符合平台要求",
            "定期更新产品信息和图片"
        ])
        
        return practices
    
    def _generate_markdown_doc(self, doc_data: TemplateDocumentation) -> str:
        """生成Markdown格式文档"""
        template = self.template_env.get_template("template_doc.md")
        return template.render(doc=doc_data)
    
    def _generate_html_doc(self, doc_data: TemplateDocumentation) -> str:
        """生成HTML格式文档"""
        template = self.template_env.get_template("template_doc.html")
        return template.render(doc=doc_data)
    
    def _generate_json_doc(self, doc_data: TemplateDocumentation) -> str:
        """生成JSON格式文档"""
        return json.dumps(doc_data.__dict__, ensure_ascii=False, indent=2)
    
    def _generate_library_markdown(self, library_data: Dict[str, Any]) -> str:
        """生成库级Markdown文档"""
        template = self.template_env.get_template("library_doc.md")
        return template.render(**library_data)
    
    def _generate_library_html(self, library_data: Dict[str, Any]) -> str:
        """生成库级HTML文档"""
        template = self.template_env.get_template("library_doc.html")
        return template.render(**library_data)
    
    def _generate_api_markdown(self, api_data: Dict[str, Any]) -> str:
        """生成API Markdown文档"""
        template = self.template_env.get_template("api_doc.md")
        return template.render(**api_data)
    
    def _generate_api_html(self, api_data: Dict[str, Any]) -> str:
        """生成API HTML文档"""
        template = self.template_env.get_template("api_doc.html")
        return template.render(**api_data)
    
    def _get_api_endpoints(self) -> List[Dict[str, Any]]:
        """获取API端点信息"""
        return [
            {
                "path": "/api/templates",
                "method": "GET",
                "description": "获取模板列表",
                "parameters": [
                    {"name": "category", "type": "string", "description": "模板分类"},
                    {"name": "status", "type": "string", "description": "模板状态"},
                    {"name": "limit", "type": "integer", "description": "返回数量限制"}
                ],
                "response": {
                    "type": "object",
                    "properties": {
                        "templates": {"type": "array", "description": "模板列表"},
                        "total": {"type": "integer", "description": "总数量"}
                    }
                }
            },
            {
                "path": "/api/templates/{id}",
                "method": "GET",
                "description": "获取单个模板详情",
                "parameters": [
                    {"name": "id", "type": "string", "description": "模板ID"}
                ],
                "response": {
                    "type": "object",
                    "description": "模板详细信息"
                }
            },
            {
                "path": "/api/templates",
                "method": "POST",
                "description": "创建新模板",
                "request_body": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "模板名称"},
                        "category": {"type": "string", "description": "模板分类"},
                        "description": {"type": "string", "description": "模板描述"}
                    }
                },
                "response": {
                    "type": "object",
                    "description": "创建的模板信息"
                }
            }
        ]
    
    def _get_api_models(self) -> List[Dict[str, Any]]:
        """获取API数据模型"""
        return [
            {
                "name": "Template",
                "description": "模板数据模型",
                "properties": {
                    "id": {"type": "string", "description": "模板唯一标识"},
                    "name": {"type": "string", "description": "模板名称"},
                    "category": {"type": "string", "description": "模板分类"},
                    "status": {"type": "string", "enum": ["draft", "published", "archived"]},
                    "version": {"type": "string", "description": "版本号"},
                    "created_at": {"type": "string", "format": "datetime"},
                    "updated_at": {"type": "string", "format": "datetime"}
                }
            },
            {
                "name": "TemplateConfig",
                "description": "模板配置模型",
                "properties": {
                    "sections": {"type": "array", "items": {"type": "string"}},
                    "assets": {"type": "object", "description": "资源文件配置"},
                    "replaceable_areas": {"type": "object", "description": "可替换区域配置"}
                }
            }
        ]
    
    def _get_api_examples(self) -> List[Dict[str, Any]]:
        """获取API使用示例"""
        return [
            {
                "title": "获取模板列表",
                "request": {
                    "method": "GET",
                    "url": "/api/templates?category=electronics&status=published",
                    "headers": {"Content-Type": "application/json"}
                },
                "response": {
                    "status": 200,
                    "body": {
                        "templates": [
                            {
                                "id": "tech_modern",
                                "name": "科技现代风",
                                "category": "electronics",
                                "status": "published"
                            }
                        ],
                        "total": 1
                    }
                }
            },
            {
                "title": "创建新模板",
                "request": {
                    "method": "POST",
                    "url": "/api/templates",
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "name": "新模板",
                        "category": "electronics",
                        "description": "这是一个新的电子产品模板"
                    }
                },
                "response": {
                    "status": 201,
                    "body": {
                        "id": "new_template",
                        "name": "新模板",
                        "category": "electronics",
                        "status": "draft"
                    }
                }
            }
        ]
    
    def _setup_default_templates(self):
        """设置默认模板"""
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # 创建模板文档模板
        template_doc_md = '''# {{ doc.template_name }}

## 基本信息

- **模板ID**: {{ doc.template_id }}
- **分类**: {{ doc.category }}
- **版本**: {{ doc.version }}
- **状态**: {{ doc.status }}
- **描述**: {{ doc.description }}

## 设计属性

{% if doc.style_tags %}
- **风格标签**: {{ doc.style_tags | join(', ') }}
{% endif %}
{% if doc.keywords %}
- **关键词**: {{ doc.keywords | join(', ') }}
{% endif %}
{% if doc.sections %}
- **模块**: {{ doc.sections | join(', ') }}
{% endif %}

## 技术规格

### 支持格式

{% for format_name, format_info in doc.supported_formats.items() %}
- **{{ format_name.title() }}**: {{ format_info.width }}x{{ format_info.height }}px - {{ format_info.description }}
{% endfor %}

### 资源文件

{% for category, assets in doc.assets.items() %}
#### {{ category.title() }}
{% if assets is mapping %}
{% for name, path in assets.items() %}
- {{ name }}: `{{ path }}`
{% endfor %}
{% else %}
- {{ category }}: `{{ assets }}`
{% endif %}
{% endfor %}

{{ doc.customization_guide }}

## 使用说明

{{ doc.usage_instructions }}

## 最佳实践

{% for practice in doc.best_practices %}
- {{ practice }}
{% endfor %}

---
*文档生成时间: {{ doc.updated_at }}*
'''
        
        with open(templates_dir / "template_doc.md", 'w', encoding='utf-8') as f:
            f.write(template_doc_md)
        
        # 创建库文档模板
        library_doc_md = '''# {{ title }}

*生成时间: {{ generated_at }}*

## 概览

- **总模板数**: {{ total_templates }}
- **分类数**: {{ categories | length }}

## 分类目录

{% for category_name, templates in categories.items() %}
### {{ category_name }}

{% for template in templates %}
- [{{ template.template_name }}](#{{ template.template_id }}) - {{ template.description }}
{% endfor %}

{% endfor %}

## 模板详情

{% for template in templates %}
## {{ template.template_name }}

- **ID**: {{ template.template_id }}
- **分类**: {{ template.category }}
- **版本**: {{ template.version }}
- **状态**: {{ template.status }}
- **描述**: {{ template.description }}

{% if template.style_tags %}
**风格标签**: {{ template.style_tags | join(', ') }}
{% endif %}

{% if template.sections %}
**包含模块**: {{ template.sections | join(', ') }}
{% endif %}

---

{% endfor %}
'''
        
        with open(templates_dir / "library_doc.md", 'w', encoding='utf-8') as f:
            f.write(library_doc_md)
        
        # 创建API文档模板
        api_doc_md = '''# {{ title }}

**版本**: {{ version }}  
**生成时间**: {{ generated_at }}

## API 端点

{% for endpoint in endpoints %}
### {{ endpoint.method }} {{ endpoint.path }}

{{ endpoint.description }}

{% if endpoint.parameters %}
**参数**:
{% for param in endpoint.parameters %}
- `{{ param.name }}` ({{ param.type }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if endpoint.request_body %}
**请求体**:
```json
{{ endpoint.request_body | tojson(indent=2) }}
```
{% endif %}

**响应**:
```json
{{ endpoint.response | tojson(indent=2) }}
```

---

{% endfor %}

## 数据模型

{% for model in models %}
### {{ model.name }}

{{ model.description }}

**属性**:
{% for prop_name, prop_info in model.properties.items() %}
- `{{ prop_name }}` ({{ prop_info.type }}): {{ prop_info.description }}
{% endfor %}

---

{% endfor %}

## 使用示例

{% for example in examples %}
### {{ example.title }}

**请求**:
```http
{{ example.request.method }} {{ example.request.url }}
{% for header_name, header_value in example.request.headers.items() %}
{{ header_name }}: {{ header_value }}
{% endfor %}

{% if example.request.body %}
{{ example.request.body | tojson(indent=2) }}
{% endif %}
```

**响应**:
```http
HTTP/1.1 {{ example.response.status }}

{{ example.response.body | tojson(indent=2) }}
```

---

{% endfor %}
'''
        
        with open(templates_dir / "api_doc.md", 'w', encoding='utf-8') as f:
            f.write(api_doc_md)


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), 
              default='markdown', help='输出格式')
@click.option('--type', '-t', type=click.Choice(['template', 'library', 'api']), 
              default='template', help='文档类型')
@click.option('--title', help='文档标题')
def main(paths: tuple[Path, ...], output: Optional[Path], format: str, type: str, title: Optional[str]):
    """文档生成工具
    
    PATHS: 模板目录或模板库根目录路径
    """
    generator = DocumentationGenerator()
    
    if type == "api":
        # 生成API文档
        content = generator.generate_api_documentation(format)
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            console.print(f"[green]API文档已生成: {output}[/green]")
        else:
            if format == "markdown":
                console.print(Markdown(content))
            else:
                print(content)
    
    elif not paths:
        console.print("[red]错误: 请指定模板目录路径[/red]")
        sys.exit(1)
    
    else:
        for path in paths:
            if type == "library" or path.name == "by_category" or "by_category" in str(path):
                # 生成库级文档
                content = generator.generate_library_documentation(path, format)
                
                if output:
                    output_file = output
                else:
                    output_file = path.parent / f"library_documentation.{format}"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                console.print(f"[green]库文档已生成: {output_file}[/green]")
            
            else:
                # 生成单个模板文档
                content = generator.generate_template_documentation(path, format)
                
                if output:
                    output_file = output
                else:
                    output_file = path / f"documentation.{format}"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                console.print(f"[green]模板文档已生成: {output_file}[/green]")


if __name__ == "__main__":
    main()