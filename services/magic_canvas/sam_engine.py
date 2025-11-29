import numpy as np
import torch
import sys
import os

class SAMService:
    """
    [Magic Canvas 专属] Segment Anything Model 服务
    负责接收点击坐标，返回物体掩码 (Mask)。
    """
    def __init__(self, checkpoint_path="weights/sam_vit_h_4b8939.pth"):
        self.predictor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_ready = False
        
        # 尝试加载 SAM
        try:
            from segment_anything import sam_model_registry, SamPredictor
            if os.path.exists(checkpoint_path):
                print(f"正在加载 SAM 模型 ({self.device})...")
                sam = sam_model_registry["vit_h"](checkpoint=checkpoint_path)
                sam.to(device=self.device)
                self.predictor = SamPredictor(sam)
                self.model_ready = True
                print("✅ SAM 模型加载成功！")
            else:
                print(f"⚠️ 未找到权重文件: {checkpoint_path}，将运行在模拟模式。")
        except ImportError:
            print("⚠️ 未安装 segment_anything 库，将运行在模拟模式。")

    def set_image(self, image_np):
        """设置当前要处理的图片"""
        if self.model_ready and self.predictor:
            self.predictor.set_image(image_np)

    def predict_mask(self, point_coords, point_labels):
        """
        根据点击点预测掩码
        :param point_coords: [[x, y]]
        :param point_labels: [1] (1表示前景点)
        """
        if self.model_ready and self.predictor:
            masks, scores, logits = self.predictor.predict(
                point_coords=np.array(point_coords),
                point_labels=np.array(point_labels),
                multimask_output=True,
            )
            # 取置信度最高的 mask
            best_idx = np.argmax(scores)
            return masks[best_idx]
        else:
            # === 模拟模式 (返回一个中心圆) ===
            print("模拟 SAM 预测...")
            return np.zeros((512, 512), dtype=bool) # 空 Mask，避免报错
