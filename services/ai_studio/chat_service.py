import google.generativeai as genai

class StudioChatService:
    def __init__(self, api_key, model_name, system_instruction=None):
        self.api_key = api_key
        self.model_name = model_name
        self.system_instruction = system_instruction
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _merge_user_messages(self, raw_msgs):
        merged_history = []
        current_turn = None

        for msg in raw_msgs:
            role = msg["role"]
            content_parts = []

            if msg.get("ref_images"):
                content_parts.extend(msg["ref_images"])
            
            if msg.get("content"):
                content_parts.append(msg["content"])

            if not content_parts:
                continue

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
        formatted_history = self._merge_user_messages(st_history_msgs)
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction
            )
        except:
            model = genai.GenerativeModel(model_name=self.model_name)
        
        return model.start_chat(history=formatted_history)
