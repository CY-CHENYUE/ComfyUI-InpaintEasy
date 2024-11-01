import torch
import node_helpers

class InpaintEasyModel:
    DESCRIPTION = "InpaintEasy- 用来处理控制模块"
    def __init__(self):
        self.type = "InpaintEasyModel"
        self.output_node = True
        self.description = "InpaintEasyModel-用来处理控制模块"
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "inpaint_image": ("IMAGE",),
                "control_net": ("CONTROL_NET",),
                "control_image": ("IMAGE",),
                "mask": ("MASK",),
                "vae": ("VAE",),
                "strength": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.01
                }),
                "start_percent": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001
                }),
                "end_percent": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001
                }),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT",)
    RETURN_NAMES = ("positive", "negative", "latent",)
    FUNCTION = "combine_conditioning"
    
    CATEGORY = "InpaintEasy"

    def combine_conditioning(self, positive, negative, control_net, inpaint_image, control_image, mask, vae, 
                           strength=1.0, start_percent=0.0, end_percent=1.0):
        x = (inpaint_image.shape[1] // 8) * 8
        y = (inpaint_image.shape[2] // 8) * 8
        mask = torch.nn.functional.interpolate(mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])), 
                                             size=(inpaint_image.shape[1], inpaint_image.shape[2]), mode="bilinear")

        orig_pixels = inpaint_image
        pixels = orig_pixels.clone()
        if pixels.shape[1] != x or pixels.shape[2] != y:
            x_offset = (pixels.shape[1] % 8) // 2
            y_offset = (pixels.shape[2] % 8) // 2
            pixels = pixels[:,x_offset:x + x_offset, y_offset:y + y_offset,:]
            mask = mask[:,:,x_offset:x + x_offset, y_offset:y + y_offset]

        m = (1.0 - mask.round()).squeeze(1)
        for i in range(3):
            pixels[:,:,:,i] -= 0.5
            pixels[:,:,:,i] *= m
            pixels[:,:,:,i] += 0.5
            
        concat_latent = vae.encode(pixels)
        orig_latent = vae.encode(orig_pixels)

        out_latent = {
            "samples": orig_latent,
            "noise_mask": mask
        }

        inpaint_conditioning = []
        for conditioning in [positive, negative]:
            c = node_helpers.conditioning_set_values(conditioning, {
                "concat_latent_image": concat_latent,
                "concat_mask": mask
            })
            inpaint_conditioning.append(c)
     
        if strength == 0:
            return (inpaint_conditioning[0], inpaint_conditioning[1], out_latent)

        control_hint = control_image.movedim(-1,1)
        cnets = {}

        out = []
        for conditioning in inpaint_conditioning:
            c = []
            for t in conditioning:
                d = t[1].copy()

                prev_cnet = d.get('control', None)
                if prev_cnet in cnets:
                    c_net = cnets[prev_cnet]
                else:
                    c_net = control_net.copy().set_cond_hint(control_hint, strength, 
                                                           (start_percent, end_percent), 
                                                           vae=vae)
                    c_net.set_previous_controlnet(prev_cnet)
                    cnets[prev_cnet] = c_net

                d['control'] = c_net
                d['control_apply_to_uncond'] = False
                n = [t[0], d]
                c.append(n)
            out.append(c)

        return (out[0], out[1], out_latent)

NODE_CLASS_MAPPINGS = {
    "InpaintEasyModel": InpaintEasyModel
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "InpaintEasyModel": "Inpaint Model"
} 