"""
亚马逊内容合规检查服务

专门用于检查A+页面内容是否符合亚马逊内容政策的服务，包括：
- 禁用词汇检测（主观词、比较词、医疗词等）
- 内容扫描和违规检测
- 合规替代建议系统
- 自动内容修正功能
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceIssueType(Enum):
    """合规问题类型"""
    SUBJECTIVE = "subjective"  # 主观性词汇
    COMPARATIVE = "comparative"  # 比较性声明
    MEDICAL = "medical"  # 医疗声明
    TIME_SENSITIVE = "time_sensitive"  # 时间敏感表述
    ABSOLUTE = "absolute"  # 绝对性声明
    PROMOTIONAL = "promotional"  # 过度促销


class ComplianceSeverity(Enum):
    """合规严重程度"""
    HIGH = "high"  # 高风险，必须修复
    MEDIUM = "medium"  # 中等风险，建议修复
    LOW = "low"  # 低风险，可选修复


@dataclass
class ComplianceIssue:
    """合规问题"""
    issue_type: ComplianceIssueType
    flagged_text: str
    position: Tuple[int, int]  # 开始和结束位置
    severity: ComplianceSeverity
    explanation: str
    suggested_alternatives: List[str]
    context: str = ""  # 上下文


@dataclass
class ComplianceResult:
    """合规检查结果"""
    is_compliant: bool
    flagged_issues: List[ComplianceIssue]
    suggested_fixes: Dict[str, List[str]]
    compliance_score: float  # 0-1分数
    check_timestamp: datetime
    original_text: str
    corrected_text: Optional[str] = None


class AmazonComplianceService:
    """
    亚马逊内容合规检查服务
    
    专门检查A+页面内容是否符合亚马逊内容政策。
    """
    
    def __init__(self):
        """初始化合规检查服务"""
        self.prohibited_words = self._load_prohibited_words()
        self.replacement_suggestions = self._load_replacement_suggestions()
        self.pattern_rules = self._compile_pattern_rules()
        
        # 统计信息
        self.check_stats = {
            'total_checks': 0,
            'compliant_checks': 0,
            'auto_fixes_applied': 0,
            'common_violations': {}
        }
    
    def _load_prohibited_words(self) -> Dict[str, List[str]]:
        """加载禁用词汇库"""
        return {
            "subjective": [
                # 中文主观词汇
                "最好的", "完美的", "神奇的", "最佳", "顶级", "无与伦比", "绝佳", "超棒",
                "极品", "顶尖", "一流", "卓越", "杰出", "优秀", "出色", "精彩", "惊人",
                "令人惊叹", "不可思议", "史上最好", "世界级", "传奇", "经典", "完美无缺",
                
                # 英文主观词汇
                "best", "perfect", "amazing", "incredible", "awesome", "fantastic",
                "excellent", "outstanding", "superior", "premium", "top-rated",
                "world-class", "legendary", "classic", "flawless", "unbeatable",
                "unmatched", "unparalleled", "extraordinary", "remarkable", "stunning"
            ],
            
            "comparative": [
                # 中文比较词汇
                "比其他更好", "市场领先", "第一名", "最便宜", "性价比最高", "独一无二",
                "领先同行", "超越竞品", "行业第一", "市场第一", "销量第一", "品质第一",
                "唯一", "独家", "专利", "首创", "原创", "独有",
                
                # 英文比较词汇
                "better than others", "market leading", "number one", "#1", "cheapest",
                "best value", "unique", "only", "exclusive", "patented", "first",
                "original", "one and only", "unrivaled", "industry leading"
            ],
            
            "medical": [
                # 中文医疗词汇
                "治疗", "治愈", "医疗级", "药用", "疗效", "康复", "痊愈", "根治",
                "诊断", "处方", "临床", "病理", "症状", "疾病", "健康", "保健",
                "养生", "调理", "滋补", "补肾", "壮阳", "减肥", "瘦身", "美白",
                "抗衰老", "延缓衰老", "抗氧化", "排毒", "解毒", "消炎", "杀菌",
                
                # 英文医疗词汇
                "cure", "treat", "medical grade", "therapeutic", "healing", "recovery",
                "diagnosis", "prescription", "clinical", "pathology", "symptom",
                "disease", "health", "healthcare", "wellness", "anti-aging",
                "detox", "antibacterial", "antimicrobial", "medicinal"
            ],
            
            "time_sensitive": [
                # 中文时间敏感词汇
                "新品", "限时", "即将下架", "最新款", "刚上市", "热销", "抢购",
                "限量", "售完即止", "今日特价", "本周特惠", "月底清仓", "年终大促",
                "现在购买", "立即下单", "马上抢购", "趁现在", "机不可失",
                
                # 英文时间敏感词汇
                "new", "limited time", "going out of stock", "latest", "just launched",
                "hot selling", "grab now", "limited quantity", "while supplies last",
                "today only", "this week only", "clearance", "buy now", "order now",
                "act fast", "don't miss out", "hurry", "urgent"
            ],
            
            "absolute": [
                # 中文绝对词汇
                "100%", "完全", "绝对", "永远", "从不", "所有", "全部", "任何",
                "每个", "总是", "必须", "一定", "肯定", "保证", "确保", "承诺",
                "无条件", "无限制", "无风险", "零风险", "万无一失", "百分百",
                
                # 英文绝对词汇
                "100%", "completely", "absolutely", "always", "never", "all",
                "every", "must", "guaranteed", "ensure", "promise", "unconditional",
                "unlimited", "risk-free", "zero risk", "foolproof", "certain"
            ]
        }
    
    def _load_replacement_suggestions(self) -> Dict[str, List[str]]:
        """加载替代建议"""
        return {
            # 主观词汇替代
            "最好的": ["高品质的", "优质的", "精心设计的", "专业级的"],
            "完美的": ["精心制作的", "设计精良的", "工艺精湛的", "品质优良的"],
            "神奇的": ["有效的", "实用的", "功能强大的", "性能出色的"],
            "最佳": ["优质", "高品质", "专业级", "精选"],
            "顶级": ["高端", "专业级", "优质", "精品"],
            
            "best": ["high-quality", "premium", "professional-grade", "well-designed"],
            "perfect": ["well-crafted", "carefully designed", "expertly made", "quality"],
            "amazing": ["effective", "functional", "high-performance", "reliable"],
            "incredible": ["impressive", "notable", "remarkable", "substantial"],
            "awesome": ["excellent", "outstanding", "impressive", "notable"],
            
            # 比较词汇替代
            "比其他更好": ["具有优势", "性能出色", "品质优良", "功能丰富"],
            "市场领先": ["行业认可", "广受好评", "用户信赖", "专业推荐"],
            "第一名": ["领先品牌", "知名品牌", "受欢迎的", "广受认可的"],
            "最便宜": ["价格实惠", "性价比高", "经济实用", "物超所值"],
            
            "better than others": ["offers advantages", "high-performing", "well-regarded"],
            "market leading": ["industry-recognized", "well-reviewed", "trusted"],
            "number one": ["leading brand", "popular choice", "well-known"],
            "cheapest": ["affordable", "good value", "economical", "budget-friendly"],
            
            # 医疗词汇替代
            "治疗": ["护理", "保养", "维护", "改善"],
            "治愈": ["缓解", "改善", "帮助", "支持"],
            "医疗级": ["专业级", "高标准", "精密", "优质"],
            "疗效": ["效果", "作用", "功能", "性能"],
            
            "cure": ["help", "support", "maintain", "care for"],
            "treat": ["care for", "maintain", "support", "help with"],
            "medical grade": ["professional grade", "high standard", "precision", "quality"],
            "therapeutic": ["beneficial", "helpful", "supportive", "wellness"],
            
            # 时间敏感词汇替代
            "新品": ["产品", "商品", "款式", "型号"],
            "限时": ["特惠", "优惠", "促销", "活动"],
            "最新款": ["当前款", "现有款", "这款", "该款"],
            "热销": ["受欢迎的", "广受好评的", "用户喜爱的", "推荐的"],
            
            "new": ["current", "available", "featured", "this"],
            "limited time": ["special offer", "promotion", "deal", "sale"],
            "latest": ["current", "available", "featured", "this model"],
            "hot selling": ["popular", "well-reviewed", "customer favorite", "recommended"],
            
            # 绝对词汇替代
            "100%": ["高度", "显著", "大幅", "明显"],
            "完全": ["高度", "充分", "全面", "深度"],
            "绝对": ["高度", "显著", "明显", "充分"],
            "永远": ["长期", "持续", "稳定", "可靠"],
            "保证": ["致力于", "努力", "旨在", "设计用于"],
            
            "100%": ["highly", "significantly", "substantially", "notably"],
            "completely": ["highly", "thoroughly", "extensively", "substantially"],
            "absolutely": ["highly", "significantly", "notably", "substantially"],
            "always": ["typically", "generally", "usually", "consistently"],
            "guaranteed": ["designed to", "intended to", "aims to", "works to"]
        }
    
    def _compile_pattern_rules(self) -> Dict[str, List[re.Pattern]]:
        """编译正则表达式规则"""
        patterns = {}
        
        # 编译各类词汇的正则表达式
        for category, words in self.prohibited_words.items():
            patterns[category] = []
            for word in words:
                # 创建不区分大小写的正则表达式
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                patterns[category].append(pattern)
        
        # 添加特殊模式规则
        patterns['promotional'] = [
            re.compile(r'限时.*?优惠', re.IGNORECASE),
            re.compile(r'立即.*?购买', re.IGNORECASE),
            re.compile(r'马上.*?下单', re.IGNORECASE),
            re.compile(r'buy.*?now', re.IGNORECASE),
            re.compile(r'order.*?today', re.IGNORECASE),
            re.compile(r'limited.*?offer', re.IGNORECASE)
        ]
        
        return patterns
    
    def check_content_compliance(self, content: str) -> ComplianceResult:
        """
        检查内容合规性
        
        Args:
            content: 要检查的文本内容
            
        Returns:
            合规检查结果
        """
        try:
            start_time = datetime.now()
            issues = []
            
            # 检查各类违规内容
            issues.extend(self._check_subjective_words(content))
            issues.extend(self._check_comparative_claims(content))
            issues.extend(self._check_medical_claims(content))
            issues.extend(self._check_time_sensitive_terms(content))
            issues.extend(self._check_absolute_claims(content))
            issues.extend(self._check_promotional_language(content))
            
            # 计算合规分数
            compliance_score = self._calculate_compliance_score(content, issues)
            
            # 生成修复建议
            suggested_fixes = self._generate_fix_suggestions(issues)
            
            # 创建结果
            result = ComplianceResult(
                is_compliant=len(issues) == 0,
                flagged_issues=issues,
                suggested_fixes=suggested_fixes,
                compliance_score=compliance_score,
                check_timestamp=start_time,
                original_text=content
            )
            
            # 更新统计
            self._update_stats(result)
            
            logger.info(f"Compliance check completed - Score: {compliance_score:.2f}, Issues: {len(issues)}")
            return result
            
        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            return ComplianceResult(
                is_compliant=False,
                flagged_issues=[],
                suggested_fixes={},
                compliance_score=0.0,
                check_timestamp=datetime.now(),
                original_text=content
            )
    
    def _check_subjective_words(self, content: str) -> List[ComplianceIssue]:
        """检查主观性词汇"""
        issues = []
        
        for pattern in self.pattern_rules.get('subjective', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.SUBJECTIVE,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.HIGH,
                    explanation=f"'{flagged_text}' 是主观性词汇，可能违反亚马逊内容政策",
                    suggested_alternatives=alternatives,
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _check_comparative_claims(self, content: str) -> List[ComplianceIssue]:
        """检查比较性声明"""
        issues = []
        
        for pattern in self.pattern_rules.get('comparative', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.COMPARATIVE,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.HIGH,
                    explanation=f"'{flagged_text}' 是比较性声明，需要客观数据支持",
                    suggested_alternatives=alternatives,
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _check_medical_claims(self, content: str) -> List[ComplianceIssue]:
        """检查医疗声明"""
        issues = []
        
        for pattern in self.pattern_rules.get('medical', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.MEDICAL,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.HIGH,
                    explanation=f"'{flagged_text}' 涉及医疗声明，严禁在A+页面使用",
                    suggested_alternatives=alternatives,
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _check_time_sensitive_terms(self, content: str) -> List[ComplianceIssue]:
        """检查时间敏感表述"""
        issues = []
        
        for pattern in self.pattern_rules.get('time_sensitive', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.TIME_SENSITIVE,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.MEDIUM,
                    explanation=f"'{flagged_text}' 是时间敏感表述，不适用于A+页面",
                    suggested_alternatives=alternatives,
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _check_absolute_claims(self, content: str) -> List[ComplianceIssue]:
        """检查绝对性声明"""
        issues = []
        
        for pattern in self.pattern_rules.get('absolute', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.ABSOLUTE,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.MEDIUM,
                    explanation=f"'{flagged_text}' 是绝对性声明，建议使用更客观的表述",
                    suggested_alternatives=alternatives,
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _check_promotional_language(self, content: str) -> List[ComplianceIssue]:
        """检查过度促销语言"""
        issues = []
        
        for pattern in self.pattern_rules.get('promotional', []):
            for match in pattern.finditer(content):
                flagged_text = match.group()
                
                issue = ComplianceIssue(
                    issue_type=ComplianceIssueType.PROMOTIONAL,
                    flagged_text=flagged_text,
                    position=(match.start(), match.end()),
                    severity=ComplianceSeverity.LOW,
                    explanation=f"'{flagged_text}' 是促销性语言，A+页面应专注于产品信息",
                    suggested_alternatives=["产品特性描述", "功能说明", "使用方法", "技术规格"],
                    context=self._get_context(content, match.start(), match.end())
                )
                issues.append(issue)
        
        return issues
    
    def _get_context(self, content: str, start: int, end: int, context_length: int = 50) -> str:
        """获取违规词汇的上下文"""
        try:
            context_start = max(0, start - context_length)
            context_end = min(len(content), end + context_length)
            
            context = content[context_start:context_end]
            
            # 标记违规部分
            relative_start = start - context_start
            relative_end = end - context_start
            
            marked_context = (
                context[:relative_start] + 
                f"[{context[relative_start:relative_end]}]" + 
                context[relative_end:]
            )
            
            return marked_context.strip()
            
        except Exception as e:
            logger.error(f"Failed to get context: {str(e)}")
            return ""
    
    def _calculate_compliance_score(self, content: str, issues: List[ComplianceIssue]) -> float:
        """计算合规分数"""
        try:
            if not issues:
                return 1.0
            
            # 根据问题严重程度计算扣分
            total_penalty = 0.0
            
            for issue in issues:
                if issue.severity == ComplianceSeverity.HIGH:
                    total_penalty += 0.3
                elif issue.severity == ComplianceSeverity.MEDIUM:
                    total_penalty += 0.2
                else:  # LOW
                    total_penalty += 0.1
            
            # 计算最终分数
            score = max(0.0, 1.0 - total_penalty)
            return score
            
        except Exception as e:
            logger.error(f"Failed to calculate compliance score: {str(e)}")
            return 0.0
    
    def _generate_fix_suggestions(self, issues: List[ComplianceIssue]) -> Dict[str, List[str]]:
        """生成修复建议"""
        suggestions = {}
        
        for issue in issues:
            issue_key = f"{issue.flagged_text} ({issue.issue_type.value})"
            suggestions[issue_key] = issue.suggested_alternatives
        
        return suggestions
    
    def _update_stats(self, result: ComplianceResult):
        """更新统计信息"""
        try:
            self.check_stats['total_checks'] += 1
            
            if result.is_compliant:
                self.check_stats['compliant_checks'] += 1
            
            # 统计常见违规类型
            for issue in result.flagged_issues:
                issue_type = issue.issue_type.value
                self.check_stats['common_violations'][issue_type] = (
                    self.check_stats['common_violations'].get(issue_type, 0) + 1
                )
                
        except Exception as e:
            logger.error(f"Failed to update stats: {str(e)}")
    
    def suggest_compliant_alternatives(self, flagged_text: str) -> List[str]:
        """为违规内容提供合规替代建议"""
        try:
            # 直接查找替代建议
            alternatives = self.replacement_suggestions.get(flagged_text.lower(), [])
            
            if alternatives:
                return alternatives
            
            # 如果没有直接匹配，尝试模糊匹配
            for word, suggestions in self.replacement_suggestions.items():
                if word in flagged_text.lower() or flagged_text.lower() in word:
                    return suggestions
            
            # 默认建议
            return ["请使用更客观的描述", "避免主观性表述", "专注于产品功能特性"]
            
        except Exception as e:
            logger.error(f"Failed to suggest alternatives: {str(e)}")
            return []
    
    def sanitize_content(self, content: str, auto_fix: bool = True) -> str:
        """
        清理内容，移除或替换违规词汇
        
        Args:
            content: 原始内容
            auto_fix: 是否自动修复
            
        Returns:
            清理后的内容
        """
        try:
            if not auto_fix:
                return content
            
            sanitized_content = content
            
            # 检查合规性
            compliance_result = self.check_content_compliance(content)
            
            # 应用自动修复
            for issue in compliance_result.flagged_issues:
                if issue.suggested_alternatives:
                    # 使用第一个建议替换
                    replacement = issue.suggested_alternatives[0]
                    sanitized_content = sanitized_content.replace(issue.flagged_text, replacement)
                    self.check_stats['auto_fixes_applied'] += 1
            
            return sanitized_content
            
        except Exception as e:
            logger.error(f"Failed to sanitize content: {str(e)}")
            return content
    
    def get_compliance_statistics(self) -> Dict[str, any]:
        """获取合规统计信息"""
        try:
            stats = self.check_stats.copy()
            
            # 计算合规率
            if stats['total_checks'] > 0:
                stats['compliance_rate'] = (stats['compliant_checks'] / stats['total_checks'] * 100)
            else:
                stats['compliance_rate'] = 0.0
            
            # 获取最常见的违规类型
            if stats['common_violations']:
                sorted_violations = sorted(
                    stats['common_violations'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                stats['top_violations'] = sorted_violations[:5]
            else:
                stats['top_violations'] = []
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get compliance statistics: {str(e)}")
            return {}
    
    def health_check(self) -> Dict[str, any]:
        """健康检查"""
        try:
            return {
                'status': 'healthy',
                'prohibited_words_loaded': sum(len(words) for words in self.prohibited_words.values()),
                'replacement_suggestions_loaded': len(self.replacement_suggestions),
                'pattern_rules_compiled': sum(len(patterns) for patterns in self.pattern_rules.values()),
                'statistics': self.get_compliance_statistics(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Amazon compliance service health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }