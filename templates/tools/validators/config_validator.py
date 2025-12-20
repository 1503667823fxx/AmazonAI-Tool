#!/usr/bin/env python3
"""
配置文件验证器
验证模板配置文件的格式和内容完整性
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import jsonschema
from jsonschema import validate, ValidationError
import click
from rich.console import Console
from rich.table import Table

console = Console()


class ConfigValidator:
    """配置文件验证器"""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """初始化验证器
        
        Args:
            schema_path: JSON Schema文件路径，默认使用内置schema
        """
        self.schema_path = schema_path or Path(__file__).parent.parent / "schemas" / "template_config_schema.json"
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict[str, Any]:
        """加载JSON Schema"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print(f"[yellow]警告: Schema文件不存在: {self.schema_path}[/yellow]")
            return self._get_default_schema()
        except json.JSONDecodeError as e:
            console.print(f"[red]错误: Schema文件格式错误: {e}[/red]")
            sys.exit(1)
    
    def _get_default_schema(self) -> Dict[str, Any]:
        """获取默认的JSON Schema"""
        return {
            "type": "object",
            "required": ["id", "name", "category", "template_type", "status"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "category": {"type": "string", "minLength": 1},
                "template_type": {"type": "string", "enum": ["standard", "premium", "seasonal"]},
                "status": {"type": "string", "enum": ["draft", "published", "archived"]},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "description": {"type": "string"},
                "classification": {
                    "type": "object",
                    "properties": {
                        "primary_category": {"type": "string"},
                        "style_tags": {"type": "array", "items": {"type": "string"}},
                        "keyword_tags": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "assets": {
                    "type": "object",
                    "properties": {
                        "preview": {"type": "string"},
                        "desktop": {"type": "object"},
                        "mobile": {"type": "object"}
                    }
                }
            }
        }
    
    def validate_config(self, config_path: Path) -> tuple[bool, List[str]]:
        """验证单个配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        try:
            # 检查文件是否存在
            if not config_path.exists():
                errors.append(f"配置文件不存在: {config_path}")
                return False, errors
            
            # 加载配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # JSON Schema验证
            try:
                validate(instance=config_data, schema=self.schema)
            except ValidationError as e:
                errors.append(f"Schema验证失败: {e.message}")
            
            # 自定义验证规则
            custom_errors = self._validate_custom_rules(config_data, config_path)
            errors.extend(custom_errors)
            
        except json.JSONDecodeError as e:
            errors.append(f"JSON格式错误: {e}")
        except Exception as e:
            errors.append(f"验证过程中发生错误: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_custom_rules(self, config: Dict[str, Any], config_path: Path) -> List[str]:
        """自定义验证规则"""
        errors = []
        
        # 检查资源文件是否存在
        if "assets" in config:
            template_dir = config_path.parent
            assets = config["assets"]
            
            # 检查预览图
            if "preview" in assets:
                preview_path = template_dir / assets["preview"]
                if not preview_path.exists():
                    errors.append(f"预览图不存在: {preview_path}")
            
            # 检查桌面版资源
            if "desktop" in assets:
                for section, filename in assets["desktop"].items():
                    asset_path = template_dir / filename
                    if not asset_path.exists():
                        errors.append(f"桌面版资源不存在: {asset_path}")
            
            # 检查移动版资源
            if "mobile" in assets:
                for section, filename in assets["mobile"].items():
                    asset_path = template_dir / filename
                    if not asset_path.exists():
                        errors.append(f"移动版资源不存在: {asset_path}")
        
        # 检查ID格式
        if "id" in config:
            template_id = config["id"]
            if not template_id.replace("_", "").replace("-", "").isalnum():
                errors.append(f"模板ID格式不正确: {template_id}")
        
        # 检查版本格式
        if "version" in config:
            version = config["version"]
            if not version.count(".") == 2:
                errors.append(f"版本号格式不正确: {version}")
        
        return errors
    
    def validate_directory(self, directory: Path) -> Dict[str, tuple[bool, List[str]]]:
        """验证目录下的所有配置文件
        
        Args:
            directory: 目录路径
            
        Returns:
            {文件路径: (是否有效, 错误列表)}
        """
        results = {}
        
        # 查找所有template.json文件
        for config_file in directory.rglob("template.json"):
            is_valid, errors = self.validate_config(config_file)
            results[str(config_file)] = (is_valid, errors)
        
        return results


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--schema', '-s', type=click.Path(exists=True, path_type=Path), 
              help='JSON Schema文件路径')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
@click.option('--quiet', '-q', is_flag=True, help='只显示错误')
def main(paths: tuple[Path, ...], schema: Optional[Path], verbose: bool, quiet: bool):
    """验证模板配置文件
    
    PATHS: 要验证的文件或目录路径
    """
    if not paths:
        console.print("[red]错误: 请指定要验证的文件或目录[/red]")
        sys.exit(1)
    
    validator = ConfigValidator(schema)
    all_valid = True
    total_files = 0
    valid_files = 0
    
    for path in paths:
        if path.is_file():
            # 验证单个文件
            is_valid, errors = validator.validate_config(path)
            total_files += 1
            
            if is_valid:
                valid_files += 1
                if verbose and not quiet:
                    console.print(f"[green]✓[/green] {path}")
            else:
                all_valid = False
                if not quiet:
                    console.print(f"[red]✗[/red] {path}")
                    for error in errors:
                        console.print(f"  [red]•[/red] {error}")
        
        elif path.is_dir():
            # 验证目录下的所有配置文件
            results = validator.validate_directory(path)
            
            for file_path, (is_valid, errors) in results.items():
                total_files += 1
                
                if is_valid:
                    valid_files += 1
                    if verbose and not quiet:
                        console.print(f"[green]✓[/green] {file_path}")
                else:
                    all_valid = False
                    if not quiet:
                        console.print(f"[red]✗[/red] {file_path}")
                        for error in errors:
                            console.print(f"  [red]•[/red] {error}")
    
    # 显示统计信息
    if not quiet:
        table = Table(title="验证结果统计")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="magenta")
        
        table.add_row("总文件数", str(total_files))
        table.add_row("有效文件", str(valid_files))
        table.add_row("无效文件", str(total_files - valid_files))
        
        console.print(table)
    
    if all_valid:
        if not quiet:
            console.print("[green]所有配置文件验证通过![/green]")
        sys.exit(0)
    else:
        if not quiet:
            console.print("[red]发现配置文件错误![/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()