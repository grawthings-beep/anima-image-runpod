from .anima_scene_nodes import AnimaLocalSceneEncode

NODE_CLASS_MAPPINGS = {
    "AnimaLocalSceneEncode": AnimaLocalSceneEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaLocalSceneEncode": "Anima Local Scene Generator + Encode",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
