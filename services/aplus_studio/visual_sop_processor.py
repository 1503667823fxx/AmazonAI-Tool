"""
Visual SOP (Standard Operating Procedure) Processor for A+ Studio system.

This service ensures visual consistency across all A+ modules by implementing
color palette locking, style conflict detection, and visual coherence validation.
"""

import colorsys
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from PIL import Image

from .models import (
    VisualStyle, ModuleType, GenerationResult, AnalysisResult,
    ValidationResult, ValidationStatus
)


@dataclass
class ColorAnalysis:
    """颜色分析结果"""
    dominant_colors: List[Tuple[int, int, int]]  # RGB values
    color_harmony_score: float
    brightness_distribution: Dict[str, float]
    saturation_levels: Dict[str, float]
    color_temperature: float  # Kelvin scale approximation


@dataclass
class StyleConsistencyMetrics:
    """风格一致性评估指标"""
    color_consistency_score: float
    lighting_consistency_score: float
    composition_consistency_score: float
    overall_coherence_score: float
    detected_conflicts: List[str]
    improvement_suggestions: List[str]


class VisualSOPProcessor:
    """视觉连贯性协议处理器 - 确保所有模块的视觉风格一致性"""
    
    def __init__(self):
        self.color_tolerance = 30  # RGB color difference tolerance
        self.brightness_tolerance = 0.15  # Brightness variation tolerance
        self.saturation_tolerance = 0.2  # Saturation variation tolerance
        
        # 预定义的和谐色彩关系
        self.harmony_rules = {
            'complementary': 180,  # 互补色
            'triadic': 120,        # 三角色
            'analogous': 30,       # 类似色
            'split_complementary': [150, 210],  # 分裂互补色
            'tetradic': [90, 180, 270]  # 四角色
        }
    
    def lock_color_palette(self, reference_analysis: AnalysisResult) -> Dict[str, Any]:
        """锁定色调盘 - 基于参考分析结果建立色彩标准"""
        visual_style = reference_analysis.visual_style
        image_analysis = reference_analysis.image_analysis
        
        # 提取主色调信息
        primary_colors = self._parse_color_strings(visual_style.color_palette)
        
        # 生成扩展色调盘
        extended_palette = self._generate_extended_palette(primary_colors)
        
        # 建立色彩一致性规则
        color_rules = {
            'primary_colors': primary_colors,
            'extended_palette': extended_palette,
            'harmony_type': self._detect_harmony_type(primary_colors),
            'temperature_range': self._calculate_temperature_range(primary_colors),
            'saturation_guidelines': self._establish_saturation_guidelines(primary_colors),
            'brightness_guidelines': self._establish_brightness_guidelines(primary_colors)
        }
        
        return {
            'locked_palette': color_rules,
            'consistency_threshold': {
                'color_deviation': self.color_tolerance,
                'brightness_deviation': self.brightness_tolerance,
                'saturation_deviation': self.saturation_tolerance
            },
            'visual_guidelines': {
                'lighting_style': visual_style.lighting_style,
                'composition_rules': visual_style.composition_rules,
                'aesthetic_direction': visual_style.aesthetic_direction
            }
        }
    
    def validate_visual_consistency(self, 
                                  module_results: Dict[ModuleType, GenerationResult],
                                  locked_palette: Dict[str, Any]) -> StyleConsistencyMetrics:
        """验证模块间的视觉一致性"""
        
        if not module_results:
            return StyleConsistencyMetrics(
                color_consistency_score=0.0,
                lighting_consistency_score=0.0,
                composition_consistency_score=0.0,
                overall_coherence_score=0.0,
                detected_conflicts=[],
                improvement_suggestions=["No module results to analyze"]
            )
        
        # 分析每个模块的视觉特征
        module_analyses = {}
        for module_type, result in module_results.items():
            if result.image_data:
                analysis = self._analyze_image_visual_features(result.image_data)
                module_analyses[module_type] = analysis
        
        if not module_analyses:
            return StyleConsistencyMetrics(
                color_consistency_score=0.0,
                lighting_consistency_score=0.0,
                composition_consistency_score=0.0,
                overall_coherence_score=0.0,
                detected_conflicts=["No valid images to analyze"],
                improvement_suggestions=["Generate images first"]
            )
        
        # 计算一致性评分
        color_score = self._calculate_color_consistency(module_analyses, locked_palette)
        lighting_score = self._calculate_lighting_consistency(module_analyses)
        composition_score = self._calculate_composition_consistency(module_analyses)
        
        # 检测风格冲突
        conflicts = self._detect_style_conflicts(module_analyses, locked_palette)
        
        # 生成改进建议
        suggestions = self._generate_improvement_suggestions(
            module_analyses, locked_palette, conflicts
        )
        
        # 计算整体连贯性评分
        overall_score = (color_score + lighting_score + composition_score) / 3
        
        return StyleConsistencyMetrics(
            color_consistency_score=color_score,
            lighting_consistency_score=lighting_score,
            composition_consistency_score=composition_score,
            overall_coherence_score=overall_score,
            detected_conflicts=conflicts,
            improvement_suggestions=suggestions
        )
    
    def detect_style_conflicts(self, 
                             module_results: Dict[ModuleType, GenerationResult],
                             locked_palette: Dict[str, Any]) -> List[str]:
        """检测风格冲突"""
        conflicts = []
        
        if len(module_results) < 2:
            return conflicts
        
        # 分析每个模块的视觉特征
        module_analyses = {}
        for module_type, result in module_results.items():
            if result.image_data:
                analysis = self._analyze_image_visual_features(result.image_data)
                module_analyses[module_type] = analysis
        
        # 检查色彩冲突
        color_conflicts = self._check_color_conflicts(module_analyses, locked_palette)
        conflicts.extend(color_conflicts)
        
        # 检查光照冲突
        lighting_conflicts = self._check_lighting_conflicts(module_analyses)
        conflicts.extend(lighting_conflicts)
        
        # 检查构图冲突
        composition_conflicts = self._check_composition_conflicts(module_analyses)
        conflicts.extend(composition_conflicts)
        
        return conflicts
    
    def ensure_module_coherence(self, 
                               target_module: ModuleType,
                               existing_results: Dict[ModuleType, GenerationResult],
                               locked_palette: Dict[str, Any]) -> Dict[str, Any]:
        """确保新模块与现有模块的连贯性"""
        
        if not existing_results:
            # 如果没有现有结果，返回基础一致性要求
            return self._get_baseline_coherence_requirements(locked_palette)
        
        # 分析现有模块的视觉特征
        existing_analyses = {}
        for module_type, result in existing_results.items():
            if result.image_data:
                analysis = self._analyze_image_visual_features(result.image_data)
                existing_analyses[module_type] = analysis
        
        # 计算目标模块应该遵循的视觉参数
        coherence_requirements = {
            'color_constraints': self._calculate_color_constraints(existing_analyses, locked_palette),
            'lighting_constraints': self._calculate_lighting_constraints(existing_analyses),
            'composition_constraints': self._calculate_composition_constraints(existing_analyses),
            'module_specific_adjustments': self._get_module_specific_adjustments(target_module)
        }
        
        return coherence_requirements
    
    def _parse_color_strings(self, color_strings: List[str]) -> List[Tuple[int, int, int]]:
        """解析颜色字符串为RGB值"""
        colors = []
        for color_str in color_strings:
            try:
                # 尝试解析十六进制颜色
                if color_str.startswith('#'):
                    hex_color = color_str[1:]
                    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    colors.append(rgb)
                # 尝试解析颜色名称（简化处理）
                elif color_str.lower() in self._get_color_name_mapping():
                    rgb = self._get_color_name_mapping()[color_str.lower()]
                    colors.append(rgb)
                else:
                    # 默认处理：基于颜色描述生成近似RGB
                    rgb = self._approximate_color_from_description(color_str)
                    colors.append(rgb)
            except Exception:
                # 如果解析失败，使用默认颜色
                colors.append((128, 128, 128))  # 中性灰
        
        return colors
    
    def _generate_extended_palette(self, primary_colors: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """基于主色调生成扩展色调盘"""
        extended = list(primary_colors)
        
        for color in primary_colors:
            # 生成明度变化
            lighter = tuple(min(255, int(c * 1.3)) for c in color)
            darker = tuple(max(0, int(c * 0.7)) for c in color)
            extended.extend([lighter, darker])
            
            # 生成饱和度变化
            hsv = colorsys.rgb_to_hsv(color[0]/255, color[1]/255, color[2]/255)
            # 降低饱和度
            desaturated_hsv = (hsv[0], hsv[1] * 0.6, hsv[2])
            desaturated_rgb = colorsys.hsv_to_rgb(*desaturated_hsv)
            desaturated = tuple(int(c * 255) for c in desaturated_rgb)
            extended.append(desaturated)
        
        return extended
    
    def _detect_harmony_type(self, colors: List[Tuple[int, int, int]]) -> str:
        """检测色彩和谐类型"""
        if len(colors) < 2:
            return 'monochromatic'
        
        # 转换为HSV以分析色相关系
        hues = []
        for color in colors:
            hsv = colorsys.rgb_to_hsv(color[0]/255, color[1]/255, color[2]/255)
            hues.append(hsv[0] * 360)  # 转换为度数
        
        # 分析色相差异
        hue_differences = []
        for i in range(len(hues)):
            for j in range(i+1, len(hues)):
                diff = abs(hues[i] - hues[j])
                diff = min(diff, 360 - diff)  # 考虑色环的循环性
                hue_differences.append(diff)
        
        if not hue_differences:
            return 'monochromatic'
        
        avg_diff = sum(hue_differences) / len(hue_differences)
        
        # 根据平均色相差异判断和谐类型
        if avg_diff < 30:
            return 'analogous'
        elif 150 < avg_diff < 210:
            return 'complementary'
        elif 90 < avg_diff < 150:
            return 'triadic'
        else:
            return 'complex'
    
    def _calculate_temperature_range(self, colors: List[Tuple[int, int, int]]) -> Tuple[float, float]:
        """计算色温范围"""
        temperatures = []
        for color in colors:
            # 简化的色温计算
            r, g, b = color
            if b > r:
                # 偏冷色调
                temp = 6500 + (b - r) * 10
            else:
                # 偏暖色调
                temp = 3000 + (r - b) * 5
            temperatures.append(temp)
        
        return (min(temperatures), max(temperatures))
    
    def _establish_saturation_guidelines(self, colors: List[Tuple[int, int, int]]) -> Dict[str, float]:
        """建立饱和度指导原则"""
        saturations = []
        for color in colors:
            hsv = colorsys.rgb_to_hsv(color[0]/255, color[1]/255, color[2]/255)
            saturations.append(hsv[1])
        
        return {
            'min_saturation': max(0.0, min(saturations) - 0.2),
            'max_saturation': min(1.0, max(saturations) + 0.2),
            'target_saturation': sum(saturations) / len(saturations)
        }
    
    def _establish_brightness_guidelines(self, colors: List[Tuple[int, int, int]]) -> Dict[str, float]:
        """建立亮度指导原则"""
        brightnesses = []
        for color in colors:
            hsv = colorsys.rgb_to_hsv(color[0]/255, color[1]/255, color[2]/255)
            brightnesses.append(hsv[2])
        
        return {
            'min_brightness': max(0.0, min(brightnesses) - 0.2),
            'max_brightness': min(1.0, max(brightnesses) + 0.2),
            'target_brightness': sum(brightnesses) / len(brightnesses)
        }
    
    def _analyze_image_visual_features(self, image_data: bytes) -> ColorAnalysis:
        """分析图片的视觉特征"""
        try:
            # 将字节数据转换为PIL图像
            import io
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 提取主要颜色
            dominant_colors = self._extract_dominant_colors(image)
            
            # 计算色彩和谐度
            harmony_score = self._calculate_color_harmony(dominant_colors)
            
            # 分析亮度分布
            brightness_dist = self._analyze_brightness_distribution(image)
            
            # 分析饱和度水平
            saturation_levels = self._analyze_saturation_levels(image)
            
            # 估算色温
            color_temp = self._estimate_color_temperature(dominant_colors)
            
            return ColorAnalysis(
                dominant_colors=dominant_colors,
                color_harmony_score=harmony_score,
                brightness_distribution=brightness_dist,
                saturation_levels=saturation_levels,
                color_temperature=color_temp
            )
        
        except Exception as e:
            # 返回默认分析结果
            return ColorAnalysis(
                dominant_colors=[(128, 128, 128)],
                color_harmony_score=0.5,
                brightness_distribution={'low': 0.3, 'mid': 0.4, 'high': 0.3},
                saturation_levels={'low': 0.3, 'mid': 0.4, 'high': 0.3},
                color_temperature=5500.0
            )
    
    def _extract_dominant_colors(self, image: Image.Image, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """提取图像的主要颜色"""
        # 缩小图像以提高处理速度
        image = image.resize((150, 150))
        
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 获取所有像素
        pixels = list(image.getdata())
        
        # 使用简化方法提取主要颜色
        return self._simple_dominant_colors(pixels, num_colors)
    
    def _simple_dominant_colors(self, pixels: List[Tuple[int, int, int]], num_colors: int) -> List[Tuple[int, int, int]]:
        """简化的主要颜色提取方法"""
        # 量化颜色空间
        quantized_pixels = []
        for r, g, b in pixels:
            # 将颜色量化到32的倍数
            quantized = ((r // 32) * 32, (g // 32) * 32, (b // 32) * 32)
            quantized_pixels.append(quantized)
        
        # 统计颜色频率
        color_counts = {}
        for color in quantized_pixels:
            color_counts[color] = color_counts.get(color, 0) + 1
        
        # 按频率排序
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前N个颜色
        return [color for color, count in sorted_colors[:num_colors]]
    
    def _calculate_color_harmony(self, colors: List[Tuple[int, int, int]]) -> float:
        """计算色彩和谐度"""
        if len(colors) < 2:
            return 1.0
        
        harmony_scores = []
        
        for i in range(len(colors)):
            for j in range(i+1, len(colors)):
                color1 = colors[i]
                color2 = colors[j]
                
                # 转换为HSV
                hsv1 = colorsys.rgb_to_hsv(color1[0]/255, color1[1]/255, color1[2]/255)
                hsv2 = colorsys.rgb_to_hsv(color2[0]/255, color2[1]/255, color2[2]/255)
                
                # 计算色相差异
                hue_diff = abs(hsv1[0] - hsv2[0]) * 360
                hue_diff = min(hue_diff, 360 - hue_diff)
                
                # 评估和谐度
                harmony = 0.0
                for rule_name, rule_value in self.harmony_rules.items():
                    if isinstance(rule_value, list):
                        for val in rule_value:
                            if abs(hue_diff - val) < 15:
                                harmony = max(harmony, 0.9)
                    else:
                        if abs(hue_diff - rule_value) < 15:
                            harmony = max(harmony, 0.9)
                
                # 如果不符合标准和谐规则，基于差异计算分数
                if harmony == 0.0:
                    if hue_diff < 30:  # 类似色
                        harmony = 0.7
                    elif hue_diff > 150:  # 对比色
                        harmony = 0.6
                    else:
                        harmony = 0.4
                
                harmony_scores.append(harmony)
        
        return sum(harmony_scores) / len(harmony_scores) if harmony_scores else 1.0
    
    def _analyze_brightness_distribution(self, image: Image.Image) -> Dict[str, float]:
        """分析亮度分布"""
        # 转换为灰度图像
        gray = image.convert('L')
        pixels = list(gray.getdata())
        
        # 计算亮度分布
        low_count = sum(1 for p in pixels if p < 85)
        mid_count = sum(1 for p in pixels if 85 <= p < 170)
        high_count = sum(1 for p in pixels if p >= 170)
        
        total = len(pixels)
        
        return {
            'low': low_count / total,
            'mid': mid_count / total,
            'high': high_count / total
        }
    
    def _analyze_saturation_levels(self, image: Image.Image) -> Dict[str, float]:
        """分析饱和度水平"""
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        pixels = list(image.getdata())
        
        saturations = []
        # 采样以提高速度
        for i in range(0, len(pixels), 100):
            pixel = pixels[i]
            hsv = colorsys.rgb_to_hsv(pixel[0]/255, pixel[1]/255, pixel[2]/255)
            saturations.append(hsv[1])
        
        low_count = sum(1 for s in saturations if s < 0.3)
        mid_count = sum(1 for s in saturations if 0.3 <= s < 0.7)
        high_count = sum(1 for s in saturations if s >= 0.7)
        
        total = len(saturations)
        
        return {
            'low': low_count / total,
            'mid': mid_count / total,
            'high': high_count / total
        }
    
    def _estimate_color_temperature(self, colors: List[Tuple[int, int, int]]) -> float:
        """估算色温"""
        if not colors:
            return 5500.0  # 默认中性色温
        
        total_temp = 0.0
        for color in colors:
            r, g, b = color
            
            # 简化的色温估算
            if b > r + g:
                # 偏蓝（冷色调）
                temp = 6500 + (b - max(r, g)) * 20
            elif r > b + g:
                # 偏红（暖色调）
                temp = 3000 + (r - max(b, g)) * 10
            else:
                # 中性
                temp = 5500
            
            total_temp += temp
        
        return total_temp / len(colors)
    
    def _calculate_color_consistency(self, 
                                   module_analyses: Dict[ModuleType, ColorAnalysis],
                                   locked_palette: Dict[str, Any]) -> float:
        """计算色彩一致性评分"""
        if len(module_analyses) < 2:
            return 1.0
        
        consistency_scores = []
        analyses = list(module_analyses.values())
        
        # 比较每对模块的色彩一致性
        for i in range(len(analyses)):
            for j in range(i+1, len(analyses)):
                score = self._compare_color_consistency(analyses[i], analyses[j], locked_palette)
                consistency_scores.append(score)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0
    
    def _calculate_lighting_consistency(self, module_analyses: Dict[ModuleType, ColorAnalysis]) -> float:
        """计算光照一致性评分"""
        if len(module_analyses) < 2:
            return 1.0
        
        # 比较色温一致性
        temperatures = [analysis.color_temperature for analysis in module_analyses.values()]
        if len(temperatures) > 1:
            temp_variance = sum((t - sum(temperatures)/len(temperatures))**2 for t in temperatures) / len(temperatures)
            temp_score = max(0.0, 1.0 - temp_variance / 1000000)  # 归一化
        else:
            temp_score = 1.0
        
        # 比较亮度分布一致性
        brightness_scores = []
        analyses = list(module_analyses.values())
        
        for i in range(len(analyses)):
            for j in range(i+1, len(analyses)):
                brightness_diff = 0.0
                for level in ['low', 'mid', 'high']:
                    diff = abs(analyses[i].brightness_distribution[level] - 
                             analyses[j].brightness_distribution[level])
                    brightness_diff += diff
                
                brightness_score = max(0.0, 1.0 - brightness_diff / 3)
                brightness_scores.append(brightness_score)
        
        brightness_consistency = sum(brightness_scores) / len(brightness_scores) if brightness_scores else 1.0
        
        return (temp_score + brightness_consistency) / 2
    
    def _calculate_composition_consistency(self, module_analyses: Dict[ModuleType, ColorAnalysis]) -> float:
        """计算构图一致性评分"""
        # 这里简化处理，主要基于饱和度分布的一致性
        if len(module_analyses) < 2:
            return 1.0
        
        saturation_scores = []
        analyses = list(module_analyses.values())
        
        for i in range(len(analyses)):
            for j in range(i+1, len(analyses)):
                saturation_diff = 0.0
                for level in ['low', 'mid', 'high']:
                    diff = abs(analyses[i].saturation_levels[level] - 
                             analyses[j].saturation_levels[level])
                    saturation_diff += diff
                
                saturation_score = max(0.0, 1.0 - saturation_diff / 3)
                saturation_scores.append(saturation_score)
        
        return sum(saturation_scores) / len(saturation_scores) if saturation_scores else 1.0
    
    def _compare_color_consistency(self, 
                                 analysis1: ColorAnalysis, 
                                 analysis2: ColorAnalysis,
                                 locked_palette: Dict[str, Any]) -> float:
        """比较两个分析结果的色彩一致性"""
        # 比较主要颜色的相似性
        color_similarity = self._calculate_color_similarity(
            analysis1.dominant_colors, analysis2.dominant_colors
        )
        
        # 比较色彩和谐度
        harmony_similarity = 1.0 - abs(analysis1.color_harmony_score - analysis2.color_harmony_score)
        
        # 比较色温
        temp_similarity = 1.0 - min(1.0, abs(analysis1.color_temperature - analysis2.color_temperature) / 3000)
        
        return (color_similarity + harmony_similarity + temp_similarity) / 3
    
    def _calculate_color_similarity(self, 
                                  colors1: List[Tuple[int, int, int]], 
                                  colors2: List[Tuple[int, int, int]]) -> float:
        """计算两组颜色的相似性"""
        if not colors1 or not colors2:
            return 0.0
        
        similarities = []
        
        for color1 in colors1:
            best_similarity = 0.0
            for color2 in colors2:
                # 计算欧几里得距离
                distance = math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))
                # 转换为相似性分数（0-1）
                similarity = max(0.0, 1.0 - distance / (255 * math.sqrt(3)))
                best_similarity = max(best_similarity, similarity)
            
            similarities.append(best_similarity)
        
        return sum(similarities) / len(similarities)
    
    def _detect_style_conflicts(self, 
                              module_analyses: Dict[ModuleType, ColorAnalysis],
                              locked_palette: Dict[str, Any]) -> List[str]:
        """检测风格冲突"""
        conflicts = []
        
        # 检查色彩冲突
        color_conflicts = self._check_color_conflicts(module_analyses, locked_palette)
        conflicts.extend(color_conflicts)
        
        # 检查光照冲突
        lighting_conflicts = self._check_lighting_conflicts(module_analyses)
        conflicts.extend(lighting_conflicts)
        
        return conflicts
    
    def _check_color_conflicts(self, 
                             module_analyses: Dict[ModuleType, ColorAnalysis],
                             locked_palette: Dict[str, Any]) -> List[str]:
        """检查色彩冲突"""
        conflicts = []
        
        if len(module_analyses) < 2:
            return conflicts
        
        # 检查色温差异
        temperatures = [(module, analysis.color_temperature) 
                       for module, analysis in module_analyses.items()]
        
        for i in range(len(temperatures)):
            for j in range(i+1, len(temperatures)):
                module1, temp1 = temperatures[i]
                module2, temp2 = temperatures[j]
                
                if abs(temp1 - temp2) > 2000:  # 色温差异超过2000K
                    conflicts.append(
                        f"Color temperature conflict between {module1.value} "
                        f"({temp1:.0f}K) and {module2.value} ({temp2:.0f}K)"
                    )
        
        # 检查色彩和谐度差异
        harmonies = [(module, analysis.color_harmony_score) 
                    for module, analysis in module_analyses.items()]
        
        for i in range(len(harmonies)):
            for j in range(i+1, len(harmonies)):
                module1, harmony1 = harmonies[i]
                module2, harmony2 = harmonies[j]
                
                if abs(harmony1 - harmony2) > 0.4:  # 和谐度差异过大
                    conflicts.append(
                        f"Color harmony conflict between {module1.value} "
                        f"({harmony1:.2f}) and {module2.value} ({harmony2:.2f})"
                    )
        
        return conflicts
    
    def _check_lighting_conflicts(self, module_analyses: Dict[ModuleType, ColorAnalysis]) -> List[str]:
        """检查光照冲突"""
        conflicts = []
        
        if len(module_analyses) < 2:
            return conflicts
        
        # 检查亮度分布差异
        analyses = list(module_analyses.items())
        
        for i in range(len(analyses)):
            for j in range(i+1, len(analyses)):
                module1, analysis1 = analyses[i]
                module2, analysis2 = analyses[j]
                
                # 计算亮度分布差异
                brightness_diff = sum(
                    abs(analysis1.brightness_distribution[level] - 
                        analysis2.brightness_distribution[level])
                    for level in ['low', 'mid', 'high']
                )
                
                if brightness_diff > 0.6:  # 亮度分布差异过大
                    conflicts.append(
                        f"Lighting distribution conflict between {module1.value} and {module2.value}"
                    )
        
        return conflicts
    
    def _check_composition_conflicts(self, module_analyses: Dict[ModuleType, ColorAnalysis]) -> List[str]:
        """检查构图冲突"""
        conflicts = []
        
        # 这里可以添加更复杂的构图分析
        # 目前简化处理，主要检查饱和度分布
        
        if len(module_analyses) < 2:
            return conflicts
        
        analyses = list(module_analyses.items())
        
        for i in range(len(analyses)):
            for j in range(i+1, len(analyses)):
                module1, analysis1 = analyses[i]
                module2, analysis2 = analyses[j]
                
                # 计算饱和度分布差异
                saturation_diff = sum(
                    abs(analysis1.saturation_levels[level] - 
                        analysis2.saturation_levels[level])
                    for level in ['low', 'mid', 'high']
                )
                
                if saturation_diff > 0.7:  # 饱和度分布差异过大
                    conflicts.append(
                        f"Saturation distribution conflict between {module1.value} and {module2.value}"
                    )
        
        return conflicts
    
    def _generate_improvement_suggestions(self, 
                                        module_analyses: Dict[ModuleType, ColorAnalysis],
                                        locked_palette: Dict[str, Any],
                                        conflicts: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if not conflicts:
            suggestions.append("Visual consistency is good across all modules")
            return suggestions
        
        # 基于冲突类型生成建议
        for conflict in conflicts:
            if "Color temperature" in conflict:
                suggestions.append("Adjust lighting conditions to maintain consistent color temperature")
            elif "Color harmony" in conflict:
                suggestions.append("Ensure all modules use colors from the locked palette")
            elif "Lighting distribution" in conflict:
                suggestions.append("Standardize lighting setup across all module generations")
            elif "Saturation distribution" in conflict:
                suggestions.append("Balance saturation levels to maintain visual coherence")
        
        # 添加通用建议
        if len(conflicts) > 2:
            suggestions.append("Consider regenerating modules with stronger visual consistency constraints")
        
        return suggestions
    
    def _get_baseline_coherence_requirements(self, locked_palette: Dict[str, Any]) -> Dict[str, Any]:
        """获取基础连贯性要求"""
        return {
            'color_constraints': {
                'use_locked_palette': True,
                'maintain_color_harmony': True,
                'color_temperature_range': locked_palette.get('temperature_range', (4000, 7000))
            },
            'lighting_constraints': {
                'consistent_lighting_style': True,
                'maintain_brightness_balance': True
            },
            'composition_constraints': {
                'follow_visual_guidelines': True,
                'maintain_aesthetic_direction': True
            },
            'module_specific_adjustments': {}
        }
    
    def _calculate_color_constraints(self, 
                                   existing_analyses: Dict[ModuleType, ColorAnalysis],
                                   locked_palette: Dict[str, Any]) -> Dict[str, Any]:
        """计算色彩约束"""
        if not existing_analyses:
            return self._get_baseline_coherence_requirements(locked_palette)['color_constraints']
        
        # 计算现有模块的平均色温
        avg_temp = sum(analysis.color_temperature for analysis in existing_analyses.values()) / len(existing_analyses)
        
        # 计算色彩和谐度范围
        harmonies = [analysis.color_harmony_score for analysis in existing_analyses.values()]
        min_harmony = min(harmonies)
        max_harmony = max(harmonies)
        
        return {
            'target_color_temperature': avg_temp,
            'temperature_tolerance': 500,  # ±500K
            'harmony_range': (max(0.0, min_harmony - 0.1), min(1.0, max_harmony + 0.1)),
            'use_existing_dominant_colors': True
        }
    
    def _calculate_lighting_constraints(self, existing_analyses: Dict[ModuleType, ColorAnalysis]) -> Dict[str, Any]:
        """计算光照约束"""
        if not existing_analyses:
            return {'maintain_consistent_lighting': True}
        
        # 计算平均亮度分布
        avg_brightness = {'low': 0.0, 'mid': 0.0, 'high': 0.0}
        for analysis in existing_analyses.values():
            for level in avg_brightness:
                avg_brightness[level] += analysis.brightness_distribution[level]
        
        for level in avg_brightness:
            avg_brightness[level] /= len(existing_analyses)
        
        return {
            'target_brightness_distribution': avg_brightness,
            'brightness_tolerance': 0.15,
            'maintain_lighting_style': True
        }
    
    def _calculate_composition_constraints(self, existing_analyses: Dict[ModuleType, ColorAnalysis]) -> Dict[str, Any]:
        """计算构图约束"""
        if not existing_analyses:
            return {'maintain_composition_style': True}
        
        # 计算平均饱和度分布
        avg_saturation = {'low': 0.0, 'mid': 0.0, 'high': 0.0}
        for analysis in existing_analyses.values():
            for level in avg_saturation:
                avg_saturation[level] += analysis.saturation_levels[level]
        
        for level in avg_saturation:
            avg_saturation[level] /= len(existing_analyses)
        
        return {
            'target_saturation_distribution': avg_saturation,
            'saturation_tolerance': 0.2,
            'maintain_composition_balance': True
        }
    
    def _get_module_specific_adjustments(self, module_type: ModuleType) -> Dict[str, Any]:
        """获取模块特定的调整要求"""
        adjustments = {
            ModuleType.IDENTITY: {
                'emphasis': 'lifestyle_integration',
                'lighting_preference': 'golden_hour',
                'color_warmth': 'slightly_warm'
            },
            ModuleType.SENSORY: {
                'emphasis': 'material_details',
                'lighting_preference': 'high_contrast',
                'color_accuracy': 'precise_material_colors'
            },
            ModuleType.EXTENSION: {
                'emphasis': 'scenario_diversity',
                'lighting_preference': 'adaptive_per_scenario',
                'color_consistency': 'maintain_across_slides'
            },
            ModuleType.TRUST: {
                'emphasis': 'information_clarity',
                'lighting_preference': 'clear_readable',
                'color_balance': 'text_image_harmony'
            }
        }
        
        return adjustments.get(module_type, {})
    
    def _get_color_name_mapping(self) -> Dict[str, Tuple[int, int, int]]:
        """获取颜色名称到RGB的映射"""
        return {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'gray': (128, 128, 128),
            'yellow': (255, 255, 0),
            'orange': (255, 165, 0),
            'purple': (128, 0, 128),
            'pink': (255, 192, 203),
            'brown': (165, 42, 42),
            'navy': (0, 0, 128),
            'gold': (255, 215, 0),
            'silver': (192, 192, 192)
        }
    
    def _approximate_color_from_description(self, description: str) -> Tuple[int, int, int]:
        """基于颜色描述近似RGB值"""
        description = description.lower()
        
        # 简化的颜色描述映射
        if 'warm' in description or 'golden' in description:
            return (255, 200, 100)
        elif 'cool' in description or 'blue' in description:
            return (100, 150, 255)
        elif 'neutral' in description or 'gray' in description:
            return (128, 128, 128)
        elif 'dark' in description:
            return (64, 64, 64)
        elif 'light' in description:
            return (224, 224, 224)
        else:
            return (128, 128, 128)  # 默认中性灰