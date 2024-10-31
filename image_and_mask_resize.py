import torch
import torch.nn.functional as F
import comfy.utils

class ImageAndMaskResizeNode:
    DESCRIPTION = "InpaintEasy- 同时调整图片和蒙版的大小"
    upscale_methods = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]
    crop_methods = ["disabled", "center", "top_left", "top_right", "bottom_left", "bottom_right"]
    

    def __init__(self):
        self.type = "ImageMaskResize"
        self.output_node = True

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "width": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 8192,
                    "step": 8
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 8192,
                    "step": 8
                }),
                "resize_method": (s.upscale_methods, {"default": "lanczos"}),
                "crop": (s.crop_methods, {"default": "disabled"}),
                "mask_blur_radius": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 64,
                    "step": 1
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK",)
    RETURN_NAMES = ("image", "mask",)
    FUNCTION = "resize_image_and_mask"
    
    CATEGORY = "InpaintEasy"

    def resize_image_and_mask(self, image, mask, width, height, resize_method="lanczos", crop="disabled", mask_blur_radius=0):
        # 处理宽高为0的情况
        if width == 0 and height == 0:
            return (image, mask)

        # 对于图像的处理
        samples = image.movedim(-1, 1)  # NHWC -> NCHW
        if width == 0:
            width = max(1, round(samples.shape[3] * height / samples.shape[2]))
        elif height == 0:
            height = max(1, round(samples.shape[2] * width / samples.shape[3]))

        # 使用 torch.nn.functional 直接进行缩放和裁剪
        if crop != "disabled":
            old_width = samples.shape[3]
            old_height = samples.shape[2]
            
            # 计算缩放比例
            scale = max(width / old_width, height / old_height)
            scaled_width = int(old_width * scale)
            scaled_height = int(old_height * scale)
            
            # 使用 common_upscale 进行缩放
            samples = comfy.utils.common_upscale(samples, scaled_width, scaled_height, resize_method, crop="disabled")
            
            # 蒙版始终使用bilinear插值
            mask = F.interpolate(mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])), size=(scaled_height, scaled_width), mode='bilinear', align_corners=True)
            
            # 计算裁剪位置
            crop_x = 0
            crop_y = 0
            
            if crop == "center":
                crop_x = (scaled_width - width) // 2
                crop_y = (scaled_height - height) // 2
            elif crop == "top_left":
                crop_x = 0
                crop_y = 0
            elif crop == "top_right":
                crop_x = scaled_width - width
                crop_y = 0
            elif crop == "bottom_left":
                crop_x = 0
                crop_y = scaled_height - height
            elif crop == "bottom_right":
                crop_x = scaled_width - width
                crop_y = scaled_height - height
            elif crop == "random":
                crop_x = torch.randint(0, max(1, scaled_width - width), (1,)).item()
                crop_y = torch.randint(0, max(1, scaled_height - height), (1,)).item()
                
            # 执行裁剪
            samples = samples[:, :, crop_y:crop_y + height, crop_x:crop_x + width]
            mask = mask[:, :, crop_y:crop_y + height, crop_x:crop_x + width]
        else:
            # 直接使用 common_upscale 调整大小
            samples = comfy.utils.common_upscale(samples, width, height, resize_method, crop="disabled")
            mask = F.interpolate(mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])), size=(height, width), mode='bilinear', align_corners=True)

        image_resized = samples.movedim(1, -1)  # NCHW -> NHWC
        mask_resized = mask.squeeze(1)  # NCHW -> NHW

        # 在返回之前添加高斯模糊处理
        if mask_blur_radius > 0:
            # 创建高斯核
            kernel_size = mask_blur_radius * 2 + 1
            x = torch.arange(kernel_size, dtype=torch.float32, device=mask_resized.device)
            x = x - (kernel_size - 1) / 2
            gaussian = torch.exp(-(x ** 2) / (2 * (mask_blur_radius / 3) ** 2))
            gaussian = gaussian / gaussian.sum()
            
            # 将kernel转换为2D
            gaussian_2d = gaussian.view(1, -1) * gaussian.view(-1, 1)
            gaussian_2d = gaussian_2d.view(1, 1, kernel_size, kernel_size)
            
            # 应用高斯模糊
            mask_for_blur = mask_resized.unsqueeze(1)  # Add channel dimension
            # 对边界进行padding，使用reflect模式避免边缘问题
            padding = kernel_size // 2
            mask_padded = F.pad(mask_for_blur, (padding, padding, padding, padding), mode='reflect')
            mask_resized = F.conv2d(mask_padded, gaussian_2d.to(mask_resized.device), padding=0).squeeze(1)
            
            # 确保值在0-1范围内
            mask_resized = torch.clamp(mask_resized, 0, 1)

        return (image_resized, mask_resized)

NODE_CLASS_MAPPINGS = {
    "ImageAndMaskResizeNode": ImageAndMaskResizeNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageAndMaskResizeNode": "Image and Mask Resize"
} 