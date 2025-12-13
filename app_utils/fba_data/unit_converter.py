# app_utils/fba_data/unit_converter.py

def convert_inputs(length, width, height, weight, unit_type="inch/lb"):
    """
    统一将输入转换为 inch 和 lb。
    亚马逊 FBA 计费核心均基于英制。
    """
    if unit_type == "cm/kg":
        # 转换逻辑
        # 1 inch = 2.54 cm
        # 1 kg ≈ 2.20462 lb
        
        # 我们保留 2 位小数，防止精度溢出导致误判尺寸分段
        l = round(length / 2.54, 2)
        w = round(width / 2.54, 2)
        h = round(height / 2.54, 2)
        wt = round(weight * 2.20462, 2)
        
        return l, w, h, wt
        
    else:
        # 如果已经是英制，原样返回
        return length, width, height, weight

def get_display_unit(unit_type):
    """
    返回用于显示的单位后缀
    """
    if unit_type == "cm/kg":
        return "cm", "kg"
    return "in", "lb"
