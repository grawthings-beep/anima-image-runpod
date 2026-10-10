"""Small controls for the native ComfyUI App Builder."""

import json


RATIOS = {
    "1:1 正方形": (1, 1),
    "3:4 縦": (3, 4),
    "4:3 横": (4, 3),
    "2:3 縦": (2, 3),
    "3:2 横": (3, 2),
    "9:16 縦": (9, 16),
    "16:9 横": (16, 9),
}


def resolution(aspect_ratio, long_edge):
    if aspect_ratio not in RATIOS:
        raise ValueError("縦横比を選び直してください。")
    if isinstance(long_edge, bool) or not isinstance(long_edge, int) or not 512 <= long_edge <= 2048 or long_edge % 8:
        raise ValueError("長辺は512〜2048pxの8の倍数にしてください。")
    x, y = RATIOS[aspect_ratio]
    scale = long_edge / max(x, y)
    return tuple(max(64, int(value * scale / 8 + 0.5) * 8) for value in (x, y))


class AnimaAppResolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "aspect_ratio": (list(RATIOS), {"default": "3:4 縦"}),
            "long_edge": ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 8}),
        }}

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "calculate"
    CATEGORY = "Anima/App"

    def calculate(self, aspect_ratio, long_edge):
        return resolution(aspect_ratio, long_edge)


class AnimaAppLoRA:
    """Only installed files are offered; '(none)' works without any LoRA files."""
    def __init__(self):
        self._loader = None

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        return {"required": {
            "model": ("MODEL",),
            "lora_name": (["(none)"] + folder_paths.get_filename_list("loras"),),
            "strength": ("FLOAT", {"default": 0.8, "min": 0, "max": 2, "step": 0.05}),
        }}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load"
    CATEGORY = "Anima/App"

    def load(self, model, lora_name, strength):
        if lora_name == "(none)" or strength == 0:
            return (model,)
        import folder_paths
        if not folder_paths.get_full_path("loras", lora_name):
            raise ValueError(f"LoRAが見つかりません。選び直してください: {lora_name}")
        from nodes import LoraLoaderModelOnly
        if self._loader is None:
            self._loader = LoraLoaderModelOnly()
        return self._loader.load_lora_model_only(model, lora_name, strength)


REGION_PRESETS = ("A・B 左右", "A・B 上下", "A・B・C 3列", "A・B・C・D 4列", "A・B・C・D 2×2")


class AnimaAppRegionPreset:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "preset": (list(REGION_PRESETS),),
            "overlap_percent": ("FLOAT", {"default": 4, "min": 0, "max": 20, "step": 1}),
            "feather_percent": ("FLOAT", {"default": 4, "min": 0, "max": 20, "step": 1}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("layout",)
    FUNCTION = "create"
    CATEGORY = "Anima/App"

    def create(self, preset, overlap_percent, feather_percent):
        if preset not in REGION_PRESETS:
            raise ValueError("領域配置を選び直してください。")
        if not all(0 <= value <= 20 for value in (overlap_percent, feather_percent)):
            raise ValueError("重なりとぼかしは0〜20%にしてください。")
        if preset == REGION_PRESETS[1]:
            columns, rows = 1, 2
        elif preset == REGION_PRESETS[4]:
            columns, rows = 2, 2
        else:
            columns, rows = {REGION_PRESETS[0]: 2, REGION_PRESETS[2]: 3, REGION_PRESETS[3]: 4}[preset], 1
        regions = [
            {"id": f"r{i + 1}", "owner": "ABCD"[i], "x": (i % columns) / columns,
             "y": (i // columns) / rows, "w": 1 / columns, "h": 1 / rows, "enabled": True}
            for i in range(columns * rows)
        ]
        return (json.dumps({"version": 1, "overlap": overlap_percent / 100,
                            "feather": feather_percent / 100, "regions": regions}),)


REGIONAL_PALETTE = ((255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 255, 255))


def regional_map_arrays(masks, image=None, feather_percent=2):
    """One ownership map drives both the solid control image and soft conditioning."""
    import numpy as np
    from PIL import Image, ImageFilter

    masks = np.asarray(masks, dtype=np.float32)
    if masks.ndim != 3 or masks.shape[0] != 4 or min(masks.shape[1:]) < 1:
        raise ValueError("Expected four equally sized region masks")
    if not np.isfinite(masks).all() or not 0 <= feather_percent <= 10:
        raise ValueError("Invalid masks or feather amount (0-10%)")
    height, width = masks.shape[1:]
    palette = np.asarray(REGIONAL_PALETTE, dtype=np.uint8)
    if image is None:
        owners = masks.argmax(axis=0)
        owners[masks.max(axis=0) <= 0] = 4
    else:
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        rgb = Image.alpha_composite(white, rgba).convert("RGB")
        pixels = np.asarray(rgb.resize((width, height), Image.Resampling.NEAREST), dtype=np.float32) / 255
        best = np.full((height, width), np.inf, dtype=np.float32)
        owners = np.full((height, width), 4, dtype=np.int64)
        for index, color in enumerate(palette.astype(np.float32) / 255):
            distance = ((pixels - color) ** 2).sum(axis=-1)
            closer = distance < best
            owners[closer] = index
            best[closer] = distance[closer]
        if np.mean(best > 0.5) > 0.01:
            raise ValueError("Use red (A), blue (B), green (C), yellow (D), and white background in the color map")
    if not np.any(owners < 4):
        raise ValueError("The color map has no character regions")
    color_map = palette[owners].astype(np.float32) / 255
    soft = np.stack([owners == index for index in range(4)]).astype(np.float32)
    radius = feather_percent * min(width, height) / 100
    if radius > 0:
        for index in range(4):
            mask_image = Image.fromarray((soft[index] * 255).astype(np.uint8))
            soft[index] = np.asarray(mask_image.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255
        soft /= np.maximum(soft.sum(axis=0), 1)[None]
    return color_map, soft


class AnimaAppRegionalMap:
    @classmethod
    def INPUT_TYPES(cls):
        from nodes import LoadImage
        image_options = LoadImage.INPUT_TYPES()["required"]["image"][0]
        return {"required": {
            **{f"mask_{letter}": ("MASK",) for letter in "ABCD"},
            "image": (["(layout)"] + image_options, {"image_upload": True}),
            "feather_percent": ("FLOAT", {"default": 2, "min": 0, "max": 10, "step": 0.5}),
        }}

    RETURN_TYPES = ("IMAGE", "MASK", "MASK", "MASK", "MASK")
    RETURN_NAMES = ("color_map", "mask_A", "mask_B", "mask_C", "mask_D")
    FUNCTION = "create"
    CATEGORY = "Anima/App"

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if image == "(layout)":
            return True
        from nodes import LoadImage
        return LoadImage.VALIDATE_INPUTS(image)

    @classmethod
    def IS_CHANGED(cls, image):
        if image == "(layout)":
            return "layout"
        from nodes import LoadImage
        return LoadImage.IS_CHANGED(image)

    def create(self, mask_A, mask_B, mask_C, mask_D, image, feather_percent):
        import numpy as np
        import torch
        from PIL import Image, ImageOps

        masks = []
        for mask in (mask_A, mask_B, mask_C, mask_D):
            if mask.ndim != 3 or mask.shape[0] != 1:
                raise ValueError("Regional color maps require a single-image layout")
            masks.append(mask[0].detach().cpu().numpy())
        source_image = None
        if image != "(layout)":
            import folder_paths
            with Image.open(folder_paths.get_annotated_filepath(image)) as loaded:
                source_image = ImageOps.exif_transpose(loaded).convert("RGBA")
        color_map, soft = regional_map_arrays(np.stack(masks), source_image, feather_percent)
        return (torch.from_numpy(color_map[None]), *[torch.from_numpy(mask[None]) for mask in soft])


NODE_CLASS_MAPPINGS = {cls.__name__: cls for cls in (AnimaAppResolution, AnimaAppLoRA, AnimaAppRegionPreset, AnimaAppRegionalMap)}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaAppResolution": "縦横比・解像度",
    "AnimaAppLoRA": "LoRA選択",
    "AnimaAppRegionPreset": "領域配置",
    "AnimaAppRegionalMap": "LLLite色マップ・領域マスク",
}
WEB_DIRECTORY = "./web"
