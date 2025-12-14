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

def fill_image(image: Image.Image, mask: Image.Image, prompt: str, use_gemini: bool = True, target_ratio: tuple = None, test_mode: bool = False) -> Image.Image:
    """
    使用Gemini进行画幅重构
    """
    try:
        if use_gemini and target_ratio:
            if test_mode:
                # 超简单测试模式
                result_image = _simple_gemini_test(image, target_ratio)
            else:
                # 正常Gemini画幅重构
                result_image = _gemini_aspect_ratio_change(image, target_ratio, prompt)
            
            if result_image:
                return result_image
            else:
                st.warning("Gemini画幅重构失败，使用智能算法扩展...")
        
        # 兜底：使用智能算法进行扩展
        result_image = _intelligent_background_extension(image, mask, prompt)
        result_image = _post_process_image(result_image, image, mask)
        return result_image
        
    except Exception as e:
        st.error(f"图像扩展失败: {str(e)}")
        print(f"详细错误信息: {e}")
        # 返回简单的白色背景扩展作为兜底
        return _simple_white_extension(image, mask)

def _gemini_aspect_ratio_change(image: Image.Image, target_ratio: tuple, background_info: str) -> Image.Image:
    """
    使用Gemini进行画幅重构 - 简单直接的方法
    """
    try:
        # 使用配置文件中指定的图像生成模型
        model_name = get_model_name("image_generation")
        model = genai.GenerativeModel(model_name)
        
        # 计算目标比例
        ratio_w, ratio_h = target_ratio
        ratio_desc = f"{ratio_w}:{ratio_h}"
        
        # 最简单直接的提示词
        simple_prompt = f"请将这张图片改为 {ratio_desc} 的画幅比例，保持产品不变，扩展背景。"
        
        # 配置生成参数 - 更简单的配置
        gen_config = genai.types.GenerationConfig(
            temperature=0.1,  # 很低的随机性
            candidate_count=1
        )
        
        # 发送生成请求
        response = model.generate_content(
            [simple_prompt, image],
            generation_config=gen_config
        )
        
        # 检查响应中是否包含图像数据
        if response.parts:
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_data = part.inline_data.data
                    generated_image = Image.open(io.BytesIO(img_data))
                    
                    # 检查生成的图像比例是否接近目标
                    gen_w, gen_h = generated_image.size
                    gen_ratio = gen_w / gen_h
                    target_ratio_val = ratio_w / ratio_h
                    
                    if abs(gen_ratio - target_ratio_val) < 0.1:  # 允许10%的误差
                        return generated_image
                    else:
                        print(f"生成图像比例不匹配: 目标{target_ratio_val:.2f}, 实际{gen_ratio:.2f}")
        
        # 如果没有图像数据，检查文本响应
        if response.text:
            print(f"Gemini响应文本: {response.text}")
        
        return None
        
    except Exception as e:
        print(f"Gemini画幅重构失败: {e}")
        return None

def _simple_gemini_test(image: Image.Image, target_ratio: tuple) -> Image.Image:
    """
    超简单的Gemini画幅重构测试
    """
    try:
        model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
        
        ratio_w, ratio_h = target_ratio
        
        # 最简单的提示词
        prompt = f"Change this image to {ratio_w}:{ratio_h} aspect ratio."
        
        response = model.generate_content([prompt, image])
        
        if response.parts:
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_data = part.inline_data.data
                    return Image.open(io.BytesIO(img_data))
        
        return None
        
    except Exception as e:
        print(f"简单测试失败: {e}")
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
