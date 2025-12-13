import math
# 引入第一步建立的数据
from app_utils.fba_data.config import SIZE_TIERS, DIM_DIVISOR, FULFILLMENT_FEES, STORAGE_FEES, LOW_INVENTORY_FEES

class FBACalculator:
    def __init__(self, length, width, height, weight_lb, category="Standard"):
        self.l = float(length)
        self.w = float(width)
        self.h = float(height)
        self.weight = float(weight_lb)
        self.category = category
        
        # 排序边长，方便比对 (长 > 宽 > 高)
        self.dims = sorted([self.l, self.w, self.h], reverse=True)
        self.longest, self.median, self.shortest = self.dims[0], self.dims[1], self.dims[2]
        self.girth_len = self.longest + 2 * (self.median + self.shortest)
        self.volume_ft3 = (self.l * self.w * self.h) / 1728 # 转化为立方英尺

    def get_dim_weight(self):
        """计算体积重"""
        return (self.l * self.w * self.h) / DIM_DIVISOR

    def get_size_tier(self):
        """
        判定尺寸分段 (层级递进法)
        """
        # 0. 准备基础数据
        billable_weight = max(self.weight, self.get_dim_weight()) # 取较大值
        
        # ----------------------------------------------------------------------
        # Level 1: Small Standard (小号标准)
        # ----------------------------------------------------------------------
        ss = SIZE_TIERS["Small Standard"]
        if (self.weight <= ss["max_weight"] and  # 标准件通常只看实重是否超1lb，但严格来说按亚马逊逻辑应看计费重，此处按图示保持实重判断
            self.longest <= ss["max_longest"] and 
            self.median <= ss["max_median"] and 
            self.shortest <= ss["max_shortest"]):
            return "Small Standard"
            
        # ----------------------------------------------------------------------
        # Level 2: Large Standard (大号标准)
        # ----------------------------------------------------------------------
        ls = SIZE_TIERS["Large Standard"]
        # 大号标准限制：计费重量 <= 20lb
        if (billable_weight <= ls["max_weight"] and 
            self.longest <= ls["max_longest"] and 
            self.median <= ls["max_median"] and 
            self.shortest <= ls["max_shortest"]):
            return "Large Standard"

        # ======================================================================
        # 进入大件 (Bulky/Oversize) 区域
        # 这里的关键是：只要符合更小尺寸的定义，就返回更小尺寸；
        # 只有 "漏" 下来的才会进入下一级。
        # ======================================================================
# ----------------------------------------------------------------------
        # Level 3: Small Bulky (小号大件)
        # ----------------------------------------------------------------------
        sb = SIZE_TIERS["Small Bulky"]
        if (billable_weight <= sb["max_weight"] and   # <= 50 lb
            self.longest <= sb["max_longest"] and     # <= 37 inch
            self.median <= sb["max_median"] and       # <= 28 inch
            self.shortest <= sb["max_shortest"] and   # <= 20 inch
            self.girth_len <= sb["length_girth"]):    # <= 130 inch
            return "Small Bulky"

        # ----------------------------------------------------------------------
        # Level 4: Medium Bulky (中号大件 / 原 Large Oversize)
        # ----------------------------------------------------------------------
        # 您提供的规则：“超大件是...最长边超过59...或重量超过50...”
        # 反过来说：如果不超过59且不超过50，它就是 Medium Bulky。
        mb = SIZE_TIERS["Medium Bulky"]
        if (billable_weight <= mb["max_weight"] and   # <= 50 lb (这里拦截了所有50磅以下的)
            self.longest <= mb["max_longest"] and     # <= 59 inch
            self.median <= mb["max_median"] and       # <= 33 inch
            self.shortest <= mb["max_shortest"] and   # <= 33 inch
            self.girth_len <= mb["length_girth"]):    # <= 130 inch
            return "Medium Bulky"

        # ----------------------------------------------------------------------
        # Level 5: Large Bulky (超大件)
        # ----------------------------------------------------------------------
        # 如果代码跑到了这里，说明它要么重 > 50lb，要么长 > 59 inch，符合您的“超大件”定义
        lb = SIZE_TIERS["Large Bulky"]
        if billable_weight <= lb["max_weight"] and self.girth_len <= lb["length_girth"]: 
            return "Large Bulky"

        # ----------------------------------------------------------------------
        # Level 6: Special Oversize (特殊超大件)
        # ----------------------------------------------------------------------
        return "Special Oversize"



def calculate_fulfillment_fee(self, price, is_apparel=False, is_dangerous=False, season="Off-Peak"):
        """
        计算基础配送费 (升级版)
        新增参数: 
        - price: 商品售价 (用于判断是否低价/高价)
        - is_apparel: 是否服装
        - is_dangerous: 是否危险品
        - season: 季节 (Off-Peak / Peak)
        """
        tier = self.get_size_tier()
        billable_weight = max(self.weight, self.get_dim_weight())
        
        # 1. 确定价格段 (Price Tier)
        if price < 10:
            price_tier = "Under_10"
        elif price > 50:
            # 如果配置里没填 Over_50，通常默认使用 Price_10_50 的费率
            price_tier = "Over_50" if "Over_50" in FULFILLMENT_FEES[season] else "Price_10_50"
        else:
            price_tier = "Price_10_50"
            
        # 2. 确定商品类型 (Product Category)
        if is_dangerous:
            prod_type = "Dangerous"
        elif is_apparel:
            prod_type = "Apparel"
        else:
            prod_type = "Standard"
            
        # 3. 逐层查找费率表
        # 路径: 季节 -> 价格段 -> 类型 -> 尺寸
     try:
            rate_card = FULFILLMENT_FEES[season][price_tier][prod_type].get(tier, [])
        except KeyError:
             # 如果找不到具体的 key，尝试回退到标准逻辑或报错
             return 0, billable_weight, f"未找到费率配置: {season}-{price_tier}-{prod_type}-{tier}"
            
# 4. 匹配重量档位
        final_fee = 0
        found_bracket = False
        
        for bracket in rate_card:
            # 找到第一个“上限重量”大于等于“当前计费重量”的档位
            if billable_weight <= bracket["max_weight"]:
                found_bracket = True
                
                # 情况 A: 简单固定费率 (Old logic)
                if "fee" in bracket:
                    final_fee = bracket["fee"]
                
                # 情况 B: 复杂公式计算 (New logic)
                elif "formula" in bracket:
                    f = bracket["formula"]
                    base_fee = f["base_fee"]
                    base_weight = f["base_weight"]
                    unit_fee = f["unit_fee"]
                    unit_step = f["unit_step"]
                    
                    # 只有当重量超过起步重时才计算增量
                    if billable_weight > base_weight:
                        # 计算超出的重量
                        excess_weight = billable_weight - base_weight
                        
                        # 计算有多少个计费单位 (比如每 4oz 一个单位，即 0.25lb)
                        # 亚马逊规则通常是“向上取整”：不足4oz按4oz算
                        units = math.ceil(excess_weight / unit_step)
                        
                        final_fee = base_fee + (units * unit_fee)
                    else:
                        # 如果虽然落在这个档位，但重量没超过起步重 (极少见，但逻辑上要闭环)
                        final_fee = base_fee
                
                break # 找到后立即停止循环
        
      # 5. 如果超过了所有档位的最大值 (Over max_weight)
        if not found_bracket and rate_card:
            # 取最后一个档位的规则继续算，通常超大件的最后一个档位 max_weight 会设得很大
            last_bracket = rate_card[-1]
            if "formula" in last_bracket:
                # 复用上面的公式逻辑
                f = last_bracket["formula"]
                base_fee = f["base_fee"]
                base_weight = f["base_weight"]
                # ... (同上计算逻辑)
                excess_weight = billable_weight - base_weight
                units = math.ceil(excess_weight / f["unit_step"])
                final_fee = base_fee + (units * f["unit_fee"])
            else:
                 # 旧逻辑的 fallback
                 final_fee = last_bracket.get("fee", 0)

        return final_fee, billable_weight, tier


    def calculate_total_cost(self, season="Jan-Sep", low_inv_days=None):
        """高级计算：包含仓储和附加费"""
        fba_fee, _, tier = self.calculate_fulfillment_fee()
        
        # 1. 仓储费
        storage_rate = STORAGE_FEES[season]["Standard" if "Standard" in tier else "Oversize"]
        storage_fee = self.volume_ft3 * storage_rate
        
        # 2. 低库存费
        low_inv_fee = 0
        if low_inv_days:
            # 简化逻辑演示
            if low_inv_days < 28:
                low_inv_fee = 0.32 # 示例取值，需完善逻辑
        
        return {
            "fulfillment_fee": fba_fee,
            "storage_fee": storage_fee,
            "low_inventory_fee": low_inv_fee,
            "total": fba_fee + storage_fee + low_inv_fee
        }

    def generate_suggestions(self):
        """智能优化建议 (本地代码实现)"""
        suggestions = []
        tier = self.get_size_tier()
        
        # 建议 1: 尺寸压线检查
        # 比如：如果是 Large Standard，且最短边接近 0.75 (Small Standard 的界限)
        if tier == "Large Standard":
            if self.shortest <= 1.0 and self.weight <= 1.0: # 接近 Small Standard
                diff = self.shortest - 0.75
                if diff > 0:
                    suggestions.append(f"⚠️ **降级机会：** 您的产品最短边为 {self.shortest}英寸。如果能压缩 {diff:.2f}英寸 至 0.75英寸，可能降级为【Small Standard】，运费将大幅降低。")
        
        # 建议 2: 体积重优化
        dim_w = self.get_dim_weight()
        if dim_w > self.weight:
            diff_w = dim_w - self.weight
            suggestions.append(f"📦 **包装优化：** 当前按体积重 {dim_w:.2f} lb 计费，比实重高出 {diff_w:.2f} lb。建议减少包装体积（使用真空包装等）。")
            
        return suggestions
