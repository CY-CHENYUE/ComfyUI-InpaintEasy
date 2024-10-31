import torch
import numpy as np
from PIL import Image

class CropByMask:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "padding": ("INT", {
                    "default": 64,
                    "min": 0,
                    "max": 512,
                    "step": 8,
                    "display_step": 8,
                    "display": "slider"
                })
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "crop_x", "crop_y", "original_width", "original_height")
    FUNCTION = "process"
    CATEGORY = "InpaintEasy"

    def process(self, image, mask, padding):
        """
        image: torch.Tensor [B, H, W, C] 范围在 0-1
        mask: torch.Tensor [B, H, W] 范围在 0-1
        返回
        - 放大后的裁剪图像
        - 裁剪区域在原图中的左上角x坐标
        - 裁剪区域在原图中的左上角y坐��
        - 原始裁剪宽度
        - 原始裁剪高度
        """
        # 获取mask中非零区域的边界框坐标
        mask_np = mask.squeeze(0).cpu().numpy()
        nonzero_indices = np.nonzero(mask_np)
        if len(nonzero_indices[0]) == 0:
            raise ValueError("Mask is empty")
        
        # 获取边界框坐标
        min_y, max_y = np.min(nonzero_indices[0]), np.max(nonzero_indices[0])
        min_x, max_x = np.min(nonzero_indices[1]), np.max(nonzero_indices[1])
        
        # 计算mask区域的最大边长
        mask_size = max(max_x - min_x + 1, max_y - min_y + 1)
        
        # 获取原图尺寸
        original_height, original_width = mask_np.shape
        
        # 添加padding并确保是8的倍数
        target_size = mask_size + (2 * padding)
        target_size = ((target_size + 7) // 8) * 8
        
        # 分别处理宽度和高度
        crop_width = min(target_size, original_width)
        crop_height = min(target_size, original_height)
        
        # 计算中心点
        center_x = (min_x + max_x) // 2
        center_y = (min_y + max_y) // 2
        
        # 计算裁剪区域的起始位置
        crop_x = center_x - (crop_width // 2)
        crop_y = center_y - (crop_height // 2)
        
        # 确保裁剪区域在图像范围内
        crop_x = max(0, min(crop_x, original_width - crop_width))
        crop_y = max(0, min(crop_y, original_height - crop_height))
        
        # 裁剪图像和mask
        cropped_image = image[:, crop_y:crop_y+crop_height, crop_x:crop_x+crop_width, :]
        cropped_mask = mask[:, crop_y:crop_y+crop_height, crop_x:crop_x+crop_width]
        
        return (cropped_image, cropped_mask, int(crop_x), int(crop_y), 
                int(crop_width), int(crop_height))

NODE_CLASS_MAPPINGS = {
    "CropByMask": CropByMask
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CropByMask": "Crop By Mask"
}