# services/hd_upscale/config.py

class UpscaleConfig:
    # Crystal Upscaler 模型 - 专门优化细节结构
    MODEL_ID = "philz1337x/crystal-upscaler"
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
