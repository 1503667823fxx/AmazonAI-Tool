import streamlit as st
from services.fba_logic.calculator import FBACalculator
from app_utils.fba_data.unit_converter import convert_inputs, get_display_unit

def show_fba_calculator():
    st.title("📦 亚马逊 FBA 智能计算器 (2025版)")
    st.markdown("基于最新规则：尺寸分段、低库存费、仓储费自动测算")
    
    # --- 侧边栏：输入区域 ---
    with st.sidebar:
        st.header("1. 产品参数输入")
        
        # 1. 选择单位
        unit_mode = st.radio("输入单位", ["inch/lb", "cm/kg"], horizontal=True)
        dim_label, wt_label = get_display_unit(unit_mode)
        
        # 2. 输入数值 (根据选择的单位动态显示 Label)
        col1, col2 = st.columns(2)
        with col1:
            raw_l = st.number_input(f"长 ({dim_label})", value=10.0, step=0.5)
            raw_h = st.number_input(f"高 ({dim_label})", value=1.0, step=0.1)
        with col2:
            raw_w = st.number_input(f"宽 ({dim_label})", value=8.0, step=0.5)
            raw_wt = st.number_input(f"重 ({wt_label})", value=1.0, step=0.1)

        # 🆕 3. 实时自动转换 (关键步骤)
        # 无论用户输入的是什么，这里都会变成 inch/lb 传给计算器
        final_l, final_w, final_h, final_wt = convert_inputs(
            raw_l, raw_w, raw_h, raw_wt, unit_mode
        )

        st.divider()
        st.header("2. 产品属性")
        price = st.number_input("商品售价 ($)", value=19.99)
        is_apparel = st.checkbox("是服装类目 (Apparel)?")
        is_dangerous = st.checkbox("是危险品 (Hazmat)?")
        
        st.divider()
        st.header("3. 高级选项")
        season = st.selectbox("当前季节", ["Jan-Sep", "Oct-Dec"], index=0)
        low_inv_days = st.slider("历史供货天数 (用于计算低库存费)", 0, 90, 45)

    # --- 主界面展示 ---
    
    # 💡 增加一个提示，让用户知道系统实际是用什么数据在算
    if unit_mode == "cm/kg":
        st.caption(f"ℹ️ 系统已自动转换用于计算: {final_l} x {final_w} x {final_h} in, {final_wt} lb")
        
    # --- 实例化计算器 ---
    # 注意：这里假设用户输入的是 inch 和 lb，如果选了 cm 需要先转换
    calc = FBACalculator(final_l, final_w, final_h, final_wt)
    
    # --- 核心计算 ---
    # 1. 基础配送费计算
    fba_fee, billable_weight, tier = calc.calculate_fulfillment_fee(
        price=price,
        is_apparel=is_apparel,
        is_dangerous=is_dangerous,
        season=season
    )
    
    # 2. 总成本计算
    costs = calc.calculate_total_cost(
        season=season, 
        low_inv_days=low_inv_days,
        price=price,
        is_apparel=is_apparel,
        is_dangerous=is_dangerous
    )
    
    # --- 主界面展示 ---
    
    # 第一部分：结果概览 (Metrics)
    st.subheader("📊 计算结果")
    c1, c2, c3 = st.columns(3)
    c1.metric("尺寸分段", tier)
    c2.metric("计费重量", f"{billable_weight:.2f} lb", delta=f"实重: {final_wt:.2f} lb", delta_color="off")
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
