import streamlit as st
from PIL import Image
import google.generativeai as genai

class ChatSessionManager:
    """
    对话逻辑控制器 (The Logic Chain Brain)
    负责管理上下文关系、多模态消息合并、以及 System Prompt 的注入。
    """
    
    def __init__(self, model_name, api_key, system_instruction=None):
        self.model_name = model_name
        self.api_key = api_key
        self.system_instruction = system_instruction
        
        # 配置 API
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _merge_user_messages(self, raw_msgs):
        """
        核心逻辑：合并连续的用户消息。
        如果用户先上传了图片(User)，又发了文字(User)，逻辑上属于同一轮对话。
        Gemini API 严格要求 User -> Model -> User 交替，因此必须合并。
        """
        merged_history = []
        current_turn = None

        for msg in raw_msgs:
            role = msg["role"]
            content_parts = []

            # 1. 提取图片 (Visual Context)
            if msg.get("ref_images"):
                content_parts.extend(msg["ref_images"])
            
            # 2. 提取文本 (Text Context)
            if msg.get("content"):
                content_parts.append(msg["content"])

            if not content_parts:
                continue

            # 3. 合并逻辑
            if current_turn and current_turn["role"] == role:
                # 如果当前角色和上一条一样（比如连续两条 User），则追加内容
                current_turn["parts"].extend(content_parts)
            else:
                # 如果角色切换了，先保存上一轮，再开启新一轮
                if current_turn:
                    merged_history.append(current_turn)
                current_turn = {"role": role, "parts": content_parts}

        # 别忘了追加最后一轮
        if current_turn:
            merged_history.append(current_turn)

        return merged_history

    def build_context_window(self, raw_msgs):
        """
        构建发送给 API 的完整上下文窗口
        """
        # 1. 清洗和合并消息
        clean_history = self._merge_user_messages(raw_msgs)
        
        # 2. 过滤掉不支持的消息类型（比如 UI 上的 Error 提示，或者尚未生成的空消息）
        # 这里的 history 是符合 Gemini SDK 标准的 [{role:.., parts:[..]}]
        final_history = []
        for turn in clean_history:
            # 确保 parts 不为空
            if turn["parts"]:
                final_history.append(turn)
                
        return final_history

    def start_chat_session(self, st_history):
        """
        启动一个带记忆的 Chat Session
        """
        # 1. 准备历史记录 (不包含最后一条正在发送的，因为 SDK 的 send_message 会处理它)
        # 注意：这里我们传入空列表或已有的历史。
        # 如果是 start_chat(history=...)，SDK 会把这些作为过去式。
        
        formatted_history = self.build_context_window(st_history)
        
        # 2. 注入 System Prompt (如果模型支持)
        # Gemini 1.5/Pro 系列支持 system_instruction 参数
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction
            )
        except:
            #以此兼容旧版库或不支持 system_instruction 的模型
            model = genai.GenerativeModel(model_name=self.model_name)
            if self.system_instruction:
                # 如果不支持原生参数，就把 System Prompt 塞到历史记录的第一条
                formatted_history.insert(0, {"role": "user", "parts": [f"System Instruction: {self.system_instruction}"]})
                formatted_history.insert(1, {"role": "model", "parts": ["Understood. I will follow these instructions."]})

        # 3. 启动会话
        chat = model.start_chat(history=formatted_history)
        return chat
