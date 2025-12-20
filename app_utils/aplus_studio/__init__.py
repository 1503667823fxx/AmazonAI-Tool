# APlus Studio App Utils
"""
A+Studio工作流系统
基于Streamlit的云端图片制作平台
"""

from .models.core_models import (
    Template, WorkflowSession, ProductData, Category, UploadedFile, Area, WorkflowStatus
)
# from .workflow import WorkflowEngine  # 已移至 services.aplus_studio
# from .file_management.upload_handler import FileUploadHandler  # 目录不存在
# from .ai_processors.gemini_client import GeminiAPIClient  # 目录不存在

# 注意：核心服务已移至 services/aplus_studio/
# 请使用: from services.aplus_studio import TemplateService, CategoryService, SearchService

__version__ = "1.0.0"
__all__ = [
    # 核心数据模型
    "Template", "WorkflowSession", "ProductData", "Category", "UploadedFile", "Area", "WorkflowStatus",
    # 注意：其他组件已移至 services/ 目录
]
