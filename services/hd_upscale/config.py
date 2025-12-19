# services/hd_upscale/config.py

class UpscaleConfig:
    # 使用经过验证的稳定模型 - 专门优化细节结构保持
    # Real-ESRGAN x4plus 版本，对细节结构有更好的保持能力
    MODEL_ID = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
