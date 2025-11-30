import streamlit as st
import replicate
import os

# ==========================================
# 1. 自动鉴权 (兼容大小写配置)
# ==========================================
token = st.secrets.get("replicate_api_token") or st.secrets.get("REPLICATE_API_TOKEN")
if token:
    os.environ["REPLICATE_API_TOKEN"] = token

def generate_image_replicate(prompt: str, aspect_ratio: str, output_format: str = "jpg", safety_tolerance: int = 2) -> str:
    """
    调用最新的 Flux 1.1 Pro 模型生成图片。
    
    Args:
        prompt: 提示词
        aspect_ratio: 比例 (如 "16:9")
        output_format: "jpg" 或 "png" (Pro 推荐 jpg)
        safety_tolerance: 安全过滤等级 (1-5)
    """
    
    # 检查 Token
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError("❌ 未检测到 Replicate Token，请检查 Secrets 配置。")

    # 🔥 核心升级：使用最新的 Flux 1.1 Pro
    model_id = "black-forest-labs/flux-1.1-pro"
    
    # 构建参数 (完全遵循官方文档)
    input_params = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "output_quality": 90,        # Pro 建议的高画质参数
        "safety_tolerance": safety_tolerance,
        "prompt_upsampling": True    # 🌟 开启自动优化，这是 Pro 的强项
    }
    
    print(f"🚀 [Flux 1.1 Pro] Starting generation...")
    print(f"📋 Params: {input_params}")

    try:
        # 调用 API
        output = replicate.run(
            model_id,
            input=input_params
        )
        
        # --- 结果解析 (针对 Flux 1.1 Pro 的特殊处理) ---
        # 文档显示 output 是一个 FileOutput 对象，而不是列表
        
        print(f"📦 Response Type: {type(output)}")
        
        # 1. 尝试直接转字符串 (Replicate SDK 通用方法)
        image_url = str(output)
        
        # 2. 如果是 FileOutput 对象，确保拿到的是 URL
        # 有些版本可能需要调用 output.url，但通常 str(output) 已经是 URL 了
        if hasattr(output, 'url') and callable(output.url):
             image_url = output.url()
        
        # 验证是否为有效 URL
        if image_url and image_url.startswith("http"):
            return image_url
        else:
            raise ValueError(f"API 返回了非 URL 内容: {output}")

    except replicate.exceptions.ReplicateError as e:
        # 捕捉官方 API 报错 (如余额不足、NSFW拦截)
        error_msg = str(e)
        if "NSFW" in error_msg:
            raise ValueError("🙈 提示词触发了安全审查，请尝试更温和的描述。")
        else:
            raise RuntimeError(f"Replicate 服务端错误: {error_msg}")
            
    except Exception as e:
        raise RuntimeError(f"生图流程异常: {str(e)}")
