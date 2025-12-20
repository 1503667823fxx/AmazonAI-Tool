"""
智能分类推荐引擎 - 基于设计特征进行分类推荐和标签生成
"""

import os
import json
import math
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from ..models.metadata import DesignFeatures, ImageAnalysis


@dataclass
class CategoryScore:
    """分类评分"""
    category: str
    score: float
    confidence: float
    reasons: List[str]


@dataclass
class TagSuggestion:
    """标签建议"""
    tag: str
    relevance: float
    category: str
    source: str  # 来源：color, style, content, etc.


class ClassificationEngine:
    """智能分类推荐引擎"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化分类引擎
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        # 导入配置
        from pathlib import Path
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import CATEGORIES_CONFIG
        
        self.config_path = config_path or str(CATEGORIES_CONFIG)
        
        # 加载分类配置
        self.categories = self._load_categories()
        
        # 预定义的分类特征映射
        self.category_features = {
            "electronics": {
                "colors": ["#2196F3", "#1976D2", "#0D47A1", "#37474F", "#263238"],
                "keywords": ["科技", "数码", "电子", "智能", "现代", "蓝色", "黑色", "简约", "冷静", "专业"],
                "style_indicators": ["modern", "minimal", "tech", "professional"],
                "color_tones": ["cool", "neutral"],
                "complexity": ["simple", "moderate"],
                "weight_preference": ["light", "medium"]
            },
            "beauty": {
                "colors": ["#E91E63", "#F8BBD9", "#FCE4EC", "#FFF", "#F5F5F5"],
                "keywords": ["美妆", "护肤", "优雅", "粉色", "白色", "柔和", "清新", "自然", "温暖", "舒适"],
                "style_indicators": ["elegant", "luxury", "natural", "soft"],
                "color_tones": ["warm", "neutral"],
                "complexity": ["simple", "moderate"],
                "weight_preference": ["light", "medium"]
            },
            "home": {
                "colors": ["#8D6E63", "#D7CCC8", "#EFEBE9", "#FF9800", "#FFF3E0"],
                "keywords": ["家居", "温馨", "舒适", "木质", "暖色", "生活", "实用", "简洁", "自然", "放松"],
                "style_indicators": ["cozy", "natural", "casual", "warm"],
                "color_tones": ["warm", "neutral"],
                "complexity": ["simple", "moderate", "complex"],
                "weight_preference": ["medium", "heavy"]
            },
            "seasonal": {
                "colors": ["#4CAF50", "#FF5722", "#FFC107", "#9C27B0"],
                "keywords": ["季节", "节日", "庆祝", "特殊", "限时", "主题", "活动", "促销"],
                "style_indicators": ["festive", "seasonal", "special", "vibrant"],
                "color_tones": ["warm", "cool", "neutral"],
                "complexity": ["moderate", "complex"],
                "weight_preference": ["medium", "heavy"]
            }
        }
        
        # 风格关键词映射
        self.style_keywords = {
            "modern": ["现代", "简约", "科技", "几何", "线条", "冷静", "专业"],
            "vintage": ["复古", "经典", "怀旧", "传统", "装饰", "温暖", "怀念"],
            "minimal": ["简约", "极简", "留白", "干净", "纯净", "清爽", "轻盈"],
            "luxury": ["奢华", "高端", "精致", "金色", "质感", "优雅", "贵气"],
            "casual": ["休闲", "轻松", "自然", "舒适", "日常", "亲和", "随意"],
            "professional": ["专业", "商务", "正式", "严谨", "可靠", "稳重", "权威"],
            "elegant": ["优雅", "精致", "柔美", "细腻", "高雅", "温柔", "迷人"],
            "natural": ["自然", "有机", "环保", "清新", "健康", "纯净", "原生"],
            "tech": ["科技", "数字", "智能", "创新", "未来", "高科技", "电子"],
            "cozy": ["温馨", "舒适", "家庭", "温暖", "亲密", "放松", "安逸"]
        }
        
        # 色彩情感映射
        self.color_emotions = {
            "red": ["热情", "活力", "激情", "力量", "紧急"],
            "blue": ["冷静", "专业", "信任", "科技", "稳定"],
            "green": ["自然", "健康", "成长", "和谐", "环保"],
            "yellow": ["快乐", "活泼", "创意", "温暖", "注意"],
            "purple": ["神秘", "奢华", "创意", "浪漫", "高贵"],
            "orange": ["友好", "活力", "温暖", "创意", "积极"],
            "pink": ["温柔", "浪漫", "女性", "甜美", "关爱"],
            "brown": ["稳重", "自然", "温暖", "可靠", "传统"],
            "gray": ["中性", "专业", "现代", "平衡", "简约"],
            "black": ["优雅", "神秘", "权威", "现代", "正式"],
            "white": ["纯净", "简约", "清洁", "和平", "空间"]
        }
    
    def _load_categories(self) -> Dict:
        """加载分类配置"""
        try:
            try:
                import yaml
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
            except ImportError:
                # YAML不可用，使用默认配置
                pass
        except Exception:
            # 文件读取失败，使用默认配置
            pass
        
        # 返回默认分类配置
        return {
            "categories": {
                "electronics": {
                    "name": "电子产品",
                    "description": "数码设备、智能产品、电子配件等",
                    "subcategories": ["mobile_accessories", "audio_devices", "smart_home", "gaming_gear"]
                },
                "beauty": {
                    "name": "美妆护肤",
                    "description": "化妆品、护肤品、美容工具等",
                    "subcategories": ["skincare", "makeup", "beauty_tools", "fragrance"]
                },
                "home": {
                    "name": "家居用品",
                    "description": "家具、装饰、生活用品等",
                    "subcategories": ["furniture", "decoration", "kitchen", "storage"]
                },
                "seasonal": {
                    "name": "季节性",
                    "description": "节日、季节主题模板",
                    "subcategories": ["spring", "summer", "autumn", "winter", "holidays"]
                }
            }
        }
    
    def classify_template(self, design_features: DesignFeatures, image_analyses: Dict[str, ImageAnalysis]) -> List[CategoryScore]:
        """
        对模板进行智能分类
        
        Args:
            design_features: 设计特征
            image_analyses: 图片分析结果
            
        Returns:
            List[CategoryScore]: 分类评分列表，按评分降序排列
        """
        category_scores = []
        
        for category_id, features in self.category_features.items():
            score, confidence, reasons = self._calculate_category_score(
                category_id, features, design_features, image_analyses
            )
            
            category_scores.append(CategoryScore(
                category=category_id,
                score=score,
                confidence=confidence,
                reasons=reasons
            ))
        
        # 按评分降序排列
        category_scores.sort(key=lambda x: x.score, reverse=True)
        
        return category_scores
    
    def _calculate_category_score(self, category_id: str, category_features: Dict, 
                                design_features: DesignFeatures, 
                                image_analyses: Dict[str, ImageAnalysis]) -> Tuple[float, float, List[str]]:
        """计算单个分类的评分"""
        total_score = 0.0
        max_score = 0.0
        reasons = []
        
        # 1. 色调匹配 (权重: 25%)
        color_score, color_reasons = self._score_color_match(
            category_features, design_features, image_analyses
        )
        total_score += color_score * 0.25
        max_score += 0.25
        reasons.extend(color_reasons)
        
        # 2. 关键词匹配 (权重: 30%)
        keyword_score, keyword_reasons = self._score_keyword_match(
            category_features, design_features
        )
        total_score += keyword_score * 0.30
        max_score += 0.30
        reasons.extend(keyword_reasons)
        
        # 3. 风格指标匹配 (权重: 20%)
        style_score, style_reasons = self._score_style_match(
            category_features, design_features
        )
        total_score += style_score * 0.20
        max_score += 0.20
        reasons.extend(style_reasons)
        
        # 4. 设计复杂度匹配 (权重: 15%)
        complexity_score, complexity_reasons = self._score_complexity_match(
            category_features, design_features
        )
        total_score += complexity_score * 0.15
        max_score += 0.15
        reasons.extend(complexity_reasons)
        
        # 5. 视觉重量匹配 (权重: 10%)
        weight_score, weight_reasons = self._score_weight_match(
            category_features, design_features
        )
        total_score += weight_score * 0.10
        max_score += 0.10
        reasons.extend(weight_reasons)
        
        # 计算最终评分和置信度
        final_score = total_score / max_score if max_score > 0 else 0.0
        confidence = self._calculate_confidence(final_score, len(reasons))
        
        return final_score, confidence, reasons
    
    def _score_color_match(self, category_features: Dict, design_features: DesignFeatures, 
                          image_analyses: Dict[str, ImageAnalysis]) -> Tuple[float, List[str]]:
        """评分色彩匹配度"""
        score = 0.0
        reasons = []
        
        # 色调匹配
        if design_features.color_tone in category_features.get("color_tones", []):
            score += 0.5
            reasons.append(f"色调匹配: {design_features.color_tone}")
        
        # 主要颜色匹配
        category_colors = set(category_features.get("colors", []))
        total_color_matches = 0
        total_colors = 0
        
        for analysis in image_analyses.values():
            for color in analysis.dominant_colors:
                total_colors += 1
                if color in category_colors:
                    total_color_matches += 1
        
        if total_colors > 0:
            color_match_ratio = total_color_matches / total_colors
            score += color_match_ratio * 0.5
            if color_match_ratio > 0.3:
                reasons.append(f"主要颜色匹配度: {color_match_ratio:.1%}")
        
        return score, reasons
    
    def _score_keyword_match(self, category_features: Dict, design_features: DesignFeatures) -> Tuple[float, List[str]]:
        """评分关键词匹配度"""
        score = 0.0
        reasons = []
        
        category_keywords = set(category_features.get("keywords", []))
        template_keywords = set(design_features.style_tags + design_features.mood_tags)
        
        if template_keywords and category_keywords:
            matches = template_keywords.intersection(category_keywords)
            match_ratio = len(matches) / len(template_keywords)
            score = match_ratio
            
            if matches:
                reasons.append(f"关键词匹配: {', '.join(list(matches)[:3])}")
        
        return score, reasons
    
    def _score_style_match(self, category_features: Dict, design_features: DesignFeatures) -> Tuple[float, List[str]]:
        """评分风格匹配度"""
        score = 0.0
        reasons = []
        
        category_styles = set(category_features.get("style_indicators", []))
        
        # 检查风格标签中是否包含分类风格指标
        for tag in design_features.style_tags:
            for style in category_styles:
                if style in tag.lower() or any(keyword in tag for keyword in self.style_keywords.get(style, [])):
                    score += 0.3
                    reasons.append(f"风格匹配: {tag} -> {style}")
                    break
        
        return min(score, 1.0), reasons
    
    def _score_complexity_match(self, category_features: Dict, design_features: DesignFeatures) -> Tuple[float, List[str]]:
        """评分复杂度匹配度"""
        score = 0.0
        reasons = []
        
        preferred_complexity = category_features.get("complexity", [])
        if design_features.design_complexity in preferred_complexity:
            score = 1.0
            reasons.append(f"复杂度匹配: {design_features.design_complexity}")
        
        return score, reasons
    
    def _score_weight_match(self, category_features: Dict, design_features: DesignFeatures) -> Tuple[float, List[str]]:
        """评分视觉重量匹配度"""
        score = 0.0
        reasons = []
        
        preferred_weights = category_features.get("weight_preference", [])
        if design_features.visual_weight in preferred_weights:
            score = 1.0
            reasons.append(f"视觉重量匹配: {design_features.visual_weight}")
        
        return score, reasons
    
    def _calculate_confidence(self, score: float, reason_count: int) -> float:
        """计算置信度"""
        # 基础置信度基于评分
        base_confidence = score
        
        # 根据匹配原因数量调整置信度
        reason_bonus = min(reason_count * 0.1, 0.3)
        
        # 最终置信度
        confidence = min(base_confidence + reason_bonus, 1.0)
        
        return confidence
    
    def generate_tags(self, design_features: DesignFeatures, image_analyses: Dict[str, ImageAnalysis], 
                     category_scores: List[CategoryScore]) -> List[TagSuggestion]:
        """
        生成标签建议
        
        Args:
            design_features: 设计特征
            image_analyses: 图片分析结果
            category_scores: 分类评分
            
        Returns:
            List[TagSuggestion]: 标签建议列表
        """
        suggestions = []
        
        # 1. 基于颜色生成标签
        color_tags = self._generate_color_tags(image_analyses)
        suggestions.extend(color_tags)
        
        # 2. 基于风格生成标签
        style_tags = self._generate_style_tags(design_features)
        suggestions.extend(style_tags)
        
        # 3. 基于分类生成标签
        category_tags = self._generate_category_tags(category_scores)
        suggestions.extend(category_tags)
        
        # 4. 基于设计特征生成标签
        feature_tags = self._generate_feature_tags(design_features)
        suggestions.extend(feature_tags)
        
        # 去重并按相关性排序
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        unique_suggestions.sort(key=lambda x: x.relevance, reverse=True)
        
        return unique_suggestions[:20]  # 返回前20个建议
    
    def _generate_color_tags(self, image_analyses: Dict[str, ImageAnalysis]) -> List[TagSuggestion]:
        """基于颜色生成标签"""
        suggestions = []
        color_counts = {}
        
        # 统计颜色出现频率
        for analysis in image_analyses.values():
            for color in analysis.dominant_colors:
                color_name = self._get_color_name(color)
                if color_name:
                    color_counts[color_name] = color_counts.get(color_name, 0) + 1
        
        # 生成颜色标签
        for color_name, count in color_counts.items():
            relevance = min(count / len(image_analyses), 1.0)
            
            # 添加颜色本身作为标签
            suggestions.append(TagSuggestion(
                tag=color_name,
                relevance=relevance,
                category="color",
                source="color_analysis"
            ))
            
            # 添加颜色相关的情感标签
            emotions = self.color_emotions.get(color_name.lower(), [])
            for emotion in emotions:
                suggestions.append(TagSuggestion(
                    tag=emotion,
                    relevance=relevance * 0.7,
                    category="emotion",
                    source="color_emotion"
                ))
        
        return suggestions
    
    def _generate_style_tags(self, design_features: DesignFeatures) -> List[TagSuggestion]:
        """基于风格生成标签"""
        suggestions = []
        
        # 现有的风格标签
        for tag in design_features.style_tags:
            suggestions.append(TagSuggestion(
                tag=tag,
                relevance=1.0,
                category="style",
                source="existing_tags"
            ))
        
        # 现有的情绪标签
        for tag in design_features.mood_tags:
            suggestions.append(TagSuggestion(
                tag=tag,
                relevance=1.0,
                category="mood",
                source="existing_tags"
            ))
        
        # 基于设计特征生成新标签
        if design_features.color_tone:
            tone_tags = {
                "warm": ["温暖", "亲和", "舒适"],
                "cool": ["冷静", "专业", "现代"],
                "neutral": ["平衡", "通用", "稳定"]
            }
            for tag in tone_tags.get(design_features.color_tone, []):
                suggestions.append(TagSuggestion(
                    tag=tag,
                    relevance=0.8,
                    category="tone",
                    source="color_tone"
                ))
        
        if design_features.design_complexity:
            complexity_tags = {
                "simple": ["简约", "清爽", "易懂"],
                "moderate": ["平衡", "适中", "实用"],
                "complex": ["丰富", "详细", "全面"]
            }
            for tag in complexity_tags.get(design_features.design_complexity, []):
                suggestions.append(TagSuggestion(
                    tag=tag,
                    relevance=0.7,
                    category="complexity",
                    source="design_complexity"
                ))
        
        return suggestions
    
    def _generate_category_tags(self, category_scores: List[CategoryScore]) -> List[TagSuggestion]:
        """基于分类生成标签"""
        suggestions = []
        
        # 取前3个最高分的分类
        for i, category_score in enumerate(category_scores[:3]):
            if category_score.score > 0.3:  # 只考虑评分较高的分类
                category_info = self.categories.get("categories", {}).get(category_score.category, {})
                category_name = category_info.get("name", category_score.category)
                
                # 添加分类名称作为标签
                relevance = category_score.score * (1.0 - i * 0.2)  # 排名越靠前相关性越高
                suggestions.append(TagSuggestion(
                    tag=category_name,
                    relevance=relevance,
                    category="category",
                    source="classification"
                ))
                
                # 添加分类相关的关键词
                category_features = self.category_features.get(category_score.category, {})
                keywords = category_features.get("keywords", [])
                for keyword in keywords[:5]:  # 取前5个关键词
                    suggestions.append(TagSuggestion(
                        tag=keyword,
                        relevance=relevance * 0.6,
                        category="keyword",
                        source="category_keywords"
                    ))
        
        return suggestions
    
    def _generate_feature_tags(self, design_features: DesignFeatures) -> List[TagSuggestion]:
        """基于设计特征生成标签"""
        suggestions = []
        
        # 布局类型标签
        if design_features.layout_type:
            layout_tags = {
                "grid": ["网格", "规整", "有序"],
                "centered": ["居中", "对称", "平衡"],
                "freeform": ["自由", "灵活", "创意"]
            }
            for tag in layout_tags.get(design_features.layout_type, []):
                suggestions.append(TagSuggestion(
                    tag=tag,
                    relevance=0.6,
                    category="layout",
                    source="layout_type"
                ))
        
        # 文本密度标签
        if design_features.text_density:
            density_tags = {
                "low": ["简洁", "留白", "空间"],
                "medium": ["适中", "平衡", "实用"],
                "high": ["信息丰富", "详细", "全面"]
            }
            for tag in density_tags.get(design_features.text_density, []):
                suggestions.append(TagSuggestion(
                    tag=tag,
                    relevance=0.5,
                    category="density",
                    source="text_density"
                ))
        
        # 视觉重量标签
        if design_features.visual_weight:
            weight_tags = {
                "light": ["轻盈", "优雅", "精致"],
                "medium": ["平衡", "稳定", "适中"],
                "heavy": ["厚重", "稳重", "强烈"]
            }
            for tag in weight_tags.get(design_features.visual_weight, []):
                suggestions.append(TagSuggestion(
                    tag=tag,
                    relevance=0.6,
                    category="weight",
                    source="visual_weight"
                ))
        
        return suggestions
    
    def _get_color_name(self, hex_color: str) -> Optional[str]:
        """根据十六进制颜色值获取颜色名称"""
        try:
            # 移除#号
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # 简单的颜色分类
            if r > 200 and g < 100 and b < 100:
                return "红色"
            elif r < 100 and g > 200 and b < 100:
                return "绿色"
            elif r < 100 and g < 100 and b > 200:
                return "蓝色"
            elif r > 200 and g > 200 and b < 100:
                return "黄色"
            elif r > 200 and g < 100 and b > 200:
                return "紫色"
            elif r > 200 and g > 150 and b < 100:
                return "橙色"
            elif r > 200 and g > 150 and b > 150:
                return "粉色"
            elif r > 150 and g > 100 and b < 100:
                return "棕色"
            elif r < 50 and g < 50 and b < 50:
                return "黑色"
            elif r > 200 and g > 200 and b > 200:
                return "白色"
            elif abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
                return "灰色"
            else:
                return None
                
        except (ValueError, IndexError):
            return None
    
    def _deduplicate_suggestions(self, suggestions: List[TagSuggestion]) -> List[TagSuggestion]:
        """去重标签建议"""
        seen_tags = {}
        unique_suggestions = []
        
        for suggestion in suggestions:
            if suggestion.tag in seen_tags:
                # 如果已存在，保留相关性更高的
                existing = seen_tags[suggestion.tag]
                if suggestion.relevance > existing.relevance:
                    seen_tags[suggestion.tag] = suggestion
            else:
                seen_tags[suggestion.tag] = suggestion
        
        return list(seen_tags.values())
    
    def generate_keywords(self, design_features: DesignFeatures, category_scores: List[CategoryScore]) -> List[str]:
        """
        生成关键词
        
        Args:
            design_features: 设计特征
            category_scores: 分类评分
            
        Returns:
            List[str]: 关键词列表
        """
        keywords = set()
        
        # 从设计特征中提取关键词
        keywords.update(design_features.style_tags)
        keywords.update(design_features.mood_tags)
        
        # 从最佳分类中提取关键词
        if category_scores:
            best_category = category_scores[0]
            if best_category.score > 0.5:
                category_features = self.category_features.get(best_category.category, {})
                category_keywords = category_features.get("keywords", [])
                keywords.update(category_keywords[:10])  # 取前10个关键词
        
        # 基于设计特征生成关键词
        if design_features.color_tone:
            tone_keywords = {
                "warm": ["温暖", "亲和", "舒适", "友好"],
                "cool": ["冷静", "专业", "现代", "科技"],
                "neutral": ["平衡", "通用", "稳定", "经典"]
            }
            keywords.update(tone_keywords.get(design_features.color_tone, []))
        
        if design_features.design_complexity:
            complexity_keywords = {
                "simple": ["简约", "极简", "清爽", "干净"],
                "moderate": ["平衡", "实用", "适中", "标准"],
                "complex": ["丰富", "详细", "全面", "复杂"]
            }
            keywords.update(complexity_keywords.get(design_features.design_complexity, []))
        
        return list(keywords)[:15]  # 返回前15个关键词
    
    def get_confidence_level(self, score: float) -> str:
        """获取置信度等级"""
        if score >= 0.8:
            return "高"
        elif score >= 0.6:
            return "中"
        elif score >= 0.4:
            return "低"
        else:
            return "很低"
    
    def explain_classification(self, category_scores: List[CategoryScore]) -> Dict[str, Any]:
        """
        解释分类结果
        
        Args:
            category_scores: 分类评分列表
            
        Returns:
            Dict: 分类解释
        """
        if not category_scores:
            return {"message": "无法进行分类", "recommendations": []}
        
        best_category = category_scores[0]
        
        explanation = {
            "best_match": {
                "category": best_category.category,
                "score": best_category.score,
                "confidence": best_category.confidence,
                "confidence_level": self.get_confidence_level(best_category.confidence),
                "reasons": best_category.reasons
            },
            "alternatives": [
                {
                    "category": score.category,
                    "score": score.score,
                    "confidence": score.confidence
                }
                for score in category_scores[1:3]  # 显示前3个备选
            ],
            "recommendations": []
        }
        
        # 生成建议
        if best_category.confidence < 0.6:
            explanation["recommendations"].append(
                "分类置信度较低，建议手动确认或添加更多设计特征"
            )
        
        if best_category.score < 0.5:
            explanation["recommendations"].append(
                "没有找到高度匹配的分类，可能需要创建新的分类或调整模板设计"
            )
        
        return explanation