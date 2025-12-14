from PIL import Image, ImageOps
import math

def calculate_target_dimensions(original_w: int, original_h: int, target_ratio: tuple) -> tuple[int, int]:
    """
    计算目标尺寸，确保画幅比例正确且包含完整原图。
    
    Args:
        original_w: 原图宽度
        original_h: 原图高度  
        target_ratio: 目标比例 (width_ratio, height_ratio)
    
    Returns:
        (target_width, target_height)
    """
    target_w_ratio, target_h_ratio = target_ratio
    target_ratio_val = target_w_ratio / target_h_ratio
    current_ratio = original_w / original_h
    
    if abs(current_ratio - target_ratio_val) < 0.01:
        # 比例已经很接近，无需调整
        return original_w, original_h
    
    # 计算两种可能的目标尺寸
    # 方案1：基于宽度计算高度
    target_h_from_w = int(original_w / target_ratio_val)
    # 方案2：基于高度计算宽度  
    target_w_from_h = int(original_h * target_ratio_val)
    
    # 选择能完全包含原图的方案
    if target_h_from_w >= original_h:
        return original_w, target_h_from_w
    else:
        return target_w_from_h, original_h

def prepare_canvas(original_img: Image.Image, target_ratio: tuple) -> tuple[Image.Image, Image.Image]:
    """
    根据目标比例，将原图居中，并填充背景，同时生成 Mask。
    使用最小扩展策略，确保原图完整保留且画幅正确。
    
    Args:
        original_img: 原始 PIL 图片
        target_ratio: 目标比例元组，例如 (4, 3)
    
    Returns:
        (padded_image, mask_image)
        padded_image: 扩展后的图片，扩充区域为灰色（给AI看）
        mask_image: 遮罩图，白色代表需要AI重绘，黑色代表保留原图
    """
    w, h = original_img.size
    target_w_ratio, target_h_ratio = target_ratio
    
    # 使用辅助函数计算精确的目标尺寸
    new_w, new_h = calculate_target_dimensions(w, h, target_ratio)
    
    # 如果尺寸没有变化，说明比例已经正确
    if new_w == w and new_h == h:
        return original_img, Image.new("L", (w, h), 0)
        
    # 创建新画布 (灰色背景帮助AI理解需要填充的区域)
    padded_image = Image.new("RGB", (new_w, new_h), (128, 128, 128))
    
    # 计算粘贴位置 (居中)
    paste_x = (new_w - w) // 2
    paste_y = (new_h - h) // 2
    
    # 粘贴原图到中心位置
    padded_image.paste(original_img, (paste_x, paste_y))
    
    # 创建 Mask：白色=需要AI填充，黑色=保留原图
    mask_image = Image.new("L", (new_w, new_h), 255)  # 全白背景
    
    # 在原图区域创建黑色遮罩（保留原图）
    original_area_mask = Image.new("L", (w, h), 0)
    mask_image.paste(original_area_mask, (paste_x, paste_y))
    
    return padded_image, mask_image
