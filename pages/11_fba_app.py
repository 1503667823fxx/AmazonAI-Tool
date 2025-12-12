import streamlit as st
from services.fba_logic.calculator import FBACalculator

def show_fba_calculator():
    st.title("📦 亚马逊 FBA 智能计算器 (2025版)")
    st.markdown("基于最新规则：尺寸分段、低库存费、仓储费自动测算")
    
    # --- 侧边栏：输入区域 ---
    with st.sidebar:
        st.header("1. 产品参数输入")
        
        col1, col2 = st.columns(2)
        with col1:
            unit = st.radio("单位", ["inch/lb", "cm/kg"])
        
        # 如果是 cm/kg 需要转换逻辑，这里为了简化演示，默认 inch/lb
        # 实际生产中您可以在这里加一个简单的转换函数
        
        length = st.number_input("长 (Length)", value=10.0, step=0.1)
        width = st.number_input("宽 (Width)", value=8.0, step=0.1)
        height = st.number_input("高 (Height)", value=1.0, step=0.1)
        weight = st.number_input("重量 (Weight lb)", value=1.0, step=0.1)
        
        st.header("2. 高级选项")
        season = st.selectbox("当前季节", ["Jan-Sep", "Oct-Dec"], index=0)
        low_inv_days = st.slider("历史供货天数 (用于计算低库存费)", 0, 90, 45)

    # --- 实例化计算器 ---
    # 注意：这里假设用户输入的是 inch 和 lb，如果选了 cm 需要先转换
    calc = FBACalculator(length, width, height, weight)
    
    # --- 核心计算 ---
    # 1. 基础配送费计算
    fba_fee, billable_weight, tier = calc.calculate_fulfillment_fee()
    
    # 2. 总成本计算
    costs = calc.calculate_total_cost(season=season, low_inv_days=low_inv_days)
    
    # --- 主界面展示 ---
    
    # 第一部分：结果概览 (Metrics)
    st.subheader("📊 计算结果")
    c1, c2, c3 = st.columns(3)
    c1.metric("尺寸分段", tier)
    c2.metric("计费重量", f"{billable_weight:.2f} lb", delta=f"实重: {weight} lb", delta_color="off")
    c3.metric("基础 FBA 配送费", f"${fba_fee:.2f}")
    
    st.divider()
    
    # 第二部分：成本明细 (Table/Chart)
    st.subheader("💰 预估总成本明细")
    
    col_detail, col_chart = st.columns([1, 1])
    
    with col_detail:
        st.write("各项费用拆解：")
        st.markdown(f"""
        * **配送费 (Fulfillment):** `${costs['fulfillment_fee']:.2f}`
        * **月度仓储费 (Storage):** `${costs['storage_fee']:.2f}` ({season})
        * **低库存水平费:** `${costs['low_inventory_fee']:.2f}`
        * ---
        * **单件总 FBA 成本:** **`${costs['total']:.2f}`**
        """)
        
        if low_inv_days < 28:
            st.error(f"⚠️ 警告：您的库存水平 ({low_inv_days}天) 过低，正在被收取低库存费！")
    
    with col_chart:
        # 简单的条形图可视化
        st.bar_chart({
            "配送费": costs['fulfillment_fee'],
            "仓储费": costs['storage_fee'],
            "低库存费": costs['low_inventory_fee']
        })

    st.divider()

    # 第三部分：智能建议 (Smart Insights)
    st.subheader("💡 AI 智能优化建议")
    suggestions = calc.generate_suggestions()
    
    if suggestions:
        for sug in suggestions:
            st.info(sug)
    else:
        st.success("✅ 完美！当前包装已是最优状态，暂无优化建议。")

# 只要在您的主入口文件 (如 main.py) 导入并调用 show_fba_calculator() 即可
if __name__ == "__main__":
    show_fba_calculator()
