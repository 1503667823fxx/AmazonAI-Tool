"""
A+ 模板智能搜索和推荐引擎
支持关键词搜索、语义匹配、风格推荐等功能
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import os

class TemplateSearchEngine:
    """模板搜索引擎"""
    
    def __init__(self, templates_config_path: str = "templates/templates_config.json"):
        self.templates_config_path = templates_config_path
        self.templates_data = self._load_templates_config()
        self.search_index = self._build_search_index()
    
    def _load_templates_config(self) -> Dict:
        """加载模板配置"""
        try:
            with open(self.templates_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"templates": {}}
    
    def _build_search_index(self) -> Dict:
        """构建搜索索引"""
        index = {}
        
        for template_id, template_config in self.templates_data.get("templates", {}).items():
            # 收集所有可搜索的文本
            searchable_text = []
            
            # 基本信息
            searchable_text.extend([
                template_config.get("name", ""),
                template_config.get("category", ""),
                template_config.get("description", "")
            ])
            
            # 标签和关键词
            searchable_text.extend(template_config.get("tags", []))
            searchable_text.extend(template_config.get("keywords", []))
            
            # 风格属性
            style_attrs = template_config.get("style_attributes", {})
            searchable_text.extend(style_attrs.values())
            
            # 节日和季节
            if "holiday" in template_config:
                searchable_text.append(template_config["holiday"])
            if "season" in template_config:
                searchable_text.append(template_config["season"])
            
            # 配色方案
            searchable_text.extend(template_config.get("color_schemes", []))
            
            # 合并所有文本并转为小写
            all_text = " ".join(str(text) for text in searchable_text).lower()
            
            index[template_id] = {
                "text": all_text,
                "config": template_config,
                "keywords": template_config.get("keywords", []),
                "tags": template_config.get("tags", []),
                "style_attributes": template_config.get("style_attributes", {}),
                "category": template_config.get("category", ""),
                "holiday": template_config.get("holiday", ""),
                "season": template_config.get("season", "")
            }
        
        return index
    
    def search_templates(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索模板"""
        if not query.strip():
            return self._get_all_templates()[:limit]
        
        query = query.lower().strip()
        results = []
        
        for template_id, template_data in self.search_index.items():
            score = self._calculate_relevance_score(query, template_data)
            if score > 0:
                results.append({
                    "template_id": template_id,
                    "config": template_data["config"],
                    "score": score,
                    "match_reasons": self._get_match_reasons(query, template_data)
                })
        
        # 按相关性得分排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def _calculate_relevance_score(self, query: str, template_data: Dict) -> float:
        """计算相关性得分"""
        score = 0.0
        
        # 1. 精确关键词匹配 (最高权重)
        for keyword in template_data["keywords"]:
            if keyword.lower() in query:
                score += 10.0
        
        # 2. 标签匹配
        for tag in template_data["tags"]:
            if tag.lower() in query:
                score += 8.0
        
        # 3. 节日/季节匹配
        if template_data["holiday"] and template_data["holiday"].lower() in query:
            score += 15.0  # 节日匹配给高分
        if template_data["season"] and template_data["season"].lower() in query:
            score += 6.0
        
        # 4. 类别匹配
        if template_data["category"].lower() in query:
            score += 7.0
        
        # 5. 风格属性匹配
        for attr_value in template_data["style_attributes"].values():
            if attr_value.lower() in query:
                score += 5.0
        
        # 6. 模糊文本匹配
        text_similarity = SequenceMatcher(None, query, template_data["text"]).ratio()
        score += text_similarity * 3.0
        
        # 7. 部分词匹配
        query_words = query.split()
        for word in query_words:
            if len(word) > 2 and word in template_data["text"]:
                score += 2.0
        
        return score
    
    def _get_match_reasons(self, query: str, template_data: Dict) -> List[str]:
        """获取匹配原因"""
        reasons = []
        
        # 检查关键词匹配
        for keyword in template_data["keywords"]:
            if keyword.lower() in query:
                reasons.append(f"关键词匹配: {keyword}")
        
        # 检查标签匹配
        for tag in template_data["tags"]:
            if tag.lower() in query:
                reasons.append(f"标签匹配: {tag}")
        
        # 检查节日匹配
        if template_data["holiday"] and template_data["holiday"].lower() in query:
            reasons.append(f"节日匹配: {template_data['holiday']}")
        
        # 检查类别匹配
        if template_data["category"].lower() in query:
            reasons.append(f"类别匹配: {template_data['category']}")
        
        return reasons[:3]  # 最多显示3个匹配原因
    
    def get_similar_templates(self, template_id: str, limit: int = 5) -> List[Dict]:
        """获取相似模板"""
        if template_id not in self.search_index:
            return []
        
        target_template = self.search_index[template_id]
        results = []
        
        for tid, template_data in self.search_index.items():
            if tid == template_id:
                continue
            
            similarity_score = self._calculate_similarity_score(target_template, template_data)
            if similarity_score > 0:
                results.append({
                    "template_id": tid,
                    "config": template_data["config"],
                    "similarity_score": similarity_score
                })
        
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
    
    def _calculate_similarity_score(self, template1: Dict, template2: Dict) -> float:
        """计算模板相似度"""
        score = 0.0
        
        # 1. 类别相同
        if template1["category"] == template2["category"]:
            score += 5.0
        
        # 2. 标签重叠
        tags1 = set(template1["tags"])
        tags2 = set(template2["tags"])
        tag_overlap = len(tags1.intersection(tags2))
        score += tag_overlap * 2.0
        
        # 3. 关键词重叠
        keywords1 = set(template1["keywords"])
        keywords2 = set(template2["keywords"])
        keyword_overlap = len(keywords1.intersection(keywords2))
        score += keyword_overlap * 3.0
        
        # 4. 风格属性相似
        style1 = template1["style_attributes"]
        style2 = template2["style_attributes"]
        for key in style1:
            if key in style2 and style1[key] == style2[key]:
                score += 1.5
        
        # 5. 节日/季节相同
        if template1["holiday"] and template1["holiday"] == template2["holiday"]:
            score += 4.0
        if template1["season"] and template1["season"] == template2["season"]:
            score += 2.0
        
        return score
    
    def get_templates_by_category(self, category: str) -> List[Dict]:
        """按类别获取模板"""
        results = []
        for template_id, template_data in self.search_index.items():
            if template_data["category"].lower() == category.lower():
                results.append({
                    "template_id": template_id,
                    "config": template_data["config"]
                })
        return results
    
    def get_templates_by_holiday(self, holiday: str) -> List[Dict]:
        """按节日获取模板"""
        results = []
        for template_id, template_data in self.search_index.items():
            if template_data["holiday"].lower() == holiday.lower():
                results.append({
                    "template_id": template_id,
                    "config": template_data["config"]
                })
        return results
    
    def get_templates_by_season(self, season: str) -> List[Dict]:
        """按季节获取模板"""
        results = []
        for template_id, template_data in self.search_index.items():
            if template_data["season"].lower() == season.lower():
                results.append({
                    "template_id": template_id,
                    "config": template_data["config"]
                })
        return results
    
    def _get_all_templates(self) -> List[Dict]:
        """获取所有模板"""
        results = []
        for template_id, template_data in self.search_index.items():
            results.append({
                "template_id": template_id,
                "config": template_data["config"],
                "score": 1.0
            })
        return results
    
    def get_search_suggestions(self, query: str) -> List[str]:
        """获取搜索建议"""
        if len(query) < 2:
            return []
        
        suggestions = set()
        query = query.lower()
        
        # 从关键词中找建议
        for template_data in self.search_index.values():
            for keyword in template_data["keywords"]:
                if query in keyword.lower():
                    suggestions.add(keyword)
            
            for tag in template_data["tags"]:
                if query in tag.lower():
                    suggestions.add(tag)
            
            # 节日建议
            if template_data["holiday"] and query in template_data["holiday"].lower():
                suggestions.add(template_data["holiday"])
        
        return list(suggestions)[:8]  # 最多8个建议

class SmartTemplateRecommender:
    """智能模板推荐器"""
    
    def __init__(self, search_engine: TemplateSearchEngine):
        self.search_engine = search_engine
    
    def recommend_by_product_info(self, product_name: str, product_category: str, 
                                 features: List[str]) -> List[Dict]:
        """根据产品信息推荐模板"""
        # 构建搜索查询
        search_terms = [product_name, product_category] + features
        query = " ".join(search_terms)
        
        # 搜索相关模板
        results = self.search_engine.search_templates(query, limit=5)
        
        # 添加推荐原因
        for result in results:
            result["recommendation_reason"] = self._generate_recommendation_reason(
                result, product_name, product_category, features
            )
        
        return results
    
    def _generate_recommendation_reason(self, template_result: Dict, product_name: str, 
                                      product_category: str, features: List[str]) -> str:
        """生成推荐原因"""
        reasons = []
        
        # 检查类别匹配
        template_category = template_result["config"].get("category", "")
        if template_category.lower() in product_category.lower():
            reasons.append(f"适合{product_category}类产品")
        
        # 检查关键词匹配
        template_keywords = template_result["config"].get("keywords", [])
        for keyword in template_keywords:
            if keyword.lower() in product_name.lower():
                reasons.append(f"匹配产品关键词'{keyword}'")
                break
        
        # 检查特性匹配
        template_tags = template_result["config"].get("tags", [])
        for feature in features:
            for tag in template_tags:
                if tag.lower() in feature.lower():
                    reasons.append(f"突出产品特色'{feature}'")
                    break
        
        if not reasons:
            reasons.append("风格匹配度高")
        
        return "，".join(reasons[:2])  # 最多显示2个原因