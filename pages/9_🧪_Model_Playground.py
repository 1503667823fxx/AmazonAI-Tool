import streamlit as st
import requests
import json
import base64
from PIL import Image
import io
import sys
import os

# --- 0. 引入门禁 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    if not auth.check_password(): st.stop()
except ImportError:
    pass 

st.set_page_config(page_title="API 终极实验室", page_icon="🧪", layout="wide")

st.title("🧪 Gemini API 终极实验室 (TS 复刻版)")
st.info("本页面复刻了 geminiService.ts 中的图像预处理逻辑 (Resize -> PNG)。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- 2. TS 逻辑复刻函数 (Python版) ---

def resize_for_context(pil_img, max_dim=1024):
    """
    复刻 TS: resizeForContext
    将图片限制在 max_dim 以内，保持比例，强制转为 PNG 字节流
    """
    w, h = pil_img.size
    # 只有当图片过大时才缩放
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # TS 代码使用的是 canvasToBase64(..., 'image/png')
    # 所以这里我们也必须转为 PNG
    buff = io.BytesIO()
    pil_img.save(buff, format="PNG")
    return base64.b64encode(buff.getvalue()).decode('utf-8')

# --- 3. 界面 ---

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数配置")
    
    # TS 代码中使用的模型名称
    model_name = st.text_input("模型名称", value="gemini-2.5-flash-image")
    
    uploaded_file = st.file_uploader("上传图片", type=["jpg", "png", "webp"])
    
    prompt_input = st.text_area("修改指令 (Prompt)", value="Change the background to a luxury office", height=100)
    
    st.caption("💡 提示：根据 TS 代码逻辑，我们将自动把图片转为 PNG 并限制在 1024px 以内。")

with col2:
    st.subheader("2. 执行与诊断")
    
    if st.button("🚀 发送请求 (复刻 TS 逻辑)", type="primary"):
        if not uploaded_file:
            st.warning("请上传图片")
        else:
            status = st.empty()
            debug_area = st.expander("🔍 查看 Payload 和 响应", expanded=True)
            
            try:
                status.info("正在预处理图片 (Resize & Convert to PNG)...")
                
                # 加载图片并转 RGB (防止 RGBA 兼容性问题)
                original_pil = Image.open(uploaded_file).convert("RGB")
                
                # 1. 准备主图 (Clean Source)
                clean_source_b64 = resize_for_context(original_pil, max_dim=1024)
                
                # 2. 构造 Prompt (参考 TS 的 Standard General Edit)
                # finalPrompt = `Edit instruction: ${prompt}. Maintain photorealism.`
                final_prompt = f"Edit instruction: {prompt_input}. Maintain photorealism."
                
                parts = []
                parts.append({"text": final_prompt})
                parts.append({"inline_data": {"mime_type": "image/png", "data": clean_source_b64}})

                # 构建请求体
                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "response_modalities": ["IMAGE"],
                        "temperature": 0.4
                    }
                }
                
                # 发起 HTTP 请求
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
                
                status.info(f"正在 POST 到 {model_name} ...")
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload)
                )
                
                # 处理响应
                if response.status_code == 200:
                    res_json = response.json()
                    with debug_area:
                        st.caption("API Response:")
                        st.json(res_json)
                    
                    # 提取图片
                    try:
                        candidates = res_json.get("candidates", [])
                        found = False
                        if candidates:
                            parts_res = candidates[0].get("content", {}).get("parts", [])
                            for part in parts_res:
                                if "inline_data" in part:
                                    b64_data = part["inline_data"]["data"]
                                    img_data = base64.b64decode(b64_data)
                                    st.image(img_data, caption="Gemini 生成结果")
                                    st.success("🎉 成功！TS 逻辑复刻生效！")
                                    found = True
                                    break
                        
                        if not found:
                            st.error("⚠️ API 返回成功但没有图片数据 (可能被拦截或返回了文本)。请查看上方 JSON。")
                            
                    except Exception as e:
                        st.error(f"解析失败: {e}")
                else:
                    status.error(f"HTTP {response.status_code}")
                    st.error(response.text)

            except Exception as e:
                st.error(f"系统错误: {e}")
                    st.error(response.text) # 打印报错详情
                    
            except Exception as e:
                st.error(f"系统错误: {e}")
