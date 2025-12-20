"""
A+Studio核心接口定义
定义系统各组件的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app_utils.aplus_studio.models.core_models import (
        Template, WorkflowSession, ProductData, Category, UploadedFile
    )


class ITemplateManager(ABC):
    """模板管理器接口"""
    
    @abstractmethod
    def load_template(self, template_id: str) -> Optional['Template']:
        """加载指定模板"""
        pass
    
    @abstractmethod
    def get_available_templates(self) -> List['Template']:
        """获取所有可用模板"""
        pass
    
    @abstractmethod
    def get_templates_by_category(self, category: str) -> List['Template']:
        """根据分类获取模板"""
        pass
    
    @abstractmethod
    def save_template(self, template: 'Template') -> bool:
        """保存模板"""
        pass
    
    @abstractmethod
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        pass


class ISearchEngine(ABC):
    """搜索引擎接口"""
    
    @abstractmethod
    def search_templates(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索模板"""
        pass
    
    @abstractmethod
    def get_similar_templates(self, template_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取相似模板"""
        pass
    
    @abstractmethod
    def get_search_suggestions(self, query: str) -> List[str]:
        """获取搜索建议"""
        pass


class ICategoryManager(ABC):
    """分类管理器接口"""
    
    @abstractmethod
    def create_category(self, category: 'Category') -> bool:
        """创建分类"""
        pass
    
    @abstractmethod
    def get_category(self, category_id: str) -> Optional['Category']:
        """获取分类"""
        pass
    
    @abstractmethod
    def get_all_categories(self) -> List['Category']:
        """获取所有分类"""
        pass
    
    @abstractmethod
    def update_category(self, category: 'Category') -> bool:
        """更新分类"""
        pass
    
    @abstractmethod
    def delete_category(self, category_id: str) -> bool:
        """删除分类"""
        pass
    
    @abstractmethod
    def get_subcategories(self, parent_id: str) -> List['Category']:
        """获取子分类"""
        pass


class IWorkflowEngine(ABC):
    """工作流引擎接口"""
    
    @abstractmethod
    def create_session(self, user_id: str, template_id: str) -> 'WorkflowSession':
        """创建工作流会话"""
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional['WorkflowSession']:
        """获取工作流会话"""
        pass
    
    @abstractmethod
    def update_session(self, session: 'WorkflowSession') -> bool:
        """更新工作流会话"""
        pass
    
    @abstractmethod
    def next_step(self, session_id: str) -> bool:
        """进入下一步"""
        pass
    
    @abstractmethod
    def previous_step(self, session_id: str) -> bool:
        """返回上一步"""
        pass
    
    @abstractmethod
    def complete_workflow(self, session_id: str) -> bool:
        """完成工作流"""
        pass
    
    @abstractmethod
    def save_progress(self, session_id: str) -> bool:
        """保存进度"""
        pass


class IStepProcessor(ABC):
    """步骤处理器接口"""
    
    @abstractmethod
    def process_step(self, session: 'WorkflowSession', step_data: Dict[str, Any]) -> bool:
        """处理工作流步骤"""
        pass
    
    @abstractmethod
    def validate_step(self, session: 'WorkflowSession', step_number: int) -> bool:
        """验证步骤完成条件"""
        pass
    
    @abstractmethod
    def get_step_requirements(self, step_number: int) -> Dict[str, Any]:
        """获取步骤要求"""
        pass


class IGeminiAPIClient(ABC):
    """Gemini API客户端接口"""
    
    @abstractmethod
    def generate_image(self, prompt: str, **kwargs) -> bytes:
        """生成图片"""
        pass
    
    @abstractmethod
    def compose_images(self, template_image: bytes, product_image: bytes, 
                      instructions: str) -> bytes:
        """合成图片"""
        pass
    
    @abstractmethod
    def enhance_text(self, text: str, context: Dict[str, Any]) -> str:
        """增强文本"""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """验证API密钥"""
        pass


class IImageCompositor(ABC):
    """图片合成器接口"""
    
    @abstractmethod
    def compose(self, template: 'Template', product_data: 'ProductData', 
               options: Dict[str, Any]) -> bytes:
        """合成图片"""
        pass
    
    @abstractmethod
    def resize_image(self, image: bytes, width: int, height: int) -> bytes:
        """调整图片尺寸"""
        pass
    
    @abstractmethod
    def optimize_position(self, template: 'Template', product_image: bytes) -> Dict[str, int]:
        """优化图片位置"""
        pass


class IFileUploadHandler(ABC):
    """文件上传处理器接口"""
    
    @abstractmethod
    def validate_file(self, file: 'UploadedFile') -> List[str]:
        """验证文件"""
        pass
    
    @abstractmethod
    def process_upload(self, file: 'UploadedFile') -> bool:
        """处理上传"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        pass
    
    @abstractmethod
    def get_max_file_size(self) -> int:
        """获取最大文件大小"""
        pass


class IStorageManager(ABC):
    """存储管理器接口"""
    
    @abstractmethod
    def save_file(self, file_path: str, data: bytes) -> bool:
        """保存文件"""
        pass
    
    @abstractmethod
    def load_file(self, file_path: str) -> Optional[bytes]:
        """加载文件"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        pass


class IContentProcessor(ABC):
    """内容处理器接口"""
    
    @abstractmethod
    def process_text(self, text: str, options: Dict[str, Any]) -> str:
        """处理文本内容"""
        pass
    
    @abstractmethod
    def optimize_layout(self, content: Dict[str, Any], style: str) -> Dict[str, Any]:
        """优化布局"""
        pass
    
    @abstractmethod
    def apply_style(self, content: Dict[str, Any], style_name: str) -> Dict[str, Any]:
        """应用样式"""
        pass
