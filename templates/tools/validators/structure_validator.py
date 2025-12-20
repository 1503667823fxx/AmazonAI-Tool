#!/usr/bin/env python3
"""
目录结构验证器
验证模板目录结构的规范性和完整性
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

# 尝试导入PIL进行图片尺寸验证
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

console = Console()


class StructureValidator:
    """目录结构验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.required_files = {
            "template.json",  # 模板配置文件
            "README.md",      # 说明文档
            "preview.jpg"     # 预览缩略图
        }
        
        self.required_directories = {
            "desktop",        # 桌面版资源
            "mobile"          # 移动版资源
        }
        
        self.optional_directories = {
            "docs",           # 文档目录
            "metadata",       # 元数据目录
            "assets"          # 额外资源
        }
        
        self.allowed_image_extensions = {".jpg", ".jpeg", ".png"}
        self.standard_sections = {
            "header", "hero", "features", "gallery", "specs", 
            "lifestyle", "ingredients", "results", "usage"
        }
        
        # 标准图片尺寸要求
        self.image_dimensions = {
            "desktop": (1464, 600),
            "mobile": (600, 450),
            "preview": (300, 200)
        }
        
        # 配置文件必需字段
        self.required_config_fields = {
            "id", "name", "category", "template_type", "status", "version"
        }
    
    def validate_template_directory(self, template_dir: Path, validate_images: bool = True, validate_config: bool = True) -> tuple[bool, List[str]]:
        """验证单个模板目录结构
        
        Args:
            template_dir: 模板目录路径
            validate_images: 是否验证图片尺寸
            validate_config: 是否验证配置文件
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        if not template_dir.exists():
            errors.append(f"模板目录不存在: {template_dir}")
            return False, errors
        
        if not template_dir.is_dir():
            errors.append(f"路径不是目录: {template_dir}")
            return False, errors
        
        # 检查必需文件
        for required_file in self.required_files:
            file_path = template_dir / required_file
            if not file_path.exists():
                errors.append(f"缺少必需文件: {required_file}")
            elif not file_path.is_file():
                errors.append(f"路径不是文件: {required_file}")
        
        # 检查必需目录
        for required_dir in self.required_directories:
            dir_path = template_dir / required_dir
            if not dir_path.exists():
                errors.append(f"缺少必需目录: {required_dir}")
            elif not dir_path.is_dir():
                errors.append(f"路径不是目录: {required_dir}")
            else:
                # 检查目录内容
                dir_errors = self._validate_asset_directory(dir_path, required_dir)
                errors.extend(dir_errors)
        
        # 检查文件命名规范
        naming_errors = self._validate_naming_conventions(template_dir)
        errors.extend(naming_errors)
        
        # 检查目录结构完整性
        structure_errors = self._validate_directory_structure(template_dir)
        errors.extend(structure_errors)
        
        # 验证图片尺寸
        if validate_images and PIL_AVAILABLE:
            image_errors = self._validate_image_dimensions(template_dir)
            errors.extend(image_errors)
        elif validate_images and not PIL_AVAILABLE:
            errors.append("警告: 无法验证图片尺寸，请安装Pillow库")
        
        # 验证配置文件
        if validate_config:
            config_errors = self._validate_config_completeness(template_dir)
            errors.extend(config_errors)
        
        return len(errors) == 0, errors
    
    def _validate_asset_directory(self, asset_dir: Path, dir_type: str) -> List[str]:
        """验证资源目录内容"""
        errors = []
        
        # 获取目录中的图片文件
        image_files = [f for f in asset_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in self.allowed_image_extensions]
        
        if not image_files:
            errors.append(f"{dir_type}目录为空或没有有效图片文件")
            return errors
        
        # 检查文件命名
        for image_file in image_files:
            stem = image_file.stem
            if stem not in self.standard_sections:
                errors.append(f"{dir_type}目录中的非标准文件名: {image_file.name}")
        
        return errors
    
    def _validate_naming_conventions(self, template_dir: Path) -> List[str]:
        """验证命名规范"""
        errors = []
        
        # 检查模板目录名称
        dir_name = template_dir.name
        if not self._is_valid_template_name(dir_name):
            errors.append(f"模板目录名称不符合规范: {dir_name} (应使用kebab-case格式)")
        
        # 检查文件名称
        for file_path in template_dir.rglob("*"):
            if file_path.is_file():
                if not self._is_valid_filename(file_path.name):
                    errors.append(f"文件名不符合规范: {file_path.relative_to(template_dir)}")
        
        return errors
    
    def _validate_directory_structure(self, template_dir: Path) -> List[str]:
        """验证目录结构完整性"""
        errors = []
        
        # 检查是否有未知的顶级目录
        for item in template_dir.iterdir():
            if item.is_dir():
                dir_name = item.name
                if (dir_name not in self.required_directories and 
                    dir_name not in self.optional_directories):
                    errors.append(f"未知的目录: {dir_name}")
        
        # 检查desktop和mobile目录的对称性
        desktop_dir = template_dir / "desktop"
        mobile_dir = template_dir / "mobile"
        
        if desktop_dir.exists() and mobile_dir.exists():
            desktop_files = {f.stem for f in desktop_dir.iterdir() 
                           if f.is_file() and f.suffix.lower() in self.allowed_image_extensions}
            mobile_files = {f.stem for f in mobile_dir.iterdir() 
                          if f.is_file() and f.suffix.lower() in self.allowed_image_extensions}
            
            # 检查文件对称性
            missing_in_mobile = desktop_files - mobile_files
            missing_in_desktop = mobile_files - desktop_files
            
            for missing_file in missing_in_mobile:
                errors.append(f"mobile目录缺少对应文件: {missing_file}")
            
            for missing_file in missing_in_desktop:
                errors.append(f"desktop目录缺少对应文件: {missing_file}")
        
        return errors
    
    def _is_valid_template_name(self, name: str) -> bool:
        """检查模板名称是否符合kebab-case规范"""
        if not name:
            return False
        
        # kebab-case: 小写字母、数字、连字符
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-_')
        return (all(c in allowed_chars for c in name) and 
                not name.startswith('-') and 
                not name.endswith('-') and
                '--' not in name)
    
    def _is_valid_filename(self, filename: str) -> bool:
        """检查文件名是否符合规范"""
        if not filename:
            return False
        
        # 允许的文件名字符
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        
        # 基本字符检查
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-_.')
        return all(c in allowed_chars for c in filename.lower())
    
    def validate_templates_root(self, templates_root: Path) -> Dict[str, tuple[bool, List[str]]]:
        """验证模板根目录下的所有模板
        
        Args:
            templates_root: 模板根目录路径
            
        Returns:
            {模板路径: (是否有效, 错误列表)}
        """
        results = {}
        
        # 查找所有模板目录
        for category_dir in templates_root.iterdir():
            if category_dir.is_dir() and category_dir.name != "config":
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir():
                        is_valid, errors = self.validate_template_directory(template_dir)
                        results[str(template_dir)] = (is_valid, errors)
        
        return results
    
    def generate_structure_tree(self, template_dir: Path) -> Tree:
        """生成目录结构树"""
        tree = Tree(f"📁 {template_dir.name}")
        
        def add_directory(parent_tree: Tree, directory: Path, max_depth: int = 3, current_depth: int = 0):
            if current_depth >= max_depth:
                return
            
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
            
            for item in items:
                if item.is_dir():
                    dir_tree = parent_tree.add(f"📁 {item.name}/")
                    add_directory(dir_tree, item, max_depth, current_depth + 1)
                else:
                    icon = "📄" if item.suffix.lower() in {".json", ".md", ".yaml", ".yml"} else "🖼️"
                    parent_tree.add(f"{icon} {item.name}")
        
        if template_dir.exists():
            add_directory(tree, template_dir)
        
        return tree
    
    def _validate_image_dimensions(self, template_dir: Path) -> List[str]:
        """验证图片尺寸"""
        errors = []
        
        # 验证预览图
        preview_path = template_dir / "preview.jpg"
        if preview_path.exists():
            dimension_error = self._check_image_dimensions(
                preview_path, self.image_dimensions["preview"], "预览图"
            )
            if dimension_error:
                errors.append(dimension_error)
        
        # 验证桌面版图片
        desktop_dir = template_dir / "desktop"
        if desktop_dir.exists():
            for image_file in desktop_dir.glob("*.jpg"):
                dimension_error = self._check_image_dimensions(
                    image_file, self.image_dimensions["desktop"], f"桌面版/{image_file.name}"
                )
                if dimension_error:
                    errors.append(dimension_error)
        
        # 验证移动版图片
        mobile_dir = template_dir / "mobile"
        if mobile_dir.exists():
            for image_file in mobile_dir.glob("*.jpg"):
                dimension_error = self._check_image_dimensions(
                    image_file, self.image_dimensions["mobile"], f"移动版/{image_file.name}"
                )
                if dimension_error:
                    errors.append(dimension_error)
        
        return errors
    
    def _check_image_dimensions(self, image_path: Path, expected_size: Tuple[int, int], image_type: str) -> Optional[str]:
        """检查单个图片尺寸"""
        try:
            with Image.open(image_path) as img:
                actual_size = img.size
                expected_width, expected_height = expected_size
                
                if actual_size != expected_size:
                    return (f"{image_type}尺寸不符合要求: "
                           f"实际{actual_size[0]}x{actual_size[1]}, "
                           f"期望{expected_width}x{expected_height}")
        except Exception as e:
            return f"{image_type}无法读取: {e}"
        
        return None
    
    def _validate_config_completeness(self, template_dir: Path) -> List[str]:
        """验证配置文件完整性"""
        errors = []
        
        config_path = template_dir / "template.json"
        if not config_path.exists():
            errors.append("缺少配置文件: template.json")
            return errors
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查必需字段
            for field in self.required_config_fields:
                if field not in config_data:
                    errors.append(f"配置文件缺少必需字段: {field}")
                elif not config_data[field]:
                    errors.append(f"配置文件字段为空: {field}")
            
            # 检查资源配置
            if "assets" in config_data:
                assets = config_data["assets"]
                
                # 检查预览图配置
                if "preview" not in assets:
                    errors.append("配置文件缺少预览图资源配置")
                
                # 检查桌面版资源配置
                if "desktop" not in assets:
                    errors.append("配置文件缺少桌面版资源配置")
                elif not isinstance(assets["desktop"], dict) or not assets["desktop"]:
                    errors.append("桌面版资源配置为空")
                
                # 检查移动版资源配置
                if "mobile" not in assets:
                    errors.append("配置文件缺少移动版资源配置")
                elif not isinstance(assets["mobile"], dict) or not assets["mobile"]:
                    errors.append("移动版资源配置为空")
            else:
                errors.append("配置文件缺少资源配置")
            
            # 检查模块配置
            if "sections" in config_data:
                sections = config_data["sections"]
                if not sections or len(sections) == 0:
                    errors.append("配置文件缺少模块配置")
            else:
                errors.append("配置文件缺少模块配置")
            
            # 检查版本格式
            if "version" in config_data:
                version = config_data["version"]
                if not isinstance(version, str) or version.count(".") != 2:
                    errors.append(f"版本号格式不正确: {version}")
            
            # 检查ID格式
            if "id" in config_data:
                template_id = config_data["id"]
                if not isinstance(template_id, str) or not template_id.replace("_", "").replace("-", "").isalnum():
                    errors.append(f"模板ID格式不正确: {template_id}")
            
        except json.JSONDecodeError as e:
            errors.append(f"配置文件JSON格式错误: {e}")
        except Exception as e:
            errors.append(f"读取配置文件时发生错误: {e}")
        
        return errors
    
    def validate_image_dimensions_only(self, template_dir: Path) -> tuple[bool, List[str]]:
        """仅验证图片尺寸
        
        Args:
            template_dir: 模板目录路径
            
        Returns:
            (是否有效, 错误列表)
        """
        if not PIL_AVAILABLE:
            return False, ["无法验证图片尺寸，请安装Pillow库: pip install Pillow"]
        
        errors = self._validate_image_dimensions(template_dir)
        return len(errors) == 0, errors
    
    def validate_config_only(self, template_dir: Path) -> tuple[bool, List[str]]:
        """仅验证配置文件
        
        Args:
            template_dir: 模板目录路径
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = self._validate_config_completeness(template_dir)
        return len(errors) == 0, errors
    
    def get_image_info(self, template_dir: Path) -> Dict[str, Dict[str, Any]]:
        """获取模板中所有图片的信息
        
        Args:
            template_dir: 模板目录路径
            
        Returns:
            图片信息字典
        """
        image_info = {}
        
        if not PIL_AVAILABLE:
            return {"error": "无法获取图片信息，请安装Pillow库"}
        
        # 预览图信息
        preview_path = template_dir / "preview.jpg"
        if preview_path.exists():
            image_info["preview"] = self._get_single_image_info(preview_path)
        
        # 桌面版图片信息
        desktop_dir = template_dir / "desktop"
        if desktop_dir.exists():
            image_info["desktop"] = {}
            for image_file in desktop_dir.glob("*.jpg"):
                image_info["desktop"][image_file.stem] = self._get_single_image_info(image_file)
        
        # 移动版图片信息
        mobile_dir = template_dir / "mobile"
        if mobile_dir.exists():
            image_info["mobile"] = {}
            for image_file in mobile_dir.glob("*.jpg"):
                image_info["mobile"][image_file.stem] = self._get_single_image_info(image_file)
        
        return image_info
    
    def _get_single_image_info(self, image_path: Path) -> Dict[str, Any]:
        """获取单个图片的信息"""
        try:
            with Image.open(image_path) as img:
                return {
                    "path": str(image_path),
                    "size": img.size,
                    "format": img.format,
                    "mode": img.mode,
                    "file_size": image_path.stat().st_size,
                    "file_size_mb": round(image_path.stat().st_size / (1024 * 1024), 2)
                }
        except Exception as e:
            return {
                "path": str(image_path),
                "error": str(e)
            }


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
@click.option('--quiet', '-q', is_flag=True, help='只显示错误')
@click.option('--show-tree', '-t', is_flag=True, help='显示目录结构树')
@click.option('--validate-images', is_flag=True, help='验证图片尺寸')
@click.option('--validate-config', is_flag=True, help='验证配置文件')
@click.option('--show-image-info', is_flag=True, help='显示图片信息')
def main(paths: tuple[Path, ...], verbose: bool, quiet: bool, show_tree: bool, 
         validate_images: bool, validate_config: bool, show_image_info: bool):
    """验证模板目录结构
    
    PATHS: 要验证的模板目录路径
    """
    if not paths:
        console.print("[red]错误: 请指定要验证的目录路径[/red]")
        sys.exit(1)
    
    validator = StructureValidator()
    all_valid = True
    total_templates = 0
    valid_templates = 0
    
    for path in paths:
        if path.name == "by_category" or "by_category" in str(path):
            # 验证整个模板库
            results = validator.validate_templates_root(path)
            
            for template_path, (is_valid, errors) in results.items():
                total_templates += 1
                
                if is_valid:
                    valid_templates += 1
                    if verbose and not quiet:
                        console.print(f"[green]✓[/green] {template_path}")
                else:
                    all_valid = False
                    if not quiet:
                        console.print(f"[red]✗[/red] {template_path}")
                        for error in errors:
                            console.print(f"  [red]•[/red] {error}")
                
                # 显示图片信息
                if show_image_info and not quiet:
                    image_info = validator.get_image_info(Path(template_path))
                    if "error" not in image_info:
                        console.print(f"[cyan]图片信息 - {template_path}:[/cyan]")
                        for category, images in image_info.items():
                            if isinstance(images, dict):
                                for name, info in images.items():
                                    if "error" not in info:
                                        console.print(f"  {category}/{name}: {info['size'][0]}x{info['size'][1]} ({info['file_size_mb']}MB)")
                                    else:
                                        console.print(f"  {category}/{name}: [red]错误 - {info['error']}[/red]")
                            else:
                                if "error" not in images:
                                    console.print(f"  {category}: {images['size'][0]}x{images['size'][1]} ({images['file_size_mb']}MB)")
                                else:
                                    console.print(f"  {category}: [red]错误 - {images['error']}[/red]")
                
                # 显示目录结构树
                if show_tree and not quiet:
                    tree = validator.generate_structure_tree(Path(template_path))
                    console.print(tree)
                    console.print()
        
        else:
            # 验证单个模板目录
            if validate_images and not validate_config:
                is_valid, errors = validator.validate_image_dimensions_only(path)
            elif validate_config and not validate_images:
                is_valid, errors = validator.validate_config_only(path)
            else:
                is_valid, errors = validator.validate_template_directory(path, validate_images, validate_config)
            
            total_templates += 1
            
            if is_valid:
                valid_templates += 1
                if verbose and not quiet:
                    console.print(f"[green]✓[/green] {path}")
            else:
                all_valid = False
                if not quiet:
                    console.print(f"[red]✗[/red] {path}")
                    for error in errors:
                        console.print(f"  [red]•[/red] {error}")
            
            # 显示图片信息
            if show_image_info and not quiet:
                image_info = validator.get_image_info(path)
                if "error" not in image_info:
                    console.print(f"[cyan]图片信息 - {path}:[/cyan]")
                    for category, images in image_info.items():
                        if isinstance(images, dict):
                            for name, info in images.items():
                                if "error" not in info:
                                    console.print(f"  {category}/{name}: {info['size'][0]}x{info['size'][1]} ({info['file_size_mb']}MB)")
                                else:
                                    console.print(f"  {category}/{name}: [red]错误 - {info['error']}[/red]")
                        else:
                            if "error" not in images:
                                console.print(f"  {category}: {images['size'][0]}x{images['size'][1]} ({images['file_size_mb']}MB)")
                            else:
                                console.print(f"  {category}: [red]错误 - {images['error']}[/red]")
            
            # 显示目录结构树
            if show_tree and not quiet:
                tree = validator.generate_structure_tree(path)
                console.print(tree)
                console.print()
    
    # 显示统计信息
    if not quiet:
        table = Table(title="结构验证统计")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="magenta")
        
        table.add_row("总模板数", str(total_templates))
        table.add_row("有效模板", str(valid_templates))
        table.add_row("无效模板", str(total_templates - valid_templates))
        
        console.print(table)
    
    if all_valid:
        if not quiet:
            console.print("[green]所有模板结构验证通过![/green]")
        sys.exit(0)
    else:
        if not quiet:
            console.print("[red]发现模板结构错误![/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()