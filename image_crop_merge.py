from comfy.utils import common_upscale

class ImageCropMerge:
    DESCRIPTION = "InpaintEasy- 图片与裁剪覆合,将裁剪的图片合并回原图中"
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "cropped_image": ("IMAGE",),  # 裁剪并处理后的图片
                "original_image": ("IMAGE",),  # 需要被合并的原始完整图片
                "crop_x": ("INT", {"default": 0, "min": 0, "max": 4096, "forceInput": True}),
                "crop_y": ("INT", {"default": 0, "min": 0, "max": 4096, "forceInput": True}),
                "cropped_original_width": ("INT", {"default": 512, "min": 1, "max": 4096, "forceInput": True}),
                "cropped_original_height": ("INT", {"default": 512, "min": 1, "max": 4096, "forceInput": True}),
                "resize_method": (["nearest-exact", "bilinear", "area", "bicubic", "lanczos"], {"default": "lanczos"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "merge_images"
    CATEGORY = "InpaintEasy"

    def merge_images(self, cropped_image, original_image, cropped_original_width, cropped_original_height, crop_x, crop_y, resize_method):
        # 首先调整裁剪图片的大小
        samples = cropped_image.movedim(-1, 1)
        resized_image = common_upscale(samples, cropped_original_width, cropped_original_height, resize_method, "disabled")
        resized_image = resized_image.movedim(1, -1)
        
        # 将调整后的图片合并到原始图片的指定位置
        result = original_image.clone()
        result[:, crop_y:crop_y+cropped_original_height, crop_x:crop_x+cropped_original_width] = resized_image
        
        return (result,)
    

NODE_CLASS_MAPPINGS = {
    "ImageCropMerge": ImageCropMerge
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageCropMerge": "Image Crop Merge"
}