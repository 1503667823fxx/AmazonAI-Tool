from PIL import Image, ImageOps

def prepare_canvas(original_img: Image.Image, target_ratio: tuple) -> tuple[Image.Image, Image.Image]:
    """
    根据目标比例，将原图居中，并填充背景，同时生成 Mask。
    
    Args:
        original_img: 原始 PIL 图片
        target_ratio: 目标比例元组，例如 (4, 3)
    
    Returns:
        (padded_image, mask_image)
        padded_image: 扩展后的图片，扩充区域为灰色/黑色（给AI看）
        mask_image: 遮罩图，白色代表保留原图，黑色代表需要AI重绘
        (注意：Flux Fill 的 mask 定义可能不同，通常白色是'在此处绘制'或'保留'，需根据具体模型微调。
         这里我们定义：白色 = 需要重绘/填充区域，黑色 = 原图保留区域)
    """
    w, h = original_img.size
    target_w_ratio, target_h_ratio = target_ratio
    
    # 计算当前比例
    current_ratio = w / h
    target_ratio_val = target_w_ratio / target_h_ratio
    
    new_w, new_h = w, h
    
    # 判断是需要加宽还是加高
    if current_ratio > target_ratio_val:
        # 原图比较宽，需要增加高度
        new_h = int(w / target_ratio_val)
    else:
        # 原图比较高，需要增加宽度
        new_w = int(h * target_ratio_val)
        
    # 创建新画布 (底色可以是灰色，帮助AI理解是空白)
    padded_image = Image.new("RGB", (new_w, new_h), (128, 128, 128))
    
    # 计算粘贴位置 (居中)
    paste_x = (new_w - w) // 2
    paste_y = (new_h - h) // 2
    
    # 粘贴原图
    padded_image.paste(original_img, (paste_x, paste_y))
    
    # 创建 Mask
    # 策略：创建一个全白的图(表示全画)，然后在原图位置画黑(表示保留)
    # Replicate Flux Fill 通常逻辑：Mask 中白色像素会被重绘 (Inpaint/Outpaint)
    mask_image = Image.new("L", (new_w, new_h), 255) # 全白 = 全重绘
    
    # 创建一个黑色的矩形代表原图区域 (保留不动画)
    original_area_mask = Image.new("L", (w, h), 0)
    mask_image.paste(original_area_mask, (paste_x, paste_y))
    
    return padded_image, mask_image
