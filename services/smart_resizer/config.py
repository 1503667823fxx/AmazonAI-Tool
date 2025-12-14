"""
Smart Resizer 配置文件
管理不同的Gemini模型选择和参数
"""

# Gemini 模型配置
GEMINI_MODELS = {
    "vision_analysis": "models/gemini-flash-latest",  # 用于背景分析
    "image_generation": "models/gemini-3-pro-image-preview",  # 用于图像生成
    
    # 备选模型
    "fallback_vision": "models/gemini-3-pro-preview",
    "fallback_generation": "models/gemini-2.5-flash-image"
}

# 生成参数配置
GENERATION_CONFIG = {
    "temperature": 0.3,  # 降低随机性，提高一致性
    "candidate_count": 1,
    "max_output_tokens": 4096
}

# 安全设置
SAFETY_SETTINGS = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH", 
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH"
}

# 图像处理参数
IMAGE_PROCESSING = {
    "max_retries": 3,  # 最大重试次数
    "timeout_seconds": 30,  # 超时时间
    "feather_size": 20,  # 羽化边缘大小
    "blur_radius": 0.5  # 后处理模糊半径
}

def get_model_name(model_type: str) -> str:
    """获取指定类型的模型名称"""
    return GEMINI_MODELS.get(model_type, GEMINI_MODELS["vision_analysis"])

def get_generation_config() -> dict:
    """获取生成配置"""
    return GENERATION_CONFIG.copy()

def get_safety_settings() -> dict:
    """获取安全设置"""
    return SAFETY_SETTINGS.copy()
