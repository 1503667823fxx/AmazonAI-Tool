import gradio as gr
import numpy as np
from PIL import Image
import sys
import os

# 将项目根目录加入路径，以便引用 services
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from services.magic_canvas.sam_engine import SAMService
from services.magic_canvas.inpaint_engine import InpaintService

# 初始化服务
sam_svc = SAMService()
inpaint_svc = InpaintService()

def on_image_click(image, evt: gr.SelectData):
    """处理图片点击事件"""
    if image is None: return None, None
    
    # 1. 设置图片给 SAM
    # Gradio 图片通常是 numpy array，需确保格式
    sam_svc.set_image(image)
    
    # 2. 获取点击坐标
    x, y = evt.index[0], evt.index[1]
    print(f"点击坐标: {x}, {y}")
    
    # 3. 预测 Mask
    # input_point = np.array([[x, y]])
    # input_label = np.array([1])
    mask = sam_svc.predict_mask([[x, y]], [1])
    
    # 4. 可视化 Mask (将 Mask 叠加在原图上)
    # 简单处理：将 Mask 区域变红
    overlay = image.copy()
    overlay[mask > 0] = [255, 0, 0] # 红色覆盖
    
    # 融合显示 (0.7原图 + 0.3红色)
    blended = (image * 0.7 + overlay * 0.3).astype(np.uint8)
    
    return blended, mask

def run_inpaint(original_image, mask, prompt):
    if original_image is None or mask is None:
        return None
    
    # 转换 Mask 为 PIL
    mask_pil = Image.fromarray(mask.astype(np.uint8) * 255)
    orig_pil = Image.fromarray(original_image)
    
    # 调用重绘服务
    result_pil = inpaint_svc.inpaint(orig_pil, mask_pil, prompt)
    return np.array(result_pil)

# === 构建 Gradio 界面 ===
with gr.Blocks(theme=gr.themes.Soft(), css="footer {visibility: hidden}") as demo:
    gr.Markdown("# 🖌️ Magic Canvas (Powered by SAM)")
    
    with gr.Row():
        with gr.Column(scale=1):
            # 输入区
            input_img = gr.Image(label="上传原图 (点击物体进行分割)", type="numpy")
            prompt = gr.Textbox(label="重绘指令 (Prompt)", placeholder="例如：换成一只带墨镜的猫")
            btn_run = gr.Button("✨ Magic Inpaint", variant="primary")
            
        with gr.Column(scale=1):
            # 输出区
            output_img = gr.Image(label="处理结果")
    
    # 隐藏状态：存储当前的 Mask
    state_mask = gr.State()

    # 事件绑定
    input_img.select(on_image_click, [input_img], [input_img, state_mask])
    btn_run.click(run_inpaint, [input_img, state_mask, prompt], [output_img])

if __name__ == "__main__":
    # 启动在 7860 端口
    demo.launch(server_name="0.0.0.0", server_port=7860, show_api=False)
