import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2
import io
from .config import get_model_name, get_generation_config, get_safety_settings

# 初始化 API
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def _intelligent_background_extension(image: Image.Image, mask: Image.Image, analysis: str) -> Image.Image:
    """
    基于Gemini分析结果，使用智能算法进行背景扩展
    """
    # 转换为numpy数组进行处理
    img_array = np.array(image)
    mask_array = np.array(mask)
    
    # 创建结果图像
    result = img_array.copy()
    
    # 找到需要填充的区域（白色区域）
    fill_mask = mask_array > 128
    
    # 基于分析结果选择填充策略
    if "纯白" in analysis or "白色背景" in analysis:
        # 纯白背景扩展
        result[fill_mask] = [255, 255, 255]
    elif "渐变" in analysis or "柔和" in analysis:
        # 创建渐变背景
        result = _create_gradient_fill(result, fill_mask, img_array)
    else:
        # 使用边缘扩展算法
        result = _edge_based_fill(result, fill_mask)
    
    return Image.fromarray(result)

def _create_gradient_fill(img_array: np.ndarray, fill_mask: np.ndarray, original: np.ndarray) -> np.ndarray:
    """创建渐变填充效果"""
    h, w = img_array.shape[:2]
    result = img_array.copy()
    
    # 找到原图边缘的平均颜色
    edge_colors = []
    for y in range(h):
        for x in range(w):
            if not fill_mask[y, x]:  # 原图区域
                # 检查周围是否有需要填充的区域
                neighbors = [(y-1,x), (y+1,x), (y,x-1), (y,x+1)]
                for ny, nx in neighbors:
                    if 0 <= ny < h and 0 <= nx < w and fill_mask[ny, nx]:
                        edge_colors.append(original[y, x])
                        break
    
    if edge_colors:
        avg_color = np.mean(edge_colors, axis=0).astype(np.uint8)
        # 创建渐变到平均颜色
        for y in range(h):
            for x in range(w):
                if fill_mask[y, x]:
                    # 计算到最近原图像素的距离
                    min_dist = float('inf')
                    for oy in range(h):
                        for ox in range(w):
                            if not fill_mask[oy, ox]:
                                dist = ((y-oy)**2 + (x-ox)**2)**0.5
                                min_dist = min(min_dist, dist)
                    
                    # 基于距离创建渐变
                    fade_factor = min(1.0, min_dist / 50.0)
                    result[y, x] = avg_color * fade_factor + np.array([255, 255, 255]) * (1 - fade_factor)
    else:
        result[fill_mask] = [255, 255, 255]
    
    return result

def _edge_based_fill(img_array: np.ndarray, fill_mask: np.ndarray) -> np.ndarray:
    """基于边缘扩展的填充算法"""
    try:
        # 使用OpenCV的inpaint功能
        mask_uint8 = fill_mask.astype(np.uint8) * 255
        
        # 使用Navier-Stokes方法进行修复
        result = cv2.inpaint(img_array, mask_uint8, 3, cv2.INPAINT_NS)
        
        return result
    except Exception as e:
        print(f"OpenCV inpaint失败，使用简单扩展: {e}")
        # 兜底方案：简单的边缘扩展
        return _simple_edge_extension(img_array, fill_mask)

def _simple_edge_extension(img_array: np.ndarray, fill_mask: np.ndarray) -> np.ndarray:
    """简单的边缘扩展算法（不依赖OpenCV）"""
    result = img_array.copy()
    h, w = img_array.shape[:2]
    
    # 多次迭代，从边缘向内填充
    for iteration in range(10):  # 最多10次迭代
        changed = False
        new_result = result.copy()
        
        for y in range(h):
            for x in range(w):
                if fill_mask[y, x]:  # 需要填充的像素
                    # 查找周围已填充的像素
                    neighbors = []
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            ny, nx = y + dy, x + dx
                            if (0 <= ny < h and 0 <= nx < w and 
                                not fill_mask[ny, nx]):  # 已有内容的像素
                                neighbors.append(result[ny, nx])
                    
                    if neighbors:
                        # 使用邻居像素的平均值
                        new_result[y, x] = np.mean(neighbors, axis=0).astype(np.uint8)
                        fill_mask[y, x] = False  # 标记为已填充
                        changed = True
        
        result = new_result
        if not changed:
            break
    
    return result

def fill_image(image: Image.Image, mask: Image.Image, prompt: str, use_gemini: bool = True) -> Image.Image:
    """
    使用Gemini图像生成模型进行图像扩充
    """
    try:
        if use_gemini:
            # 尝试使用Gemini进行图像生成
            result_image = _gemini_image_generation(image, mask, prompt)
            
            if result_image:
                return result_image
            else:
                # 如果Gemini生成失败，使用智能算法兜底
                st.warning("Gemini图像生成不可用，使用智能算法扩展...")
        
        # 使用智能算法进行扩展
        result_image = _intelligent_background_extension(image, mask, prompt)
        result_image = _post_process_image(result_image, image, mask)
        return result_image
        
    except Exception as e:
        st.error(f"图像扩展失败: {str(e)}")
        print(f"详细错误信息: {e}")
        # 返回简单的白色背景扩展作为兜底
        return _simple_white_extension(image, mask)

def _gemini_image_generation(image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    """
    使用Gemini进行图像生成
    """
    try:
        # 使用配置文件中指定的图像生成模型
        model_name = get_model_name("image_generation")
        model = genai.GenerativeModel(model_name)
        
        # 构建详细的图像生成提示词
        generation_prompt = f"""
        请基于这张图片进行智能画幅扩展 (Outpainting)。

        任务要求：
        1. 保持中心产品完全不变 - 位置、大小、颜色、细节都必须完全一致
        2. 只扩展灰色区域的背景，生成与原图风格完美融合的内容
        3. 背景特征：{prompt}
        4. 确保扩展区域与原图的光照、色调、透视完全一致
        5. 不要添加任何新物体、文字或水印
        6. 输出完整的高质量图像

        重要：这是画幅扩展任务，不是重新创作。请严格保持原图内容不变，只扩展背景。
        """
        
        # 配置生成参数
        gen_config = genai.types.GenerationConfig(**get_generation_config())
        
        # 发送生成请求
        response = model.generate_content(
            [generation_prompt, image],
            generation_config=gen_config
        )
        
        # 检查响应中是否包含图像数据
        if response.parts:
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_data = part.inline_data.data
                    generated_image = Image.open(io.BytesIO(img_data))
                    
                    # 验证生成的图像尺寸是否正确
                    if generated_image.size == image.size:
                        return generated_image
                    else:
                        print(f"生成图像尺寸不匹配: 期望{image.size}, 实际{generated_image.size}")
                        return None
        
        # 如果没有图像数据，检查文本响应
        if response.text:
            print(f"Gemini响应文本: {response.text}")
        
        return None
        
    except Exception as e:
        print(f"Gemini图像生成失败: {e}")
        return None

def _post_process_image(result: Image.Image, original: Image.Image, mask: Image.Image) -> Image.Image:
    """后处理优化图像质量"""
    # 轻微的高斯模糊来平滑边缘
    result_array = np.array(result)
    mask_array = np.array(mask)
    
    # 只对填充区域应用轻微模糊
    blurred = result.filter(ImageFilter.GaussianBlur(radius=0.5))
    blurred_array = np.array(blurred)
    
    # 混合原图和模糊结果
    fill_mask = mask_array > 128
    result_array[fill_mask] = blurred_array[fill_mask]
    
    return Image.fromarray(result_array)

def _simple_white_extension(image: Image.Image, mask: Image.Image) -> Image.Image:
    """简单的白色背景扩展作为兜底方案"""
    result = image.copy()
    mask_array = np.array(mask)
    result_array = np.array(result)
    
    # 将需要填充的区域设为白色
    fill_mask = mask_array > 128
    result_array[fill_mask] = [255, 255, 255]
    
    return Image.fromarray(result_array)
