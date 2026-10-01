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


NODE_CLASS_MAPPINGS = {cls.__name__: cls for cls in (AnimaAppResolution, AnimaAppLoRA, AnimaAppRegionPreset)}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaAppResolution": "縦横比・解像度",
    "AnimaAppLoRA": "LoRA選択",
    "AnimaAppRegionPreset": "領域配置",
}
WEB_DIRECTORY = "./web"
