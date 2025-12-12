# app_utils/fba_data/config.py

# 1. 基础常量
DIM_DIVISOR = 139  # 体积重除数

# 2. 尺寸分段定义 (根据图片 5cfb...jpg 和 9e4f...jpg)
# 注意：单位是 英寸(inch) 和 磅(lb)
SIZE_TIERS = {
    "Small Standard": {
        "max_weight": 16/16,  # 16 oz = 1 lb
        "max_longest": 15,
        "max_median": 12,
        "max_shortest": 0.75,
        "length_girth": None
    },
    "Large Standard": {
        "max_weight": 20,     # 20 lb
        "max_longest": 18,
        "max_median": 14,
        "max_shortest": 8,
        "length_girth": None
    },
    "Large Bulky (Small Oversize)": { # 2026年前叫 Small Oversize
        "max_weight": 50,
        "max_longest": 59,    #
        "max_median": 33,
        "max_shortest": 33,
        "length_girth": 130
    }
    # 超大件逻辑暂略，可按需添加
}

# 3. 基础 FBA 配送费率表 (需要您根据图1完善具体金额)
# 结构：尺寸分段 -> 重量上限(lb) -> 费用($)
FULFILLMENT_FEES = {
    "Small Standard": [
        {"max_weight": 4/16, "fee": 3.22}, # 示例数据，请核对您的图1
        {"max_weight": 8/16, "fee": 3.40},
        {"max_weight": 12/16, "fee": 3.58},
        {"max_weight": 16/16, "fee": 3.77},
    ],
    "Large Standard": [
        {"max_weight": 4/16, "fee": 3.86},
        {"max_weight": 8/16, "fee": 4.08},
        {"max_weight": 12/16, "fee": 4.24},
        {"max_weight": 1.0, "fee": 4.75},
        {"max_weight": 1.5, "fee": 5.40},
        {"max_weight": 2.0, "fee": 5.69},
        {"max_weight": 2.5, "fee": 6.10},
        # ... 超过部分通常是每磅增加多少钱
    ]
}

# 4. 月度仓储费 (根据图片 f3f1...jpg 和 07cf...jpg)
# 单位：美元/立方英尺
STORAGE_FEES = {
    "Jan-Sep": {
        "Standard": 0.78,
        "Oversize": 0.56
    },
    "Oct-Dec": {
        "Standard": 2.40,
        "Oversize": 1.40
    }
}

# 5. 低库存水平费 (根据图片 888a...jpg)
LOW_INVENTORY_FEES = {
    "Small Standard": {
        "0-13": 0.89,
        "14-20": 0.63,
        "21-27": 0.32
    },
    "Large Standard": {
        "0-13_light": 0.97, # <3lb
        "14-20_light": 0.70,
        "21-27_light": 0.36,
        "0-13_heavy": 1.11, # >3lb
        "14-20_heavy": 0.87,
        "21-27_heavy": 0.47
    }
}
