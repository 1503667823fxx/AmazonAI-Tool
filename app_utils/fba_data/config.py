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

# 3. FBA 配送费率表 (FULFILLMENT_FEES) - 重新优化版
# ==============================================================================
# 填写说明：
# 1. 结构逻辑：季节 -> 价格段 -> 商品类型 -> 尺寸分段 -> 重量阶梯
# 2. 这里的价格单位均为美元 ($)
# 3. 重量单位均为磅 (lb)
# 4. 如果某一项没有特定费率（比如危险品没有低价段优惠），可以填 None 或复用标准费率
# ==============================================================================

FULFILLMENT_FEES = {
    # --- 第一大类：淡季 (Off-Peak) 通常是 1月-9月 ---
    "Off-Peak": {
        
        # 1. 低价商品 (Under $10) - 以前叫“轻小商品计划”，现在整合为低价费率
        "Under_10": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 4/16, "fee": 0.00}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 8/16, "fee": 0.00}, # ⏳ 请填写图表中 4-8oz 的金额
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 0.00},
                    {"max_weight": 3.0,  "fee": 0.00}, # 比如 3lb 以内
                    # ...
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 4/16, "fee": 0.00},
                ],
                 # ...
            },
            "Dangerous": { # 危险品
                 # 危险品费率
            }
        },

        # 2. 中段价格商品 ($10 - $50) - 绝大多数商品的标准费率
        "Price_10_50": {
            "Standard": { # 非服饰类 (最常用)
                "Small Standard": [
                    {"max_weight": 4/16, "fee": 3.22}, # 示例
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
                    {"max_weight": 3.0, "fee": 6.39}, 
                    # ... 这里的列表很长，请对照您的图1慢慢填
                ],
                "Large Bulky": [
                    # 小号大件/大号大件等
                ]
            },
            "Apparel": { # 服饰类 (通常比标准类贵一点)
                "Small Standard": [
                     {"max_weight": 4/16, "fee": 0.00},
                ],
                "Large Standard": [
                     {"max_weight": 1.0, "fee": 0.00},
                ]
            },
            "Dangerous": { # 危险品 (通常最贵)
                "Small Standard": [],
                "Large Standard": []
            }
        },

        # 3. 高价商品 (Over $50) - 有时高价商品费率与中段一致，有时不同，保留此结构以防万一
        # 如果费率与 10-50 相同，逻辑代码里我们会做一个 fallback 处理
        "Over_50": {
             # ... 结构同上
        }
    },

    # --- 第二大类：旺季 (Peak) 通常是 10月-12月 ---
    "Peak": {
        # 旺季费率通常会在淡季基础上每单加收 $0.20 - $0.50 不等
        # 结构完全复用上面的，只需填入旺季的具体价格
        
        "Under_10": {
            "Standard": {
                "Small Standard": [],
                # ...
            }
            # ...
        },
        
        "Price_10_50": {
            "Standard": {
                # ... 这里的价格通常比 Off-Peak 贵
            }
            # ...
        }
    }
}

# 辅助配置：每磅附加费 (Surcharge per lb)
# 当重量超过费率表最大值时使用
WEIGHT_SURCHARGES = {
    "Standard": {
        "Large Standard": 0.16, # 示例：超过3lb后，每半磅加收多少钱
        "Large Bulky": 0.38
    },
    "Apparel": {
        # ...
    }
}

# ==============================================================================
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
