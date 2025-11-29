import streamlit as st
import google.generativeai as genai

class StudioChatService:
    """
    [AI Studio 专属] 对话服务控制器
    负责管理上下文、合并多模态消息、处理流式响应。
    """
    
    def __init__(self, api_key, model_name, system_instruction=None):
        self.api_key = api_key
        self.model_name = model_name
        self.system_instruction = system_instruction
        
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _merge_user_messages(self, raw_msgs):
        """
        核心逻辑：合并连续的用户消息。
        Gemini API 要求 User -> Model 交替，必须合并连续的 User 消息。
        """
        merged_history = []
        current_turn = None

        for msg in raw_msgs:
            role = msg["role"]
            content_parts = []

            # 1. 提取图片
            if msg.get("ref_images"):
                content_parts.extend(msg["ref_images"])
            
            # 2. 提取文本
            if msg.get("content"):
                content_parts.append(msg["content"])

            if not content_parts:
                continue

            # 3. 合并逻辑
            if current_turn and current_turn["role"] == role:
                current_turn["parts"].extend(content_parts)
            else:
                if current_turn:
                    merged_history.append(current_turn)
                current_turn = {"role": role, "parts": content_parts}

        if current_turn:
            merged_history.append(current_turn)

        return merged_history

    def create_chat_session(self, st_history_msgs):
        """创建 Gemini Chat Session"""
        # 1. 格式化历史消息
        formatted_history = self._merge_user_messages(st_history_msgs)
        
        # 2. 初始化模型
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction
            )
        except:
            # 兼容性回退
            model = genai.GenerativeModel(model_name=self.model_name)
            # 如果不支持 system_instruction，可以手动插入 history 头部（此处简化处理）

        # 3. 启动
        return model.start_chat(history=formatted_history)
