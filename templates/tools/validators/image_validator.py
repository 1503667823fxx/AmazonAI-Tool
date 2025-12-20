#!/usr/bin/env python3
"""
图片验证器
验证模板图片的尺寸、格式和质量
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import click
from PIL import Image
from rich.console import Console
from rich.table import Table

console = Console()


class ImageValidator:
    """图片验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.desktop_size = (1464, 600)  # 桌面版标准尺寸
        self.mobile_size = (600, 450)    # 移动版标准尺寸
        self.preview_size = (300, 200)   # 预览图标准尺寸
        
        self.allowed_formats = {"JPEG", "PNG"}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.min_quality_score = 70  # 最低质量分数
    
    def validate_image(self, image_path: Path, expected_size: Optional[Tuple[int, int]] = None) -> tuple[bool, List[str]]:
        """验证单个图片文件
        
        Args:
            image_path: 图片文件路径
            expected_size: 期望的尺寸 (width, height)
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        try:
            # 检查文件是否存在
            if not image_path.exists():
                errors.append(f"图片文件不存在: {image_path}")
                return False, errors
            
            # 检查文件大小
            file_size = image_path.stat().st_size
            if file_size > self.max_file_size:
                errors.append(f"文件过大: {file_size / 1024 / 1024:.1f}MB (最大5MB)")
            
            # 打开图片
            with Image.open(image_path) as img:
                # 检查格式
                if img.format not in self.allowed_formats:
                    errors.append(f"不支持的图片格式: {img.format} (支持: {', '.join(self.allowed_formats)})")
                
                # 检查尺寸
                actual_size = img.size
                if expected_size:
                    if actual_size != expected_size:
                        errors.append(f"尺寸不正确: {actual_size[0]}x{actual_size[1]} (期望: {expected_size[0]}x{expected_size[1]})")
                
                # 检查颜色模式
                if img.mode not in ["RGB", "RGBA"]:
                    errors.append(f"颜色模式不正确: {img.mode} (建议: RGB或RGBA)")
                
                # 检查图片质量
                quality_errors = self._check_image_quality(img, image_path)
                errors.extend(quality_errors)
        
        except Exception as e:
            errors.append(f"无法处理图片文件: {e}")
        
        return len(errors) == 0, errors
    
    def _check_image_quality(self, img: Image.Image, image_path: Path) -> List[str]:
        """检查图片质量"""
        errors = []
        
        try:
            # 检查是否为空白图片
            if self._is_blank_image(img):
                errors.append("图片内容为空白")
            
            # 检查分辨率是否过低
            width, height = img.size
            if width < 100 or height < 100:
                errors.append(f"分辨率过低: {width}x{height}")
            
            # 检查宽高比是否合理
            aspect_ratio = width / height
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                errors.append(f"宽高比异常: {aspect_ratio:.2f}")
        
        except Exception as e:
            errors.append(f"质量检查失败: {e}")
        
        return errors
    
    def _is_blank_image(self, img: Image.Image) -> bool:
        """检查是否为空白图片"""
        try:
            # 转换为RGB模式
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # 获取图片的极值
            extrema = img.getextrema()
            
            # 检查是否所有通道的最小值和最大值相同（纯色图片）
            for min_val, max_val in extrema:
                if max_val - min_val > 10:  # 允许小幅变化
                    return False
            
            return True
        
        except Exception:
            return False
    
    def validate_template_images(self, template_dir: Path) -> Dict[str, tuple[bool, List[str]]]:
        """验证模板目录下的所有图片
        
        Args:
            template_dir: 模板目录路径
            
        Returns:
            {图片路径: (是否有效, 错误列表)}
        """
        results = {}
        
        # 验证预览图
        preview_path = template_dir / "preview.jpg"
        if preview_path.exists():
            is_valid, errors = self.validate_image(preview_path, self.preview_size)
            results[str(preview_path)] = (is_valid, errors)
        
        # 验证桌面版图片
        desktop_dir = template_dir / "desktop"
        if desktop_dir.exists():
            for img_file in desktop_dir.glob("*.jpg"):
                is_valid, errors = self.validate_image(img_file, self.desktop_size)
                results[str(img_file)] = (is_valid, errors)
            
            for img_file in desktop_dir.glob("*.png"):
                is_valid, errors = self.validate_image(img_file, self.desktop_size)
                results[str(img_file)] = (is_valid, errors)
        
        # 验证移动版图片
        mobile_dir = template_dir / "mobile"
        if mobile_dir.exists():
            for img_file in mobile_dir.glob("*.jpg"):
                is_valid, errors = self.validate_image(img_file, self.mobile_size)
                results[str(img_file)] = (is_valid, errors)
            
            for img_file in mobile_dir.glob("*.png"):
                is_valid, errors = self.validate_image(img_file, self.mobile_size)
                results[str(img_file)] = (is_valid, errors)
        
        return results
    
    def get_image_info(self, image_path: Path) -> Dict[str, any]:
        """获取图片详细信息"""
        try:
            with Image.open(image_path) as img:
                file_size = image_path.stat().st_size
                
                return {
                    "path": str(image_path),
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "aspect_ratio": img.width / img.height,
                    "file_size": file_size,
                    "file_size_mb": file_size / 1024 / 1024,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                }
        except Exception as e:
            return {"error": str(e)}


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--desktop-size', default="1464x600", help='桌面版图片尺寸 (默认: 1464x600)')
@click.option('--mobile-size', default="600x450", help='移动版图片尺寸 (默认: 600x450)')
@click.option('--preview-size', default="300x200", help='预览图尺寸 (默认: 300x200)')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
@click.option('--quiet', '-q', is_flag=True, help='只显示错误')
@click.option('--info', '-i', is_flag=True, help='显示图片信息')
def main(paths: tuple[Path, ...], desktop_size: str, mobile_size: str, preview_size: str, 
         verbose: bool, quiet: bool, info: bool):
    """验证模板图片尺寸和质量
    
    PATHS: 要验证的图片文件或模板目录路径
    """
    if not paths:
        console.print("[red]错误: 请指定要验证的图片文件或目录[/red]")
        sys.exit(1)
    
    # 解析尺寸参数
    def parse_size(size_str: str) -> Tuple[int, int]:
        try:
            width, height = map(int, size_str.split('x'))
            return width, height
        except ValueError:
            console.print(f"[red]错误: 无效的尺寸格式: {size_str}[/red]")
            sys.exit(1)
    
    validator = ImageValidator()
    validator.desktop_size = parse_size(desktop_size)
    validator.mobile_size = parse_size(mobile_size)
    validator.preview_size = parse_size(preview_size)
    
    all_valid = True
    total_images = 0
    valid_images = 0
    
    for path in paths:
        if path.is_file():
            # 验证单个图片文件
            # 根据文件路径推断期望尺寸
            expected_size = None
            if "desktop" in str(path):
                expected_size = validator.desktop_size
            elif "mobile" in str(path):
                expected_size = validator.mobile_size
            elif path.name == "preview.jpg":
                expected_size = validator.preview_size
            
            is_valid, errors = validator.validate_image(path, expected_size)
            total_images += 1
            
            if is_valid:
                valid_images += 1
                if verbose and not quiet:
                    console.print(f"[green]✓[/green] {path}")
            else:
                all_valid = False
                if not quiet:
                    console.print(f"[red]✗[/red] {path}")
                    for error in errors:
                        console.print(f"  [red]•[/red] {error}")
            
            # 显示图片信息
            if info and not quiet:
                img_info = validator.get_image_info(path)
                if "error" not in img_info:
                    console.print(f"  📊 {img_info['width']}x{img_info['height']} "
                                f"{img_info['format']} {img_info['file_size_mb']:.1f}MB")
        
        elif path.is_dir():
            # 验证模板目录下的所有图片
            results = validator.validate_template_images(path)
            
            for img_path, (is_valid, errors) in results.items():
                total_images += 1
                
                if is_valid:
                    valid_images += 1
                    if verbose and not quiet:
                        console.print(f"[green]✓[/green] {img_path}")
                else:
                    all_valid = False
                    if not quiet:
                        console.print(f"[red]✗[/red] {img_path}")
                        for error in errors:
                            console.print(f"  [red]•[/red] {error}")
                
                # 显示图片信息
                if info and not quiet:
                    img_info = validator.get_image_info(Path(img_path))
                    if "error" not in img_info:
                        console.print(f"  📊 {img_info['width']}x{img_info['height']} "
                                    f"{img_info['format']} {img_info['file_size_mb']:.1f}MB")
    
    # 显示统计信息
    if not quiet:
        table = Table(title="图片验证统计")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="magenta")
        
        table.add_row("总图片数", str(total_images))
        table.add_row("有效图片", str(valid_images))
        table.add_row("无效图片", str(total_images - valid_images))
        
        console.print(table)
    
    if all_valid:
        if not quiet:
            console.print("[green]所有图片验证通过![/green]")
        sys.exit(0)
    else:
        if not quiet:
            console.print("[red]发现图片错误![/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()