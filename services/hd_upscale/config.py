# services/hd_upscale/config.py

class UpscaleConfig:
    # 使用SUPIR模型 - 先进的超分辨率模型，擅长保持细节结构
    MODEL_ID = "cjwbw/supir:1302b550b4f7681da87ed0e405016d443fe1fafd64dabce6673401855a5039b5"
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
