# services/hd_upscale/config.py

class UpscaleConfig:
    # 经过验证的Replicate平台可用模型
    MODELS = {
        # Real-ESRGAN - 经典通用模型，适合照片和自然图像 (已验证可用)
        "real_esrgan": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
        
        # Real-ESRGAN (另一个版本) - 可能有更好的结构保持
        "real_esrgan_v2": "cjwbw/real-esrgan:d0ee3d708c9b911f122a4ad90046c5d26a0293b99476d697f6bb7f2e251ce2d4"
    }
    
    # 默认使用Real-ESRGAN，但可以根据图像类型切换
    DEFAULT_MODEL = "real_esrgan"
    MODEL_ID = MODELS[DEFAULT_MODEL]
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
