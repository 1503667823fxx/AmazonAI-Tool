#!/usr/bin/env python3
"""
质量检查器
实现模板完整性和规范性检查，创建质量评分和问题检测算法，建立自动修复建议系统
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID

# 导入现有的验证器
sys.path.append(str(Path(__file__).parent.parent))
from validators.structure_validator import StructureValidator
from validators.config_validator import ConfigValidator
from validators.image_validator import ImageValidator
from models.validation import ValidationResult, ValidationError, ValidationLevel, ValidationCategory

console = Console()


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"  # 90-100分
    GOOD = "good"           # 80-89分
    FAIR = "fair"           # 70-79分
    POOR = "poor"           # 60-69分
    CRITICAL = "critical"   # <60分


@dataclass
class QualityMetrics:
    """质量指标"""
    completeness_score: float = 0.0      # 完整性评分
    structure_score: float = 0.0         # 结构规范性评分
    config_score: float = 0.0            # 配置质量评分
    image_score: float = 0.0             # 图片质量评分
    naming_score: float = 0.0            # 命名规范评分
    documentation_score: float = 0.0     # 文档质量评分
    
    overall_score: float = 0.0           # 总体评分
    quality_level: QualityLevel = QualityLevel.CRITICAL
    
    # 详细统计
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings: int = 0
    
    def calculate_overall_score(self):
        """计算总体评分"""
        scores = [
            self.completeness_score,
            self.structure_score,
            self.config_score,
            self.image_score,
            self.naming_score,
            self.documentation_score
        ]
        
        # 加权平均，结构和配置权重更高
        weights = [0.2, 0.25, 0.25, 0.15, 0.1, 0.05]
        self.overall_score = sum(score * weight for score, weight in zip(scores, weights))
        
        # 确定质量等级
        if self.overall_score >= 90:
            self.quality_level = QualityLevel.EXCELLENT
        elif self.overall_score >= 80:
            self.quality_level = QualityLevel.GOOD
        elif self.overall_score >= 70:
            self.quality_level = QualityLevel.FAIR
        elif self.overall_score >= 60:
            self.quality_level = QualityLevel.POOR
        else:
            self.quality_level = QualityLevel.CRITICAL


@dataclass
class FixSuggestion:
    """修复建议"""
    issue_code: str
    issue_description: str
    severity: ValidationLevel
    category: ValidationCategory
    suggestion: str
    auto_fixable: bool = False
    fix_command: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "issue_code": self.issue_code,
            "issue_description": self.issue_description,
            "severity": self.severity.value,
            "category": self.category.value,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
            "fix_command": self.fix_command
        }


@dataclass
class QualityReport:
    """质量报告"""
    template_path: str
    template_id: str
    template_name: str
    
    metrics: QualityMetrics
    validation_result: ValidationResult
    fix_suggestions: List[FixSuggestion] = field(default_factory=list)
    
    # 报告元数据
    generated_at: datetime = field(default_factory=datetime.now)
    checker_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_path": self.template_path,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "metrics": {
                "completeness_score": self.metrics.completeness_score,
                "structure_score": self.metrics.structure_score,
                "config_score": self.metrics.config_score,
                "image_score": self.metrics.image_score,
                "naming_score": self.metrics.naming_score,
                "documentation_score": self.metrics.documentation_score,
                "overall_score": self.metrics.overall_score,
                "quality_level": self.metrics.quality_level.value,
                "total_checks": self.metrics.total_checks,
                "passed_checks": self.metrics.passed_checks,
                "failed_checks": self.metrics.failed_checks,
                "warnings": self.metrics.warnings
            },
            "validation_summary": self.validation_result.get_summary(),
            "fix_suggestions": [suggestion.to_dict() for suggestion in self.fix_suggestions],
            "generated_at": self.generated_at.isoformat(),
            "checker_version": self.checker_version
        }


class QualityChecker:
    """质量检查器"""
    
    def __init__(self):
        """初始化质量检查器"""
        self.structure_validator = StructureValidator()
        self.config_validator = ConfigValidator()
        self.image_validator = ImageValidator()
        
        # 质量检查权重配置
        self.weights = {
            "completeness": 0.2,
            "structure": 0.25,
            "config": 0.25,
            "image": 0.15,
            "naming": 0.1,
            "documentation": 0.05
        }
        
        # 修复建议模板
        self.fix_suggestions_db = self._load_fix_suggestions()
    
    def check_template_quality(self, template_path: Path, detailed: bool = True) -> QualityReport:
        """检查单个模板的质量
        
        Args:
            template_path: 模板目录路径
            detailed: 是否进行详细检查
            
        Returns:
            质量报告
        """
        # 初始化报告
        template_id = template_path.name
        template_name = self._get_template_name(template_path)
        
        metrics = QualityMetrics()
        validation_result = ValidationResult(is_valid=True)
        
        # 1. 完整性检查
        completeness_score, completeness_errors = self._check_completeness(template_path)
        metrics.completeness_score = completeness_score
        validation_result.add_errors(completeness_errors)
        
        # 2. 结构规范性检查
        structure_score, structure_errors = self._check_structure_quality(template_path)
        metrics.structure_score = structure_score
        validation_result.add_errors(structure_errors)
        
        # 3. 配置质量检查
        config_score, config_errors = self._check_config_quality(template_path)
        metrics.config_score = config_score
        validation_result.add_errors(config_errors)
        
        # 4. 图片质量检查
        image_score, image_errors = self._check_image_quality(template_path)
        metrics.image_score = image_score
        validation_result.add_errors(image_errors)
        
        # 5. 命名规范检查
        naming_score, naming_errors = self._check_naming_quality(template_path)
        metrics.naming_score = naming_score
        validation_result.add_errors(naming_errors)
        
        # 6. 文档质量检查
        doc_score, doc_errors = self._check_documentation_quality(template_path)
        metrics.documentation_score = doc_score
        validation_result.add_errors(doc_errors)
        
        # 计算总体评分
        metrics.total_checks = validation_result.total_checks
        metrics.passed_checks = validation_result.passed_checks
        metrics.failed_checks = validation_result.failed_checks
        metrics.warnings = validation_result.warning_count
        metrics.calculate_overall_score()
        
        # 生成修复建议
        fix_suggestions = self._generate_fix_suggestions(validation_result.errors + validation_result.warnings)
        
        return QualityReport(
            template_path=str(template_path),
            template_id=template_id,
            template_name=template_name,
            metrics=metrics,
            validation_result=validation_result,
            fix_suggestions=fix_suggestions
        )
    
    def check_templates_batch(self, templates_root: Path, progress_callback=None) -> Dict[str, QualityReport]:
        """批量检查模板质量
        
        Args:
            templates_root: 模板根目录
            progress_callback: 进度回调函数
            
        Returns:
            {模板路径: 质量报告}
        """
        reports = {}
        
        # 查找所有模板目录
        template_dirs = []
        for category_dir in templates_root.iterdir():
            if category_dir.is_dir() and category_dir.name != "config":
                for template_dir in category_dir.iterdir():
                    if template_dir.is_dir():
                        template_dirs.append(template_dir)
        
        total_templates = len(template_dirs)
        
        for i, template_dir in enumerate(template_dirs):
            if progress_callback:
                progress_callback(i, total_templates, template_dir.name)
            
            try:
                report = self.check_template_quality(template_dir)
                reports[str(template_dir)] = report
            except Exception as e:
                console.print(f"[red]检查模板 {template_dir} 时发生错误: {e}[/red]")
        
        return reports
    
    def _check_completeness(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查模板完整性"""
        errors = []
        score = 100.0
        
        # 必需文件检查
        required_files = ["template.json", "README.md", "preview.jpg"]
        missing_files = []
        
        for required_file in required_files:
            if not (template_path / required_file).exists():
                missing_files.append(required_file)
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    code="MISSING_REQUIRED_FILE",
                    message=f"缺少必需文件: {required_file}",
                    field=required_file
                ))
        
        # 必需目录检查
        required_dirs = ["desktop", "mobile"]
        missing_dirs = []
        
        for required_dir in required_dirs:
            if not (template_path / required_dir).exists():
                missing_dirs.append(required_dir)
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    code="MISSING_REQUIRED_DIRECTORY",
                    message=f"缺少必需目录: {required_dir}",
                    field=required_dir
                ))
        
        # 计算完整性评分
        total_required = len(required_files) + len(required_dirs)
        missing_count = len(missing_files) + len(missing_dirs)
        
        if total_required > 0:
            score = max(0, (total_required - missing_count) / total_required * 100)
        
        return score, errors
    
    def _check_structure_quality(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查结构质量"""
        is_valid, structure_errors = self.structure_validator.validate_template_directory(
            template_path, validate_images=False, validate_config=False
        )
        
        # 转换为ValidationError对象
        validation_errors = []
        for error_msg in structure_errors:
            validation_errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.STRUCTURE,
                code="STRUCTURE_VIOLATION",
                message=error_msg
            ))
        
        # 计算结构评分
        if is_valid:
            score = 100.0
        else:
            # 根据错误数量计算评分
            error_count = len(structure_errors)
            score = max(0, 100 - (error_count * 10))  # 每个错误扣10分
        
        return score, validation_errors
    
    def _check_config_quality(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查配置质量"""
        config_path = template_path / "template.json"
        
        if not config_path.exists():
            return 0.0, [ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.CONFIG,
                code="MISSING_CONFIG",
                message="缺少配置文件"
            )]
        
        is_valid, config_errors = self.config_validator.validate_config(config_path)
        
        # 转换为ValidationError对象
        validation_errors = []
        for error_msg in config_errors:
            validation_errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.CONFIG,
                code="CONFIG_VIOLATION",
                message=error_msg
            ))
        
        # 计算配置评分
        if is_valid:
            score = 100.0
        else:
            error_count = len(config_errors)
            score = max(0, 100 - (error_count * 15))  # 每个错误扣15分
        
        return score, validation_errors
    
    def _check_image_quality(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查图片质量"""
        errors = []
        score = 100.0
        
        try:
            # 使用图片验证器检查尺寸
            is_valid, image_errors = self.structure_validator.validate_image_dimensions_only(template_path)
            
            # 转换为ValidationError对象
            for error_msg in image_errors:
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.IMAGE,
                    code="IMAGE_DIMENSION_ERROR",
                    message=error_msg
                ))
            
            # 计算图片评分
            if is_valid:
                score = 100.0
            else:
                error_count = len(image_errors)
                score = max(0, 100 - (error_count * 20))  # 每个错误扣20分
                
        except Exception as e:
            errors.append(ValidationError(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.IMAGE,
                code="IMAGE_CHECK_FAILED",
                message=f"图片检查失败: {e}"
            ))
            score = 50.0  # 无法检查时给予中等评分
        
        return score, errors
    
    def _check_naming_quality(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查命名规范质量"""
        errors = []
        score = 100.0
        
        # 检查目录名称
        dir_name = template_path.name
        if not self._is_valid_kebab_case(dir_name):
            errors.append(ValidationError(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.NAMING,
                code="INVALID_DIRECTORY_NAME",
                message=f"目录名称不符合kebab-case规范: {dir_name}",
                suggestion="使用小写字母、数字和连字符，如: tech-modern"
            ))
            score -= 20
        
        # 检查文件命名
        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                filename = file_path.name
                if not self._is_valid_filename(filename):
                    errors.append(ValidationError(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.NAMING,
                        code="INVALID_FILENAME",
                        message=f"文件名不符合规范: {filename}",
                        suggestion="使用小写字母、数字、连字符和下划线"
                    ))
                    score -= 5
        
        return max(0, score), errors
    
    def _check_documentation_quality(self, template_path: Path) -> Tuple[float, List[ValidationError]]:
        """检查文档质量"""
        errors = []
        score = 100.0
        
        # 检查README.md
        readme_path = template_path / "README.md"
        if not readme_path.exists():
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.CONTENT,
                code="MISSING_README",
                message="缺少README.md文档"
            ))
            score -= 50
        else:
            # 检查README内容质量
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if len(content.strip()) < 100:
                    errors.append(ValidationError(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.CONTENT,
                        code="README_TOO_SHORT",
                        message="README.md内容过于简短",
                        suggestion="添加详细的模板说明、使用方法和示例"
                    ))
                    score -= 20
                
                # 检查是否包含基本章节
                required_sections = ["# ", "## "]
                if not any(section in content for section in required_sections):
                    errors.append(ValidationError(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.CONTENT,
                        code="README_NO_SECTIONS",
                        message="README.md缺少章节结构",
                        suggestion="添加标题和章节来组织内容"
                    ))
                    score -= 15
                    
            except Exception as e:
                errors.append(ValidationError(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.CONTENT,
                    code="README_READ_ERROR",
                    message=f"无法读取README.md: {e}"
                ))
                score -= 30
        
        return max(0, score), errors
    
    def _get_template_name(self, template_path: Path) -> str:
        """获取模板名称"""
        config_path = template_path / "template.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("name", template_path.name)
        except:
            return template_path.name
    
    def _is_valid_kebab_case(self, name: str) -> bool:
        """检查是否为有效的kebab-case格式"""
        if not name:
            return False
        
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
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-_.')
        return all(c in allowed_chars for c in filename.lower())
    
    def _generate_fix_suggestions(self, errors: List[ValidationError]) -> List[FixSuggestion]:
        """生成修复建议"""
        suggestions = []
        
        for error in errors:
            suggestion = self._get_fix_suggestion(error)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _get_fix_suggestion(self, error: ValidationError) -> Optional[FixSuggestion]:
        """根据错误生成修复建议"""
        suggestions_map = {
            "MISSING_REQUIRED_FILE": {
                "suggestion": "创建缺少的必需文件",
                "auto_fixable": True,
                "fix_command": "touch {field}"
            },
            "MISSING_REQUIRED_DIRECTORY": {
                "suggestion": "创建缺少的必需目录",
                "auto_fixable": True,
                "fix_command": "mkdir -p {field}"
            },
            "INVALID_DIRECTORY_NAME": {
                "suggestion": "重命名目录为kebab-case格式",
                "auto_fixable": False,
                "fix_command": None
            },
            "IMAGE_DIMENSION_ERROR": {
                "suggestion": "调整图片尺寸到标准规格",
                "auto_fixable": False,
                "fix_command": None
            },
            "CONFIG_VIOLATION": {
                "suggestion": "修复配置文件格式或内容错误",
                "auto_fixable": False,
                "fix_command": None
            },
            "MISSING_README": {
                "suggestion": "创建README.md文档",
                "auto_fixable": True,
                "fix_command": "touch README.md"
            }
        }
        
        suggestion_info = suggestions_map.get(error.code)
        if not suggestion_info:
            return None
        
        fix_command = suggestion_info.get("fix_command")
        if fix_command and error.field:
            fix_command = fix_command.format(field=error.field)
        
        return FixSuggestion(
            issue_code=error.code,
            issue_description=error.message,
            severity=error.level,
            category=error.category,
            suggestion=suggestion_info["suggestion"],
            auto_fixable=suggestion_info["auto_fixable"],
            fix_command=fix_command
        )
    
    def _load_fix_suggestions(self) -> Dict[str, Dict[str, Any]]:
        """加载修复建议数据库"""
        # 这里可以从配置文件加载，现在使用硬编码
        return {}
    
    def generate_quality_summary(self, reports: Dict[str, QualityReport]) -> Dict[str, Any]:
        """生成质量摘要统计"""
        if not reports:
            return {}
        
        total_templates = len(reports)
        quality_levels = {level: 0 for level in QualityLevel}
        
        total_score = 0.0
        total_errors = 0
        total_warnings = 0
        
        category_errors = {category: 0 for category in ValidationCategory}
        
        for report in reports.values():
            quality_levels[report.metrics.quality_level] += 1
            total_score += report.metrics.overall_score
            total_errors += report.metrics.failed_checks
            total_warnings += report.metrics.warnings
            
            # 统计各类别错误
            for error in report.validation_result.errors:
                category_errors[error.category] += 1
        
        avg_score = total_score / total_templates if total_templates > 0 else 0
        
        return {
            "total_templates": total_templates,
            "average_score": round(avg_score, 2),
            "quality_distribution": {level.value: count for level, count in quality_levels.items()},
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "errors_by_category": {category.value: count for category, count in category_errors.items()},
            "health_percentage": round((quality_levels[QualityLevel.EXCELLENT] + quality_levels[QualityLevel.GOOD]) / total_templates * 100, 2) if total_templates > 0 else 0
        }


@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='输出报告文件路径')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='输出格式')
@click.option('--detailed', '-d', is_flag=True, help='显示详细检查结果')
@click.option('--summary-only', '-s', is_flag=True, help='只显示摘要统计')
@click.option('--min-score', type=float, help='最低质量分数过滤')
def main(paths: tuple[Path, ...], output: Optional[Path], format: str, 
         detailed: bool, summary_only: bool, min_score: Optional[float]):
    """模板质量检查工具
    
    PATHS: 要检查的模板目录或模板库根目录
    """
    if not paths:
        console.print("[red]错误: 请指定要检查的目录路径[/red]")
        sys.exit(1)
    
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
                            severity_color = "red" if suggestion.severity == ValidationLevel.ERROR else "yellow"
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


if __name__ == "__main__":
    main()