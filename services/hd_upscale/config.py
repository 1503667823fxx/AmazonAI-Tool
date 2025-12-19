# services/hd_upscale/config.py

class UpscaleConfig:
    # 模型选择 - 针对不同场景优化
    MODELS = {
        # Real-ESRGAN - 适合照片和自然图像
        "real_esrgan": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
        
        # ESRGAN - 更好的结构保持能力
        "esrgan": "xinntao/esrgan:ac732df83cea7fff18b8472768c88ad0b6f4b240636047ece72d6f057ca1c129",
        
        # SwinIR - 专门针对细节结构优化
        "swinir": "jingyunliang/swinir:660d922d33153019e8c594a46de7e5e5d76bdf3b564a86b9c4b7750e30094da0"
    }
    
    # 默认使用Real-ESRGAN，但可以根据图像类型切换
    DEFAULT_MODEL = "real_esrgan"
    MODEL_ID = MODELS[DEFAULT_MODEL]
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 60
