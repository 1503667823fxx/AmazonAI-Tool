#!/usr/bin/env python3
"""
模板库管理CLI工具
提供模板创建、管理、验证等功能的命令行接口
"""

import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# 导入相关组件
try:
    # 添加tools目录到Python路径
    tools_path = Path(__file__).parent.parent
    sys.path.insert(0, str(tools_path))
    
    # 导入配置
    from config import (
        TEMPLATES_ROOT, TEMPLATES_BY_CATEGORY, TEMPLATES_CONFIG, 
        TEMPLATES_INDEX, get_template_path, ensure_directories
    )
    
    from generators.template_generator import TemplateGenerator
    from managers.config_manager import ConfigManager
    from managers.version_controller import VersionController
    from managers.migration_tool import MigrationTool, MigrationFilter, MigrationMode, ConflictResolution
    from validators.structure_validator import StructureValidator
    from validators.config_validator import ConfigValidator
    from validators.image_validator import ImageValidator
    from checkers.quality_checker import QualityChecker
    from checkers.documentation_generator import DocumentationGenerator
    from checkers.statistics_reporter import StatisticsReporter
    from models.template import TemplateType, TemplateStatus
    from models.search import SearchQuery, SearchOperator, SortField, SortOrder
    from models.operations import BatchOperation, OperationType
    
    # 确保目录存在
    ensure_directories()
    
except ImportError as e:
    console = Console()
    console.print(f"[red]导入错误: {e}[/red]")
    console.print("[yellow]请确保所有依赖模块都已正确安装[/yellow]")
    console.print(f"[yellow]当前工作目录: {Path.cwd()}[/yellow]")
    console.print(f"[yellow]CLI工具位置: {Path(__file__).parent}[/yellow]")
    sys.exit(1)

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="template-cli")
def cli():
    """APlus Studio 模板库管理工具
    
    提供模板创建、管理、验证等功能的命令行接口
    """
    pass


@cli.command()
@click.option('--name', '-n', help='模板显示名称')
@click.option('--template-id', help='模板ID (默认根据名称生成)')
@click.option('--category', '-c', help='模板分类')
@click.option('--subcategory', help='子分类')
@click.option('--template-type', '-t', default='standard', 
              type=click.Choice(['standard', 'premium', 'minimal']),
              help='模板类型')
@click.option('--description', '-d', help='模板描述')
@click.option('--tags', help='标签列表 (逗号分隔)')
@click.option('--keywords', help='关键词列表 (逗号分隔)')
@click.option('--sections', help='模块列表 (逗号分隔)')
@click.option('--interactive', '-i', is_flag=True, help='交互式创建')
@click.option('--dry-run', is_flag=True, help='预览模式，不实际创建')
def create(name: Optional[str], template_id: Optional[str], category: Optional[str], 
           subcategory: Optional[str], template_type: str, description: Optional[str],
           tags: Optional[str], keywords: Optional[str], sections: Optional[str],
           interactive: bool, dry_run: bool):
    """创建新模板"""
    try:
        # 使用配置中的模板根目录
        if not TEMPLATES_ROOT.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            console.print(f"[yellow]期望路径: {TEMPLATES_ROOT}[/yellow]")
            sys.exit(1)
        
        # 初始化组件
        generator = TemplateGenerator(TEMPLATES_ROOT)
        config_manager = ConfigManager(TEMPLATES_CONFIG)
        
        # 交互式模式或参数收集
        if interactive or not all([name, category]):
            template_data = _interactive_template_creation(config_manager)
        else:
            template_data = {
                'name': name,
                'template_id': template_id or _generate_template_id(name),
                'category': category,
                'subcategory': subcategory,
                'template_type': template_type,
                'description': description or f"{name}模板",
                'tags': tags.split(',') if tags else [],
                'keywords': keywords.split(',') if keywords else [],
                'sections': sections.split(',') if sections else ['hero', 'features', 'gallery', 'specs']
            }
        
        # 显示创建信息
        _display_template_info(template_data, dry_run)
        
        if dry_run:
            console.print("[yellow]预览模式，未实际创建模板[/yellow]")
            return
        
        # 确认创建
        if not Confirm.ask("确认创建此模板吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 创建模板
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("正在创建模板...", total=None)
            
            try:
                template = generator.create_template(
                    template_id=template_data['template_id'],
                    name=template_data['name'],
                    category=template_data['category'],
                    template_type=TemplateType(template_data['template_type']),
                    subcategory=template_data.get('subcategory'),
                    sections=template_data['sections'],
                    description=template_data['description'],
                    tags=template_data['tags'],
                    keywords=template_data['keywords']
                )
                
                progress.update(task, description="模板创建完成!")
                
                # 显示成功信息
                console.print(f"\n[green]✓ 模板创建成功![/green]")
                console.print(f"模板ID: {template.id}")
                console.print(f"模板路径: {template.root_path}")
                
                # 显示下一步操作提示
                _show_next_steps(template)
                
            except FileExistsError:
                console.print(f"[red]错误: 模板已存在: {template_data['template_id']}[/red]")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]创建模板时发生错误: {e}[/red]")
                sys.exit(1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]发生错误: {e}[/red]")
        sys.exit(1)


@cli.command(name="list")
@click.option('--category', '-c', help='按分类筛选')
@click.option('--status', '-s', help='按状态筛选')
@click.option('--template-type', '-t', help='按类型筛选')
@click.option('--tags', help='按标签筛选 (逗号分隔)')
@click.option('--format', '-f', default='table', 
              type=click.Choice(['table', 'json', 'csv']),
              help='输出格式')
@click.option('--limit', '-l', default=20, help='结果数量限制')
@click.option('--sort-by', default='name',
              type=click.Choice(['name', 'created_at', 'updated_at', 'category']),
              help='排序字段')
@click.option('--sort-order', default='asc',
              type=click.Choice(['asc', 'desc']),
              help='排序顺序')
@click.option('--filter', 'filters', multiple=True, help='自定义过滤条件 (field:value)')
def list_templates(category: Optional[str], status: Optional[str], template_type: Optional[str],
                  tags: Optional[str], format: str, limit: int, sort_by: str, sort_order: str,
                  filters: tuple):
    """列出模板"""
    try:
        # 获取模板根目录
        templates_root = Path("templates")
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        # 构建搜索查询
        query = SearchQuery(
            page_size=limit,
            sort_by=SortField(sort_by.upper()),
            sort_order=SortOrder(sort_order.upper())
        )
        
        # 添加过滤条件
        if category:
            query.add_category_filter(category)
        if status:
            query.add_filter('status', 'eq', status)
        if template_type:
            query.add_filter('template_type', 'eq', template_type)
        if tags:
            for tag in tags.split(','):
                query.add_tag_filter(tag.strip())
        
        # 处理自定义过滤条件
        for filter_str in filters:
            if ':' in filter_str:
                field, value = filter_str.split(':', 1)
                query.add_filter(field.strip(), 'eq', value.strip())
        
        # 搜索模板
        results = _search_templates(templates_root, query)
        
        # 输出结果
        if format == 'table':
            _display_templates_table(results)
        elif format == 'json':
            _display_templates_json(results)
        elif format == 'csv':
            _display_templates_csv(results)
            
    except Exception as e:
        console.print(f"[red]列出模板时发生错误: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--category', '-c', help='限制搜索分类')
@click.option('--tags', help='按标签筛选 (逗号分隔)')
@click.option('--template-type', '-t', help='按类型筛选')
@click.option('--status', '-s', help='按状态筛选')
@click.option('--limit', '-l', default=10, help='结果数量限制')
@click.option('--format', '-f', default='table',
              type=click.Choice(['table', 'json', 'csv']),
              help='输出格式')
@click.option('--fuzzy', is_flag=True, help='启用模糊搜索')
@click.option('--case-sensitive', is_flag=True, help='区分大小写')
def search(query: str, category: Optional[str], tags: Optional[str], 
          template_type: Optional[str], status: Optional[str], limit: int, 
          format: str, fuzzy: bool, case_sensitive: bool):
    """搜索模板"""
    try:
        # 获取模板根目录
        templates_root = Path("templates")
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        # 构建搜索查询
        search_query = SearchQuery(
            query_text=query,
            page_size=limit,
            fuzzy_search=fuzzy,
            case_sensitive=case_sensitive,
            sort_by=SortField.RELEVANCE
        )
        
        # 添加过滤条件
        if category:
            search_query.add_category_filter(category)
        if template_type:
            search_query.add_filter('template_type', 'eq', template_type)
        if status:
            search_query.add_filter('status', 'eq', status)
        if tags:
            for tag in tags.split(','):
                search_query.add_tag_filter(tag.strip())
        
        console.print(f"[green]搜索: {query}[/green]")
        if category:
            console.print(f"分类: {category}")
        if tags:
            console.print(f"标签: {tags}")
        
        # 执行搜索
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("正在搜索...", total=None)
            
            results = _search_templates(templates_root, search_query)
            
            progress.update(task, description="搜索完成!")
        
        # 显示结果
        if not results.results:
            console.print("[yellow]未找到匹配的模板[/yellow]")
            
            # 显示搜索建议
            if results.suggestions:
                console.print("\n[cyan]搜索建议:[/cyan]")
                for suggestion in results.suggestions:
                    console.print(f"  • {suggestion}")
            
            # 显示"你是否想要"建议
            if results.did_you_mean:
                console.print(f"\n[cyan]你是否想要: {results.did_you_mean}[/cyan]")
        else:
            console.print(f"\n[green]找到 {results.total_count} 个模板，显示前 {len(results.results)} 个[/green]")
            console.print(f"搜索耗时: {results.search_time_ms:.1f}ms")
            
            # 输出结果
            if format == 'table':
                _display_search_results_table(results)
            elif format == 'json':
                _display_templates_json(results)
            elif format == 'csv':
                _display_templates_csv(results)
            
            # 显示分面统计
            if results.facets and format == 'table':
                _display_search_facets(results.facets)
                
    except Exception as e:
        console.print(f"[red]搜索时发生错误: {e}[/red]")
        sys.exit(1)


@cli.command(name='search-wildcard')
@click.argument('pattern')
@click.option('--field', '-f', default='name', help='搜索字段')
@click.option('--limit', '-l', default=10, help='结果数量限制')
def search_wildcard(pattern: str, field: str, limit: int):
    """通配符搜索 (支持 * 和 ?)"""
    try:
        from engines.search_engine import SearchEngine
        
        templates_root = Path("templates")
        index_root = Path("index")
        
        search_engine = SearchEngine(templates_root, index_root)
        results = search_engine.search_by_wildcard(pattern, field)
        
        console.print(f"[green]通配符搜索: {pattern} (字段: {field})[/green]")
        console.print(f"找到 {len(results)} 个匹配结果")
        
        # 显示结果
        if results:
            table = Table(title="通配符搜索结果")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="white")
            table.add_column("分类", style="green")
            table.add_column("匹配值", style="yellow")
            
            for template in results[:limit]:
                table.add_row(
                    template.get('id', ''),
                    template.get('name', ''),
                    template.get('category', ''),
                    str(template.get(field, ''))
                )
            
            console.print(table)
        else:
            console.print("[yellow]未找到匹配的模板[/yellow]")
            
    except Exception as e:
        console.print(f"[red]通配符搜索失败: {e}[/red]")
        sys.exit(1)


@cli.command(name='search-regex')
@click.argument('pattern')
@click.option('--field', '-f', default='name', help='搜索字段')
@click.option('--limit', '-l', default=10, help='结果数量限制')
def search_regex(pattern: str, field: str, limit: int):
    """正则表达式搜索"""
    try:
        from engines.search_engine import SearchEngine
        
        templates_root = Path("templates")
        index_root = Path("index")
        
        search_engine = SearchEngine(templates_root, index_root)
        results = search_engine.search_by_regex(pattern, field)
        
        console.print(f"[green]正则表达式搜索: {pattern} (字段: {field})[/green]")
        console.print(f"找到 {len(results)} 个匹配结果")
        
        # 显示结果
        if results:
            table = Table(title="正则表达式搜索结果")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="white")
            table.add_column("分类", style="green")
            table.add_column("匹配值", style="yellow")
            
            for template in results[:limit]:
                table.add_row(
                    template.get('id', ''),
                    template.get('name', ''),
                    template.get('category', ''),
                    str(template.get(field, ''))
                )
            
            console.print(table)
        else:
            console.print("[yellow]未找到匹配的模板[/yellow]")
            
    except Exception as e:
        console.print(f"[red]正则表达式搜索失败: {e}[/red]")
        sys.exit(1)


@cli.command(name='similar')
@click.argument('template_id')
@click.option('--limit', '-l', default=5, help='结果数量限制')
def find_similar(template_id: str, limit: int):
    """查找相似模板"""
    try:
        from engines.search_engine import SearchEngine
        
        templates_root = Path("templates")
        index_root = Path("index")
        
        search_engine = SearchEngine(templates_root, index_root)
        results = search_engine.get_similar_templates(template_id, limit)
        
        console.print(f"[green]查找与 {template_id} 相似的模板[/green]")
        
        if results:
            table = Table(title="相似模板")
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="white")
            table.add_column("分类", style="green")
            table.add_column("共同标签", style="magenta")
            
            for template in results:
                table.add_row(
                    template.get('id', ''),
                    template.get('name', ''),
                    template.get('category', ''),
                    ', '.join(template.get('tags', [])[:3])
                )
            
            console.print(table)
        else:
            console.print("[yellow]未找到相似的模板[/yellow]")
            
    except Exception as e:
        console.print(f"[red]查找相似模板失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('template_name')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
@click.option('--validate-structure', is_flag=True, default=True, help='验证目录结构')
@click.option('--validate-config', is_flag=True, default=True, help='验证配置文件')
@click.option('--validate-images', is_flag=True, default=True, help='验证图片尺寸')
@click.option('--auto-fix', is_flag=True, help='自动修复可修复的问题')
@click.option('--batch', is_flag=True, help='批量验证所有模板')
def validate(template_name: str, verbose: bool, validate_structure: bool, 
            validate_config: bool, validate_images: bool, auto_fix: bool, batch: bool):
    """验证模板"""
    try:
        # 获取模板根目录
        templates_root = Path("templates")
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        # 初始化验证器
        structure_validator = StructureValidator()
        config_validator = ConfigValidator()
        image_validator = ImageValidator()
        
        if batch:
            # 批量验证所有模板
            _batch_validate_templates(templates_root, structure_validator, config_validator, 
                                     image_validator, validate_structure, validate_config, 
                                     validate_images, verbose)
        else:
            # 验证单个模板
            template_path = _find_template_path(templates_root, template_name)
            
            if not template_path:
                console.print(f"[red]错误: 未找到模板: {template_name}[/red]")
                sys.exit(1)
            
            console.print(f"[green]验证模板: {template_name}[/green]")
            console.print(f"路径: {template_path}\n")
            
            all_valid = True
            all_errors = []
            
            # 结构验证
            if validate_structure:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("验证目录结构...", total=None)
                    
                    is_valid, errors = structure_validator.validate_template_directory(
                        template_path, validate_images=False, validate_config=False
                    )
                    
                    if is_valid:
                        progress.update(task, description="[green]✓ 目录结构验证通过[/green]")
                    else:
                        progress.update(task, description="[red]✗ 目录结构验证失败[/red]")
                        all_valid = False
                        all_errors.extend(errors)
                        
                        if verbose:
                            for error in errors:
                                console.print(f"  [red]•[/red] {error}")
            
            # 配置验证
            if validate_config:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("验证配置文件...", total=None)
                    
                    config_path = template_path / "template.json"
                    is_valid, errors = config_validator.validate_config(config_path)
                    
                    if is_valid:
                        progress.update(task, description="[green]✓ 配置文件验证通过[/green]")
                    else:
                        progress.update(task, description="[red]✗ 配置文件验证失败[/red]")
                        all_valid = False
                        all_errors.extend(errors)
                        
                        if verbose:
                            for error in errors:
                                console.print(f"  [red]•[/red] {error}")
            
            # 图片验证
            if validate_images:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("验证图片尺寸...", total=None)
                    
                    image_results = image_validator.validate_template_images(template_path)
                    
                    image_errors = []
                    for img_path, (is_valid, errors) in image_results.items():
                        if not is_valid:
                            image_errors.extend(errors)
                    
                    if not image_errors:
                        progress.update(task, description="[green]✓ 图片验证通过[/green]")
                    else:
                        progress.update(task, description="[red]✗ 图片验证失败[/red]")
                        all_valid = False
                        all_errors.extend(image_errors)
                        
                        if verbose:
                            for error in image_errors:
                                console.print(f"  [red]•[/red] {error}")
            
            # 显示验证结果
            console.print()
            if all_valid:
                console.print("[bold green]✓ 所有验证通过![/bold green]")
            else:
                console.print(f"[bold red]✗ 发现 {len(all_errors)} 个问题[/bold red]")
                
                if not verbose:
                    console.print("\n[yellow]使用 --verbose 查看详细错误信息[/yellow]")
                
                if auto_fix:
                    console.print("\n[cyan]尝试自动修复...[/cyan]")
                    _auto_fix_issues(template_path, all_errors)
                else:
                    console.print("\n[yellow]使用 --auto-fix 尝试自动修复问题[/yellow]")
                
                sys.exit(1)
                
    except Exception as e:
        console.print(f"[red]验证时发生错误: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--rebuild', '-r', is_flag=True, help='重建索引')
@click.option('--update', '-u', is_flag=True, help='更新索引')
@click.option('--verify', '-v', is_flag=True, help='验证索引完整性')
def index(rebuild: bool, update: bool, verify: bool):
    """管理搜索索引"""
    try:
        templates_root = Path("templates")
        index_root = Path("index")
        
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        # 确保索引目录存在
        index_root.mkdir(exist_ok=True)
        
        if rebuild:
            console.print("[green]重建搜索索引...[/green]")
            _rebuild_search_index(templates_root, index_root)
        elif update:
            console.print("[green]更新搜索索引...[/green]")
            _update_search_index(templates_root, index_root)
        elif verify:
            console.print("[green]验证索引完整性...[/green]")
            _verify_search_index(templates_root, index_root)
        else:
            console.print("[green]更新搜索索引...[/green]")
            _update_search_index(templates_root, index_root)
            
    except Exception as e:
        console.print(f"[red]索引管理时发生错误: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--by-category', is_flag=True, help='按分类统计')
@click.option('--by-status', is_flag=True, help='按状态统计')
@click.option('--by-type', is_flag=True, help='按类型统计')
@click.option('--detailed', '-d', is_flag=True, help='显示详细统计')
@click.option('--export', '-e', help='导出统计报告到文件')
def stats(by_category: bool, by_status: bool, by_type: bool, detailed: bool, export: Optional[str]):
    """显示统计信息"""
    try:
        templates_root = Path("templates")
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        console.print("[green]模板库统计:[/green]\n")
        
        # 收集统计数据
        stats_data = _collect_template_statistics(templates_root)
        
        # 显示基本统计
        _display_basic_statistics(stats_data)
        
        # 按分类统计
        if by_category or detailed:
            _display_category_statistics(stats_data)
        
        # 按状态统计
        if by_status or detailed:
            _display_status_statistics(stats_data)
        
        # 按类型统计
        if by_type or detailed:
            _display_type_statistics(stats_data)
        
        # 详细统计
        if detailed:
            _display_detailed_statistics(stats_data)
        
        # 导出报告
        if export:
            _export_statistics_report(stats_data, export)
            console.print(f"\n[green]统计报告已导出到: {export}[/green]")
            
    except Exception as e:
        console.print(f"[red]统计时发生错误: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('operation', type=click.Choice(['move', 'copy', 'delete', 'update-status']))
@click.option('--targets', '-t', help='目标模板列表 (逗号分隔或通配符)')
@click.option('--filter', 'filters', multiple=True, help='过滤条件 (field:value)')
@click.option('--to-category', help='目标分类 (用于move操作)')
@click.option('--status', help='目标状态 (用于update-status操作)')
@click.option('--dry-run', is_flag=True, help='预览模式，不实际执行')
@click.option('--confirm', is_flag=True, help='跳过确认提示')
def batch(operation: str, targets: Optional[str], filters: tuple, to_category: Optional[str],
          status: Optional[str], dry_run: bool, confirm: bool):
    """批量操作模板"""
    try:
        templates_root = Path("templates")
        if not templates_root.exists():
            console.print("[red]错误: 模板根目录不存在[/red]")
            sys.exit(1)
        
        # 构建目标列表
        target_templates = []
        
        if targets:
            # 从参数获取目标
            target_list = [t.strip() for t in targets.split(',')]
            target_templates.extend(target_list)
        
        if filters:
            # 从过滤条件获取目标
            query = SearchQuery()
            for filter_str in filters:
                if ':' in filter_str:
                    field, value = filter_str.split(':', 1)
                    query.add_filter(field.strip(), 'eq', value.strip())
            
            results = _search_templates(templates_root, query)
            target_templates.extend([r.template_id for r in results.results])
        
        if not target_templates:
            console.print("[yellow]没有找到目标模板[/yellow]")
            return
        
        # 去重
        target_templates = list(set(target_templates))
        
        console.print(f"[green]批量操作: {operation}[/green]")
        console.print(f"目标模板数量: {len(target_templates)}")
        
        if dry_run:
            console.print("[yellow]预览模式 - 以下模板将被处理:[/yellow]")
            for template_id in target_templates:
                console.print(f"  • {template_id}")
            return
        
        # 确认操作
        if not confirm:
            if not Confirm.ask(f"确认对 {len(target_templates)} 个模板执行 {operation} 操作吗?"):
                console.print("[yellow]操作已取消[/yellow]")
                return
        
        # 执行批量操作
        batch_op = BatchOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=OperationType(operation.upper()),
            description=f"批量{operation}操作",
            targets=target_templates
        )
        
        _execute_batch_operation(templates_root, batch_op, operation, to_category, status)
        
    except Exception as e:
        console.print(f"[red]批量操作时发生错误: {e}[/red]")
        sys.exit(1)


def _generate_template_id(name: str) -> str:
    """根据名称生成模板ID"""
    # 转换为kebab-case格式
    template_id = name.lower()
    template_id = template_id.replace(' ', '_').replace('-', '_')
    # 移除特殊字符
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789_')
    template_id = ''.join(c for c in template_id if c in allowed_chars)
    # 移除连续的下划线
    while '__' in template_id:
        template_id = template_id.replace('__', '_')
    # 移除首尾下划线
    template_id = template_id.strip('_')
    
    return template_id or 'template_' + str(uuid.uuid4())[:8]


def _interactive_template_creation(config_manager: ConfigManager) -> Dict[str, Any]:
    """交互式模板创建"""
    console.print(Panel.fit("🎨 模板创建向导", style="bold blue"))
    
    # 获取可用选项
    available_categories = config_manager.get_available_categories()
    available_types = config_manager.get_available_template_types()
    
    # 收集基本信息
    name = Prompt.ask("模板显示名称", default="新模板")
    template_id = Prompt.ask("模板ID", default=_generate_template_id(name))
    
    # 选择分类
    console.print(f"\n可用分类: {', '.join(available_categories)}")
    category = Prompt.ask("选择分类", choices=available_categories, default=available_categories[0])
    
    subcategory = Prompt.ask("子分类 (可选)", default="")
    
    # 选择类型
    console.print(f"\n可用类型: {', '.join(available_types)}")
    template_type = Prompt.ask("选择模板类型", choices=available_types, default="standard")
    
    description = Prompt.ask("模板描述", default=f"{name}模板")
    
    # 标签和关键词
    tags_input = Prompt.ask("标签 (逗号分隔)", default="")
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    
    keywords_input = Prompt.ask("关键词 (逗号分隔)", default="")
    keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
    
    # 模块选择
    default_sections = ['hero', 'features', 'gallery', 'specs']
    sections_input = Prompt.ask("模块列表 (逗号分隔)", default=','.join(default_sections))
    sections = [section.strip() for section in sections_input.split(',') if section.strip()]
    
    return {
        'name': name,
        'template_id': template_id,
        'category': category,
        'subcategory': subcategory if subcategory else None,
        'template_type': template_type,
        'description': description,
        'tags': tags,
        'keywords': keywords,
        'sections': sections
    }


def _display_template_info(template_data: Dict[str, Any], dry_run: bool = False):
    """显示模板信息"""
    title = "🔍 模板预览" if dry_run else "📋 模板信息"
    
    table = Table(title=title, show_header=False, box=None)
    table.add_column("属性", style="cyan", width=15)
    table.add_column("值", style="white")
    
    table.add_row("模板ID", template_data['template_id'])
    table.add_row("显示名称", template_data['name'])
    table.add_row("分类", template_data['category'])
    if template_data.get('subcategory'):
        table.add_row("子分类", template_data['subcategory'])
    table.add_row("类型", template_data['template_type'])
    table.add_row("描述", template_data['description'])
    
    if template_data['tags']:
        table.add_row("标签", ', '.join(template_data['tags']))
    if template_data['keywords']:
        table.add_row("关键词", ', '.join(template_data['keywords']))
    
    table.add_row("模块", ', '.join(template_data['sections']))
    
    console.print(table)


def _show_next_steps(template):
    """显示下一步操作提示"""
    console.print("\n[bold cyan]下一步操作:[/bold cyan]")
    console.print("1. 将图片文件放置到对应目录:")
    console.print(f"   • 预览图: {template.root_path}/preview.jpg (300x200px)")
    console.print(f"   • 桌面版: {template.root_path}/desktop/*.jpg (1464x600px)")
    console.print(f"   • 移动版: {template.root_path}/mobile/*.jpg (600x450px)")
    console.print("\n2. 验证模板结构:")
    console.print(f"   template-cli validate {template.id}")
    console.print("\n3. 查看模板信息:")
    console.print(f"   template-cli list --filter id:{template.id}")


def _search_templates(templates_root: Path, query: SearchQuery):
    """搜索模板"""
    from engines.search_engine import SearchEngine
    
    # 创建搜索引擎
    index_root = Path("index")
    search_engine = SearchEngine(templates_root, index_root)
    
    # 执行搜索
    return search_engine.search(query)


def _load_template_data(config_path: Path) -> Optional[Dict[str, Any]]:
    """加载模板数据"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _matches_query(template_data: Dict[str, Any], query: SearchQuery) -> bool:
    """检查模板是否匹配查询条件"""
    # 检查文本查询
    if query.query_text:
        search_text = query.query_text.lower()
        searchable_fields = [
            template_data.get('name', ''),
            template_data.get('description', ''),
            ' '.join(template_data.get('tags', [])),
            ' '.join(template_data.get('keywords', []))
        ]
        
        if not query.case_sensitive:
            searchable_content = ' '.join(searchable_fields).lower()
        else:
            searchable_content = ' '.join(searchable_fields)
        
        if query.fuzzy_search:
            # 简单的模糊匹配
            if search_text not in searchable_content:
                return False
        else:
            # 精确匹配
            if search_text not in searchable_content:
                return False
    
    # 检查过滤条件
    for filter_criteria in query.filters:
        field_value = template_data.get(filter_criteria.field)
        if not filter_criteria.matches(field_value):
            return False
    
    # 检查标签
    if query.tags:
        template_tags = template_data.get('tags', [])
        if not any(tag in template_tags for tag in query.tags):
            return False
    
    # 检查关键词
    if query.keywords:
        template_keywords = template_data.get('keywords', [])
        if not any(kw in template_keywords for kw in query.keywords):
            return False
    
    return True


def _calculate_relevance(template_data: Dict[str, Any], query: SearchQuery) -> float:
    """计算相关性分数"""
    if not query.query_text:
        return 1.0
    
    score = 0.0
    search_text = query.query_text.lower()
    
    # 名称匹配权重最高
    if search_text in template_data.get('name', '').lower():
        score += 10.0
    
    # 描述匹配
    if search_text in template_data.get('description', '').lower():
        score += 5.0
    
    # 标签匹配
    for tag in template_data.get('tags', []):
        if search_text in tag.lower():
            score += 3.0
    
    # 关键词匹配
    for keyword in template_data.get('keywords', []):
        if search_text in keyword.lower():
            score += 2.0
    
    return score


def _sort_templates(templates: List[Dict[str, Any]], sort_by: SortField, sort_order: SortOrder) -> List[Dict[str, Any]]:
    """排序模板"""
    reverse = sort_order == SortOrder.DESC
    
    if sort_by == SortField.NAME:
        return sorted(templates, key=lambda t: t.get('name', ''), reverse=reverse)
    elif sort_by == SortField.CATEGORY:
        return sorted(templates, key=lambda t: t.get('category', ''), reverse=reverse)
    elif sort_by == SortField.CREATED_AT:
        return sorted(templates, key=lambda t: t.get('metadata', {}).get('created_at', ''), reverse=reverse)
    elif sort_by == SortField.UPDATED_AT:
        return sorted(templates, key=lambda t: t.get('metadata', {}).get('updated_at', ''), reverse=reverse)
    else:
        return templates


def _display_templates_table(results):
    """以表格形式显示模板列表"""
    if not results.results:
        console.print("[yellow]没有找到模板[/yellow]")
        return
    
    table = Table(title="模板列表")
    table.add_column("ID", style="cyan", width=20)
    table.add_column("名称", style="white", width=25)
    table.add_column("分类", style="green", width=15)
    table.add_column("类型", style="blue", width=10)
    table.add_column("状态", style="yellow", width=10)
    table.add_column("标签", style="magenta", width=30)
    
    for result in results.results:
        tags_str = ', '.join(result.tags[:3])  # 只显示前3个标签
        if len(result.tags) > 3:
            tags_str += f" (+{len(result.tags) - 3})"
        
        table.add_row(
            result.template_id,
            result.name,
            result.category,
            result.template_type,
            result.status,
            tags_str
        )
    
    console.print(table)
    
    # 显示分页信息
    if results.total_count > len(results.results):
        console.print(f"\n显示 {len(results.results)} / {results.total_count} 个模板")


def _display_search_results_table(results):
    """以表格形式显示搜索结果"""
    if not results.results:
        console.print("[yellow]没有找到匹配的模板[/yellow]")
        return
    
    table = Table(title="搜索结果")
    table.add_column("相关性", style="red", width=8)
    table.add_column("ID", style="cyan", width=20)
    table.add_column("名称", style="white", width=25)
    table.add_column("分类", style="green", width=15)
    table.add_column("描述", style="dim", width=40)
    
    for result in results.results:
        relevance = f"{result.relevance_score:.1f}" if result.relevance_score > 0 else "-"
        description = result.description[:37] + "..." if len(result.description) > 40 else result.description
        
        table.add_row(
            relevance,
            result.template_id,
            result.name,
            result.category,
            description
        )
    
    console.print(table)
    
    # 显示搜索统计
    console.print(f"\n找到 {results.total_count} 个匹配结果，显示前 {len(results.results)} 个")


def _display_templates_json(results):
    """以JSON格式显示模板"""
    output = {
        "total_count": results.total_count,
        "page": results.page,
        "page_size": results.page_size,
        "templates": [result.to_dict() for result in results.results]
    }
    console.print(json.dumps(output, ensure_ascii=False, indent=2))


def _display_templates_csv(results):
    """以CSV格式显示模板"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题行
    writer.writerow(['ID', '名称', '分类', '类型', '状态', '描述', '标签', '关键词'])
    
    # 写入数据行
    for result in results.results:
        writer.writerow([
            result.template_id,
            result.name,
            result.category,
            result.template_type,
            result.status,
            result.description,
            ', '.join(result.tags),
            ', '.join(result.keywords)
        ])
    
    console.print(output.getvalue())


def _find_template_path(templates_root: Path, template_name: str) -> Optional[Path]:
    """查找模板路径"""
    by_category_dir = templates_root / "by_category"
    
    if by_category_dir.exists():
        for category_dir in by_category_dir.iterdir():
            if category_dir.is_dir():
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir() and template_dir.name == template_name:
                        return template_dir
                    
                    # 也检查配置文件中的ID
                    config_path = template_dir / "template.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                                if config_data.get('id') == template_name:
                                    return template_dir
                        except Exception:
                            continue
    
    return None


def _batch_validate_templates(templates_root: Path, structure_validator, config_validator, 
                             image_validator, validate_structure: bool, validate_config: bool, 
                             validate_images: bool, verbose: bool):
    """批量验证所有模板"""
    by_category_dir = templates_root / "by_category"
    
    if not by_category_dir.exists():
        console.print("[red]错误: 模板分类目录不存在[/red]")
        return
    
    all_templates = []
    for category_dir in by_category_dir.iterdir():
        if category_dir.is_dir():
            for template_dir in category_dir.iterdir():
                if template_dir.is_dir():
                    all_templates.append(template_dir)
    
    if not all_templates:
        console.print("[yellow]没有找到模板[/yellow]")
        return
    
    console.print(f"[green]批量验证 {len(all_templates)} 个模板[/green]\n")
    
    valid_count = 0
    invalid_count = 0
    
    with Progress(console=console) as progress:
        task = progress.add_task("验证模板...", total=len(all_templates))
        
        for template_dir in all_templates:
            template_name = template_dir.name
            all_valid = True
            all_errors = []
            
            # 结构验证
            if validate_structure:
                is_valid, errors = structure_validator.validate_template_directory(
                    template_dir, validate_images=False, validate_config=False
                )
                if not is_valid:
                    all_valid = False
                    all_errors.extend(errors)
            
            # 配置验证
            if validate_config:
                config_path = template_dir / "template.json"
                is_valid, errors = config_validator.validate_config(config_path)
                if not is_valid:
                    all_valid = False
                    all_errors.extend(errors)
            
            # 图片验证
            if validate_images:
                image_results = image_validator.validate_template_images(template_dir)
                for img_path, (is_valid, errors) in image_results.items():
                    if not is_valid:
                        all_valid = False
                        all_errors.extend(errors)
            
            if all_valid:
                valid_count += 1
                if verbose:
                    console.print(f"[green]✓[/green] {template_name}")
            else:
                invalid_count += 1
                console.print(f"[red]✗[/red] {template_name} ({len(all_errors)} 个问题)")
                if verbose:
                    for error in all_errors[:3]:  # 只显示前3个错误
                        console.print(f"    [red]•[/red] {error}")
                    if len(all_errors) > 3:
                        console.print(f"    [dim]... 还有 {len(all_errors) - 3} 个问题[/dim]")
            
            progress.advance(task)
    
    # 显示统计结果
    console.print(f"\n[bold]验证完成:[/bold]")
    console.print(f"  [green]有效模板: {valid_count}[/green]")
    console.print(f"  [red]无效模板: {invalid_count}[/red]")
    console.print(f"  [cyan]总计: {len(all_templates)}[/cyan]")


def _auto_fix_issues(template_path: Path, errors: List[str]):
    """自动修复问题"""
    fixed_count = 0
    
    for error in errors:
        if "缺少必需文件" in error:
            # 创建缺失的文件
            if "README.md" in error:
                readme_path = template_path / "README.md"
                if not readme_path.exists():
                    readme_path.write_text(f"# {template_path.name}\n\n模板说明文档", encoding='utf-8')
                    console.print(f"[green]✓ 创建了 README.md[/green]")
                    fixed_count += 1
        
        elif "缺少必需目录" in error:
            # 创建缺失的目录
            if "desktop" in error:
                (template_path / "desktop").mkdir(exist_ok=True)
                console.print(f"[green]✓ 创建了 desktop 目录[/green]")
                fixed_count += 1
            elif "mobile" in error:
                (template_path / "mobile").mkdir(exist_ok=True)
                console.print(f"[green]✓ 创建了 mobile 目录[/green]")
                fixed_count += 1
    
    if fixed_count > 0:
        console.print(f"\n[green]自动修复了 {fixed_count} 个问题[/green]")
    else:
        console.print("\n[yellow]没有可自动修复的问题[/yellow]")


def _rebuild_search_index(templates_root: Path, index_root: Path):
    """重建搜索索引"""
    from engines.search_engine import SearchEngine
    
    # 创建搜索引擎并重建索引
    search_engine = SearchEngine(templates_root, index_root)
    success = search_engine.rebuild_index()
    
    if success:
        stats = search_engine.get_search_statistics()
        console.print(f"[green]✓ 索引重建完成，共索引 {stats['total_templates']} 个模板[/green]")
    else:
        console.print("[red]✗ 索引重建失败[/red]")


def _update_search_index(templates_root: Path, index_root: Path):
    """更新搜索索引"""
    from engines.search_engine import SearchEngine
    
    # 创建搜索引擎并重建索引 (简单实现)
    search_engine = SearchEngine(templates_root, index_root)
    success = search_engine.rebuild_index()
    
    if success:
        stats = search_engine.get_search_statistics()
        console.print(f"[green]✓ 索引更新完成，共索引 {stats['total_templates']} 个模板[/green]")
    else:
        console.print("[red]✗ 索引更新失败[/red]")


def _verify_search_index(templates_root: Path, index_root: Path):
    """验证索引完整性"""
    from engines.search_engine import SearchEngine
    
    issues = []
    
    # 检查索引文件是否存在
    required_files = ["search_index.json", "category_index.json", "tag_index.json"]
    for filename in required_files:
        index_file = index_root / filename
        if not index_file.exists():
            issues.append(f"缺少索引文件: {filename}")
    
    if not issues:
        # 检查索引内容
        try:
            search_engine = SearchEngine(templates_root, index_root)
            stats = search_engine.get_search_statistics()
            console.print("[green]✓ 索引验证通过[/green]")
            console.print(f"  模板数量: {stats['total_templates']}")
            console.print(f"  分类数量: {stats['total_categories']}")
            console.print(f"  标签数量: {stats['total_tags']}")
            console.print(f"  最后更新: {stats['last_updated']}")
        except Exception as e:
            issues.append(f"索引内容验证失败: {e}")
    
    if issues:
        console.print("[red]索引验证失败:[/red]")
        for issue in issues:
            console.print(f"  [red]•[/red] {issue}")
        console.print("\n[yellow]建议运行 --rebuild 重建索引[/yellow]")


def _collect_template_statistics(templates_root: Path) -> Dict[str, Any]:
    """收集模板统计数据"""
    stats = {
        "total_templates": 0,
        "by_category": {},
        "by_status": {},
        "by_type": {},
        "total_files": 0,
        "total_size_mb": 0.0,
        "templates": []
    }
    
    by_category_dir = templates_root / "by_category"
    
    if by_category_dir.exists():
        for category_dir in by_category_dir.iterdir():
            if category_dir.is_dir():
                category_name = category_dir.name
                category_count = 0
                
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir():
                        config_path = template_dir / "template.json"
                        if config_path.exists():
                            try:
                                template_data = _load_template_data(config_path)
                                if template_data:
                                    stats["templates"].append(template_data)
                                    stats["total_templates"] += 1
                                    category_count += 1
                                    
                                    # 按状态统计
                                    status = template_data.get('status', 'unknown')
                                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                                    
                                    # 按类型统计
                                    template_type = template_data.get('template_type', 'unknown')
                                    stats["by_type"][template_type] = stats["by_type"].get(template_type, 0) + 1
                                    
                                    # 文件统计
                                    for file_path in template_dir.rglob("*"):
                                        if file_path.is_file():
                                            stats["total_files"] += 1
                                            stats["total_size_mb"] += file_path.stat().st_size / (1024 * 1024)
                            except Exception:
                                continue
                
                if category_count > 0:
                    stats["by_category"][category_name] = category_count
    
    return stats


def _display_basic_statistics(stats: Dict[str, Any]):
    """显示基本统计信息"""
    table = Table(title="基本统计", show_header=False)
    table.add_column("项目", style="cyan", width=20)
    table.add_column("数量", style="white", width=15)
    
    table.add_row("总模板数", str(stats["total_templates"]))
    table.add_row("总文件数", str(stats["total_files"]))
    table.add_row("总大小", f"{stats['total_size_mb']:.1f} MB")
    table.add_row("分类数", str(len(stats["by_category"])))
    
    console.print(table)


def _display_category_statistics(stats: Dict[str, Any]):
    """显示分类统计"""
    if not stats["by_category"]:
        return
    
    table = Table(title="按分类统计")
    table.add_column("分类", style="cyan")
    table.add_column("模板数", style="white")
    table.add_column("占比", style="green")
    
    total = stats["total_templates"]
    for category, count in sorted(stats["by_category"].items()):
        percentage = (count / total * 100) if total > 0 else 0
        table.add_row(category, str(count), f"{percentage:.1f}%")
    
    console.print(table)


def _display_status_statistics(stats: Dict[str, Any]):
    """显示状态统计"""
    if not stats["by_status"]:
        return
    
    table = Table(title="按状态统计")
    table.add_column("状态", style="cyan")
    table.add_column("模板数", style="white")
    table.add_column("占比", style="green")
    
    total = stats["total_templates"]
    for status, count in sorted(stats["by_status"].items()):
        percentage = (count / total * 100) if total > 0 else 0
        table.add_row(status, str(count), f"{percentage:.1f}%")
    
    console.print(table)


def _display_type_statistics(stats: Dict[str, Any]):
    """显示类型统计"""
    if not stats["by_type"]:
        return
    
    table = Table(title="按类型统计")
    table.add_column("类型", style="cyan")
    table.add_column("模板数", style="white")
    table.add_column("占比", style="green")
    
    total = stats["total_templates"]
    for template_type, count in sorted(stats["by_type"].items()):
        percentage = (count / total * 100) if total > 0 else 0
        table.add_row(template_type, str(count), f"{percentage:.1f}%")
    
    console.print(table)


def _display_detailed_statistics(stats: Dict[str, Any]):
    """显示详细统计"""
    console.print("\n[bold cyan]详细信息:[/bold cyan]")
    
    # 平均文件数
    avg_files = stats["total_files"] / stats["total_templates"] if stats["total_templates"] > 0 else 0
    console.print(f"平均每个模板文件数: {avg_files:.1f}")
    
    # 平均大小
    avg_size = stats["total_size_mb"] / stats["total_templates"] if stats["total_templates"] > 0 else 0
    console.print(f"平均每个模板大小: {avg_size:.1f} MB")


def _export_statistics_report(stats: Dict[str, Any], output_path: str):
    """导出统计报告"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_templates": stats["total_templates"],
            "total_files": stats["total_files"],
            "total_size_mb": round(stats["total_size_mb"], 2),
            "categories_count": len(stats["by_category"])
        },
        "by_category": stats["by_category"],
        "by_status": stats["by_status"],
        "by_type": stats["by_type"]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _execute_batch_operation(templates_root: Path, batch_op: BatchOperation, 
                           operation: str, to_category: Optional[str], status: Optional[str]):
    """执行批量操作"""
    from engines.batch_engine import BatchEngine
    
    # 创建批量操作引擎
    batch_engine = BatchEngine(TEMPLATES_BY_CATEGORY, TEMPLATES_CONFIG)
    
    # 设置操作参数
    if operation == "move" and to_category:
        batch_op.parameters['target_category'] = to_category
    elif operation == "update-status" and status:
        batch_op.parameters['updates'] = {'status': status}
    
    # 进度回调
    def progress_callback(progress_data):
        pass  # Rich Progress 会自动处理
    
    # 执行批量操作
    with Progress(console=console) as progress:
        task = progress.add_task(f"执行{operation}操作...", total=len(batch_op.targets))
        
        def update_progress(progress_data):
            progress.update(task, completed=progress_data['processed_items'])
        
        batch_result = batch_engine.execute_batch_operation(batch_op, update_progress)
    
    # 显示结果
    console.print(f"\n[bold]批量操作完成:[/bold]")
    console.print(f"  [green]成功: {batch_result.summary['successful_operations']}[/green]")
    console.print(f"  [red]失败: {batch_result.summary['failed_operations']}[/red]")
    console.print(f"  [cyan]总计: {batch_result.summary['total_operations']}[/cyan]")
    
    # 显示失败的操作
    failed_results = batch_result.get_failed_results()
    if failed_results:
        console.print("\n[red]失败的操作:[/red]")
        for result in failed_results[:5]:  # 只显示前5个
            console.print(f"  [red]•[/red] {result.target}: {result.message}")
        if len(failed_results) > 5:
            console.print(f"  [dim]... 还有 {len(failed_results) - 5} 个失败操作[/dim]")


def main():
    """CLI入口点"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()



# ==================== 分类管理命令 ====================

@cli.group(name='category')
def category_group():
    """分类管理命令"""
    pass


@category_group.command(name='list')
@click.option('--parent', '-p', help='父分类ID')
@click.option('--format', '-f', default='tree', 
              type=click.Choice(['tree', 'table', 'json']),
              help='输出格式')
@click.option('--show-stats', is_flag=True, help='显示统计信息')
def list_categories(parent: Optional[str], format: str, show_stats: bool):
    """列出分类"""
    try:
        from managers.category_organizer import CategoryOrganizer
        
        config_root = Path("templates/config")
        organizer = CategoryOrganizer(config_root)
        
        if format == 'tree':
            _display_category_tree(organizer, parent)
        elif format == 'table':
            _display_category_table(organizer, parent)
        elif format == 'json':
            categories = organizer.list_categories(parent)
            data = [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description,
                    'subcategories': cat.subcategories,
                    'children_count': len(cat.children)
                }
                for cat in categories
            ]
            console.print_json(data=data)
        
        if show_stats:
            stats = organizer.get_statistics()
            _display_category_stats(stats)
            
    except Exception as e:
        console.print(f"[red]列出分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='create')
@click.option('--id', 'category_id', required=True, help='分类ID')
@click.option('--name', '-n', required=True, help='分类名称')
@click.option('--description', '-d', default='', help='分类描述')
@click.option('--parent', '-p', help='父分类ID')
@click.option('--subcategories', help='子分类列表 (逗号分隔)')
@click.option('--interactive', '-i', is_flag=True, help='交互式创建')
def create_category(category_id: str, name: str, description: str, 
                   parent: Optional[str], subcategories: Optional[str], interactive: bool):
    """创建新分类"""
    try:
        from managers.category_organizer import CategoryOrganizer
        
        config_root = Path("templates/config")
        organizer = CategoryOrganizer(config_root)
        
        # 交互式模式
        if interactive:
            category_id = Prompt.ask("分类ID", default=category_id)
            name = Prompt.ask("分类名称", default=name)
            description = Prompt.ask("分类描述", default=description)
            
            # 显示可用的父分类
            root_cats = organizer.list_categories()
            if root_cats:
                console.print("\n可用的父分类:")
                for cat in root_cats:
                    console.print(f"  - {cat.id}: {cat.name}")
                parent = Prompt.ask("父分类ID (留空表示根分类)", default=parent or "")
                if not parent:
                    parent = None
        
        # 验证分类名称唯一性
        if not organizer.validate_category_name_uniqueness(name):
            console.print(f"[red]错误: 分类名称已存在: {name}[/red]")
            sys.exit(1)
        
        # 解析子分类
        subcat_list = []
        if subcategories:
            subcat_list = [s.strip() for s in subcategories.split(',')]
        
        # 显示创建信息
        console.print("\n[bold]将创建以下分类:[/bold]")
        console.print(f"ID: {category_id}")
        console.print(f"名称: {name}")
        console.print(f"描述: {description}")
        console.print(f"父分类: {parent or '(根分类)'}")
        if subcat_list:
            console.print(f"子分类: {', '.join(subcat_list)}")
        
        if not Confirm.ask("\n确认创建此分类吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 创建分类
        success = organizer.create_category(
            category_id=category_id,
            name=name,
            description=description,
            parent_id=parent,
            subcategories=subcat_list
        )
        
        if success:
            # 保存配置
            organizer.save_categories()
            console.print(f"\n[green]✓ 分类创建成功: {category_id}[/green]")
        else:
            console.print(f"[red]创建分类失败[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]创建分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='update')
@click.option('--id', 'category_id', required=True, help='分类ID')
@click.option('--name', '-n', help='新名称')
@click.option('--description', '-d', help='新描述')
@click.option('--subcategories', help='新子分类列表 (逗号分隔)')
def update_category(category_id: str, name: Optional[str], description: Optional[str],
                   subcategories: Optional[str]):
    """更新分类信息"""
    try:
        from managers.category_organizer import CategoryOrganizer
        
        config_root = Path("templates/config")
        organizer = CategoryOrganizer(config_root)
        
        # 检查分类是否存在
        category = organizer.get_category(category_id)
        if not category:
            console.print(f"[red]错误: 分类不存在: {category_id}[/red]")
            sys.exit(1)
        
        # 显示当前信息
        console.print(f"\n[bold]当前分类信息:[/bold]")
        console.print(f"ID: {category.id}")
        console.print(f"名称: {category.name}")
        console.print(f"描述: {category.description}")
        console.print(f"子分类: {', '.join(category.subcategories) if category.subcategories else '(无)'}")
        
        # 解析更新数据
        updates = {}
        if name:
            updates['name'] = name
        if description:
            updates['description'] = description
        if subcategories:
            updates['subcategories'] = [s.strip() for s in subcategories.split(',')]
        
        if not updates:
            console.print("[yellow]没有提供更新内容[/yellow]")
            return
        
        # 显示更新信息
        console.print(f"\n[bold]将更新为:[/bold]")
        for key, value in updates.items():
            console.print(f"{key}: {value}")
        
        if not Confirm.ask("\n确认更新此分类吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 更新分类
        success = organizer.update_category(category_id, **updates)
        
        if success:
            organizer.save_categories()
            console.print(f"\n[green]✓ 分类更新成功: {category_id}[/green]")
        else:
            console.print(f"[red]更新分类失败[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]更新分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='delete')
@click.option('--id', 'category_id', required=True, help='分类ID')
@click.option('--force', '-f', is_flag=True, help='强制删除（即使有子分类）')
def delete_category(category_id: str, force: bool):
    """删除分类"""
    try:
        from managers.category_organizer import CategoryOrganizer
        from managers.reference_manager import ReferenceManager
        
        config_root = Path("templates/config")
        templates_root = Path("templates")
        
        organizer = CategoryOrganizer(config_root)
        ref_manager = ReferenceManager(templates_root, config_root)
        
        # 检查分类是否存在
        category = organizer.get_category(category_id)
        if not category:
            console.print(f"[red]错误: 分类不存在: {category_id}[/red]")
            sys.exit(1)
        
        # 分析影响
        console.print(f"\n[bold]分析删除影响...[/bold]")
        impact = ref_manager.analyze_category_change_impact(category_id, operation='delete')
        
        # 显示影响分析
        console.print(f"\n[yellow]警告: 此操作将影响 {impact.total_affected} 个模板[/yellow]")
        if impact.warnings:
            for warning in impact.warnings:
                console.print(f"  - {warning}")
        
        if category.children and not force:
            console.print(f"\n[red]错误: 分类有 {len(category.children)} 个子分类，使用 --force 强制删除[/red]")
            sys.exit(1)
        
        if not Confirm.ask(f"\n确认删除分类 '{category.name}' 吗? 此操作不可恢复!"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 删除分类
        success = organizer.delete_category(category_id, force=force)
        
        if success:
            organizer.save_categories()
            console.print(f"\n[green]✓ 分类删除成功: {category_id}[/green]")
            
            # 提示清理引用
            if impact.total_affected > 0:
                console.print(f"\n[yellow]提示: 有 {impact.total_affected} 个模板引用了此分类[/yellow]")
                console.print("运行以下命令清理损坏的引用:")
                console.print(f"  template-cli category cleanup-refs")
        else:
            console.print(f"[red]删除分类失败[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]删除分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='move')
@click.option('--id', 'category_id', required=True, help='要移动的分类ID')
@click.option('--parent', '-p', help='新父分类ID (留空表示移动到根级别)')
def move_category(category_id: str, parent: Optional[str]):
    """移动分类到新的父分类下"""
    try:
        from managers.category_organizer import CategoryOrganizer
        
        config_root = Path("templates/config")
        organizer = CategoryOrganizer(config_root)
        
        # 检查分类是否存在
        category = organizer.get_category(category_id)
        if not category:
            console.print(f"[red]错误: 分类不存在: {category_id}[/red]")
            sys.exit(1)
        
        # 显示当前位置
        path = organizer.get_category_path(category_id)
        console.print(f"\n当前路径: {' > '.join(path)}")
        
        # 显示移动信息
        if parent:
            parent_cat = organizer.get_category(parent)
            if not parent_cat:
                console.print(f"[red]错误: 父分类不存在: {parent}[/red]")
                sys.exit(1)
            console.print(f"将移动到: {parent_cat.name} ({parent})")
        else:
            console.print("将移动到: 根级别")
        
        if not Confirm.ask("\n确认移动此分类吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 移动分类
        success = organizer.move_category(category_id, parent)
        
        if success:
            organizer.save_categories()
            console.print(f"\n[green]✓ 分类移动成功[/green]")
            
            # 显示新路径
            new_path = organizer.get_category_path(category_id)
            console.print(f"新路径: {' > '.join(new_path)}")
        else:
            console.print(f"[red]移动分类失败[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]移动分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='rename')
@click.option('--old-id', required=True, help='旧分类ID')
@click.option('--new-id', required=True, help='新分类ID')
@click.option('--update-refs', is_flag=True, default=True, help='自动更新模板引用')
@click.option('--dry-run', is_flag=True, help='预览模式')
def rename_category(old_id: str, new_id: str, update_refs: bool, dry_run: bool):
    """重命名分类并更新所有引用"""
    try:
        from managers.category_organizer import CategoryOrganizer
        from managers.reference_manager import ReferenceManager
        
        config_root = Path("templates/config")
        templates_root = Path("templates")
        
        organizer = CategoryOrganizer(config_root)
        ref_manager = ReferenceManager(templates_root, config_root)
        
        # 检查旧分类是否存在
        old_category = organizer.get_category(old_id)
        if not old_category:
            console.print(f"[red]错误: 分类不存在: {old_id}[/red]")
            sys.exit(1)
        
        # 检查新ID是否已存在
        if organizer.get_category(new_id):
            console.print(f"[red]错误: 新分类ID已存在: {new_id}[/red]")
            sys.exit(1)
        
        # 分析影响
        console.print(f"\n[bold]分析重命名影响...[/bold]")
        impact = ref_manager.analyze_category_change_impact(old_id, new_id, 'rename')
        
        # 显示影响分析
        console.print(f"\n将重命名分类: {old_category.name} ({old_id}) -> ({new_id})")
        console.print(f"受影响的模板数量: {impact.total_affected}")
        console.print(f"需要更新的引用: {impact.total_changes}")
        console.print(f"预计耗时: {impact.estimated_update_time:.2f} 秒")
        
        if impact.warnings:
            console.print("\n[yellow]警告:[/yellow]")
            for warning in impact.warnings:
                console.print(f"  - {warning}")
        
        if dry_run:
            console.print("\n[yellow]预览模式，未实际执行操作[/yellow]")
            return
        
        if not Confirm.ask("\n确认重命名此分类吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 执行重命名
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # 1. 创建新分类
            task = progress.add_task("创建新分类...", total=None)
            success = organizer.create_category(
                category_id=new_id,
                name=old_category.name,
                description=old_category.description,
                parent_id=old_category.parent_id,
                subcategories=old_category.subcategories,
                metadata=old_category.metadata
            )
            
            if not success:
                console.print(f"[red]创建新分类失败[/red]")
                sys.exit(1)
            
            # 2. 更新引用
            if update_refs and impact.total_affected > 0:
                progress.update(task, description=f"更新 {impact.total_affected} 个模板引用...")
                success, errors = ref_manager.update_category_references(old_id, new_id, dry_run=False)
                
                if not success:
                    console.print(f"\n[yellow]警告: 部分引用更新失败[/yellow]")
                    for error in errors[:5]:  # 只显示前5个错误
                        console.print(f"  - {error}")
            
            # 3. 删除旧分类
            progress.update(task, description="删除旧分类...")
            organizer.delete_category(old_id, force=True)
            
            # 4. 保存配置
            progress.update(task, description="保存配置...")
            organizer.save_categories()
            
            progress.update(task, description="重命名完成!")
        
        console.print(f"\n[green]✓ 分类重命名成功: {old_id} -> {new_id}[/green]")
        console.print(f"更新了 {impact.total_affected} 个模板的引用")
        
    except Exception as e:
        console.print(f"[red]重命名分类失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='validate')
def validate_categories():
    """验证分类结构和引用完整性"""
    try:
        from managers.category_organizer import CategoryOrganizer
        from managers.reference_manager import ReferenceManager
        
        config_root = Path("templates/config")
        templates_root = Path("templates")
        
        organizer = CategoryOrganizer(config_root)
        ref_manager = ReferenceManager(templates_root, config_root)
        
        console.print("[bold]验证分类结构...[/bold]\n")
        
        # 验证分类树结构
        is_valid, errors = organizer.validate_structure()
        
        if is_valid:
            console.print("[green]✓ 分类结构有效[/green]")
        else:
            console.print("[red]✗ 分类结构存在问题:[/red]")
            for error in errors:
                console.print(f"  - {error}")
        
        # 验证引用
        console.print("\n[bold]验证分类引用...[/bold]\n")
        refs_valid, invalid_refs = ref_manager.validate_references()
        
        if refs_valid:
            console.print("[green]✓ 所有分类引用有效[/green]")
        else:
            console.print(f"[red]✗ 发现 {len(invalid_refs)} 个无效引用:[/red]")
            for ref in invalid_refs[:10]:  # 只显示前10个
                console.print(f"  - {ref}")
            if len(invalid_refs) > 10:
                console.print(f"  ... 还有 {len(invalid_refs) - 10} 个")
            
            console.print("\n运行以下命令清理无效引用:")
            console.print("  template-cli category cleanup-refs")
        
        # 显示统计信息
        console.print("\n[bold]分类统计:[/bold]")
        stats = organizer.get_statistics()
        _display_category_stats(stats)
        
        console.print("\n[bold]引用统计:[/bold]")
        ref_stats = ref_manager.get_reference_statistics()
        _display_reference_stats(ref_stats)
        
    except Exception as e:
        console.print(f"[red]验证失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='cleanup-refs')
@click.option('--dry-run', is_flag=True, help='预览模式')
def cleanup_references(dry_run: bool):
    """清理损坏的分类引用"""
    try:
        from managers.reference_manager import ReferenceManager
        
        config_root = Path("templates/config")
        templates_root = Path("templates")
        
        ref_manager = ReferenceManager(templates_root, config_root)
        
        console.print("[bold]清理损坏的分类引用...[/bold]\n")
        
        # 执行清理
        cleaned_count, errors = ref_manager.cleanup_broken_references(dry_run=dry_run)
        
        if dry_run:
            console.print(f"[yellow]预览模式: 将清理 {cleaned_count} 个损坏引用[/yellow]")
        else:
            if cleaned_count > 0:
                console.print(f"[green]✓ 成功清理 {cleaned_count} 个损坏引用[/green]")
            else:
                console.print("[green]✓ 没有发现损坏的引用[/green]")
            
            if errors:
                console.print(f"\n[yellow]警告: {len(errors)} 个清理失败:[/yellow]")
                for error in errors[:5]:
                    console.print(f"  - {error}")
        
    except Exception as e:
        console.print(f"[red]清理失败: {e}[/red]")
        sys.exit(1)


@category_group.command(name='stats')
def category_statistics():
    """显示分类统计信息"""
    try:
        from managers.category_organizer import CategoryOrganizer
        from managers.reference_manager import ReferenceManager
        
        config_root = Path("templates/config")
        templates_root = Path("templates")
        
        organizer = CategoryOrganizer(config_root)
        ref_manager = ReferenceManager(templates_root, config_root)
        
        # 分类统计
        console.print("[bold]分类统计信息[/bold]\n")
        stats = organizer.get_statistics()
        _display_category_stats(stats)
        
        # 引用统计
        console.print("\n[bold]引用统计信息[/bold]\n")
        ref_stats = ref_manager.get_reference_statistics()
        _display_reference_stats(ref_stats)
        
    except Exception as e:
        console.print(f"[red]获取统计信息失败: {e}[/red]")
        sys.exit(1)


# ==================== 辅助函数 ====================

def _display_category_tree(organizer, parent_id=None, indent=0):
    """显示分类树"""
    categories = organizer.list_categories(parent_id)
    
    for category in categories:
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        console.print(f"{prefix}[bold]{category.name}[/bold] ({category.id})")
        if category.description:
            console.print(f"{'  ' * (indent + 1)}  {category.description}")
        if category.subcategories:
            console.print(f"{'  ' * (indent + 1)}  子分类: {', '.join(category.subcategories)}")
        
        # 递归显示子分类
        if category.children:
            _display_category_tree(organizer, category.id, indent + 1)


def _display_category_table(organizer, parent_id=None):
    """以表格形式显示分类"""
    categories = organizer.list_categories(parent_id)
    
    table = Table(title="分类列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("描述")
    table.add_column("子分类数", justify="right")
    table.add_column("子节点数", justify="right")
    
    for category in categories:
        table.add_row(
            category.id,
            category.name,
            category.description[:50] + "..." if len(category.description) > 50 else category.description,
            str(len(category.subcategories)),
            str(len(category.children))
        )
    
    console.print(table)


def _display_category_stats(stats: Dict[str, Any]):
    """显示分类统计信息"""
    table = Table(show_header=False, box=None)
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("总分类数", str(stats['total_categories']))
    table.add_row("根分类数", str(stats['root_categories']))
    table.add_row("最大层级深度", str(stats['max_depth']))
    table.add_row("结构有效性", "✓ 有效" if stats['tree_valid'] else "✗ 无效")
    
    console.print(table)


def _display_reference_stats(stats: Dict[str, Any]):
    """显示引用统计信息"""
    table = Table(show_header=False, box=None)
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("模板总数", str(stats['total_templates']))
    table.add_row("引用总数", str(stats['total_references']))
    table.add_row("使用的分类数", str(stats['unique_categories_used']))
    table.add_row("未使用的分类数", str(len(stats['unused_categories'])))
    table.add_row("平均引用数/模板", f"{stats['average_references_per_template']:.2f}")
    
    if stats['most_used_categories']:
        console.print("\n[bold]最常用的分类:[/bold]")
        for cat_id, count in stats['most_used_categories'][:5]:
            console.print(f"  {cat_id}: {count} 次")
    
    if stats['unused_categories']:
        console.print(f"\n[yellow]未使用的分类 ({len(stats['unused_categories'])}):[/yellow]")
        for cat_id in stats['unused_categories'][:5]:
            console.print(f"  - {cat_id}")
        if len(stats['unused_categories']) > 5:
            console.print(f"  ... 还有 {len(stats['unused_categories']) - 5} 个")
    
    console.print(table)


def _display_search_facets(facets: Dict[str, Dict[str, int]]):
    """显示搜索分面统计"""
    console.print("\n[bold cyan]搜索统计:[/bold cyan]")
    
    for facet_name, facet_data in facets.items():
        if not facet_data:
            continue
        
        # 只显示前5个最常见的值
        sorted_items = sorted(facet_data.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if facet_name == "categories":
            console.print("\n[bold]按分类:[/bold]")
        elif facet_name == "template_types":
            console.print("\n[bold]按类型:[/bold]")
        elif facet_name == "statuses":
            console.print("\n[bold]按状态:[/bold]")
        elif facet_name == "tags":
            console.print("\n[bold]热门标签:[/bold]")
        
        for value, count in sorted_items:
            console.print(f"  {value}: {count}")
        
        if len(facet_data) > 5:
            console.print(f"  ... 还有 {len(facet_data) - 5} 个")

# ==================== 质量检查和文档生成命令 ====================

@cli.group(name='quality')
def quality_group():
    """质量检查和文档生成命令"""
    pass


@quality_group.command(name='check')
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出报告文件路径')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='输出格式')
@click.option('--detailed', '-d', is_flag=True, help='显示详细检查结果')
@click.option('--summary-only', '-s', is_flag=True, help='只显示摘要统计')
@click.option('--min-score', type=float, help='最低质量分数过滤')
def quality_check(paths: tuple[Path, ...], output: Optional[Path], format: str, 
                 detailed: bool, summary_only: bool, min_score: Optional[float]):
    """模板质量检查
    
    PATHS: 要检查的模板目录或模板库根目录
    """
    if not paths:
        templates_root = Path("templates/by_category")
        if templates_root.exists():
            paths = (templates_root,)
        else:
            console.print("[red]错误: 请指定要检查的目录路径或确保templates/by_category目录存在[/red]")
            sys.exit(1)
    
    try:
        checker = QualityChecker()
        all_reports = {}
        
        with Progress() as progress:
            for path in paths:
                if path.name == "by_category" or "by_category" in str(path):
                    # 批量检查整个模板库
                    task = progress.add_task(f"检查模板库 {path}", total=None)
                    
                    def progress_callback(current, total, template_name):
                        progress.update(task, completed=current, total=total, description=f"检查 {template_name}")
                    
                    reports = checker.check_templates_batch(path, progress_callback)
                    all_reports.update(reports)
                    
                else:
                    # 检查单个模板
                    task = progress.add_task(f"检查模板 {path.name}", total=1)
                    report = checker.check_template_quality(path, detailed)
                    all_reports[str(path)] = report
                    progress.update(task, completed=1)
        
        # 过滤结果
        if min_score is not None:
            all_reports = {
                path: report for path, report in all_reports.items()
                if report.metrics.overall_score >= min_score
            }
        
        # 生成摘要
        summary = checker.generate_quality_summary(all_reports)
        
        if format == 'json':
            # JSON格式输出
            output_data = {
                "summary": summary,
                "reports": {path: report.to_dict() for path, report in all_reports.items()}
            }
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                console.print(f"[green]质量报告已保存到: {output}[/green]")
            else:
                print(json.dumps(output_data, ensure_ascii=False, indent=2))
        
        else:
            # 表格格式输出
            if not summary_only:
                # 显示详细报告
                table = Table(title="模板质量检查报告")
                table.add_column("模板", style="cyan")
                table.add_column("总分", style="magenta")
                table.add_column("质量等级", style="green")
                table.add_column("错误", style="red")
                table.add_column("警告", style="yellow")
                
                for path, report in all_reports.items():
                    template_name = Path(path).name
                    score = f"{report.metrics.overall_score:.1f}"
                    level = report.metrics.quality_level.value
                    errors = str(report.metrics.failed_checks)
                    warnings = str(report.metrics.warnings)
                    
                    table.add_row(template_name, score, level, errors, warnings)
                
                console.print(table)
                
                # 显示修复建议
                if detailed:
                    for path, report in all_reports.items():
                        if report.fix_suggestions:
                            console.print(f"\n[cyan]修复建议 - {Path(path).name}:[/cyan]")
                            for suggestion in report.fix_suggestions:
                                severity_color = "red" if suggestion.severity.value == "error" else "yellow"
                                console.print(f"  [{severity_color}]•[/{severity_color}] {suggestion.suggestion}")
                                if suggestion.fix_command:
                                    console.print(f"    命令: [dim]{suggestion.fix_command}[/dim]")
            
            # 显示摘要统计
            console.print("\n[bold]质量摘要统计:[/bold]")
            summary_table = Table()
            summary_table.add_column("指标", style="cyan")
            summary_table.add_column("数值", style="magenta")
            
            summary_table.add_row("总模板数", str(summary.get("total_templates", 0)))
            summary_table.add_row("平均分数", f"{summary.get('average_score', 0):.1f}")
            summary_table.add_row("健康度", f"{summary.get('health_percentage', 0):.1f}%")
            summary_table.add_row("总错误数", str(summary.get("total_errors", 0)))
            summary_table.add_row("总警告数", str(summary.get("total_warnings", 0)))
            
            console.print(summary_table)
            
            # 显示质量分布
            if summary.get("quality_distribution"):
                console.print("\n[bold]质量等级分布:[/bold]")
                for level, count in summary["quality_distribution"].items():
                    if count > 0:
                        console.print(f"  {level}: {count}")
        
    except Exception as e:
        console.print(f"[red]质量检查失败: {e}[/red]")
        sys.exit(1)


@quality_group.command(name='docs')
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), 
              default='markdown', help='输出格式')
@click.option('--type', '-t', type=click.Choice(['template', 'library', 'api']), 
              default='template', help='文档类型')
@click.option('--title', help='文档标题')
def generate_docs(paths: tuple[Path, ...], output: Optional[Path], format: str, type: str, title: Optional[str]):
    """生成模板文档
    
    PATHS: 模板目录或模板库根目录路径
    """
    try:
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
                    from rich.markdown import Markdown
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
    
    except Exception as e:
        console.print(f"[red]文档生成失败: {e}[/red]")
        sys.exit(1)


@quality_group.command(name='stats')
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), 
              default='table', help='输出格式')
@click.option('--category', '-c', help='指定分类生成报告')
@click.option('--export-csv', is_flag=True, help='导出CSV格式数据')
def statistics_report(paths: tuple[Path, ...], output: Optional[Path], format: str, 
                     category: Optional[str], export_csv: bool):
    """生成统计报告
    
    PATHS: 模板库根目录路径
    """
    if not paths:
        templates_root = Path("templates/by_category")
        if templates_root.exists():
            paths = (templates_root,)
        else:
            console.print("[red]错误: 请指定模板库根目录路径或确保templates/by_category目录存在[/red]")
            sys.exit(1)
    
    try:
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
    
    except Exception as e:
        console.print(f"[red]统计报告生成失败: {e}[/red]")
        sys.exit(1)


@quality_group.command(name='fix')
@click.argument('template_path', type=click.Path(exists=True, path_type=Path))
@click.option('--auto', '-a', is_flag=True, help='自动修复可修复的问题')
@click.option('--dry-run', is_flag=True, help='预览模式，不实际修复')
def fix_issues(template_path: Path, auto: bool, dry_run: bool):
    """修复模板质量问题
    
    TEMPLATE_PATH: 模板目录路径
    """
    try:
        checker = QualityChecker()
        
        # 检查模板质量
        console.print(f"[bold]检查模板质量: {template_path.name}[/bold]\n")
        report = checker.check_template_quality(template_path, detailed=True)
        
        # 显示当前状态
        console.print(f"质量评分: {report.metrics.overall_score:.1f}")
        console.print(f"质量等级: {report.metrics.quality_level.value}")
        console.print(f"错误数量: {report.metrics.failed_checks}")
        console.print(f"警告数量: {report.metrics.warnings}")
        
        if not report.fix_suggestions:
            console.print("\n[green]✓ 没有发现可修复的问题[/green]")
            return
        
        # 显示修复建议
        console.print(f"\n[bold]发现 {len(report.fix_suggestions)} 个可修复的问题:[/bold]")
        
        auto_fixable = []
        manual_fixes = []
        
        for i, suggestion in enumerate(report.fix_suggestions, 1):
            severity_color = "red" if suggestion.severity.value == "error" else "yellow"
            console.print(f"\n{i}. [{severity_color}]{suggestion.issue_description}[/{severity_color}]")
            console.print(f"   建议: {suggestion.suggestion}")
            
            if suggestion.auto_fixable:
                auto_fixable.append(suggestion)
                console.print(f"   [green]可自动修复[/green]")
                if suggestion.fix_command:
                    console.print(f"   命令: [dim]{suggestion.fix_command}[/dim]")
            else:
                manual_fixes.append(suggestion)
                console.print(f"   [yellow]需要手动修复[/yellow]")
        
        # 自动修复
        if auto_fixable and (auto or Confirm.ask(f"\n发现 {len(auto_fixable)} 个可自动修复的问题，是否修复?")):
            console.print(f"\n[bold]{'预览' if dry_run else '执行'}自动修复...[/bold]")
            
            fixed_count = 0
            for suggestion in auto_fixable:
                try:
                    if suggestion.issue_code == "MISSING_REQUIRED_FILE":
                        if "README.md" in suggestion.issue_description:
                            readme_path = template_path / "README.md"
                            if not readme_path.exists() and not dry_run:
                                readme_path.write_text(f"# {template_path.name}\n\n模板说明文档", encoding='utf-8')
                            console.print(f"[green]✓ {'将创建' if dry_run else '创建了'} README.md[/green]")
                            fixed_count += 1
                    
                    elif suggestion.issue_code == "MISSING_REQUIRED_DIRECTORY":
                        if "desktop" in suggestion.issue_description:
                            if not dry_run:
                                (template_path / "desktop").mkdir(exist_ok=True)
                            console.print(f"[green]✓ {'将创建' if dry_run else '创建了'} desktop 目录[/green]")
                            fixed_count += 1
                        elif "mobile" in suggestion.issue_description:
                            if not dry_run:
                                (template_path / "mobile").mkdir(exist_ok=True)
                            console.print(f"[green]✓ {'将创建' if dry_run else '创建了'} mobile 目录[/green]")
                            fixed_count += 1
                
                except Exception as e:
                    console.print(f"[red]✗ 修复失败: {e}[/red]")
            
            if dry_run:
                console.print(f"\n[yellow]预览模式: 将修复 {fixed_count} 个问题[/yellow]")
            else:
                console.print(f"\n[green]自动修复完成，共修复 {fixed_count} 个问题[/green]")
                
                # 重新检查质量
                console.print("\n[bold]重新检查质量...[/bold]")
                new_report = checker.check_template_quality(template_path, detailed=False)
                console.print(f"新质量评分: {new_report.metrics.overall_score:.1f} (提升: {new_report.metrics.overall_score - report.metrics.overall_score:.1f})")
        
        # 手动修复提示
        if manual_fixes:
            console.print(f"\n[yellow]还有 {len(manual_fixes)} 个问题需要手动修复:[/yellow]")
            for suggestion in manual_fixes:
                console.print(f"  • {suggestion.suggestion}")
    
    except Exception as e:
        console.print(f"[red]修复失败: {e}[/red]")
        sys.exit(1)

# ==================== 版本控制命令 ====================

@cli.group(name='version')
def version_group():
    """版本控制命令"""
    pass


@version_group.command(name='create')
@click.option('--template', '-t', required=True, help='模板名称或ID')
@click.option('--version', '-v', required=True, help='版本号')
@click.option('--message', '-m', required=True, help='版本说明')
@click.option('--user', '-u', default='cli_user', help='用户名')
def create_version(template: str, version: str, message: str, user: str):
    """创建版本快照"""
    try:
        from managers.version_controller import VersionController
        
        templates_root = Path("templates")
        version_controller = VersionController(templates_root)
        
        # 查找模板路径
        template_path = _find_template_path(templates_root, template)
        if not template_path:
            console.print(f"[red]错误: 模板不存在: {template}[/red]")
            sys.exit(1)
        
        console.print(f"为模板 {template_path.name} 创建版本 {version}...")
        
        # 检测变更
        changes = version_controller.detect_changes(template_path)
        
        if changes:
            console.print(f"\n检测到 {len(changes)} 个变更:")
            for change in changes[:5]:  # 只显示前5个
                console.print(f"  [cyan]{change.change_type.value}[/cyan] {change.file_path}")
            if len(changes) > 5:
                console.print(f"  ... 还有 {len(changes) - 5} 个变更")
        else:
            console.print("\n[yellow]没有检测到变更[/yellow]")
        
        if not Confirm.ask("\n确认创建版本快照吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 创建版本快照
        snapshot = version_controller.create_version_snapshot(
            template_path, version, message, user
        )
        
        # 保存快照
        success = version_controller.save_version_snapshot(snapshot)
        
        if success:
            console.print(f"\n[green]✓ 版本快照创建成功: {version}[/green]")
            console.print(f"  模板: {snapshot.template_id}")
            console.print(f"  文件数: {snapshot.total_files}")
            console.print(f"  大小: {snapshot.total_size_bytes / 1024 / 1024:.1f} MB")
        else:
            console.print("[red]版本快照创建失败[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]创建版本失败: {e}[/red]")
        sys.exit(1)


@version_group.command(name='list')
@click.option('--template', '-t', required=True, help='模板名称或ID')
@click.option('--format', '-f', default='table', 
              type=click.Choice(['table', 'json']),
              help='输出格式')
def list_versions(template: str, format: str):
    """列出版本历史"""
    try:
        from managers.version_controller import VersionController
        
        templates_root = Path("templates")
        version_controller = VersionController(templates_root)
        
        # 查找模板路径
        template_path = _find_template_path(templates_root, template)
        if not template_path:
            console.print(f"[red]错误: 模板不存在: {template}[/red]")
            sys.exit(1)
        
        template_id = template_path.name
        history = version_controller.get_version_history(template_id)
        
        if not history.versions:
            console.print(f"[yellow]模板 {template_id} 没有版本历史[/yellow]")
            return
        
        if format == 'table':
            table = Table(title=f"版本历史 - {template_id}")
            table.add_column("版本", style="cyan")
            table.add_column("时间", style="white")
            table.add_column("用户", style="green")
            table.add_column("说明", style="dim")
            table.add_column("文件数", style="blue")
            table.add_column("大小", style="magenta")
            
            for version in history.versions:
                size_mb = version.total_size_bytes / 1024 / 1024
                table.add_row(
                    version.version,
                    version.timestamp.strftime("%Y-%m-%d %H:%M"),
                    version.user,
                    version.message[:40] + "..." if len(version.message) > 40 else version.message,
                    str(version.total_files),
                    f"{size_mb:.1f} MB"
                )
            
            console.print(table)
            
        elif format == 'json':
            versions_data = []
            for version in history.versions:
                versions_data.append({
                    "version": version.version,
                    "timestamp": version.timestamp.isoformat(),
                    "user": version.user,
                    "message": version.message,
                    "total_files": version.total_files,
                    "total_size_bytes": version.total_size_bytes,
                    "changes_count": len(version.changes)
                })
            
            output = {
                "template_id": template_id,
                "current_version": history.current_version,
                "total_versions": len(history.versions),
                "versions": versions_data
            }
            console.print_json(data=output)
            
    except Exception as e:
        console.print(f"[red]列出版本失败: {e}[/red]")
        sys.exit(1)


@version_group.command(name='compare')
@click.option('--template', '-t', required=True, help='模板名称或ID')
@click.option('--version1', required=True, help='版本1')
@click.option('--version2', required=True, help='版本2')
@click.option('--format', '-f', default='table', 
              type=click.Choice(['table', 'json']),
              help='输出格式')
def compare_versions(template: str, version1: str, version2: str, format: str):
    """比较两个版本"""
    try:
        from managers.version_controller import VersionController
        
        templates_root = Path("templates")
        version_controller = VersionController(templates_root)
        
        # 查找模板路径
        template_path = _find_template_path(templates_root, template)
        if not template_path:
            console.print(f"[red]错误: 模板不存在: {template}[/red]")
            sys.exit(1)
        
        template_id = template_path.name
        comparison = version_controller.compare_versions(template_id, version1, version2)
        
        if "error" in comparison:
            console.print(f"[red]比较失败: {comparison['error']}[/red]")
            sys.exit(1)
        
        if format == 'table':
            # 显示文件变更
            file_changes = comparison["file_changes"]
            
            if file_changes["added"]:
                console.print(f"\n[green]新增文件 ({len(file_changes['added'])}):[/green]")
                for file_path in file_changes["added"]:
                    console.print(f"  [green]+[/green] {file_path}")
            
            if file_changes["removed"]:
                console.print(f"\n[red]删除文件 ({len(file_changes['removed'])}):[/red]")
                for file_path in file_changes["removed"]:
                    console.print(f"  [red]-[/red] {file_path}")
            
            if file_changes["modified"]:
                console.print(f"\n[yellow]修改文件 ({len(file_changes['modified'])}):[/yellow]")
                for file_path in file_changes["modified"]:
                    console.print(f"  [yellow]~[/yellow] {file_path}")
            
            # 显示配置变更
            config_changes = comparison["config_changes"]
            if any(config_changes.values()):
                console.print(f"\n[cyan]配置变更:[/cyan]")
                
                for key, value in config_changes["added"].items():
                    console.print(f"  [green]+[/green] {key}: {value}")
                
                for key, value in config_changes["removed"].items():
                    console.print(f"  [red]-[/red] {key}: {value}")
                
                for key, change in config_changes["modified"].items():
                    console.print(f"  [yellow]~[/yellow] {key}: {change['old']} → {change['new']}")
            
            # 显示统计信息
            stats = comparison["statistics"]
            console.print(f"\n[bold]统计信息:[/bold]")
            console.print(f"  总变更数: {stats['total_changes']}")
            console.print(f"  {version1} 文件数: {stats['files_v1']}")
            console.print(f"  {version2} 文件数: {stats['files_v2']}")
            console.print(f"  {version1} 大小: {stats['size_v1'] / 1024 / 1024:.1f} MB")
            console.print(f"  {version2} 大小: {stats['size_v2'] / 1024 / 1024:.1f} MB")
            
        elif format == 'json':
            console.print_json(data=comparison)
            
    except Exception as e:
        console.print(f"[red]比较版本失败: {e}[/red]")
        sys.exit(1)


@version_group.command(name='rollback')
@click.option('--template', '-t', required=True, help='模板名称或ID')
@click.option('--version', '-v', required=True, help='目标版本')
@click.option('--backup/--no-backup', default=True, help='是否备份当前版本')
@click.option('--force', is_flag=True, help='强制回滚，不询问确认')
def rollback_version(template: str, version: str, backup: bool, force: bool):
    """回滚到指定版本"""
    try:
        from managers.version_controller import VersionController
        
        templates_root = Path("templates")
        version_controller = VersionController(templates_root)
        
        # 查找模板路径
        template_path = _find_template_path(templates_root, template)
        if not template_path:
            console.print(f"[red]错误: 模板不存在: {template}[/red]")
            sys.exit(1)
        
        template_id = template_path.name
        
        # 检查目标版本是否存在
        history = version_controller.get_version_history(template_id)
        target_snapshot = history.get_version(version)
        
        if not target_snapshot:
            console.print(f"[red]错误: 版本不存在: {version}[/red]")
            available_versions = history.get_version_list()
            if available_versions:
                console.print(f"可用版本: {', '.join(available_versions)}")
            sys.exit(1)
        
        # 显示回滚信息
        console.print(f"\n[bold]回滚信息:[/bold]")
        console.print(f"模板: {template_id}")
        console.print(f"当前版本: {history.current_version}")
        console.print(f"目标版本: {version}")
        console.print(f"目标版本时间: {target_snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"目标版本说明: {target_snapshot.message}")
        console.print(f"备份当前版本: {'是' if backup else '否'}")
        
        if not force and not Confirm.ask("\n确认执行回滚操作吗? 此操作不可逆!"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 执行回滚
        console.print("\n正在执行回滚...")
        result = version_controller.rollback_to_version(template_path, version, backup)
        
        if result.success:
            console.print(f"\n[green]✓ 回滚成功[/green]")
            console.print(f"  {result.message}")
            if backup:
                console.print(f"  当前版本已备份")
        else:
            console.print(f"\n[red]✗ 回滚失败: {result.message}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]回滚失败: {e}[/red]")
        sys.exit(1)


@version_group.command(name='stats')
@click.option('--template', '-t', required=True, help='模板名称或ID')
def version_stats(template: str):
    """显示版本统计信息"""
    try:
        from managers.version_controller import VersionController
        
        templates_root = Path("templates")
        version_controller = VersionController(templates_root)
        
        # 查找模板路径
        template_path = _find_template_path(templates_root, template)
        if not template_path:
            console.print(f"[red]错误: 模板不存在: {template}[/red]")
            sys.exit(1)
        
        template_id = template_path.name
        stats = version_controller.get_version_statistics(template_id)
        
        if "error" in stats:
            console.print(f"[red]获取统计信息失败: {stats['error']}[/red]")
            sys.exit(1)
        
        # 显示基本信息
        console.print(f"\n[bold cyan]版本统计 - {template_id}[/bold cyan]")
        
        table = Table(show_header=False, box=None)
        table.add_column("项目", style="cyan", width=20)
        table.add_column("值", style="white")
        
        table.add_row("总版本数", str(stats["total_versions"]))
        table.add_row("当前版本", stats["current_version"])
        table.add_row("时间跨度", f"{stats['time_span_days']} 天")
        table.add_row("总变更数", str(stats["change_statistics"]["total_changes"]))
        
        latest = stats["latest_version_info"]
        table.add_row("最新版本", latest["version"])
        table.add_row("最新版本时间", latest["timestamp"][:19])
        table.add_row("最新版本用户", latest["user"])
        table.add_row("最新版本文件数", str(latest["total_files"]))
        table.add_row("最新版本大小", f"{latest['total_size_mb']} MB")
        
        console.print(table)
        
        # 显示变更类型统计
        change_types = stats["change_statistics"]["change_types"]
        if change_types:
            console.print(f"\n[bold]变更类型统计:[/bold]")
            for change_type, count in change_types.items():
                console.print(f"  {change_type}: {count}")
        
        # 显示用户统计
        user_stats = stats["user_statistics"]
        if user_stats:
            console.print(f"\n[bold]用户统计:[/bold]")
            for user, count in user_stats.items():
                console.print(f"  {user}: {count} 个版本")
        
        # 显示版本列表
        console.print(f"\n[bold]版本列表:[/bold]")
        versions = stats["version_list"]
        for i, version in enumerate(versions[:10]):  # 只显示前10个
            marker = " (当前)" if version == stats["current_version"] else ""
            console.print(f"  {version}{marker}")
        if len(versions) > 10:
            console.print(f"  ... 还有 {len(versions) - 10} 个版本")
            
    except Exception as e:
        console.print(f"[red]获取版本统计失败: {e}[/red]")
        sys.exit(1)


# ==================== 迁移工具命令 ====================

@cli.group(name='migrate')
def migrate_group():
    """迁移工具命令"""
    pass


@migrate_group.command(name='export')
@click.option('--output', '-o', required=True, help='导出文件路径')
@click.option('--category', '-c', multiple=True, help='导出指定分类 (可多次使用)')
@click.option('--template-type', multiple=True, help='导出指定模板类型')
@click.option('--status', multiple=True, help='导出指定状态的模板')
@click.option('--tags', help='导出包含指定标签的模板 (逗号分隔)')
@click.option('--include-versions', is_flag=True, help='包含版本历史')
@click.option('--compress/--no-compress', default=True, help='是否压缩导出文件')
@click.option('--mode', default='full', 
              type=click.Choice(['full', 'selective', 'category']),
              help='导出模式')
def export_templates(output: str, category: tuple, template_type: tuple, status: tuple,
                    tags: Optional[str], include_versions: bool, compress: bool, mode: str):
    """导出模板库"""
    try:
        from managers.migration_tool import MigrationTool, MigrationFilter, MigrationMode
        
        templates_root = Path("templates")
        migration_tool = MigrationTool(templates_root)
        
        # 创建过滤器
        migration_filter = None
        if any([category, template_type, status, tags]):
            tag_list = []
            if tags:
                tag_list = [t.strip() for t in tags.split(',')]
            
            migration_filter = MigrationFilter(
                categories=list(category),
                template_types=list(template_type),
                status_list=list(status),
                tags=tag_list
            )
        
        # 显示导出信息
        console.print(f"\n[bold]导出配置:[/bold]")
        console.print(f"输出文件: {output}")
        console.print(f"导出模式: {mode}")
        console.print(f"包含版本历史: {'是' if include_versions else '否'}")
        console.print(f"压缩文件: {'是' if compress else '否'}")
        
        if migration_filter:
            console.print(f"\n[bold]过滤条件:[/bold]")
            if migration_filter.categories:
                console.print(f"分类: {', '.join(migration_filter.categories)}")
            if migration_filter.template_types:
                console.print(f"类型: {', '.join(migration_filter.template_types)}")
            if migration_filter.status_list:
                console.print(f"状态: {', '.join(migration_filter.status_list)}")
            if migration_filter.tags:
                console.print(f"标签: {', '.join(migration_filter.tags)}")
        
        if not Confirm.ask("\n确认执行导出操作吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        # 执行导出
        console.print("\n正在导出模板...")
        
        export_path = Path(output)
        migration_mode = MigrationMode(mode)
        
        result = migration_tool.export_templates(
            export_path,
            migration_filter,
            migration_mode,
            include_versions,
            compress
        )
        
        if result.success:
            console.print(f"\n[green]✓ 导出成功[/green]")
            console.print(f"  导出文件: {result.export_path}")
            console.print(f"  模板数量: {result.total_templates}")
            console.print(f"  文件大小: {result.file_size_mb} MB")
            console.print(f"  总大小: {result.total_size_mb} MB")
        else:
            console.print(f"\n[red]✗ 导出失败: {result.message}[/red]")
            if result.errors:
                console.print("\n错误详情:")
                for error in result.errors[:5]:
                    console.print(f"  [red]•[/red] {error}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")
        sys.exit(1)


@migrate_group.command(name='import')
@click.option('--source', '-s', required=True, help='导入文件或目录路径')
@click.option('--conflict', default='skip',
              type=click.Choice(['skip', 'overwrite', 'rename', 'merge']),
              help='冲突解决策略')
@click.option('--validate/--no-validate', default=True, help='是否验证完整性')
@click.option('--backup/--no-backup', default=True, help='是否创建备份')
@click.option('--dry-run', is_flag=True, help='预览模式，不实际执行')
def import_templates(source: str, conflict: str, validate: bool, backup: bool, dry_run: bool):
    """导入模板库"""
    try:
        from managers.migration_tool import MigrationTool, ConflictResolution
        
        templates_root = Path("templates")
        migration_tool = MigrationTool(templates_root)
        
        source_path = Path(source)
        if not source_path.exists():
            console.print(f"[red]错误: 源文件不存在: {source}[/red]")
            sys.exit(1)
        
        conflict_resolution = ConflictResolution(conflict)
        
        # 显示导入信息
        console.print(f"\n[bold]导入配置:[/bold]")
        console.print(f"源文件: {source}")
        console.print(f"冲突策略: {conflict}")
        console.print(f"验证完整性: {'是' if validate else '否'}")
        console.print(f"创建备份: {'是' if backup else '否'}")
        console.print(f"预览模式: {'是' if dry_run else '否'}")
        
        if dry_run:
            console.print("\n[yellow]预览模式：将分析导入内容但不实际执行[/yellow]")
        
        if not dry_run and not Confirm.ask("\n确认执行导入操作吗?"):
            console.print("[yellow]操作已取消[/yellow]")
            return
        
        if dry_run:
            # 预览模式：只分析不执行
            console.print("\n正在分析导入内容...")
            
            # 这里可以添加预览逻辑
            console.print("[yellow]预览功能待实现[/yellow]")
            return
        
        # 执行导入
        console.print("\n正在导入模板...")
        
        result = migration_tool.import_templates(
            source_path,
            conflict_resolution,
            validate,
            backup
        )
        
        if result.success:
            console.print(f"\n[green]✓ 导入成功[/green]")
            console.print(f"  成功导入: {result.successful_imports} 个模板")
            console.print(f"  跳过: {len(result.skipped_templates)} 个模板")
            console.print(f"  失败: {result.failed_imports} 个模板")
            
            if result.conflicts:
                console.print(f"  冲突处理: {len(result.conflicts)} 个")
        else:
            console.print(f"\n[red]✗ 导入失败: {result.message}[/red]")
        
        # 显示详细信息
        if result.failed_templates:
            console.print(f"\n[red]失败的模板:[/red]")
            for template_id in result.failed_templates[:5]:
                console.print(f"  [red]•[/red] {template_id}")
            if len(result.failed_templates) > 5:
                console.print(f"  ... 还有 {len(result.failed_templates) - 5} 个")
        
        if result.conflicts:
            console.print(f"\n[yellow]冲突处理:[/yellow]")
            for conflict in result.conflicts[:3]:
                console.print(f"  [yellow]•[/yellow] {conflict['template_id']}: {conflict['conflict_type']}")
            if len(result.conflicts) > 3:
                console.print(f"  ... 还有 {len(result.conflicts) - 3} 个冲突")
        
        if result.errors:
            console.print(f"\n[red]错误详情:[/red]")
            for error in result.errors[:3]:
                console.print(f"  [red]•[/red] {error}")
            if len(result.errors) > 3:
                console.print(f"  ... 还有 {len(result.errors) - 3} 个错误")
        
        if result.warnings:
            console.print(f"\n[yellow]警告信息:[/yellow]")
            for warning in result.warnings[:3]:
                console.print(f"  [yellow]•[/yellow] {warning}")
            if len(result.warnings) > 3:
                console.print(f"  ... 还有 {len(result.warnings) - 3} 个警告")
                
    except Exception as e:
        console.print(f"[red]导入失败: {e}[/red]")
        sys.exit(1)


@migrate_group.command(name='stats')
def migration_stats():
    """显示迁移统计信息"""
    try:
        from managers.migration_tool import MigrationTool
        
        templates_root = Path("templates")
        migration_tool = MigrationTool(templates_root)
        
        stats = migration_tool.get_migration_statistics()
        
        if "error" in stats:
            console.print(f"[red]获取统计信息失败: {stats['error']}[/red]")
            sys.exit(1)
        
        # 显示基本统计
        console.print(f"\n[bold cyan]模板库统计信息[/bold cyan]")
        
        table = Table(show_header=False, box=None)
        table.add_column("项目", style="cyan", width=20)
        table.add_column("值", style="white")
        
        table.add_row("总模板数", str(stats["total_templates"]))
        table.add_row("总大小", f"{stats['total_size_mb']} MB")
        table.add_row("平均大小", f"{stats['average_template_size_mb']} MB")
        
        console.print(table)
        
        # 显示分类统计
        if stats["categories"]:
            console.print(f"\n[bold]按分类统计:[/bold]")
            for category, count in stats["categories"].items():
                percentage = (count / stats["total_templates"] * 100) if stats["total_templates"] > 0 else 0
                console.print(f"  {category}: {count} ({percentage:.1f}%)")
        
        # 显示类型统计
        if stats["template_types"]:
            console.print(f"\n[bold]按类型统计:[/bold]")
            for template_type, count in stats["template_types"].items():
                percentage = (count / stats["total_templates"] * 100) if stats["total_templates"] > 0 else 0
                console.print(f"  {template_type}: {count} ({percentage:.1f}%)")
        
        # 显示状态统计
        if stats["status_distribution"]:
            console.print(f"\n[bold]按状态统计:[/bold]")
            for status, count in stats["status_distribution"].items():
                percentage = (count / stats["total_templates"] * 100) if stats["total_templates"] > 0 else 0
                console.print(f"  {status}: {count} ({percentage:.1f}%)")
                
    except Exception as e:
        console.print(f"[red]获取统计信息失败: {e}[/red]")
        sys.exit(1)