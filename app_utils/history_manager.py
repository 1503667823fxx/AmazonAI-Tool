import streamlit as st
import time
from collections import deque

class HistoryManager:
    """
    [纯逻辑层] 只负责管理 Session State 中的数据，不包含任何 UI 代码。
    """
    def __init__(self, key="history_queue", max_len=20):
        self.key = key
        if self.key not in st.session_state:
            st.session_state[self.key] = deque(maxlen=max_len)

    def add(self, image_bytes, source_name, prompt_summary):
        """添加一条新记录"""
        timestamp = time.strftime("%H:%M")
        unique_id = f"{int(time.time()*1000)}"
        
        st.session_state[self.key].appendleft({
            "id": unique_id,
            "image": image_bytes,
            "source": source_name,
            "time": timestamp,
            "desc": prompt_summary
        })

    def get_all(self):
        """获取所有数据"""
        return list(st.session_state[self.key])
