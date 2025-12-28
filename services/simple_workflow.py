"""
简化的A+工作流 - 专为云端Streamlit设计
移除所有无效的持久化、监控、复杂状态管理
只保留核心业务逻辑
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SimpleWorkflow:
    """简化的工作流管理器"""
    
    @staticmethod
    def create_simple_session() -> Dict[str, Any]:
        """创建简单的会话数据"""
        return {
            'session_id': f"session_{int(datetime.now().timestamp())}",
            'current_state': 'INITIAL',
            'created_at': datetime.now().isoformat(),
            'data': {}
        }
    
    @staticmethod
    def save_analysis_result(session: Dict[str, Any], analysis_data: Dict[str, Any]):
        """保存分析结果"""
        session['data']['analysis_result'] = analysis_data
        session['current_state'] = 'ANALYSIS_COMPLETED'
        logger.info("Analysis result saved to simple session")
    
    @staticmethod
    def save_module_recommendation(session: Dict[str, Any], recommendation_data: Dict[str, Any]):
        """保存模块推荐"""
        session['data']['module_recommendation'] = recommendation_data
        session['current_state'] = 'RECOMMENDATION_COMPLETED'
        logger.info("Module recommendation saved to simple session")
    
    @staticmethod
    def save_generated_content(session: Dict[str, Any], content_data: Dict[str, Any]):
        """保存生成内容"""
        session['data']['generated_content'] = content_data
        session['current_state'] = 'CONTENT_GENERATED'
        logger.info("Generated content saved to simple session")
    
    @staticmethod
    def save_final_content(session: Dict[str, Any], final_content: Dict[str, Any]):
        """保存最终内容"""
        session['data']['final_content'] = final_content
        session['current_state'] = 'CONTENT_FINALIZED'
        logger.info("Final content saved to simple session")
    
    @staticmethod
    def save_style_theme(session: Dict[str, Any], style_theme: Dict[str, Any]):
        """保存风格主题"""
        session['data']['style_theme'] = style_theme
        session['current_state'] = 'STYLE_SELECTED'
        logger.info("Style theme saved to simple session")
    
    @staticmethod
    def save_generated_images(session: Dict[str, Any], images_data: Dict[str, Any]):
        """保存生成图片"""
        # 确保数据完全可序列化
        clean_images = {}
        for key, value in images_data.items():
            if isinstance(value, dict):
                clean_images[str(key)] = {
                    'image_path': str(value.get('image_path', '')),
                    'generation_time': float(value.get('generation_time', 0.0)),
                    'quality_score': float(value.get('quality_score', 0.0)),
                    'success': bool(value.get('success', False)),
                    'has_image_data': bool(value.get('has_image_data', False)),
                    'module_name': str(value.get('module_name', str(key))),
                    'generated_at': str(value.get('generated_at', datetime.now().isoformat()))
                }
            else:
                clean_images[str(key)] = str(value)
        
        session['data']['generated_images'] = clean_images
        session['current_state'] = 'IMAGES_GENERATED'
        logger.info(f"Generated images saved to simple session: {len(clean_images)} modules")
    
    @staticmethod
    def get_data(session: Dict[str, Any], key: str) -> Optional[Any]:
        """获取数据"""
        return session.get('data', {}).get(key)
    
    @staticmethod
    def get_current_state(session: Dict[str, Any]) -> str:
        """获取当前状态"""
        return session.get('current_state', 'INITIAL')
    
    @staticmethod
    def set_state(session: Dict[str, Any], state: str):
        """设置状态"""
        session['current_state'] = state
        logger.info(f"State changed to: {state}")

# 简化的数据转换工具
class SimpleDataConverter:
    """简化的数据转换工具"""
    
    @staticmethod
    def complex_to_simple(complex_data: Any) -> Dict[str, Any]:
        """将复杂对象转换为简单字典"""
        if hasattr(complex_data, '__dict__'):
            # 如果是对象，转换为字典
            result = {}
            for key, value in complex_data.__dict__.items():
                if not key.startswith('_'):  # 跳过私有属性
                    result[key] = SimpleDataConverter._clean_value(value)
            return result
        elif isinstance(complex_data, dict):
            # 如果是字典，清理值
            return {k: SimpleDataConverter._clean_value(v) for k, v in complex_data.items()}
        else:
            return SimpleDataConverter._clean_value(complex_data)
    
    @staticmethod
    def _clean_value(value: Any) -> Any:
        """清理值，确保可序列化"""
        if isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, list):
            return [SimpleDataConverter._clean_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: SimpleDataConverter._clean_value(v) for k, v in value.items()}
        elif hasattr(value, 'value'):  # 枚举类型
            return value.value
        elif hasattr(value, '__dict__'):  # 对象
            return SimpleDataConverter.complex_to_simple(value)
        elif value is None:
            return None
        else:
            return str(value)  # 其他类型转为字符串
