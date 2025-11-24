import streamlit as st

def check_password():
    """
    检查密码是否正确。
    如果没有登录，显示输入框；
    如果登录成功，返回 True。
    """
    # 1. 检查 Session 中是否有登录标记
    if st.session_state.get("password_correct", False):
        return True

    # 2. 定义验证逻辑
    def password_entered():
        """检查用户输入的密码是否匹配 Secrets 中的密码"""
        if st.session_state["password_input"] == st.secrets["TEAM_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]  # 验证成功后清除输入框缓存
        else:
            st.session_state["password_correct"] = False

    # 3. 显示登录界面
    st.markdown("## 🔒 亚马逊全能智造台 - 内部登录")
    st.text_input(
        "请输入团队访问密码", 
        type="password", 
        key="password_input", 
        on_change=password_entered
    )

    # 4. 错误提示
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ 密码错误，请重试")
    
    # 5. 只要没通过验证，就停止运行后面的代码
    return False
