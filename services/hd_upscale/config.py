# services/hd_upscale/config.py

class UpscaleConfig:
    # SUPIR v0q 模型 - 根据你提供的正确代码
    MODEL_ID = "cjwbw/supir-v0q:ede69f6a5ae7d09f769d683347325b08d2f83a93d136ed89747941205e0a71da"
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
