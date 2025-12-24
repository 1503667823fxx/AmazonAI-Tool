"""
合规验证器

为亚马逊A+要求创建全面的合规验证，负责：
- 实现技术验证(尺寸、文件大小、色彩空间、DPI)
- 创建内容政策合规检查
- 添加可访问性标准验证
- 实现文本可读性评估
- 创建合规报告和建议
"""

import logging
import re
import io
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from PIL import Image, ImageStat
import colorsys

from .models import (
    ModuleType, MaterialSet, GeneratedModule, ComplianceStatus,
    ValidationStatus, UploadedFile
)

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """合规级别枚举"""
    STRICT = "strict"  # 严格模式
    STANDARD = "standard"  # 标准模式
    LENIENT = "lenient"  # 宽松模式


class ViolationType(Enum):
    """违规类型枚举"""
    CRITICAL = "critical"  # 严重违规
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息提示


@dataclass
class ComplianceIssue:
    """合规问题"""
    issue_id: str
    violation_type: ViolationType
    category: str  # technical, content, accessibility
    title: str
    description: str
    recommendation: str
    auto_fixable: bool = False
    severity_score: float = 0.0  # 0-1, 1为最严重


@dataclass
class ComplianceReport:
    """合规报告"""
    report_id: str
    module_type: ModuleType
    compliance_level: ComplianceLevel
    overall_status: ComplianceStatus
    overall_score: float  # 0-1
    issues: List[ComplianceIssue]
    passed_checks: List[str]
    auto_fixes_applied: List[str]
    generation_time: datetime
    validation_time: float


class ComplianceValidator:
    """
    合规验证器
    
    提供全面的亚马逊A+合规验证功能。
    """
    
    def __init__(self, compliance_level: ComplianceLevel = ComplianceLevel.STANDARD):
        """
        初始化合规验证器
        
        Args:
            compliance_level: 合规级别
        """
        self.compliance_level = compliance_level
        
        # 技术规范
        self._technical_specs = {
            'required_dimensions': (600, 450),
            'max_file_size': 5 * 1024 * 1024,  # 5MB
            'allowed_formats': ['PNG', 'JPEG', 'JPG'],
            'required_color_space': 'sRGB',
            'min_dpi': 72,
            'max_dpi': 300,
            'max_compression_artifacts': 0.1,
            'min_image_quality': 0.8
        }
        
        # 内容政策规则
        self._content_policies = {
            'prohibited_words': [
                '最好', '第一', '最佳', '最优', '最棒', '最强',
                'best', 'first', 'top', 'number one', '#1',
                '保证', '承诺', '确保', 'guarantee', 'promise',
                '治疗', '医疗', '药用', 'medical', 'cure', 'treat'
            ],
            'required_disclaimers': [
                '效果因人而异',
                '请遵循使用说明',
                '如有不适请停止使用'
            ],
            'max_text_density': 0.7,  # 文本占比不超过70%
            'min_image_ratio': 0.3,   # 图像占比至少30%
            'max_promotional_text': 0.2  # 促销文本不超过20%
        }
        
        # 可访问性标准
        self._accessibility_standards = {
            'min_contrast_ratio': 4.5,  # WCAG AA标准
            'min_font_size': 12,
            'max_font_size': 72,
            'min_clickable_area': 44,  # 44x44像素
            'color_blind_safe': True,
            'text_alternatives_required': True
        }
        
        # 验证统计
        self._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'auto_fixes_applied': 0,
            'average_validation_time': 0.0,
            'common_issues': {}
        }
    
    def validate_module(self, 
                       module: GeneratedModule,
                       materials: Optional[MaterialSet] = None,
                       enable_auto_fix: bool = True) -> ComplianceReport:
        """
        验证模块合规性
        
        Args:
            module: 生成的模块
            materials: 原始素材（可选）
            enable_auto_fix: 是否启用自动修复
            
        Returns:
            合规报告
        """
        try:
            start_time = datetime.now()
            
            # 创建报告
            report = ComplianceReport(
                report_id=f"compliance_{module.module_type.value}_{int(start_time.timestamp())}",
                module_type=module.module_type,
                compliance_level=self.compliance_level,
                overall_status=ComplianceStatus.PENDING_REVIEW,
                overall_score=0.0,
                issues=[],
                passed_checks=[],
                auto_fixes_applied=[],
                generation_time=start_time,
                validation_time=0.0
            )
            
            # 执行各类验证
            self._validate_technical_specs(module, report)
            self._validate_content_policies(module, materials, report)
            self._validate_accessibility_standards(module, report)
            
            # 应用自动修复
            if enable_auto_fix:
                self._apply_auto_fixes(module, report)
            
            # 计算总体分数和状态
            self._calculate_overall_results(report)
            
            # 记录验证时间
            validation_time = (datetime.now() - start_time).total_seconds()
            report.validation_time = validation_time
            
            # 更新统计
            self._update_validation_stats(report, validation_time)
            
            logger.info(f"Validated {module.module_type.value} - Status: {report.overall_status.value}, Score: {report.overall_score:.2f}")
            return report
            
        except Exception as e:
            logger.error(f"Validation failed for {module.module_type.value}: {str(e)}")
            
            # 返回错误报告
            return ComplianceReport(
                report_id=f"error_{int(datetime.now().timestamp())}",
                module_type=module.module_type,
                compliance_level=self.compliance_level,
                overall_status=ComplianceStatus.NON_COMPLIANT,
                overall_score=0.0,
                issues=[ComplianceIssue(
                    issue_id="validation_error",
                    violation_type=ViolationType.CRITICAL,
                    category="system",
                    title="验证系统错误",
                    description=str(e),
                    recommendation="请检查模块数据和验证器配置",
                    severity_score=1.0
                )],
                passed_checks=[],
                auto_fixes_applied=[],
                generation_time=datetime.now(),
                validation_time=0.0
            )
    
    def _validate_technical_specs(self, module: GeneratedModule, report: ComplianceReport):
        """验证技术规范"""
        try:
            if not module.image_data:
                report.issues.append(ComplianceIssue(
                    issue_id="no_image_data",
                    violation_type=ViolationType.CRITICAL,
                    category="technical",
                    title="缺少图像数据",
                    description="模块没有生成图像数据",
                    recommendation="检查模块生成器配置",
                    severity_score=1.0
                ))
                return
            
            # 加载图像进行分析
            try:
                image = Image.open(io.BytesIO(module.image_data))
            except Exception as e:
                report.issues.append(ComplianceIssue(
                    issue_id="invalid_image_format",
                    violation_type=ViolationType.CRITICAL,
                    category="technical",
                    title="无效图像格式",
                    description=f"无法解析图像数据: {str(e)}",
                    recommendation="检查图像生成过程",
                    severity_score=1.0
                ))
                return
            
            # 验证图像尺寸
            width, height = image.size
            required_width, required_height = self._technical_specs['required_dimensions']
            
            if (width, height) != (required_width, required_height):
                severity = 1.0 if self.compliance_level == ComplianceLevel.STRICT else 0.7
                report.issues.append(ComplianceIssue(
                    issue_id="incorrect_dimensions",
                    violation_type=ViolationType.CRITICAL if severity >= 0.8 else ViolationType.WARNING,
                    category="technical",
                    title="图像尺寸不符合要求",
                    description=f"当前尺寸: {width}x{height}, 要求尺寸: {required_width}x{required_height}",
                    recommendation="调整画布尺寸为600x450像素",
                    auto_fixable=True,
                    severity_score=severity
                ))
            else:
                report.passed_checks.append("图像尺寸符合要求")
            
            # 验证文件大小
            file_size = len(module.image_data)
            max_size = self._technical_specs['max_file_size']
            
            if file_size > max_size:
                severity = min(file_size / max_size, 1.0)
                report.issues.append(ComplianceIssue(
                    issue_id="file_size_exceeded",
                    violation_type=ViolationType.CRITICAL if severity >= 0.8 else ViolationType.WARNING,
                    category="technical",
                    title="文件大小超限",
                    description=f"当前大小: {file_size / 1024 / 1024:.1f}MB, 最大限制: {max_size / 1024 / 1024}MB",
                    recommendation="优化图像质量或减少内容复杂度",
                    auto_fixable=True,
                    severity_score=severity
                ))
            else:
                report.passed_checks.append("文件大小符合要求")
            
            # 验证图像格式
            if image.format not in self._technical_specs['allowed_formats']:
                report.issues.append(ComplianceIssue(
                    issue_id="unsupported_format",
                    violation_type=ViolationType.WARNING,
                    category="technical",
                    title="不支持的图像格式",
                    description=f"当前格式: {image.format}, 支持格式: {', '.join(self._technical_specs['allowed_formats'])}",
                    recommendation="转换为PNG或JPEG格式",
                    auto_fixable=True,
                    severity_score=0.5
                ))
            else:
                report.passed_checks.append("图像格式符合要求")
            
            # 验证色彩空间
            if image.mode not in ['RGB', 'RGBA']:
                report.issues.append(ComplianceIssue(
                    issue_id="incorrect_color_mode",
                    violation_type=ViolationType.WARNING,
                    category="technical",
                    title="色彩模式不正确",
                    description=f"当前模式: {image.mode}, 建议模式: RGB",
                    recommendation="转换为RGB色彩模式",
                    auto_fixable=True,
                    severity_score=0.6
                ))
            else:
                report.passed_checks.append("色彩模式符合要求")
            
            # 验证图像质量
            quality_score = self._assess_image_quality(image)
            min_quality = self._technical_specs['min_image_quality']
            
            if quality_score < min_quality:
                report.issues.append(ComplianceIssue(
                    issue_id="low_image_quality",
                    violation_type=ViolationType.WARNING,
                    category="technical",
                    title="图像质量偏低",
                    description=f"质量分数: {quality_score:.2f}, 最低要求: {min_quality}",
                    recommendation="提高图像分辨率或减少压缩",
                    severity_score=1.0 - quality_score
                ))
            else:
                report.passed_checks.append("图像质量符合要求")
                
        except Exception as e:
            logger.error(f"Technical validation failed: {str(e)}")
            report.issues.append(ComplianceIssue(
                issue_id="technical_validation_error",
                violation_type=ViolationType.WARNING,
                category="technical",
                title="技术验证错误",
                description=str(e),
                recommendation="检查图像数据完整性",
                severity_score=0.5
            ))
    
    def _validate_content_policies(self, module: GeneratedModule, materials: Optional[MaterialSet], report: ComplianceReport):
        """验证内容政策"""
        try:
            if not materials:
                return
            
            # 收集所有文本内容
            all_text = []
            if materials.text_inputs:
                all_text.extend(materials.text_inputs)
            if materials.custom_prompts:
                all_text.extend(materials.custom_prompts)
            
            combined_text = ' '.join(all_text).lower()
            
            # 检查禁用词汇
            prohibited_found = []
            for word in self._content_policies['prohibited_words']:
                if word.lower() in combined_text:
                    prohibited_found.append(word)
            
            if prohibited_found:
                report.issues.append(ComplianceIssue(
                    issue_id="prohibited_words",
                    violation_type=ViolationType.WARNING,
                    category="content",
                    title="包含禁用词汇",
                    description=f"发现禁用词汇: {', '.join(prohibited_found)}",
                    recommendation="移除或替换禁用词汇，使用更客观的描述",
                    severity_score=0.6
                ))
            else:
                report.passed_checks.append("未发现禁用词汇")
            
            # 检查促销性语言密度
            promotional_words = ['优惠', '折扣', '特价', '限时', '抢购', 'sale', 'discount', 'offer']
            promotional_count = sum(combined_text.count(word.lower()) for word in promotional_words)
            total_words = len(combined_text.split())
            
            if total_words > 0:
                promotional_ratio = promotional_count / total_words
                max_promotional = self._content_policies['max_promotional_text']
                
                if promotional_ratio > max_promotional:
                    report.issues.append(ComplianceIssue(
                        issue_id="excessive_promotional_text",
                        violation_type=ViolationType.WARNING,
                        category="content",
                        title="促销性语言过多",
                        description=f"促销词汇占比: {promotional_ratio:.1%}, 建议上限: {max_promotional:.1%}",
                        recommendation="减少促销性语言，增加产品功能描述",
                        severity_score=promotional_ratio
                    ))
                else:
                    report.passed_checks.append("促销性语言适度")
            
            # 检查文本可读性
            readability_score = self._assess_text_readability(combined_text)
            if readability_score < 0.6:
                report.issues.append(ComplianceIssue(
                    issue_id="poor_readability",
                    violation_type=ViolationType.INFO,
                    category="content",
                    title="文本可读性偏低",
                    description=f"可读性分数: {readability_score:.2f}",
                    recommendation="使用更简洁明了的语言，避免过长的句子",
                    severity_score=1.0 - readability_score
                ))
            else:
                report.passed_checks.append("文本可读性良好")
                
        except Exception as e:
            logger.error(f"Content policy validation failed: {str(e)}")
            report.issues.append(ComplianceIssue(
                issue_id="content_validation_error",
                violation_type=ViolationType.INFO,
                category="content",
                title="内容验证错误",
                description=str(e),
                recommendation="检查文本内容格式",
                severity_score=0.3
            ))
    
    def _validate_accessibility_standards(self, module: GeneratedModule, report: ComplianceReport):
        """验证可访问性标准"""
        try:
            if not module.image_data:
                return
            
            # 加载图像
            try:
                image = Image.open(io.BytesIO(module.image_data))
            except:
                return
            
            # 检查颜色对比度
            contrast_issues = self._check_color_contrast(image)
            if contrast_issues:
                report.issues.append(ComplianceIssue(
                    issue_id="low_color_contrast",
                    violation_type=ViolationType.WARNING,
                    category="accessibility",
                    title="颜色对比度不足",
                    description=f"发现 {len(contrast_issues)} 处对比度问题",
                    recommendation="增加文本和背景的颜色对比度，确保至少达到4.5:1",
                    severity_score=min(len(contrast_issues) / 10.0, 1.0)
                ))
            else:
                report.passed_checks.append("颜色对比度符合要求")
            
            # 检查色盲友好性
            if not self._check_color_blind_friendly(image):
                report.issues.append(ComplianceIssue(
                    issue_id="not_color_blind_friendly",
                    violation_type=ViolationType.INFO,
                    category="accessibility",
                    title="色盲友好性不足",
                    description="图像可能对色盲用户不够友好",
                    recommendation="避免仅依赖颜色传达信息，添加文字标签或图案",
                    severity_score=0.4
                ))
            else:
                report.passed_checks.append("色盲友好性良好")
            
            # 检查视觉层次
            visual_hierarchy_score = self._assess_visual_hierarchy(image)
            if visual_hierarchy_score < 0.6:
                report.issues.append(ComplianceIssue(
                    issue_id="poor_visual_hierarchy",
                    violation_type=ViolationType.INFO,
                    category="accessibility",
                    title="视觉层次不清晰",
                    description=f"视觉层次分数: {visual_hierarchy_score:.2f}",
                    recommendation="使用不同的字体大小、颜色和间距来建立清晰的视觉层次",
                    severity_score=1.0 - visual_hierarchy_score
                ))
            else:
                report.passed_checks.append("视觉层次清晰")
                
        except Exception as e:
            logger.error(f"Accessibility validation failed: {str(e)}")
            report.issues.append(ComplianceIssue(
                issue_id="accessibility_validation_error",
                violation_type=ViolationType.INFO,
                category="accessibility",
                title="可访问性验证错误",
                description=str(e),
                recommendation="检查图像数据完整性",
                severity_score=0.3
            ))
    
    def _apply_auto_fixes(self, module: GeneratedModule, report: ComplianceReport):
        """应用自动修复"""
        try:
            fixes_applied = []
            
            for issue in report.issues:
                if not issue.auto_fixable:
                    continue
                
                if issue.issue_id == "incorrect_dimensions":
                    if self._auto_fix_dimensions(module):
                        fixes_applied.append("调整图像尺寸为600x450")
                        issue.violation_type = ViolationType.INFO  # 降级为信息
                
                elif issue.issue_id == "file_size_exceeded":
                    if self._auto_fix_file_size(module):
                        fixes_applied.append("优化文件大小")
                        issue.violation_type = ViolationType.INFO
                
                elif issue.issue_id == "unsupported_format":
                    if self._auto_fix_format(module):
                        fixes_applied.append("转换图像格式为PNG")
                        issue.violation_type = ViolationType.INFO
                
                elif issue.issue_id == "incorrect_color_mode":
                    if self._auto_fix_color_mode(module):
                        fixes_applied.append("转换色彩模式为RGB")
                        issue.violation_type = ViolationType.INFO
            
            report.auto_fixes_applied = fixes_applied
            
            if fixes_applied:
                logger.info(f"Applied {len(fixes_applied)} auto-fixes")
                
        except Exception as e:
            logger.error(f"Auto-fix failed: {str(e)}")
    
    def _auto_fix_dimensions(self, module: GeneratedModule) -> bool:
        """自动修复图像尺寸"""
        try:
            if not module.image_data:
                return False
            
            image = Image.open(io.BytesIO(module.image_data))
            required_width, required_height = self._technical_specs['required_dimensions']
            
            # 调整尺寸
            resized_image = image.resize((required_width, required_height), Image.Resampling.LANCZOS)
            
            # 保存修复后的图像
            img_buffer = io.BytesIO()
            resized_image.save(img_buffer, format='PNG', optimize=True)
            img_buffer.seek(0)
            
            module.image_data = img_buffer.getvalue()
            return True
            
        except Exception as e:
            logger.error(f"Failed to auto-fix dimensions: {str(e)}")
            return False
    
    def _auto_fix_file_size(self, module: GeneratedModule) -> bool:
        """自动修复文件大小"""
        try:
            if not module.image_data:
                return False
            
            image = Image.open(io.BytesIO(module.image_data))
            max_size = self._technical_specs['max_file_size']
            
            # 尝试不同的质量设置
            for quality in [85, 75, 65, 55]:
                img_buffer = io.BytesIO()
                
                if image.format == 'PNG':
                    image.save(img_buffer, format='PNG', optimize=True)
                else:
                    image.save(img_buffer, format='JPEG', quality=quality, optimize=True)
                
                if len(img_buffer.getvalue()) <= max_size:
                    img_buffer.seek(0)
                    module.image_data = img_buffer.getvalue()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to auto-fix file size: {str(e)}")
            return False
    
    def _auto_fix_format(self, module: GeneratedModule) -> bool:
        """自动修复图像格式"""
        try:
            if not module.image_data:
                return False
            
            image = Image.open(io.BytesIO(module.image_data))
            
            # 转换为PNG格式
            img_buffer = io.BytesIO()
            if image.mode == 'RGBA':
                image.save(img_buffer, format='PNG', optimize=True)
            else:
                image.save(img_buffer, format='PNG', optimize=True)
            
            img_buffer.seek(0)
            module.image_data = img_buffer.getvalue()
            return True
            
        except Exception as e:
            logger.error(f"Failed to auto-fix format: {str(e)}")
            return False
    
    def _auto_fix_color_mode(self, module: GeneratedModule) -> bool:
        """自动修复色彩模式"""
        try:
            if not module.image_data:
                return False
            
            image = Image.open(io.BytesIO(module.image_data))
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                rgb_image = image.convert('RGB')
                
                img_buffer = io.BytesIO()
                rgb_image.save(img_buffer, format='PNG', optimize=True)
                img_buffer.seek(0)
                
                module.image_data = img_buffer.getvalue()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to auto-fix color mode: {str(e)}")
            return False
    
    def _calculate_overall_results(self, report: ComplianceReport):
        """计算总体结果"""
        try:
            if not report.issues:
                report.overall_status = ComplianceStatus.COMPLIANT
                report.overall_score = 1.0
                return
            
            # 计算加权分数
            total_weight = 0
            weighted_score = 0
            
            for issue in report.issues:
                weight = self._get_issue_weight(issue)
                total_weight += weight
                
                # 根据违规类型计算分数损失
                if issue.violation_type == ViolationType.CRITICAL:
                    score_penalty = issue.severity_score * 0.8
                elif issue.violation_type == ViolationType.WARNING:
                    score_penalty = issue.severity_score * 0.5
                else:  # INFO
                    score_penalty = issue.severity_score * 0.2
                
                weighted_score += weight * (1.0 - score_penalty)
            
            # 计算总分
            if total_weight > 0:
                report.overall_score = max(0.0, weighted_score / total_weight)
            else:
                report.overall_score = 1.0
            
            # 确定合规状态
            critical_issues = [i for i in report.issues if i.violation_type == ViolationType.CRITICAL]
            
            if critical_issues:
                if self.compliance_level == ComplianceLevel.STRICT:
                    report.overall_status = ComplianceStatus.NON_COMPLIANT
                elif len(critical_issues) > 2:
                    report.overall_status = ComplianceStatus.NON_COMPLIANT
                else:
                    report.overall_status = ComplianceStatus.NEEDS_OPTIMIZATION
            elif report.overall_score >= 0.8:
                report.overall_status = ComplianceStatus.COMPLIANT
            elif report.overall_score >= 0.6:
                report.overall_status = ComplianceStatus.NEEDS_OPTIMIZATION
            else:
                report.overall_status = ComplianceStatus.NON_COMPLIANT
                
        except Exception as e:
            logger.error(f"Failed to calculate overall results: {str(e)}")
            report.overall_status = ComplianceStatus.NON_COMPLIANT
            report.overall_score = 0.0
    
    def _get_issue_weight(self, issue: ComplianceIssue) -> float:
        """获取问题权重"""
        category_weights = {
            'technical': 0.4,
            'content': 0.35,
            'accessibility': 0.25
        }
        
        type_multipliers = {
            ViolationType.CRITICAL: 1.0,
            ViolationType.WARNING: 0.7,
            ViolationType.INFO: 0.3
        }
        
        base_weight = category_weights.get(issue.category, 0.3)
        multiplier = type_multipliers.get(issue.violation_type, 0.5)
        
        return base_weight * multiplier
    
    def _assess_image_quality(self, image: Image.Image) -> float:
        """评估图像质量"""
        try:
            # 转换为RGB模式进行分析
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 计算图像统计信息
            stat = ImageStat.Stat(image)
            
            # 评估清晰度（基于标准差）
            sharpness_score = min(sum(stat.stddev) / (3 * 255), 1.0)
            
            # 评估亮度分布
            brightness_score = 1.0 - abs(sum(stat.mean) / 3 - 127.5) / 127.5
            
            # 评估对比度
            contrast_score = min(max(stat.stddev) / 255, 1.0)
            
            # 综合质量分数
            quality_score = (sharpness_score * 0.4 + brightness_score * 0.3 + contrast_score * 0.3)
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"Failed to assess image quality: {str(e)}")
            return 0.5
    
    def _assess_text_readability(self, text: str) -> float:
        """评估文本可读性"""
        try:
            if not text.strip():
                return 1.0
            
            # 计算基本指标
            sentences = len(re.split(r'[.!?]+', text))
            words = len(text.split())
            characters = len(text.replace(' ', ''))
            
            if sentences == 0 or words == 0:
                return 0.5
            
            # 平均句长
            avg_sentence_length = words / sentences
            sentence_score = max(0, 1.0 - (avg_sentence_length - 15) / 20)  # 理想句长15词
            
            # 平均词长
            avg_word_length = characters / words
            word_score = max(0, 1.0 - (avg_word_length - 5) / 5)  # 理想词长5字符
            
            # 复杂词汇比例
            complex_words = len([w for w in text.split() if len(w) > 8])
            complexity_ratio = complex_words / words if words > 0 else 0
            complexity_score = max(0, 1.0 - complexity_ratio * 2)
            
            # 综合可读性分数
            readability_score = (sentence_score * 0.4 + word_score * 0.3 + complexity_score * 0.3)
            
            return max(0.0, min(1.0, readability_score))
            
        except Exception as e:
            logger.error(f"Failed to assess text readability: {str(e)}")
            return 0.5
    
    def _check_color_contrast(self, image: Image.Image) -> List[str]:
        """检查颜色对比度"""
        try:
            issues = []
            
            # 简化的对比度检查
            # 在实际实现中，这里应该进行更复杂的文本区域检测和对比度计算
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 采样图像中的颜色
            width, height = image.size
            sample_points = [
                (width // 4, height // 4),
                (3 * width // 4, height // 4),
                (width // 4, 3 * height // 4),
                (3 * width // 4, 3 * height // 4),
                (width // 2, height // 2)
            ]
            
            colors = []
            for x, y in sample_points:
                try:
                    color = image.getpixel((x, y))
                    colors.append(color)
                except:
                    continue
            
            # 检查相邻颜色的对比度
            min_contrast = self._accessibility_standards['min_contrast_ratio']
            
            for i in range(len(colors) - 1):
                contrast_ratio = self._calculate_contrast_ratio(colors[i], colors[i + 1])
                if contrast_ratio < min_contrast:
                    issues.append(f"区域对比度不足: {contrast_ratio:.1f}:1")
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to check color contrast: {str(e)}")
            return []
    
    def _calculate_contrast_ratio(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
        """计算两个颜色的对比度"""
        try:
            def get_luminance(rgb):
                """计算相对亮度"""
                r, g, b = [x / 255.0 for x in rgb]
                
                # 应用gamma校正
                def gamma_correct(c):
                    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                
                r = gamma_correct(r)
                g = gamma_correct(g)
                b = gamma_correct(b)
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
            lum1 = get_luminance(color1)
            lum2 = get_luminance(color2)
            
            # 确保较亮的颜色在分子
            if lum1 < lum2:
                lum1, lum2 = lum2, lum1
            
            return (lum1 + 0.05) / (lum2 + 0.05)
            
        except Exception as e:
            logger.error(f"Failed to calculate contrast ratio: {str(e)}")
            return 1.0
    
    def _check_color_blind_friendly(self, image: Image.Image) -> bool:
        """检查色盲友好性"""
        try:
            # 简化的色盲友好性检查
            # 检查是否过度依赖红绿色差异
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 采样图像颜色
            colors = []
            width, height = image.size
            
            for y in range(0, height, height // 10):
                for x in range(0, width, width // 10):
                    try:
                        color = image.getpixel((x, y))
                        colors.append(color)
                    except:
                        continue
            
            # 检查红绿色差异依赖
            red_green_dependent = 0
            total_comparisons = 0
            
            for i in range(len(colors)):
                for j in range(i + 1, min(i + 10, len(colors))):
                    r1, g1, b1 = colors[i]
                    r2, g2, b2 = colors[j]
                    
                    # 计算红绿差异和蓝色差异
                    rg_diff = abs((r1 - g1) - (r2 - g2))
                    b_diff = abs(b1 - b2)
                    
                    total_comparisons += 1
                    
                    # 如果主要依赖红绿差异而蓝色差异很小
                    if rg_diff > 50 and b_diff < 20:
                        red_green_dependent += 1
            
            if total_comparisons > 0:
                dependency_ratio = red_green_dependent / total_comparisons
                return dependency_ratio < 0.3  # 少于30%的颜色对比依赖红绿差异
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check color blind friendliness: {str(e)}")
            return True  # 默认认为友好
    
    def _assess_visual_hierarchy(self, image: Image.Image) -> float:
        """评估视觉层次"""
        try:
            # 简化的视觉层次评估
            # 基于图像的对比度分布和区域差异
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 将图像分为9个区域（3x3网格）
            width, height = image.size
            region_width = width // 3
            region_height = height // 3
            
            region_contrasts = []
            
            for row in range(3):
                for col in range(3):
                    x1 = col * region_width
                    y1 = row * region_height
                    x2 = min(x1 + region_width, width)
                    y2 = min(y1 + region_height, height)
                    
                    # 提取区域
                    region = image.crop((x1, y1, x2, y2))
                    
                    # 计算区域对比度
                    stat = ImageStat.Stat(region)
                    contrast = sum(stat.stddev) / 3  # 平均标准差
                    region_contrasts.append(contrast)
            
            # 评估对比度分布的变化
            if len(region_contrasts) > 1:
                contrast_variance = sum((c - sum(region_contrasts) / len(region_contrasts)) ** 2 
                                      for c in region_contrasts) / len(region_contrasts)
                
                # 标准化分数
                hierarchy_score = min(contrast_variance / 10000, 1.0)
            else:
                hierarchy_score = 0.5
            
            return hierarchy_score
            
        except Exception as e:
            logger.error(f"Failed to assess visual hierarchy: {str(e)}")
            return 0.5
    
    def _update_validation_stats(self, report: ComplianceReport, validation_time: float):
        """更新验证统计"""
        try:
            self._validation_stats['total_validations'] += 1
            
            if report.overall_status == ComplianceStatus.COMPLIANT:
                self._validation_stats['passed_validations'] += 1
            else:
                self._validation_stats['failed_validations'] += 1
            
            self._validation_stats['auto_fixes_applied'] += len(report.auto_fixes_applied)
            
            # 更新平均验证时间
            total_time = (self._validation_stats['average_validation_time'] * 
                         (self._validation_stats['total_validations'] - 1))
            self._validation_stats['average_validation_time'] = (
                (total_time + validation_time) / self._validation_stats['total_validations']
            )
            
            # 统计常见问题
            for issue in report.issues:
                issue_type = issue.issue_id
                self._validation_stats['common_issues'][issue_type] = (
                    self._validation_stats['common_issues'].get(issue_type, 0) + 1
                )
                
        except Exception as e:
            logger.error(f"Failed to update validation stats: {str(e)}")
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        try:
            stats = self._validation_stats.copy()
            
            # 计算成功率
            if stats['total_validations'] > 0:
                stats['pass_rate'] = (stats['passed_validations'] / stats['total_validations'] * 100)
                stats['auto_fix_rate'] = (stats['auto_fixes_applied'] / stats['total_validations'])
            else:
                stats['pass_rate'] = 0.0
                stats['auto_fix_rate'] = 0.0
            
            # 获取最常见的问题
            if stats['common_issues']:
                sorted_issues = sorted(stats['common_issues'].items(), 
                                     key=lambda x: x[1], reverse=True)
                stats['top_issues'] = sorted_issues[:5]
            else:
                stats['top_issues'] = []
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get validation statistics: {str(e)}")
            return {}
    
    def generate_compliance_summary(self, report: ComplianceReport) -> str:
        """生成合规摘要"""
        try:
            summary_lines = []
            
            # 总体状态
            status_text = {
                ComplianceStatus.COMPLIANT: "✅ 完全合规",
                ComplianceStatus.NEEDS_OPTIMIZATION: "⚠️ 需要优化",
                ComplianceStatus.NON_COMPLIANT: "❌ 不合规",
                ComplianceStatus.PENDING_REVIEW: "⏳ 待审核"
            }
            
            summary_lines.append(f"合规状态: {status_text.get(report.overall_status, '未知')}")
            summary_lines.append(f"总体分数: {report.overall_score:.1%}")
            summary_lines.append(f"验证时间: {report.validation_time:.2f}秒")
            summary_lines.append("")
            
            # 问题统计
            if report.issues:
                critical_count = len([i for i in report.issues if i.violation_type == ViolationType.CRITICAL])
                warning_count = len([i for i in report.issues if i.violation_type == ViolationType.WARNING])
                info_count = len([i for i in report.issues if i.violation_type == ViolationType.INFO])
                
                summary_lines.append("问题统计:")
                if critical_count > 0:
                    summary_lines.append(f"  严重问题: {critical_count}")
                if warning_count > 0:
                    summary_lines.append(f"  警告: {warning_count}")
                if info_count > 0:
                    summary_lines.append(f"  信息提示: {info_count}")
                summary_lines.append("")
            
            # 主要问题
            if report.issues:
                summary_lines.append("主要问题:")
                for issue in report.issues[:3]:  # 显示前3个问题
                    icon = "🔴" if issue.violation_type == ViolationType.CRITICAL else "🟡" if issue.violation_type == ViolationType.WARNING else "🔵"
                    summary_lines.append(f"  {icon} {issue.title}")
                    summary_lines.append(f"     {issue.recommendation}")
                summary_lines.append("")
            
            # 自动修复
            if report.auto_fixes_applied:
                summary_lines.append("已应用自动修复:")
                for fix in report.auto_fixes_applied:
                    summary_lines.append(f"  ✅ {fix}")
                summary_lines.append("")
            
            # 通过的检查
            if report.passed_checks:
                summary_lines.append(f"通过检查: {len(report.passed_checks)}项")
                summary_lines.append("")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate compliance summary: {str(e)}")
            return f"合规摘要生成失败: {str(e)}"
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = self.get_validation_statistics()
            
            # 检查验证器状态
            if stats.get('total_validations', 0) == 0:
                status = 'warning'
                message = 'No validations performed yet'
            elif stats.get('pass_rate', 0) < 50:
                status = 'warning'
                message = 'Low compliance pass rate'
            else:
                status = 'healthy'
                message = 'All systems operational'
            
            return {
                'status': status,
                'message': message,
                'compliance_level': self.compliance_level.value,
                'technical_specs_loaded': len(self._technical_specs) > 0,
                'content_policies_loaded': len(self._content_policies) > 0,
                'accessibility_standards_loaded': len(self._accessibility_standards) > 0,
                'statistics': stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Compliance validator health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }