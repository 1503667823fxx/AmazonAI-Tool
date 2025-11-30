import streamlit as st
import replicate
import os

# ==========================================
# 1. 鉴权配置 (增强健壮性)
# ==========================================
# 优先读取 REPLICATE_API_TOKEN，兼容大小写
token = st.secrets.get("replicate_api_token") or st.secrets.get("REPLICATE_API_TOKEN")
if token:
    os.environ["REPLICATE_API_TOKEN"] = token

def generate_image_replicate(prompt: str, aspect_ratio: str, output_format: str = "webp", safety_tolerance: int = 2) -> str:
    """
    调用 Replicate 上的 Flux 模型生成图片 (带详细调试信息)。
    """
    
    # 检查 Token 是否存在
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError("❌ 未检测到 Replicate API Token。请在 secrets.toml 中配置。")

    # 2. 确定模型 ID (使用官方别名)
    # flux-schnell: 速度快 (0.01$/图)
    # flux-dev: 质量高 (0.025$/图)
    model_id = "black-forest-labs/flux-schnell"
    
    # 3. 构建参数
    # 注意: Flux 对 aspect_ratio 的要求必须是特定字符串
    # 确保传入的是 "1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4" 之一
    input_params = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio, 
        "output_format": output_format,
        "safety_tolerance": safety_tolerance
    }
    
    # --- 调试日志 (会在 Streamlit 后台右侧打印) ---
    print(f"🚀 [Flux Request] Model: {model_id}")
    print(f"📋 [Flux Params] {input_params}")

    try:
        # 4. 发起调用
        output = replicate.run(
            model_id,
            input=input_params
        )
        
        # --- 调试日志 (查看原始返回结果) ---
        print(f"📦 [Flux Response] Type: {type(output)}")
        print(f"📦 [Flux Response] Data: {output}")

        # 5. 解析结果
        # Replicate SDK 通常返回一个列表: ['https://...']
        if output and isinstance(output, list) and len(output) > 0:
            # 将 FileOutput 对象转换为字符串 URL
            image_url = str(output[0])
            return image_url
            
        elif output and isinstance(output, str):
            # 极少数情况直接返回字符串
            return output
            
        else:
            # 如果是空列表，极大概率是触发了安全拦截
            raise ValueError(
                "API 返回结果为空。\n"
                "可能原因：\n"
                "1. 提示词触发了内容安全过滤器 (NSFW/敏感词)。\n"
                "2. 提示词为空或格式错误。"
            )
            
    except replicate.exceptions.ReplicateError as e:
        # 捕获 Replicate 官方定义的错误
        raise RuntimeError(f"Replicate API 拒绝服务: {str(e)}")
    except Exception as e:
        # 捕获其他未知错误
        raise RuntimeError(f"生图流程未知错误: {str(e)}")
