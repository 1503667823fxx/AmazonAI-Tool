#!/usr/bin/env python3
"""
统计报告生成器
实现模板库统计数据收集，开发可视化报告生成功能，创建导出和分享机制
"""

import json
import sys
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.columns import Columns

console = Console()


@dataclass
class TemplateStats:
    """模板统计信息"""
    template_id: str
    template_name: str
    category: str
    status: str
    version: str
    
    # 文件统计
    total_files: int = 0
    image_files: int = 0
    config_files: int = 0
    doc_files: int = 0
    
    # 大小统计
    total_size_bytes: int = 0
    total_size_mb: float = 0.0
    
    # 质量统计
    quality_score: float = 0.0
    error_count: int = 0
    warning_count: int = 0
    
    # 时间统计
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    days_since_update: int = 0
    
    def __post_init__(self):
        """计算派生字段"""
        self.total_size_mb = round(self.total_size_bytes / (1024 * 1024), 2)
        
        if self.updated_at:
            try:
                updated_date = datetime.fromisoformat(self.updated_at.replace('Z', '+00:00'))
                self.days_since_update = (datetime.now() - updated_date.replace(tzinfo=None)).days
            except:
                self.days_since_update = 0


@dataclass
class CategoryStats:
    """分类统计信息"""
    category_name: str
    template_count: int = 0
    total_size_mb: float = 0.0
    avg_quality_score: float = 0.0
    
    # 状态分布
    status_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 质量分布
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 最新更新
    latest_update: Optional[str] = None
    oldest_template: Optional[str] = None


@dataclass
class LibraryStats:
    """模板库整体统计"""
    total_templates: int = 0
    total_categories: int = 0
    total_size_mb: float = 0.0
    avg_quality_score: float = 0.0
    
    # 分布统计
    category_distribution: Dict[str, int] = field(default_factory=dict)
    status_distribution: Dict[str, int] = field(default_factory=dict)
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 时间统计
    templates_by_month: Dict[str, int] = field(default_factory=dict)
    recent_updates: List[Dict[str, Any]] = field(default_factory=list)
    
    # 问题统计
    total_errors: int = 0
    total_warnings: int = 0
    problematic_templates: List[str] = field(default_factory=list)
    
    # 生成信息
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    report_version: str = "1.0.0"


class StatisticsReporter:
    """统计报告生成器"""
    
    def __init__(self):
        """初始化统计报告生成器"""
        self.quality_levels = {
            "excellent": (90, 100),
            "good": (80, 89),
            "fair": (70, 79),
            "poor": (60, 69),
            "critical": (0, 59)
        }
    
    def collect_template_statistics(self, template_path: Path) -> TemplateStats:
        """收集单个模板的统计信息
        
        Args:
            template_path: 模板目录路径
            
        Returns:
            模板统计信息
        """
        # 读取配置文件
        config_path = template_path / "template.json"
        config = {}
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
        
        # 统计文件信息
        file_stats = self._analyze_template_files(template_path)
        
        # 提取基本信息
        template_id = config.get("id", template_path.name)
        template_name = config.get("name", template_path.name)
        category = config.get("category", "未分类")
        status = config.get("status", "unknown")
        version = config.get("version", "1.0.0")
        
        # 提取质量信息
        quality_metrics = config.get("quality_metrics", {})
        quality_score = quality_metrics.get("overall_score", 0.0)
        
        # 提取时间信息
        metadata = config.get("metadata", {})
        created_at = metadata.get("created_at")
        updated_at = metadata.get("updated_at")
        
        return TemplateStats(
            template_id=template_id,
            template_name=template_name,
            category=category,
            status=status,
            version=version,
            total_files=file_stats["total_files"],
            image_files=file_stats["image_files"],
            config_files=file_stats["config_files"],
            doc_files=file_stats["doc_files"],
            total_size_bytes=file_stats["total_size"],
            quality_score=quality_score,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def collect_library_statistics(self, templates_root: Path, include_quality: bool = False) -> LibraryStats:
        """收集整个模板库的统计信息
        
        Args:
            templates_root: 模板库根目录
            include_quality: 是否包含质量统计
            
        Returns:
            库统计信息
        """
        library_stats = LibraryStats()
        template_stats_list = []
        category_stats = {}
        
        # 遍历所有模板
        with Progress() as progress:
            # 先统计总数
            total_templates = sum(1 for category_dir in templates_root.iterdir() 
                                if category_dir.is_dir() and category_dir.name != "config"
                                for template_dir in category_dir.iterdir() 
                                if template_dir.is_dir())
            
            task = progress.add_task("收集统计信息", total=total_templates)
            
            for category_dir in templates_root.iterdir():
                if category_dir.is_dir() and category_dir.name != "config":
                    category_name = category_dir.name
                    
                    for template_dir in category_dir.iterdir():
                        if template_dir.is_dir():
                            try:
                                template_stats = self.collect_template_statistics(template_dir)
                                template_stats_list.append(template_stats)
                                
                                # 更新分类统计
                                if category_name not in category_stats:
                                    category_stats[category_name] = CategoryStats(category_name)
                                
                                cat_stats = category_stats[category_name]
                                cat_stats.template_count += 1
                                cat_stats.total_size_mb += template_stats.total_size_mb
                                
                                # 更新状态分布
                                status = template_stats.status
                                cat_stats.status_distribution[status] = cat_stats.status_distribution.get(status, 0) + 1
                                
                                # 更新质量分布
                                quality_level = self._get_quality_level(template_stats.quality_score)
                                cat_stats.quality_distribution[quality_level] = cat_stats.quality_distribution.get(quality_level, 0) + 1
                                
                                # 更新最新时间
                                if template_stats.updated_at:
                                    if not cat_stats.latest_update or template_stats.updated_at > cat_stats.latest_update:
                                        cat_stats.latest_update = template_stats.updated_at
                                
                                progress.update(task, advance=1)
                                
                            except Exception as e:
                                console.print(f"[yellow]警告: 处理模板 {template_dir} 时出错: {e}[/yellow]")
        
        # 计算整体统计
        library_stats.total_templates = len(template_stats_list)
        library_stats.total_categories = len(category_stats)
        
        if template_stats_list:
            library_stats.total_size_mb = sum(t.total_size_mb for t in template_stats_list)
            library_stats.avg_quality_score = sum(t.quality_score for t in template_stats_list) / len(template_stats_list)
            
            # 分布统计
            library_stats.category_distribution = {name: stats.template_count for name, stats in category_stats.items()}
            library_stats.status_distribution = Counter(t.status for t in template_stats_list)
            library_stats.quality_distribution = Counter(self._get_quality_level(t.quality_score) for t in template_stats_list)
            
            # 时间统计
            library_stats.templates_by_month = self._calculate_monthly_distribution(template_stats_list)
            library_stats.recent_updates = self._get_recent_updates(template_stats_list)
            
            # 问题统计
            library_stats.total_errors = sum(t.error_count for t in template_stats_list)
            library_stats.total_warnings = sum(t.warning_count for t in template_stats_list)
            library_stats.problematic_templates = [
                t.template_id for t in template_stats_list 
                if t.quality_score < 70 or t.error_count > 0
            ]
        
        return library_stats
    
    def generate_statistics_report(self, templates_root: Path, output_format: str = "table") -> str:
        """生成统计报告
        
        Args:
            templates_root: 模板库根目录
            output_format: 输出格式 (table, json, csv)
            
        Returns:
            报告内容
        """
        # 收集统计信息
        library_stats = self.collect_library_statistics(templates_root, include_quality=True)
        
        if output_format == "json":
            return self._generate_json_report(library_stats)
        elif output_format == "csv":
            return self._generate_csv_report(templates_root)
        else:
            return self._generate_table_report(library_stats)
    
    def generate_category_report(self, templates_root: Path, category: str) -> str:
        """生成分类报告
        
        Args:
            templates_root: 模板库根目录
            category: 分类名称
            
        Returns:
            分类报告内容
        """
        category_dir = templates_root / category
        if not category_dir.exists():
            return f"分类不存在: {category}"
        
        template_stats_list = []
        
        for template_dir in category_dir.iterdir():
            if template_dir.is_dir():
                try:
                    template_stats = self.collect_template_statistics(template_dir)
                    template_stats_list.append(template_stats)
                except Exception as e:
                    console.print(f"[yellow]警告: 处理模板 {template_dir} 时出错: {e}[/yellow]")
        
        return self._generate_category_table_report(category, template_stats_list)
    
    def _analyze_template_files(self, template_path: Path) -> Dict[str, Any]:
        """分析模板文件"""
        stats = {
            "total_files": 0,
            "image_files": 0,
            "config_files": 0,
            "doc_files": 0,
            "total_size": 0
        }
        
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        config_extensions = {".json", ".yaml", ".yml"}
        doc_extensions = {".md", ".txt", ".rst"}
        
        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                stats["total_files"] += 1
                stats["total_size"] += file_path.stat().st_size
                
                ext = file_path.suffix.lower()
                if ext in image_extensions:
                    stats["image_files"] += 1
                elif ext in config_extensions:
                    stats["config_files"] += 1
                elif ext in doc_extensions:
                    stats["doc_files"] += 1
        
        return stats
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        for level, (min_score, max_score) in self.quality_levels.items():
            if min_score <= score <= max_score:
                return level
        return "unknown"
    
    def _calculate_monthly_distribution(self, template_stats_list: List[TemplateStats]) -> Dict[str, int]:
        """计算月度分布"""
        monthly_counts = defaultdict(int)
        
        for template_stats in template_stats_list:
            if template_stats.created_at:
                try:
                    created_date = datetime.fromisoformat(template_stats.created_at.replace('Z', '+00:00'))
                    month_key = created_date.strftime("%Y-%m")
                    monthly_counts[month_key] += 1
                except:
                    pass
        
        return dict(monthly_counts)
    
    def _get_recent_updates(self, template_stats_list: List[TemplateStats], limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近更新"""
        recent_templates = []
        
        for template_stats in template_stats_list:
            if template_stats.updated_at:
                recent_templates.append({
                    "template_id": template_stats.template_id,
                    "template_name": template_stats.template_name,
                    "updated_at": template_stats.updated_at,
                    "days_ago": template_stats.days_since_update
                })
        
        # 按更新时间排序
        recent_templates.sort(key=lambda x: x["updated_at"], reverse=True)
        return recent_templates[:limit]
    
    def _generate_json_report(self, library_stats: LibraryStats) -> str:
        """生成JSON格式报告"""
        return json.dumps(library_stats.__dict__, ensure_ascii=False, indent=2, default=str)
    
    def _generate_csv_report(self, templates_root: Path) -> str:
        """生成CSV格式报告"""
        output_lines = []
        
        # CSV头部
        headers = [
            "模板ID", "模板名称", "分类", "状态", "版本", 
            "文件总数", "图片文件", "配置文件", "文档文件", 
            "总大小(MB)", "质量评分", "创建时间", "更新时间"
        ]
        output_lines.append(",".join(headers))
        
        # 收集所有模板数据
        for category_dir in templates_root.iterdir():
            if category_dir.is_dir() and category_dir.name != "config":
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir():
                        try:
                            template_stats = self.collect_template_statistics(template_dir)
                            
                            row = [
                                template_stats.template_id,
                                template_stats.template_name,
                                template_stats.category,
                                template_stats.status,
                                template_stats.version,
                                str(template_stats.total_files),
                                str(template_stats.image_files),
                                str(template_stats.config_files),
                                str(template_stats.doc_files),
                                str(template_stats.total_size_mb),
                                str(template_stats.quality_score),
                                template_stats.created_at or "",
                                template_stats.updated_at or ""
                            ]
                            output_lines.append(",".join(f'"{item}"' for item in row))
                            
                        except Exception as e:
                            console.print(f"[yellow]警告: 处理模板 {template_dir} 时出错: {e}[/yellow]")
        
        return "\n".join(output_lines)
    
    def _generate_table_report(self, library_stats: LibraryStats) -> str:
        """生成表格格式报告"""
        output = []
        
        # 整体统计
        output.append("# 模板库统计报告\n")
        output.append(f"**生成时间**: {library_stats.generated_at}")
        output.append(f"**报告版本**: {library_stats.report_version}\n")
        
        # 基本统计表格
        basic_table = Table(title="基本统计信息")
        basic_table.add_column("指标", style="cyan")
        basic_table.add_column("数值", style="magenta")
        
        basic_table.add_row("总模板数", str(library_stats.total_templates))
        basic_table.add_row("总分类数", str(library_stats.total_categories))
        basic_table.add_row("总大小", f"{library_stats.total_size_mb:.2f} MB")
        basic_table.add_row("平均质量评分", f"{library_stats.avg_quality_score:.1f}")
        basic_table.add_row("总错误数", str(library_stats.total_errors))
        basic_table.add_row("总警告数", str(library_stats.total_warnings))
        
        console.print(basic_table)
        
        # 分类分布
        if library_stats.category_distribution:
            category_table = Table(title="分类分布")
            category_table.add_column("分类", style="cyan")
            category_table.add_column("模板数", style="magenta")
            category_table.add_column("占比", style="green")
            
            total = library_stats.total_templates
            for category, count in library_stats.category_distribution.items():
                percentage = (count / total * 100) if total > 0 else 0
                category_table.add_row(category, str(count), f"{percentage:.1f}%")
            
            console.print(category_table)
        
        # 状态分布
        if library_stats.status_distribution:
            status_table = Table(title="状态分布")
            status_table.add_column("状态", style="cyan")
            status_table.add_column("数量", style="magenta")
            status_table.add_column("占比", style="green")
            
            total = library_stats.total_templates
            for status, count in library_stats.status_distribution.items():
                percentage = (count / total * 100) if total > 0 else 0
                status_table.add_row(status, str(count), f"{percentage:.1f}%")
            
            console.print(status_table)
        
        # 质量分布
        if library_stats.quality_distribution:
            quality_table = Table(title="质量分布")
            quality_table.add_column("质量等级", style="cyan")
            quality_table.add_column("数量", style="magenta")
            quality_table.add_column("占比", style="green")
            
            total = library_stats.total_templates
            for quality, count in library_stats.quality_distribution.items():
                percentage = (count / total * 100) if total > 0 else 0
                quality_table.add_row(quality, str(count), f"{percentage:.1f}%")
            
            console.print(quality_table)
        
        # 最近更新
        if library_stats.recent_updates:
            recent_table = Table(title="最近更新")
            recent_table.add_column("模板", style="cyan")
            recent_table.add_column("更新时间", style="magenta")
            recent_table.add_column("天数", style="green")
            
            for update in library_stats.recent_updates[:5]:
                recent_table.add_row(
                    update["template_name"],
                    update["updated_at"][:10],  # 只显示日期部分
                    f"{update['days_ago']} 天前"
                )
            
            console.print(recent_table)
        
        return "报告已在控制台显示"
    
    def _generate_category_table_report(self, category: str, template_stats_list: List[TemplateStats]) -> str:
        """生成分类表格报告"""
        console.print(f"\n[bold]分类报告: {category}[/bold]\n")
        
        if not template_stats_list:
            console.print("[yellow]该分类下没有模板[/yellow]")
            return "空分类"
        
        # 分类统计表格
        table = Table(title=f"{category} 分类详情")
        table.add_column("模板名称", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("版本", style="magenta")
        table.add_column("大小(MB)", style="yellow")
        table.add_column("质量评分", style="red")
        table.add_column("更新时间", style="blue")
        
        total_size = 0
        total_score = 0
        
        for template_stats in template_stats_list:
            total_size += template_stats.total_size_mb
            total_score += template_stats.quality_score
            
            table.add_row(
                template_stats.template_name,
                template_stats.status,
                template_stats.version,
                f"{template_stats.total_size_mb:.2f}",
                f"{template_stats.quality_score:.1f}",
                template_stats.updated_at[:10] if template_stats.updated_at else "未知"
            )
        
        console.print(table)
        
        # 分类摘要
        avg_score = total_score / len(template_stats_list) if template_stats_list else 0
        
        summary_table = Table(title="分类摘要")
        summary_table.add_column("指标", style="cyan")
        summary_table.add_column("数值", style="magenta")
        
        summary_table.add_row("模板总数", str(len(template_stats_list)))
        summary_table.add_row("总大小", f"{total_size:.2f} MB")
        summary_table.add_row("平均质量评分", f"{avg_score:.1f}")
        
        console.print(summary_table)
        
        return f"分类 {category} 报告已显示"


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), 
              default='table', help='输出格式')
@click.option('--category', '-c', help='指定分类生成报告')
@click.option('--export-csv', is_flag=True, help='导出CSV格式数据')
def main(paths: tuple[Path, ...], output: Optional[Path], format: str, 
         category: Optional[str], export_csv: bool):
    """统计报告生成工具
    
    PATHS: 模板库根目录路径
    """
    if not paths:
        console.print("[red]错误: 请指定模板库根目录路径[/red]")
        sys.exit(1)
    
    reporter = StatisticsReporter()
    
    for path in paths:
        if category:
            # 生成分类报告
            content = reporter.generate_category_report(path, category)
        else:
            # 生成整体报告
            content = reporter.generate_statistics_report(path, format)
        
        # 输出结果
        if output and format != "table":
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            console.print(f"[green]报告已保存到: {output}[/green]")
        elif format == "json" or format == "csv":
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(content)
                console.print(f"[green]报告已保存到: {output}[/green]")
            else:
                print(content)
        
        # 额外导出CSV
        if export_csv:
            csv_content = reporter.generate_statistics_report(path, "csv")
            csv_output = output.with_suffix('.csv') if output else path / "statistics.csv"
            with open(csv_output, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            console.print(f"[green]CSV数据已导出到: {csv_output}[/green]")


if __name__ == "__main__":
    main()