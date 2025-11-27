import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import time
from collections import deque

# ==========================================
# 🧠 智能分析核心 (Smart Analysis Engine)
# ==========================================
def smart_analyze_image(model_name, image_file, task_type, user_idea, user_weight, enable_split, translator):
    """
    执行智能图片分析，生成中英文对照的 Prompt 数据
    """
    try:
        # 重置文件指针
        image_file.seek(0)
        img_obj = Image.open(image_file)
        
        model = genai.GenerativeModel(model_name)
        
        # 注入高质量摄影指令
        special_instruction = ""
        if "Product Only" in task_type:
            special_instruction = """
            SPECIAL INSTRUCTION FOR PRODUCT PHOTOGRAPHY:
            1. **Layout**: If user implies 'flat lay' or 'break down', use "Knolling photography", "Neatly arranged".
            2. **Realism**: Use "Contact shadows", "Ambient occlusion" to avoid floating look.
            3. **Texture**: Emphasize "fabric texture", "material details".
            """
        
        # 核心权重逻辑注入
        weight_instruction = f"""
        WEIGHT CONTROL INSTRUCTION:
        The user has set an influence weight of {user_weight} (Range 0.0 to 1.0).
        - If weight > 0.7: Prioritize the User's Idea ('{user_idea}') completely.
        - If weight < 0.3: Prioritize the Visual Analysis of the image.
        - If weight is 0.4-0.6: Balance both.
        """

        # 强制英文输出指令
        lang_instruction = "STRICT FORMAT: Output MUST be in ENGLISH. Do not output Chinese directly."

        if enable_split:
            prompt_req = f"""
            Role: Art Director. 
            Task: Create detailed prompts based on User Idea and Image. Type: {task_type}.
            {weight_instruction}
            {special_instruction}
            {lang_instruction}
            IMPORTANT LOGIC: Split distinct outputs into separate prompts using "|||".
            STRICT OUTPUT FORMAT: Separate prompts with "|||". NO Markdown.
            User Idea: {user_idea}
            Output: English Prompts Only.
            """
        else:
            prompt_req = f"""
            Role: Art Director. 
            Task: Create ONE single, high-quality prompt based on User Idea and Image. Type: {task_type}.
            {weight_instruction}
            {special_instruction}
            {lang_instruction}
            STRICT OUTPUT FORMAT: Provide ONE unified prompt. NO "|||". NO Markdown.
            User Idea: {user_idea}
            Output: English Prompt Only.
            """

        response = model.generate_content([prompt_req, img_obj])
        raw_text = response.text.strip()
        
        # 解析并翻译
        prompt_list = raw_text.split("|||")
        result_data = []
        
        for p in prompt_list:
            # 清洗文本：去除开头的 =、-、空格
            p_en = p.strip().lstrip("=- ").strip()
            
            if p_en:
                # 翻译为中文
                p_zh = translator.to_chinese(p_en)
                
                # 兜底：如果翻译回来还是空的（极少情况），用英文填充
                if not p_zh: 
                    p_zh = p_en
                
                result_data.append({"en": p_en, "zh": p_zh})
        
        return result_data

    except Exception as e:
        st.error(f"智能分析模块出错: {str(e)}")
        return []

# ==========================================
# 🗂️ 历史记录核心 (History Manager)
# ==========================================
class HistoryManager:
    def __init__(self):
        if "history_queue" not in st.session_state:
            st.session_state["history_queue"] = deque(maxlen=20)

    def add(self, image_bytes, source, prompt_summary):
        timestamp = time.strftime("%H:%M")
        unique_id = f"{int(time.time()*1000)}"
        
        st.session_state["history_queue"].appendleft({
            "id": unique_id,
            "image": image_bytes,
            "source": source,
            "time": timestamp,
            "desc": prompt_summary
        })

    def render_sidebar(self):
        with st.expander("🕒 历史记录 (History)", expanded=False):
            if not st.session_state["history_queue"]:
                st.caption("暂无生成记录")
                return

            for item in st.session_state["history_queue"]:
                col_thumb, col_info = st.columns([1, 2])
                with col_thumb:
                    thumb = create_preview_thumbnail(item['image'], max_width=150)
                    st.image(thumb, use_container_width=True)
                with col_info:
                    st.caption(f"**{item['source']}**")
                    st.caption(f"_{item['desc'][:15]}..._")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("🔍", key=f"h_zoom_{item['id']}"):
                            show_preview_modal(item['image'], item['source'])
                    with b2:
                        final_bytes, mime = process_image_for_download(item['image'], format="JPEG")
                        st.download_button("📥", data=final_bytes, file_name=f"hist_{item['id']}.jpg", mime=mime, key=f"h_dl_{item['id']}")
                st.divider()

# ==========================================
# 🛠️ 图片处理核心 (Image Engine)
# ==========================================
@st.cache_data(show_spinner=False)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    try:
        if not image_bytes: return None, None
        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        target_format = format.upper()
        mime_type = f"image/{target_format.lower()}"

        if target_format == "JPEG":
            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
            image.save(buf, format="JPEG", quality=quality)
        else:
            image.save(buf, format="PNG")
        
        return buf.getvalue(), mime_type
    except Exception:
        return image_bytes, "image/png"

@st.cache_data(show_spinner=False)
def create_preview_thumbnail(image_bytes, max_width=800):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except:
        return image_bytes

def show_preview_modal(image_bytes, caption):
    st.toast(f"正在全屏预览: {caption}")
    st.image(image_bytes, caption=caption, use_container_width=True)

# ==========================================
# 🗣️ 翻译核心 (Translation Engine)
# ==========================================
class AITranslator:
    def __init__(self):
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.model = genai.GenerativeModel("models/gemini-flash-latest")
            self.valid = True
        else:
            self.valid = False

    def to_chinese(self, text):
        if not text or not self.valid: return text
        # 优化提示词，强制中文输出
        return self._run(text, "Simplified Chinese")

    def to_english(self, text):
        if not text or not self.valid: return text
        return self._run(text, "English")

    def _run(self, text, lang):
        # 增加安全设置，防止因“误判”导致翻译被拦截（返回空）
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        try:
            prompt = f"Translate the following text to {lang}. Output ONLY the translation without any explanation. Text: {text}"
            resp = self.model.generate_content(prompt, safety_settings=safety_settings)
            return resp.text.strip()
        except Exception:
            # 简单的重试机制
            try:
                time.sleep(0.5)
                resp = self.model.generate_content(prompt)
                return resp.text.strip()
            except:
                return text # 最终兜底：返回原文
