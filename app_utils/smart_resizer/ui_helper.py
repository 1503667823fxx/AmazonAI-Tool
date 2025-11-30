import streamlit as st

def show_empty_state():
    st.info("👈 请在左侧侧边栏上传图片并选择目标比例。")
    st.markdown("""
    **功能说明：**
    * **1:1** - 适合亚马逊主图
    * **4:3** - 适合A+页面标准插图
    * **21:9** - 适合品牌故事模块或Banner
    """)
