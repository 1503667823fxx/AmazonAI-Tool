# services/hd_upscale/config.py

class UpscaleConfig:
    # 2024年最先进的超分辨率模型选择 (基于Replicate平台实际可用模型)
    MODELS = {
        # Real-ESRGAN - 经典通用模型，适合照片和自然图像
        "real_esrgan": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
        
        # GFPGAN - 专门针对人脸修复和增强，保持面部细节
        "gfpgan": "tencentarc/gfpgan:9283608cc6b7be6b65a8e44983db012355fde4132009bf99d976b2f0896856a3",
        
        # CodeFormer - 最新的人脸修复技术，保持身份特征和结构
        "codeformer": "sczhou/codeformer:7de2ea26c616d5bf2245ad0d5e24f0ff9a6204578a5c876db53142edd9d2cd56",
        
        # SwinIR - Transformer架构，细节保持最佳，适合结构图
        "swinir": "jingyunliang/swinir:660d922d33153019e8c594a46de7e5e5d76bdf3b564a86b9c4b7750e30094da0",
        
        # ESRGAN - 增强版，更好的结构保持能力
        "esrgan": "xinntao/esrgan:ac732df83cea7fff18b8472768c88ad0b6f4b240636047ece72d6f057ca1c129",
        
        # BSRGAN - 盲超分辨率，专门处理真实世界的降质图像
        "bsrgan": "cjwbw/real-esrgan:d0ee3d708c9b911f122a4ad90046c5d26a0293b99476d697f6bb7f2e251ce2d4"
    }
    
    # 默认使用Real-ESRGAN，但可以根据图像类型切换
    DEFAULT_MODEL = "real_esrgan"
    MODEL_ID = MODELS[DEFAULT_MODEL]
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
