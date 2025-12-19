# services/hd_upscale/upscale_engine.py
import replicate
import streamlit as st
from .config import UpscaleConfig

class UpscaleEngine:
    def __init__(self):
        try:
            self.api_token = st.secrets["REPLICATE_API_TOKEN"]
            self.client = replicate.Client(api_token=self.api_token)
        except Exception:
            self.client = None

    def process_image(self, image_file, use_fallback=False, quality_preset="平衡"):
        """
        使用SUPIR模型执行图片放大，包含内存优化和错误处理
        :param image_file: 上传的图片文件
        :param use_fallback: 是否使用备用配置
        :return: 放大后的图片 URL (字符串)
        """
        if not self.client:
            raise ValueError("API Client 未初始化")

        # 选择模型版本
        if use_fallback:
            model_id = UpscaleConfig.SUPIR_MODELS.get("stable", UpscaleConfig.MODEL_ID)
        else:
            model_id = UpscaleConfig.MODEL_ID

        try:
            # 根据质量预设调整参数
            if quality_preset == "高质量 (慢)":
                num_steps = 50
                s_cfg = 8.0
            elif quality_preset == "快速":
                num_steps = 20
                s_cfg = 5.0
            else:  # 平衡
                num_steps = 35
                s_cfg = 7.0
            
            # SUPIR模型的输入参数 - 简化版本避免内存问题
            input_params = {
                "image": image_file
            }
            
            # 只在非fallback模式下添加高级参数
            if not use_fallback:
                input_params.update({
                    "num_steps": num_steps,
                    "s_cfg": s_cfg,
                    "seed": 42,
                    "a_prompt": "highly detailed, sharp, professional photography, high resolution",
                    "n_prompt": "blurry, low quality, distorted, deformed, low resolution"
                })
            
            # 调用SUPIR模型
            output = self.client.run(model_id, input=input_params)
            
            # 处理输出结果
            if hasattr(output, 'url'):
                return str(output.url())
            elif isinstance(output, list) and len(output) > 0:
                result = output[0]
                if hasattr(result, 'url'):
                    return str(result.url())
                else:
                    return str(result)
            else:
                return str(output)

        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是内存相关错误
            if any(keyword in error_msg.lower() for keyword in ['memory', 'cuda', 'xformers', 'attention']):
                if not use_fallback:
                    # 尝试使用内存优化配置重试
                    try:
                        return self._process_with_memory_optimization(image_file)
                    except Exception as retry_error:
                        raise RuntimeError(f"SUPIR模型内存优化重试失败: {str(retry_error)}")
                else:
                    raise RuntimeError(f"SUPIR模型内存不足，请尝试使用较小的图片: {error_msg}")
            else:
                raise RuntimeError(f"SUPIR模型调用失败: {error_msg}")

    def _process_with_memory_optimization(self, image_file):
        """
        使用最简配置处理图片，避免内存问题
        """
        # 使用最简配置，只传递必要参数
        input_params = {
            "image": image_file
        }
        
        # 使用主模型，但不添加任何可能导致内存问题的参数
        output = self.client.run(UpscaleConfig.MODEL_ID, input=input_params)
        
        # 处理输出
        if hasattr(output, 'url'):
            return str(output.url())
        elif isinstance(output, list) and len(output) > 0:
            result = output[0]
            if hasattr(result, 'url'):
                return str(result.url())
            else:
                return str(result)
        else:
            return str(output)
