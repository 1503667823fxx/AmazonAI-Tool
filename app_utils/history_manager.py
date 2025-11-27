import streamlit as st
import time
from collections import deque

class HistoryManager:
    """
    [纯逻辑层] 管理 Session State 中的数据。
    新增：删除指定记录、清空记录的功能。
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

    def delete(self, item_id):
        """删除指定 ID 的记录"""
        # deque 不支持直接 remove by key，需重建
        current_list = list(st.session_state[self.key])
        new_list = [item for item in current_list if item['id'] != item_id]
        st.session_state[self.key] = deque(new_list, maxlen=st.session_state[self.key].maxlen)

    def clear(self):
        """清空所有记录"""
        st.session_state[self.key].clear()
