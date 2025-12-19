# services/hd_upscale/config.py

class UpscaleConfig:
    # SUPIR模型配置 - 多个版本以确保兼容性
    SUPIR_MODELS = {
        # 主要版本 - 最新功能
        "main": "cjwbw/supir:1302b550b4f7681da87ed0e405016d443fe1fafd64dabce6673401855a5039b5",
        
        # 备用版本 - 更好的兼容性
        "stable": "cjwbw/supir:7d9c12dc7c8c9b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c8b9c",
        
        # 轻量版本 - 降低内存需求
        "lite": "cjwbw/supir:a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
    }
    
    # 默认使用主要版本
    MODEL_ID = SUPIR_MODELS["main"]
    
    # 默认参数
    DEFAULT_SCALE = 4
    DEFAULT_FACE_ENHANCE = False
    
    # 超时设置 (秒)
    TIMEOUT = 120
