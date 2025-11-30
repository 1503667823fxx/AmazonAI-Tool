# services/hd_upscale/config.py

class UpscaleConfig:
    # Real-ESRGAN A100 快速推理版本 (SOTA standard)
    MODEL_ID = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b"
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 60
