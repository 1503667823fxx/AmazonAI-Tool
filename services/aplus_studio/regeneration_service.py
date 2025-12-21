"""
A+ Studio Regeneration Service.

This service handles single module regeneration functionality, including
parameter preservation, version history management, and user customization.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from copy import deepcopy

from .models import (
    ModuleType, GenerationResult, ValidationStatus, 
    ModulePrompt, AnalysisResult
)


@dataclass
class RegenerationParameters:
    """重新生成参数"""
    module_type: ModuleType
    original_prompt: str
    custom_modifications: Dict[str, Any] = field(default_factory=dict)
    style_adjustments: Dict[str, Any] = field(default_factory=dict)
    preserve_visual_consistency: bool = True
    generation_seed: Optional[int] = None


@dataclass
class GenerationVersion:
    """生成版本记录"""
    version_id: str
    generation_result: GenerationResult
    parameters_used: RegenerationParameters
    creation_timestamp: datetime
    user_rating: Optional[float] = None
    user_notes: Optional[str] = None
    is_active: bool = False


@dataclass
class ModuleHistory:
    """模块历史记录"""
    module_type: ModuleType
    versions: List[GenerationVersion] = field(default_factory=list)
    original_version_id: Optional[str] = None
    active_version_id: Optional[str] = None
    
    def get_active_version(self) -> Optional[GenerationVersion]:
        """获取当前活跃版本"""
        for version in self.versions:
            if version.version_id == self.active_version_id:
                return version
        return None
    
    def get_original_version(self) -> Optional[GenerationVersion]:
        """获取原始版本"""
        for version in self.versions:
            if version.version_id == self.original_version_id:
                return version
        return None


class RegenerationService:
    """重新生成服务 - 处理单模块重新生成和版本管理"""
    
    def __init__(self):
        self.module_histories: Dict[str, Dict[ModuleType, ModuleHistory]] = {}
    
    def initialize_module_history(
        self, 
        session_id: str, 
        module_type: ModuleType, 
        initial_result: GenerationResult,
        initial_parameters: RegenerationParameters
    ) -> str:
        """初始化模块历史记录"""
        if session_id not in self.module_histories:
            self.module_histories[session_id] = {}
        
        version_id = str(uuid.uuid4())
        
        # 创建初始版本
        initial_version = GenerationVersion(
            version_id=version_id,
            generation_result=initial_result,
            parameters_used=initial_parameters,
            creation_timestamp=datetime.now(),
            is_active=True
        )
        
        # 创建模块历史
        module_history = ModuleHistory(
            module_type=module_type,
            versions=[initial_version],
            original_version_id=version_id,
            active_version_id=version_id
        )
        
        self.module_histories[session_id][module_type] = module_history
        
        return version_id
    
    def prepare_regeneration_parameters(
        self, 
        session_id: str,
        module_type: ModuleType,
        custom_modifications: Optional[Dict[str, Any]] = None,
        style_adjustments: Optional[Dict[str, Any]] = None
    ) -> RegenerationParameters:
        """准备重新生成参数，保留原有设置"""
        # 获取模块历史
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            raise ValueError(f"未找到模块 {module_type.value} 的历史记录")
        
        # 获取当前活跃版本的参数
        active_version = module_history.get_active_version()
        if not active_version:
            raise ValueError(f"模块 {module_type.value} 没有活跃版本")
        
        # 复制原始参数
        original_params = deepcopy(active_version.parameters_used)
        
        # 创建新的重新生成参数
        regen_params = RegenerationParameters(
            module_type=module_type,
            original_prompt=original_params.original_prompt,
            custom_modifications=custom_modifications or {},
            style_adjustments=style_adjustments or {},
            preserve_visual_consistency=original_params.preserve_visual_consistency,
            generation_seed=None  # 新的随机种子
        )
        
        # 合并自定义修改
        if custom_modifications:
            # 将自定义修改应用到原始参数上
            regen_params.custom_modifications.update(custom_modifications)
        
        if style_adjustments:
            regen_params.style_adjustments.update(style_adjustments)
        
        return regen_params
    
    def apply_parameter_modifications(
        self, 
        base_prompt: str, 
        parameters: RegenerationParameters
    ) -> str:
        """应用参数修改到提示词"""
        modified_prompt = base_prompt
        
        # 应用自定义修改
        for key, value in parameters.custom_modifications.items():
            if key == "additional_elements":
                modified_prompt += f"\n\nAdditional elements: {value}"
            elif key == "style_emphasis":
                modified_prompt = f"Style emphasis: {value}\n\n{modified_prompt}"
            elif key == "lighting_adjustment":
                modified_prompt = modified_prompt.replace(
                    "natural lighting", f"{value} lighting"
                )
            elif key == "color_preference":
                modified_prompt += f"\n\nColor preference: {value}"
            elif key == "composition_adjustment":
                modified_prompt += f"\n\nComposition: {value}"
        
        # 应用风格调整
        for key, value in parameters.style_adjustments.items():
            if key == "contrast_level":
                modified_prompt += f"\n\nContrast level: {value}"
            elif key == "saturation_level":
                modified_prompt += f"\n\nSaturation: {value}"
            elif key == "mood_adjustment":
                modified_prompt += f"\n\nMood: {value}"
            elif key == "detail_level":
                modified_prompt += f"\n\nDetail level: {value}"
        
        return modified_prompt
    
    def add_generation_version(
        self, 
        session_id: str,
        module_type: ModuleType,
        generation_result: GenerationResult,
        parameters_used: RegenerationParameters,
        set_as_active: bool = True
    ) -> str:
        """添加新的生成版本"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            raise ValueError(f"未找到模块 {module_type.value} 的历史记录")
        
        version_id = str(uuid.uuid4())
        
        # 创建新版本
        new_version = GenerationVersion(
            version_id=version_id,
            generation_result=generation_result,
            parameters_used=parameters_used,
            creation_timestamp=datetime.now(),
            is_active=set_as_active
        )
        
        # 如果设置为活跃版本，取消其他版本的活跃状态
        if set_as_active:
            for version in module_history.versions:
                version.is_active = False
            module_history.active_version_id = version_id
        
        # 添加到历史记录
        module_history.versions.append(new_version)
        
        # 限制版本数量（保留最近10个版本）
        if len(module_history.versions) > 10:
            # 保留原始版本和最近的9个版本
            original_version = module_history.get_original_version()
            recent_versions = sorted(
                module_history.versions, 
                key=lambda v: v.creation_timestamp, 
                reverse=True
            )[:9]
            
            if original_version and original_version not in recent_versions:
                module_history.versions = [original_version] + recent_versions
            else:
                module_history.versions = recent_versions
        
        return version_id
    
    def get_module_history(
        self, 
        session_id: str, 
        module_type: ModuleType
    ) -> Optional[ModuleHistory]:
        """获取模块历史记录"""
        session_histories = self.module_histories.get(session_id, {})
        return session_histories.get(module_type)
    
    def get_version_comparison(
        self, 
        session_id: str,
        module_type: ModuleType,
        version_ids: List[str]
    ) -> Dict[str, Any]:
        """获取版本对比信息"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            return {"error": "未找到模块历史记录"}
        
        comparison_data = {
            "module_type": module_type.value,
            "versions": [],
            "comparison_metrics": {}
        }
        
        versions_to_compare = []
        for version in module_history.versions:
            if version.version_id in version_ids:
                versions_to_compare.append(version)
        
        if len(versions_to_compare) < 2:
            return {"error": "需要至少两个版本进行对比"}
        
        # 添加版本信息
        for version in versions_to_compare:
            version_info = {
                "version_id": version.version_id,
                "creation_time": version.creation_timestamp.isoformat(),
                "quality_score": version.generation_result.quality_score,
                "validation_status": version.generation_result.validation_status.value,
                "generation_time": version.generation_result.generation_time,
                "user_rating": version.user_rating,
                "user_notes": version.user_notes,
                "is_active": version.is_active,
                "is_original": version.version_id == module_history.original_version_id,
                "parameters_summary": self._summarize_parameters(version.parameters_used)
            }
            comparison_data["versions"].append(version_info)
        
        # 计算对比指标
        quality_scores = [v.generation_result.quality_score for v in versions_to_compare]
        generation_times = [v.generation_result.generation_time for v in versions_to_compare]
        
        comparison_data["comparison_metrics"] = {
            "quality_range": {
                "min": min(quality_scores),
                "max": max(quality_scores),
                "avg": sum(quality_scores) / len(quality_scores)
            },
            "generation_time_range": {
                "min": min(generation_times),
                "max": max(generation_times),
                "avg": sum(generation_times) / len(generation_times)
            },
            "improvement_trend": self._calculate_improvement_trend(versions_to_compare)
        }
        
        return comparison_data
    
    def set_active_version(
        self, 
        session_id: str,
        module_type: ModuleType,
        version_id: str
    ) -> bool:
        """设置活跃版本"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            return False
        
        # 查找目标版本
        target_version = None
        for version in module_history.versions:
            if version.version_id == version_id:
                target_version = version
                break
        
        if not target_version:
            return False
        
        # 更新活跃状态
        for version in module_history.versions:
            version.is_active = (version.version_id == version_id)
        
        module_history.active_version_id = version_id
        
        return True
    
    def rate_version(
        self, 
        session_id: str,
        module_type: ModuleType,
        version_id: str,
        rating: float,
        notes: Optional[str] = None
    ) -> bool:
        """为版本评分"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            return False
        
        for version in module_history.versions:
            if version.version_id == version_id:
                version.user_rating = max(0.0, min(5.0, rating))  # 限制在0-5分
                version.user_notes = notes
                return True
        
        return False
    
    def get_regeneration_suggestions(
        self, 
        session_id: str,
        module_type: ModuleType
    ) -> List[Dict[str, Any]]:
        """获取重新生成建议"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            return []
        
        suggestions = []
        
        # 基于历史版本分析提供建议
        if len(module_history.versions) > 1:
            # 分析质量趋势
            recent_versions = sorted(
                module_history.versions[-3:], 
                key=lambda v: v.creation_timestamp
            )
            
            quality_trend = [v.generation_result.quality_score for v in recent_versions]
            
            if len(quality_trend) >= 2 and quality_trend[-1] < quality_trend[-2]:
                suggestions.append({
                    "type": "quality_decline",
                    "message": "最近的生成质量有所下降，建议回到之前的参数设置",
                    "action": "revert_parameters"
                })
        
        # 基于模块类型提供特定建议
        if module_type == ModuleType.IDENTITY:
            suggestions.extend([
                {
                    "type": "lighting_adjustment",
                    "message": "尝试调整为黄金时段光线以增强氛围感",
                    "parameters": {"lighting_adjustment": "golden hour"}
                },
                {
                    "type": "scene_enhancement",
                    "message": "增加更多北美中产生活场景元素",
                    "parameters": {"additional_elements": "middle-class lifestyle elements"}
                }
            ])
        elif module_type == ModuleType.SENSORY:
            suggestions.extend([
                {
                    "type": "detail_enhancement",
                    "message": "增强材质细节的展示效果",
                    "parameters": {"detail_level": "high", "contrast_level": "enhanced"}
                },
                {
                    "type": "angle_adjustment",
                    "message": "尝试不同的3/4视角以突出产品特征",
                    "parameters": {"composition_adjustment": "3/4 angle variation"}
                }
            ])
        elif module_type == ModuleType.EXTENSION:
            suggestions.extend([
                {
                    "type": "carousel_balance",
                    "message": "平衡四个维度的内容重点",
                    "parameters": {"style_emphasis": "balanced carousel content"}
                }
            ])
        elif module_type == ModuleType.TRUST:
            suggestions.extend([
                {
                    "type": "layout_optimization",
                    "message": "优化黄金比例布局以提高信息密度",
                    "parameters": {"composition_adjustment": "golden ratio optimization"}
                }
            ])
        
        return suggestions
    
    def _summarize_parameters(self, parameters: RegenerationParameters) -> Dict[str, Any]:
        """总结参数设置"""
        return {
            "has_custom_modifications": bool(parameters.custom_modifications),
            "has_style_adjustments": bool(parameters.style_adjustments),
            "modification_count": len(parameters.custom_modifications),
            "adjustment_count": len(parameters.style_adjustments),
            "preserve_consistency": parameters.preserve_visual_consistency
        }
    
    def _calculate_improvement_trend(self, versions: List[GenerationVersion]) -> str:
        """计算改进趋势"""
        if len(versions) < 2:
            return "insufficient_data"
        
        # 按时间排序
        sorted_versions = sorted(versions, key=lambda v: v.creation_timestamp)
        
        # 计算质量分数趋势
        quality_scores = [v.generation_result.quality_score for v in sorted_versions]
        
        if len(quality_scores) < 2:
            return "insufficient_data"
        
        # 简单的趋势分析
        first_half_avg = sum(quality_scores[:len(quality_scores)//2]) / (len(quality_scores)//2)
        second_half_avg = sum(quality_scores[len(quality_scores)//2:]) / (len(quality_scores) - len(quality_scores)//2)
        
        if second_half_avg > first_half_avg + 0.1:
            return "improving"
        elif second_half_avg < first_half_avg - 0.1:
            return "declining"
        else:
            return "stable"
    
    def cleanup_old_versions(self, session_id: str, days_to_keep: int = 7):
        """清理旧版本（保留指定天数内的版本）"""
        if session_id not in self.module_histories:
            return
        
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
        
        for module_type, module_history in self.module_histories[session_id].items():
            # 保留原始版本、活跃版本和最近的版本
            versions_to_keep = []
            
            for version in module_history.versions:
                should_keep = (
                    version.version_id == module_history.original_version_id or
                    version.version_id == module_history.active_version_id or
                    version.creation_timestamp >= cutoff_date or
                    version.user_rating is not None  # 保留用户评分过的版本
                )
                
                if should_keep:
                    versions_to_keep.append(version)
            
            module_history.versions = versions_to_keep
    
    def export_module_history(
        self, 
        session_id: str, 
        module_type: ModuleType
    ) -> Optional[Dict[str, Any]]:
        """导出模块历史记录"""
        module_history = self.get_module_history(session_id, module_type)
        if not module_history:
            return None
        
        export_data = {
            "module_type": module_type.value,
            "total_versions": len(module_history.versions),
            "original_version_id": module_history.original_version_id,
            "active_version_id": module_history.active_version_id,
            "versions": []
        }
        
        for version in module_history.versions:
            version_data = {
                "version_id": version.version_id,
                "creation_time": version.creation_timestamp.isoformat(),
                "quality_score": version.generation_result.quality_score,
                "validation_status": version.generation_result.validation_status.value,
                "generation_time": version.generation_result.generation_time,
                "user_rating": version.user_rating,
                "user_notes": version.user_notes,
                "is_active": version.is_active,
                "parameters_summary": self._summarize_parameters(version.parameters_used)
            }
            export_data["versions"].append(version_data)
        
        return export_data