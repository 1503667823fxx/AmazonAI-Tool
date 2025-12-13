# app_utils/fba_data/config.py

# 1. 基础常量
DIM_DIVISOR = 139  # 体积重除数

# ==============================================================================
# 2. 尺寸分段定义 (SIZE_TIERS) - 修正版
# ==============================================================================
# 逻辑说明：
# 这里定义的是每个分段的【最大上限】(Inclusive)。
# 只要有一项指标超过了当前分段的上限，程序就会自动判断为下一级分段。
# ==============================================================================

SIZE_TIERS = {
    "Small Standard": {
        "max_weight": 16/16,    # 1 lb
        "max_longest": 15,
        "max_median": 12,
        "max_shortest": 0.75,
        "length_girth": None
    },
    "Large Standard": {
        "max_weight": 20,       # 20 lb
        "max_longest": 18,
        "max_median": 14,
        "max_shortest": 8,
        "length_girth": None
    },
    # 2026新规 / 当前特定类目使用
    "Small Bulky": {
        "max_weight": 50,       # 50 lb (实重或体积重)
        "max_longest": 37,      #
        "max_median": 28,
        "max_shortest": 20,
        "length_girth": 130     # 围长+长 <= 130
    },
    # 🆕 关键点：根据您的描述补充 Medium Bulky 的上限
    # 只要不超过这些，就是 Medium；超过了任意一项，就是 Large Bulky
    "Medium Bulky": {
        "max_weight": 50,       # 50 lb
        "max_longest": 59,      #
        "max_median": 33,
        "max_shortest": 33,
        "length_girth": 130
    },
    # 🆕 Large Bulky (超大件)
    # 通常指 50-150lb 或 尺寸超过 Medium 但未达到 Special Oversize
    "Large Bulky": {
        "max_weight": 150,      # 150 lb 界线
        "max_longest": 108,     # 亚马逊常规限制
        "length_girth": 165
    }
    # 再往上就是 Special Oversize (需特殊处理)
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
                    {"max_weight": 2/16, "fee": 2.43},
                    {"max_weight": 4/16, "fee": 2.49}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 2.56}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 2.66},
                    {"max_weight": 10/16, "fee": 2.77},
                    {"max_weight": 12/16, "fee": 2.82},
                    {"max_weight": 14/16, "fee": 2.92},
                    {"max_weight": 16/16, "fee": 2.95},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 2.91},
                    {"max_weight": 8/16, "fee": 3.13},
                    {"max_weight": 12/16, "fee": 3.38},
                    {"max_weight": 16/16, "fee": 3.78},
                    {"max_weight": 1.25,  "fee": 4.22}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 4.60},
                    {"max_weight": 1.75,  "fee": 4.75},
                    {"max_weight": 2.0,  "fee": 5.00},
                    {"max_weight": 2.25,  "fee": 5.10},
                    {"max_weight": 2.5,  "fee": 5.28},
                    {"max_weight": 2.75,  "fee": 5.44},
                    {"max_weight": 3.0,  "fee": 5.85},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.15,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 6.78,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 8.58,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 25.56,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 36.55,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 50.55,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.18,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 2.62},
                    {"max_weight": 4/16, "fee": 2.64},
                    {"max_weight": 6/16, "fee": 2.68},
                    {"max_weight": 8/16, "fee": 2.81},
                    {"max_weight": 10/16, "fee": 3.00},
                    {"max_weight": 12/16, "fee": 3.10},
                    {"max_weight": 14/16, "fee": 3.20},
                    {"max_weight": 16/16, "fee": 3.30},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.48},
                    {"max_weight": 8/16, "fee": 3.68},
                    {"max_weight": 12/16, "fee": 3.90},
                    {"max_weight": 16/16, "fee": 4.35},
                    {"max_weight": 1.25,  "fee": 5.05}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.22},
                    {"max_weight": 1.75,  "fee": 5.32},
                    {"max_weight": 2.0,  "fee": 5.43},
                    {"max_weight": 2.25,  "fee": 5.78},
                    {"max_weight": 2.5,  "fee": 5.90},
                    {"max_weight": 2.75,  "fee": 5.95},
                    {"max_weight": 3.0,  "fee": 6.08},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.82,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 6.78,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 8.58,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 25.56,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 36.55,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 50.55,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.18,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.40},
                    {"max_weight": 4/16, "fee": 3.43},
                    {"max_weight": 6/16, "fee": 3.48},
                    {"max_weight": 8/16, "fee": 3.55},
                    {"max_weight": 10/16, "fee": 3.46},
                    {"max_weight": 12/16, "fee": 3.65},
                    {"max_weight": 14/16, "fee": 3.73},
                    {"max_weight": 16/16, "fee": 3.77},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.73},
                    {"max_weight": 8/16, "fee": 3.94},
                    {"max_weight": 12/16, "fee": 4.17},
                    {"max_weight": 16/16, "fee": 4.37},
                    {"max_weight": 1.25,  "fee": 4.82}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.20},
                    {"max_weight": 1.75,  "fee": 5.35},
                    {"max_weight": 2.0,  "fee": 5.49},
                    {"max_weight": 2.25,  "fee": 5.56},
                    {"max_weight": 2.5,  "fee": 5.74},
                    {"max_weight": 2.75,  "fee": 5.90},
                    {"max_weight": 3.0,  "fee": 6.31},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.61,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $7.5 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 7.5,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $9.3 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.3,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 27.67,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 39.76,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 57.68,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 218.76,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
        },

        # 2. 中段价格商品 ($10 - $50) - 绝大多数商品的标准费率
        "Price_10_50": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.32},
                    {"max_weight": 4/16, "fee": 3.42}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 3.45}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 3.54},
                    {"max_weight": 10/16, "fee": 3.68},
                    {"max_weight": 12/16, "fee": 3.78},
                    {"max_weight": 14/16, "fee": 3.91},
                    {"max_weight": 16/16, "fee": 3.96},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.73},
                    {"max_weight": 8/16, "fee": 3.95},
                    {"max_weight": 12/16, "fee": 4.20},
                    {"max_weight": 16/16, "fee": 4.60},
                    {"max_weight": 1.25,  "fee": 5.04}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.42},
                    {"max_weight": 1.75,  "fee": 5.57},
                    {"max_weight": 2.0,  "fee": 5.82},
                    {"max_weight": 2.25,  "fee": 5.92},
                    {"max_weight": 2.5,  "fee": 6.10},
                    {"max_weight": 2.75,  "fee": 6.26},
                    {"max_weight": 3.0,  "fee": 6.67},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.97,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 7.55,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.35,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 26.33,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 37.32,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 51.32,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.95,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.51},
                    {"max_weight": 4/16, "fee": 3.54},
                    {"max_weight": 6/16, "fee": 3.59},
                    {"max_weight": 8/16, "fee": 3.69},
                    {"max_weight": 10/16, "fee": 3.91},
                    {"max_weight": 12/16, "fee": 4.09},
                    {"max_weight": 14/16, "fee": 4.20},
                    {"max_weight": 16/16, "fee": 4.25},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.30},
                    {"max_weight": 8/16, "fee": 4.50},
                    {"max_weight": 12/16, "fee": 4.72},
                    {"max_weight": 16/16, "fee": 5.17},
                    {"max_weight": 1.25,  "fee": 5.87}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.04},
                    {"max_weight": 1.75,  "fee": 6.14},
                    {"max_weight": 2.0,  "fee": 6.25},
                    {"max_weight": 2.25,  "fee": 6.60},
                    {"max_weight": 2.5,  "fee": 6.72},
                    {"max_weight": 2.75,  "fee": 6.77},
                    {"max_weight": 3.0,  "fee": 6.90},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.97,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 7.55,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.35,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 26.33,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 37.32,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 51.32,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.95,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 4.29},
                    {"max_weight": 4/16, "fee": 4.36},
                    {"max_weight": 6/16, "fee": 4.37},
                    {"max_weight": 8/16, "fee": 4.43},
                    {"max_weight": 10/16, "fee": 4.55},
                    {"max_weight": 12/16, "fee": 4.61},
                    {"max_weight": 14/16, "fee": 4.72},
                    {"max_weight": 16/16, "fee": 4.78},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.55},
                    {"max_weight": 8/16, "fee": 4.76},
                    {"max_weight": 12/16, "fee": 4.99},
                    {"max_weight": 16/16, "fee": 5.19},
                    {"max_weight": 1.25,  "fee": 5.64}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.02},
                    {"max_weight": 1.75,  "fee": 6.17},
                    {"max_weight": 2.0,  "fee": 6.31},
                    {"max_weight": 2.25,  "fee": 6.38},
                    {"max_weight": 2.5,  "fee": 6.56},
                    {"max_weight": 2.75,  "fee": 6.72},
                    {"max_weight": 3.0,  "fee": 7.13},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.43,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $8.27 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 8.27,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $10.07 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.07,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 28.44,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 40.53,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 58.45,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 219.53,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
        },

        # 3. 高价商品 (Over $50) - 有时高价商品费率与中段一致，有时不同，保留此结构以防万一
        # 如果费率与 10-50 相同，逻辑代码里我们会做一个 fallback 处理
        "Over_50": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.58},
                    {"max_weight": 4/16, "fee": 3.68}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 3.71}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 3.80},
                    {"max_weight": 10/16, "fee": 3.94},
                    {"max_weight": 12/16, "fee": 4.04},
                    {"max_weight": 14/16, "fee": 4.17},
                    {"max_weight": 16/16, "fee": 4.22},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.99},
                    {"max_weight": 8/16, "fee": 4.21},
                    {"max_weight": 12/16, "fee": 4.46},
                    {"max_weight": 16/16, "fee": 4.86},
                    {"max_weight": 1.25,  "fee": 5.30}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.68},
                    {"max_weight": 1.75,  "fee": 5.83},
                    {"max_weight": 2.0,  "fee": 6.08},
                    {"max_weight": 2.25,  "fee": 6.18},
                    {"max_weight": 2.5,  "fee": 6.36},
                    {"max_weight": 2.75,  "fee": 6.52},
                    {"max_weight": 3.0,  "fee": 6.93},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.23,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 7.55,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.35,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 26.33,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 37.32,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 51.32,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.95,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.77},
                    {"max_weight": 4/16, "fee": 3.80},
                    {"max_weight": 6/16, "fee": 3.85},
                    {"max_weight": 8/16, "fee": 3.95},
                    {"max_weight": 10/16, "fee": 4.17},
                    {"max_weight": 12/16, "fee": 4.35},
                    {"max_weight": 14/16, "fee": 4.46},
                    {"max_weight": 16/16, "fee": 4.51},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.56},
                    {"max_weight": 8/16, "fee": 4.76},
                    {"max_weight": 12/16, "fee": 4.98},
                    {"max_weight": 16/16, "fee": 5.43},
                    {"max_weight": 1.25,  "fee": 6.13}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.30},
                    {"max_weight": 1.75,  "fee": 6.40},
                    {"max_weight": 2.0,  "fee": 6.51},
                    {"max_weight": 2.25,  "fee": 6.86},
                    {"max_weight": 2.5,  "fee": 6.98},
                    {"max_weight": 2.75,  "fee": 7.03},
                    {"max_weight": 3.0,  "fee": 7.16},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.63,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 7.55,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.35,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 26.33,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 37.32,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 51.32,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 194.95,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 4.55},
                    {"max_weight": 4/16, "fee": 4.62},
                    {"max_weight": 6/16, "fee": 4.63},
                    {"max_weight": 8/16, "fee": 4.69},
                    {"max_weight": 10/16, "fee": 4.81},
                    {"max_weight": 12/16, "fee": 4.87},
                    {"max_weight": 14/16, "fee": 4.98},
                    {"max_weight": 16/16, "fee": 5.04},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.81},
                    {"max_weight": 8/16, "fee": 5.02},
                    {"max_weight": 12/16, "fee": 5.25},
                    {"max_weight": 16/16, "fee": 5.45},
                    {"max_weight": 1.25,  "fee": 5.90}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.28},
                    {"max_weight": 1.75,  "fee": 6.43},
                    {"max_weight": 2.0,  "fee": 6.57},
                    {"max_weight": 2.25,  "fee": 6.64},
                    {"max_weight": 2.5,  "fee": 6.82},
                    {"max_weight": 2.75,  "fee": 6.98},
                    {"max_weight": 3.0,  "fee": 7.39},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.69,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $8.27 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 8.27,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $10.07 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.07,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 28.44,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 40.53,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 58.45,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 219.53,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
    },

    # --- 第二大类：旺季 (Peak) 通常是 10月-12月 -----------------------------------------------------------------------------------------------------------------------------------------------
    "Peak": {
        # 1. 低价商品 (Under $10) - 以前叫“轻小商品计划”，现在整合为低价费率
        "Under_10": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 2.48},
                    {"max_weight": 4/16, "fee": 2.57}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 2.67}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 2.76},
                    {"max_weight": 10/16, "fee": 2.87},
                    {"max_weight": 12/16, "fee": 2.97},
                    {"max_weight": 14/16, "fee": 3.05},
                    {"max_weight": 16/16, "fee": 3.10},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.15},
                    {"max_weight": 8/16, "fee": 3.39},
                    {"max_weight": 12/16, "fee": 3.66},
                    {"max_weight": 16/16, "fee": 4.07},
                    {"max_weight": 1.25,  "fee": 4.52}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 4.91},
                    {"max_weight": 1.75,  "fee": 5.07},
                    {"max_weight": 2.0,  "fee": 5.33},
                    {"max_weight": 2.25,  "fee": 5.47},
                    {"max_weight": 2.5,  "fee": 5.67},
                    {"max_weight": 2.75,  "fee": 5.84},
                    {"max_weight": 3.0,  "fee": 6.26},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.69,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $9.88 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.88,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $9.88 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.88,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 28.92,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.16,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 58.46,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 202.69,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 2.73},
                    {"max_weight": 4/16, "fee": 2.73},
                    {"max_weight": 6/16, "fee": 2.90},
                    {"max_weight": 8/16, "fee": 2.90},
                    {"max_weight": 10/16, "fee": 3.22},
                    {"max_weight": 12/16, "fee": 3.22},
                    {"max_weight": 14/16, "fee": 3.50},
                    {"max_weight": 16/16, "fee": 3.50},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.79},
                    {"max_weight": 8/16, "fee": 4.00},
                    {"max_weight": 12/16, "fee": 4.23},
                    {"max_weight": 16/16, "fee": 4.69},
                    {"max_weight": 1.25,  "fee": 5.50}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.50},
                    {"max_weight": 1.75,  "fee": 5.76},
                    {"max_weight": 2.0,  "fee": 5.76},
                    {"max_weight": 2.25,  "fee": 6.27},
                    {"max_weight": 2.5,  "fee": 6.27},
                    {"max_weight": 2.75,  "fee": 6.50},
                    {"max_weight": 3.0,  "fee": 6.50},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 6.82,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.88,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 9.88,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 28.29,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.16,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 58.46,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 202.69,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.60},
                    {"max_weight": 4/16, "fee": 3.69},
                    {"max_weight": 6/16, "fee": 3.79},
                    {"max_weight": 8/16, "fee": 3.88},
                    {"max_weight": 10/16, "fee": 3.99},
                    {"max_weight": 12/16, "fee": 4.08},
                    {"max_weight": 14/16, "fee": 4.16},
                    {"max_weight": 16/16, "fee": 4.25},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.32},
                    {"max_weight": 8/16, "fee": 4.56},
                    {"max_weight": 12/16, "fee": 4.82},
                    {"max_weight": 16/16, "fee": 5.04},
                    {"max_weight": 1.25,  "fee": 5.51}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.91},
                    {"max_weight": 1.75,  "fee": 6.08},
                    {"max_weight": 2.0,  "fee": 6.24},
                    {"max_weight": 2.25,  "fee": 6.33},
                    {"max_weight": 2.5,  "fee": 6.53},
                    {"max_weight": 2.75,  "fee": 6.70},
                    {"max_weight": 3.0,  "fee": 7.12},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.51,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $7.5 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.12,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $9.3 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.12,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 31.71,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 46.66,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 67.53,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 230.84,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
        },

        # 2. 中段价格商品 ($10 - $50) - 绝大多数商品的标准费率
        "Price_10_50": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.25},
                    {"max_weight": 4/16, "fee": 3.34}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 3.45}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 3.53},
                    {"max_weight": 10/16, "fee": 3.64},
                    {"max_weight": 12/16, "fee": 3.74},
                    {"max_weight": 14/16, "fee": 3.82},
                    {"max_weight": 16/16, "fee": 3.87},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.92},
                    {"max_weight": 8/16, "fee": 4.16},
                    {"max_weight": 12/16, "fee": 4.43},
                    {"max_weight": 16/16, "fee": 4.84},
                    {"max_weight": 1.25,  "fee": 5.29}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.68},
                    {"max_weight": 1.75,  "fee": 5.84},
                    {"max_weight": 2.0,  "fee": 6.10},
                    {"max_weight": 2.25,  "fee": 6.24},
                    {"max_weight": 2.5,  "fee": 6.44},
                    {"max_weight": 2.75,  "fee": 6.61},
                    {"max_weight": 3.0,  "fee": 7.03},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.46,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 29.06,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.93,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 59.23,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 203.46,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.50},
                    {"max_weight": 4/16, "fee": 3.50},
                    {"max_weight": 6/16, "fee": 3.67},
                    {"max_weight": 8/16, "fee": 3.67},
                    {"max_weight": 10/16, "fee": 3.99},
                    {"max_weight": 12/16, "fee": 3.99},
                    {"max_weight": 14/16, "fee": 4.27},
                    {"max_weight": 16/16, "fee": 4.27},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.56},
                    {"max_weight": 8/16, "fee": 4.77},
                    {"max_weight": 12/16, "fee": 5.00},
                    {"max_weight": 16/16, "fee": 5.46},
                    {"max_weight": 1.25,  "fee": 6.27}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.27},
                    {"max_weight": 1.75,  "fee": 6.53},
                    {"max_weight": 2.0,  "fee": 6.53},
                    {"max_weight": 2.25,  "fee": 7.04},
                    {"max_weight": 2.5,  "fee": 7.04},
                    {"max_weight": 2.75,  "fee": 7.27},
                    {"max_weight": 3.0,  "fee": 7.27},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.59,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $6.78 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $8.58 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 29.06,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.93,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 59.23,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 203.46,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 4.37},
                    {"max_weight": 4/16, "fee": 4.46},
                    {"max_weight": 6/16, "fee": 4.56},
                    {"max_weight": 8/16, "fee": 4.65},
                    {"max_weight": 10/16, "fee": 4.76},
                    {"max_weight": 12/16, "fee": 4.85},
                    {"max_weight": 14/16, "fee": 4.93},
                    {"max_weight": 16/16, "fee": 5.02},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 5.09},
                    {"max_weight": 8/16, "fee": 5.33},
                    {"max_weight": 12/16, "fee": 5.59},
                    {"max_weight": 16/16, "fee": 5.81},
                    {"max_weight": 1.25,  "fee": 6.28}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.68},
                    {"max_weight": 1.75,  "fee": 6.85},
                    {"max_weight": 2.0,  "fee": 7.01},
                    {"max_weight": 2.25,  "fee": 7.10},
                    {"max_weight": 2.5,  "fee": 7.30},
                    {"max_weight": 2.75,  "fee": 7.47},
                    {"max_weight": 3.0,  "fee": 7.89},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 8.28,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $11.89 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.89,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $11.89 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.89,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 32.48,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 47.43,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 68.30,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 231.61,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
        },

        # 3. 高价商品 (Over $50) - 有时高价商品费率与中段一致，有时不同，保留此结构以防万一
        # 如果费率与 10-50 相同，逻辑代码里我们会做一个 fallback 处理
        "Over_50": {
            "Standard": { # 非服饰类
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.25},
                    {"max_weight": 4/16, "fee": 3.34}, # ⏳ 请填写图表中 <4oz 的金额
                    {"max_weight": 6/16, "fee": 3.44}, # ⏳ 请填写图表中 4-6oz 的金额
                    {"max_weight": 8/16, "fee": 3.53},
                    {"max_weight": 10/16, "fee": 3.64},
                    {"max_weight": 12/16, "fee": 3.74},
                    {"max_weight": 14/16, "fee": 3.82},
                    {"max_weight": 16/16, "fee": 3.87},
                    # ... 继续填写
                ],
                "Large Standard": [
                    {"max_weight": 4/16, "fee": 3.92},
                    {"max_weight": 8/16, "fee": 4.16},
                    {"max_weight": 12/16, "fee": 4.43},
                    {"max_weight": 16/16, "fee": 4.84},
                    {"max_weight": 1.25,  "fee": 5.29}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 5.68},
                    {"max_weight": 1.75,  "fee": 5.84},
                    {"max_weight": 2.0,  "fee": 6.10},
                    {"max_weight": 2.25,  "fee": 6.24},
                    {"max_weight": 2.5,  "fee": 6.44},
                    {"max_weight": 2.75,  "fee": 6.61},
                    {"max_weight": 3.0,  "fee": 7.03},
                    # ...
                    # 2. 【🔴 难点 1】 "3至20磅" 公式写法
                    # 逻辑：3lb以内按前面档位算。超过3lb，每增加0.25lb(4oz) 加 $0.08
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.46,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 29.06,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.93,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 59.23,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 203.46,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Apparel": { # 服饰类
                # 服饰类通常没有超低价的大幅优惠，或者有单独表格，请按需填写
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 3.50},
                    {"max_weight": 4/16, "fee": 3.50},
                    {"max_weight": 6/16, "fee": 3.67},
                    {"max_weight": 8/16, "fee": 3.67},
                    {"max_weight": 10/16, "fee": 3.99},
                    {"max_weight": 12/16, "fee": 3.99},
                    {"max_weight": 14/16, "fee": 4.27},
                    {"max_weight": 16/16, "fee": 4.27},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 4.56},
                    {"max_weight": 8/16, "fee": 4.77},
                    {"max_weight": 12/16, "fee": 5.00},
                    {"max_weight": 16/16, "fee": 5.46},
                    {"max_weight": 1.25,  "fee": 6.27}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.27},
                    {"max_weight": 1.75,  "fee": 6.53},
                    {"max_weight": 2.0,  "fee": 6.53},
                    {"max_weight": 2.25,  "fee": 7.04},
                    {"max_weight": 2.5,  "fee": 7.04},
                    {"max_weight": 2.75,  "fee": 7.24},
                    {"max_weight": 3.0,  "fee": 7.24},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 7.59,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.16,      # 增量单价
                            "unit_step": 8/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ]
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $10.65 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 10.65,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 29.06,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 42.93,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 59.23,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 203.46,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            },
            "Dangerous": { # 危险品
                 # 危险品费率，这类较少
                "Small Standard": [
                    {"max_weight": 2/16, "fee": 4.37},
                    {"max_weight": 4/16, "fee": 4.46},
                    {"max_weight": 6/16, "fee": 4.56},
                    {"max_weight": 8/16, "fee": 4.65},
                    {"max_weight": 10/16, "fee": 4.76},
                    {"max_weight": 12/16, "fee": 4.85},
                    {"max_weight": 14/16, "fee": 4.93},
                    {"max_weight": 16/16, "fee": 5.02},
                ],
               "Large Standard": [
                    {"max_weight": 4/16, "fee": 5.09},
                    {"max_weight": 8/16, "fee": 5.33},
                    {"max_weight": 12/16, "fee": 5.59},
                    {"max_weight": 16/16, "fee": 5.81},
                    {"max_weight": 1.25,  "fee": 6.28}, # 比如 1.25lb 以内
                    {"max_weight": 1.5,  "fee": 6.68},
                    {"max_weight": 1.75,  "fee": 6.85},
                    {"max_weight": 2.0,  "fee": 7.01},
                    {"max_weight": 2.25,  "fee": 7.10},
                    {"max_weight": 2.5,  "fee": 7.30},
                    {"max_weight": 2.75,  "fee": 7.47},
                    {"max_weight": 3.0,  "fee": 7.89},
                    # ...
                   # 【🔴 难点 1】逻辑：3lb以内按前面档位算。超过3lb，每增加0.5lb(8oz) 加 $0.16
                  {
                        "max_weight": 20.0, 
                        "formula": {
                            "base_fee": 8.28,      # 起步价
                            "base_weight": 3.0,    # 起步重 (lb)
                            "unit_fee": 0.08,      # 增量单价
                            "unit_step": 4/16      # 增量步长 (4盎司 = 0.25磅)
                        }
                    }
                ],
                 # 🔴 难点 2: 小号大件 (Small Bulky/Oversize)
                 # 0-50磅: $11.89 + 超出首磅(1lb)的部分每磅 $0.38
                "Small Bulky": [
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.89,
                            "base_weight": 1.0,   # "超出首磅"意味着起步重是 1.0
                            "unit_fee": 0.38,
                            "unit_step": 1.0      # 每 1 磅
                        }
                    }
                ],

                # 🔴 难点 3: 大号大件 (Medium Bulky/Oversize)
                # 0-50磅: $11.89 + 超出首磅(1lb)的部分每磅 $0.38
                "Medium Bulky": [ 
                    {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 11.89,
                            "base_weight": 1.0,
                            "unit_fee": 0.38,
                            "unit_step": 1.0
                        }
                    }
                ],

                # 🔴 难点 4: 超大件 (Large Bulky) 分段公式
                "Large Bulky": [
                    # 0至50磅:超出1磅的部分
                     {
                        "max_weight": 50.0,
                        "formula": {
                            "base_fee": 32.48,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 1.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.38,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 50至70磅: 超出51磅的部分... (注意：原文通常是超出50磅，请核对是否是51)
                    {
                        "max_weight": 70.0,
                        "formula": {
                            "base_fee": 47.43,    # ⏳ 请填入 50-70磅档位的 起步价
                            "base_weight": 51.0,  # 起步重 (通常是上一档的上限)
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 70至150磅
                    {
                        "max_weight": 150.0,
                        "formula": {
                            "base_fee": 68.30,    # ⏳ 请填入 70磅时的 起步价
                            "base_weight": 71.0,
                            "unit_fee": 0.75,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    },
                    # 超过150磅
                    {
                        "max_weight": 9999.0,     # 无限大
                        "formula": {
                            "base_fee": 231.61,   # ⏳ 请填入 150磅时的 起步价
                            "base_weight": 151.0,
                            "unit_fee": 0.19,     # ⏳ 请填入每磅加收多少
                            "unit_step": 1.0
                        }
                    }
                ]
            }
        }
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
