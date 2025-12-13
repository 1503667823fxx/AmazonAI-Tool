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
        """判定尺寸分段"""
        # 逻辑：从小到大判断，符合即返回
        # 1. Check Small Standard
        ss = SIZE_TIERS["Small Standard"]
        if (self.weight <= ss["max_weight"] and 
            self.longest <= ss["max_longest"] and 
            self.median <= ss["max_median"] and 
            self.shortest <= ss["max_shortest"]):
            return "Small Standard"
            
        # 2. Check Large Standard
        ls = SIZE_TIERS["Large Standard"]
        # 注意：大号标准需要看 (实重 vs 体积重) 的较大值是否超过20lb
        billable_weight = max(self.weight, self.get_dim_weight())
        if (billable_weight <= ls["max_weight"] and 
            self.longest <= ls["max_longest"] and 
            self.median <= ls["max_median"] and 
            self.shortest <= ls["max_shortest"]):
            return "Large Standard"

        return "Large Bulky (Oversize)"

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
            # 安全获取，防止字典这就没配
            category_data = FULFILLMENT_FEES.get(season, {}).get(price_tier, {}).get(prod_type, {})
            rate_card = category_data.get(tier, [])
        except Exception as e:
            return 0, billable_weight, f"Error: 费率配置缺失 ({str(e)})"

        if not rate_card:
            # 如果没找到对应尺寸的费率表 (比如该类型不支持该尺寸)
            return 0, billable_weight, tier

        # 4. 匹配重量档位
        base_fee = 0
        found = False
        
        for bracket in rate_card:
            if billable_weight <= bracket["max_weight"]:
                base_fee = bracket["fee"]
                found = True
                break
        
        # 5. 处理超重情况 (如果没有在表里找到，取最后一档 + 附加费)
        # 这里的逻辑比较复杂，为了简化，您可以暂时先取最后一档的价格
        # 或者后续我们再完善“每磅附加费”的计算逻辑
        if not found and rate_card:
             base_fee = rate_card[-1]["fee"]
             # TODO: 这里可以加上超重部分的计算逻辑
            
        return base_fee, billable_weight, tier

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
