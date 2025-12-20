"""
元数据服务 - 集成元数据生成和智能分类功能
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from .metadata_generator import MetadataGenerator
from .classification_engine import ClassificationEngine, CategoryScore, TagSuggestion
from ..models.metadata import TemplateMetadata, DesignFeatures, ImageAnalysis


class MetadataService:
    """元数据服务 - 提供完整的模板元数据生成和分析功能"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化元数据服务
        
        Args:
            config_path: 配置文件路径
        """
        self.metadata_generator = MetadataGenerator()
        self.classification_engine = ClassificationEngine(config_path)
    
    def analyze_template(self, template_path: str, save_metadata: bool = True) -> Dict[str, Any]:
        """
        完整分析模板
        
        Args:
            template_path: 模板目录路径
            save_metadata: 是否保存元数据到文件
            
        Returns:
            Dict: 完整的分析结果
        """
        # 1. 生成基础元数据
        metadata = self.metadata_generator.generate_template_metadata(template_path)
        
        # 2. 智能分类
        category_scores = self.classification_engine.classify_template(
            metadata.design_features, 
            metadata.image_analyses
        )
        
        # 3. 生成标签建议
        tag_suggestions = self.classification_engine.generate_tags(
            metadata.design_features,
            metadata.image_analyses,
            category_scores
        )
        
        # 4. 生成关键词
        keywords = self.classification_engine.generate_keywords(
            metadata.design_features,
            category_scores
        )
        
        # 5. 更新元数据
        for keyword in keywords:
            metadata.add_generated_keyword(keyword)
        
        for suggestion in tag_suggestions:
            if suggestion.relevance > 0.6:  # 只添加高相关性的标签
                metadata.add_generated_tag(suggestion.tag)
        
        # 6. 更新推荐分类
        for category_score in category_scores[:3]:  # 前3个推荐
            if category_score.score > 0.3:
                metadata.suggest_category(category_score.category)
        
        # 7. 构建完整结果
        result = {
            "template_id": metadata.template_id,
            "metadata": metadata,
            "classification": {
                "category_scores": category_scores,
                "explanation": self.classification_engine.explain_classification(category_scores)
            },
            "suggestions": {
                "tags": tag_suggestions,
                "keywords": keywords,
                "categories": [score.category for score in category_scores[:3]]
            },
            "analysis_summary": self._create_analysis_summary(metadata, category_scores, tag_suggestions)
        }
        
        # 8. 保存元数据
        if save_metadata:
            self._save_analysis_results(template_path, result)
        
        return result
    
    def _create_analysis_summary(self, metadata: TemplateMetadata, 
                               category_scores: List[CategoryScore],
                               tag_suggestions: List[TagSuggestion]) -> Dict[str, Any]:
        """创建分析摘要"""
        best_category = category_scores[0] if category_scores else None
        
        return {
            "template_id": metadata.template_id,
            "image_count": len(metadata.image_analyses),
            "overall_quality": metadata.quality_metrics.overall_score,
            "quality_grade": metadata.quality_metrics.get_grade(),
            
            "design_analysis": {
                "color_tone": metadata.design_features.color_tone,
                "design_complexity": metadata.design_features.design_complexity,
                "visual_weight": metadata.design_features.visual_weight,
                "layout_type": metadata.design_features.layout_type
            },
            
            "classification_result": {
                "best_category": best_category.category if best_category else None,
                "confidence": best_category.confidence if best_category else 0.0,
                "confidence_level": self.classification_engine.get_confidence_level(
                    best_category.confidence if best_category else 0.0
                )
            },
            
            "generated_content": {
                "tags_count": len([s for s in tag_suggestions if s.relevance > 0.6]),
                "keywords_count": len(metadata.generated_keywords),
                "top_tags": [s.tag for s in tag_suggestions[:5] if s.relevance > 0.6]
            },
            
            "recommendations": self._generate_recommendations(metadata, category_scores)
        }
    
    def _generate_recommendations(self, metadata: TemplateMetadata, 
                                category_scores: List[CategoryScore]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 质量相关建议
        if metadata.quality_metrics.overall_score < 70:
            recommendations.append("模板整体质量较低，建议优化图片质量和配置完整性")
        
        if metadata.quality_metrics.image_quality < 60:
            recommendations.append("图片质量需要改善，建议使用更高分辨率和更好压缩质量的图片")
        
        if metadata.quality_metrics.completeness_score < 80:
            recommendations.append("模板文件不完整，建议添加缺失的预览图、桌面版或移动版图片")
        
        # 分类相关建议
        best_category = category_scores[0] if category_scores else None
        if best_category and best_category.confidence < 0.6:
            recommendations.append("分类置信度较低，建议调整设计风格或手动确认分类")
        
        # 设计相关建议
        if not metadata.design_features.style_tags:
            recommendations.append("缺少风格标签，建议添加更多设计特征描述")
        
        if len(metadata.generated_keywords) < 5:
            recommendations.append("关键词较少，建议丰富模板的设计元素以生成更多相关关键词")
        
        # 尺寸相关建议
        dimension_errors = metadata.validate_image_dimensions({
            "desktop": (1464, 600),
            "mobile": (600, 450),
            "preview": (300, 200)
        })
        
        if dimension_errors:
            recommendations.append("部分图片尺寸不符合标准，建议调整图片尺寸")
        
        return recommendations
    
    def _save_analysis_results(self, template_path: str, result: Dict[str, Any]):
        """保存分析结果"""
        # 创建metadata目录
        metadata_dir = os.path.join(template_path, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        # 保存完整元数据
        metadata_file = os.path.join(metadata_dir, "analysis.json")
        self.metadata_generator.save_metadata(result["metadata"], metadata_file)
        
        # 保存分类结果
        classification_file = os.path.join(metadata_dir, "classification.json")
        classification_data = {
            "category_scores": [
                {
                    "category": score.category,
                    "score": score.score,
                    "confidence": score.confidence,
                    "reasons": score.reasons
                }
                for score in result["classification"]["category_scores"]
            ],
            "explanation": result["classification"]["explanation"]
        }
        
        with open(classification_file, 'w', encoding='utf-8') as f:
            json.dump(classification_data, f, ensure_ascii=False, indent=2)
        
        # 保存标签和关键词建议
        suggestions_file = os.path.join(metadata_dir, "suggestions.json")
        suggestions_data = {
            "tags": [
                {
                    "tag": suggestion.tag,
                    "relevance": suggestion.relevance,
                    "category": suggestion.category,
                    "source": suggestion.source
                }
                for suggestion in result["suggestions"]["tags"]
            ],
            "keywords": result["suggestions"]["keywords"],
            "categories": result["suggestions"]["categories"]
        }
        
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions_data, f, ensure_ascii=False, indent=2)
        
        # 保存分析摘要
        summary_file = os.path.join(metadata_dir, "summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(result["analysis_summary"], f, ensure_ascii=False, indent=2)
    
    def batch_analyze_templates(self, templates_dir: str, 
                              template_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        批量分析模板
        
        Args:
            templates_dir: 模板根目录
            template_filter: 模板过滤条件（可选）
            
        Returns:
            Dict: 批量分析结果
        """
        results = {}
        errors = []
        
        # 查找所有模板目录
        template_paths = self._find_template_directories(templates_dir, template_filter)
        
        for template_path in template_paths:
            try:
                template_id = os.path.basename(template_path)
                print(f"正在分析模板: {template_id}")
                
                result = self.analyze_template(template_path, save_metadata=True)
                results[template_id] = result["analysis_summary"]
                
            except Exception as e:
                error_msg = f"分析模板 {template_path} 时出错: {str(e)}"
                errors.append(error_msg)
                print(f"错误: {error_msg}")
        
        # 生成批量分析报告
        batch_result = {
            "total_templates": len(template_paths),
            "successful_analyses": len(results),
            "failed_analyses": len(errors),
            "results": results,
            "errors": errors,
            "statistics": self._calculate_batch_statistics(results)
        }
        
        return batch_result
    
    def _find_template_directories(self, templates_dir: str, 
                                 template_filter: Optional[str] = None) -> List[str]:
        """查找模板目录"""
        template_paths = []
        
        # 遍历templates目录
        for root, dirs, files in os.walk(templates_dir):
            # 检查是否包含template.json或图片文件
            has_config = "template.json" in files
            has_images = any(f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) for f in files)
            
            if has_config or has_images:
                # 应用过滤条件
                if template_filter is None or template_filter in os.path.basename(root):
                    template_paths.append(root)
        
        return template_paths
    
    def _calculate_batch_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算批量分析统计信息"""
        if not results:
            return {}
        
        # 质量统计
        quality_scores = [r["overall_quality"] for r in results.values()]
        
        # 分类统计
        categories = [r["classification_result"]["best_category"] 
                     for r in results.values() 
                     if r["classification_result"]["best_category"]]
        
        category_counts = {}
        for category in categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 置信度统计
        confidences = [r["classification_result"]["confidence"] for r in results.values()]
        
        return {
            "quality_statistics": {
                "average_quality": sum(quality_scores) / len(quality_scores),
                "min_quality": min(quality_scores),
                "max_quality": max(quality_scores),
                "high_quality_count": len([q for q in quality_scores if q >= 80]),
                "low_quality_count": len([q for q in quality_scores if q < 60])
            },
            
            "category_distribution": category_counts,
            
            "confidence_statistics": {
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "high_confidence_count": len([c for c in confidences if c >= 0.7]),
                "low_confidence_count": len([c for c in confidences if c < 0.5])
            },
            
            "content_statistics": {
                "average_tags": sum(r["generated_content"]["tags_count"] for r in results.values()) / len(results),
                "average_keywords": sum(r["generated_content"]["keywords_count"] for r in results.values()) / len(results)
            }
        }
    
    def generate_config_template(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于分析结果生成配置模板
        
        Args:
            analysis_result: 模板分析结果
            
        Returns:
            Dict: 配置模板
        """
        metadata = analysis_result["metadata"]
        best_category = analysis_result["classification"]["category_scores"][0] if analysis_result["classification"]["category_scores"] else None
        
        # 基础配置模板
        config_template = {
            "id": metadata.template_id,
            "name": metadata.template_id.replace('_', ' ').title(),
            "version": "1.0.0",
            "category": best_category.category if best_category else "uncategorized",
            "template_type": "standard",
            "status": "draft",
            "description": f"基于 {metadata.design_features.color_tone} 色调的 {metadata.design_features.design_complexity} 风格模板",
            
            "classification": {
                "primary_category": best_category.category if best_category else "uncategorized",
                "style_tags": metadata.design_features.style_tags,
                "keyword_tags": metadata.generated_keywords,
                "target_audience": metadata.design_features.target_audience,
                "use_cases": metadata.design_features.use_cases
            },
            
            "design_attributes": {
                "color_tone": metadata.design_features.color_tone,
                "design_style": metadata.design_features.style_category,
                "visual_weight": metadata.design_features.visual_weight,
                "complexity_level": metadata.design_features.design_complexity
            },
            
            "layout_structure": {
                "layout_type": metadata.design_features.layout_type,
                "text_density": metadata.design_features.text_density,
                "image_ratio": metadata.design_features.image_ratio,
                "sections": list(set(
                    os.path.splitext(os.path.basename(path))[0] 
                    for path in metadata.image_analyses.keys()
                    if '/' in path
                ))
            },
            
            "quality_metrics": {
                "completeness_score": metadata.quality_metrics.completeness_score,
                "design_quality": metadata.quality_metrics.design_quality,
                "usability_score": metadata.quality_metrics.usability_score,
                "performance_score": metadata.quality_metrics.performance_score,
                "overall_score": metadata.quality_metrics.overall_score,
                "grade": metadata.quality_metrics.get_grade()
            },
            
            "generated_metadata": {
                "analysis_version": metadata.analysis_version,
                "generated_at": metadata.updated_at.isoformat(),
                "confidence": best_category.confidence if best_category else 0.0,
                "auto_generated": True
            }
        }
        
        return config_template
    
    def update_existing_config(self, template_path: str, analysis_result: Dict[str, Any]) -> bool:
        """
        更新现有配置文件
        
        Args:
            template_path: 模板路径
            analysis_result: 分析结果
            
        Returns:
            bool: 是否成功更新
        """
        config_file = os.path.join(template_path, "template.json")
        
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            
            # 生成新的配置模板
            new_config = self.generate_config_template(analysis_result)
            
            # 合并配置（保留现有的手动设置）
            merged_config = self._merge_configs(existing_config, new_config)
            
            # 保存更新后的配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(merged_config, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"更新配置文件失败: {str(e)}")
            return False
    
    def _merge_configs(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置文件"""
        merged = new.copy()
        
        # 保留现有的重要字段
        preserve_fields = [
            "name", "description", "status", "version",
            "visibility_rules", "customization_options", "assets"
        ]
        
        for field in preserve_fields:
            if field in existing:
                merged[field] = existing[field]
        
        # 合并标签和关键词（去重）
        if "classification" in existing:
            existing_classification = existing["classification"]
            new_classification = merged.get("classification", {})
            
            # 合并标签
            existing_tags = set(existing_classification.get("style_tags", []))
            new_tags = set(new_classification.get("style_tags", []))
            merged["classification"]["style_tags"] = list(existing_tags.union(new_tags))
            
            # 合并关键词
            existing_keywords = set(existing_classification.get("keyword_tags", []))
            new_keywords = set(new_classification.get("keyword_tags", []))
            merged["classification"]["keyword_tags"] = list(existing_keywords.union(new_keywords))
        
        return merged