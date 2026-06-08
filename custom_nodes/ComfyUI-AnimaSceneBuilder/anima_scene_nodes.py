import gc
import os
import threading
from pathlib import Path

import folder_paths

from .scene_core import (
    append_jsonl_log,
    build_full_prompt,
    make_variation_hint,
    parse_scene_response,
    profile_instruction,
    validate_adult_only,
)


_MODEL_LOCK = threading.Lock()
_MODEL_CACHE = {"key": None, "llm": None}

SYSTEM_PROMPT = """You create scene-only prompt additions for the Anima text-to-image model.

The user's quality tags and character tags are fixed elsewhere. Never repeat, rewrite, or contradict character identity, physical appearance, hairstyle, eye color, clothing, franchise, artist, quality, score, safety, or LoRA tags.
Match the maturity level implied by the fixed quality/safety tags, but do not repeat those tags. Do not invent sexual content unless those fixed tags or the scene direction request it.

Generate only:
- composition and framing
- camera angle and camera distance
- body pose, action, and spatial relationships
- location and situational context
- visible facial state
- lighting and environmental details

All people must be fictional adults aged 18 or older. Never introduce minors, youthful age labels, real people, celebrities, or extra characters not implied by the fixed tags.

Return exactly one JSON object with this shape:
{"tags":"lowercase, comma-separated Anima/Danbooru-style scene tags","description":"Two to four concise natural-English sentences describing the scene geometry and action."}

Use spaces instead of underscores in tags. Do not output markdown, commentary, or additional keys."""


def _model_directory():
    configured = os.environ.get("ANIMA_LLM_MODEL_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path(folder_paths.models_dir) / "llm_gguf"


def _list_gguf_models():
    model_dir = _model_directory()
    if not model_dir.exists():
        return ["NO_GGUF_MODEL_FOUND"]
    models = sorted(
        path.relative_to(model_dir).as_posix()
        for path in model_dir.rglob("*.gguf")
        if path.is_file()
    )
    return models or ["NO_GGUF_MODEL_FOUND"]


def _resolve_model_path(model_name):
    if model_name == "NO_GGUF_MODEL_FOUND":
        raise FileNotFoundError(
            f"No GGUF model found. Put one in {_model_directory()} and restart ComfyUI."
        )
    model_path = (_model_directory() / model_name).resolve()
    model_root = _model_directory().resolve()
    if model_root not in model_path.parents:
        raise ValueError("Invalid GGUF model path.")
    if not model_path.is_file():
        raise FileNotFoundError(f"GGUF model not found: {model_path}")
    return model_path


def _load_llm(model_path, context_size, cpu_threads, gpu_layers):
    cache_key = (
        str(model_path),
        int(context_size),
        int(cpu_threads),
        int(gpu_layers),
    )
    if _MODEL_CACHE["key"] == cache_key and _MODEL_CACHE["llm"] is not None:
        return _MODEL_CACHE["llm"]

    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError(
            "llama-cpp-python is not installed in ComfyUI's Python environment. "
            "Run the included install_runpod.sh script."
        ) from exc

    _MODEL_CACHE["llm"] = None
    _MODEL_CACHE["key"] = None
    gc.collect()

    llm = Llama(
        model_path=str(model_path),
        n_ctx=int(context_size),
        n_threads=int(cpu_threads),
        n_gpu_layers=int(gpu_layers),
        n_batch=256,
        verbose=False,
    )
    _MODEL_CACHE["key"] = cache_key
    _MODEL_CACHE["llm"] = llm
    return llm


def _completion_content(result):
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected llama.cpp response: {result!r}") from exc
    return str(content or "")


def _generate_scene(
    llm,
    quality_tags,
    character_tags,
    scene_direction,
    extra_constraints,
    scene_profile,
    seed,
    temperature,
    top_p,
    max_tokens,
):
    direction = scene_direction.strip() or (
        "Invent one coherent and visually readable scene for the fixed adult character(s)."
    )
    character_context = character_tags.strip() or (
        "No cast tags were supplied. Use one fictional adult character."
    )
    user_prompt = f"""/no_think
Fixed quality/safety tags for maturity context only:
{quality_tags.strip() or "No maturity tag supplied."}

Fixed character tags for cast-count context only:
{character_context}

Scene direction:
{direction}

Additional constraints:
{extra_constraints.strip() or "None."}

Profile:
{profile_instruction(scene_profile) or "Choose freely."}

Variation cue:
{make_variation_hint(seed)}

Variation seed: {int(seed)}
Output the JSON object only."""

    kwargs = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(temperature),
        "top_p": float(top_p),
        "max_tokens": int(max_tokens),
        "seed": int(seed) % 2147483647,
    }

    try:
        result = llm.create_chat_completion(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except (TypeError, ValueError):
        result = llm.create_chat_completion(**kwargs)
    return _completion_content(result)


class AnimaLocalSceneEncode:
    @classmethod
    def INPUT_TYPES(cls):
        default_threads = max(1, min(32, (os.cpu_count() or 8) - 2))
        default_log_dir = os.environ.get(
            "ANIMA_SCENE_LOG_DIR",
            str(Path(folder_paths.get_output_directory()) / "anima_auto_scene" / "logs"),
        )
        return {
            "required": {
                "clip": ("CLIP",),
                "gguf_model": (_list_gguf_models(),),
                "quality_tags": (
                    "STRING",
                    {
                        "default": "masterpiece, best quality, score_7, explicit",
                        "multiline": True,
                    },
                ),
                "character_tags": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
                "scene_direction": (
                    "STRING",
                    {
                        "default": (
                            "Invent one coherent scene for the fixed adult character(s). "
                            "Vary composition, camera, action, location, facial state, "
                            "and lighting on every seed. Do not add extra characters."
                        ),
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
                "extra_constraints": (
                    "STRING",
                    {
                        "default": (
                            "Preserve the fixed cast count. Do not repeat appearance, "
                            "clothing, quality, artist, or style tags."
                        ),
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
                "scene_profile": (
                    ["random", "cinematic", "dynamic", "intimate", "slice of life", "dramatic"],
                ),
                "output_mode": (
                    ["tags + natural language", "tags only", "natural language only"],
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
                "temperature": (
                    "FLOAT",
                    {"default": 0.95, "min": 0.0, "max": 2.0, "step": 0.05},
                ),
                "top_p": (
                    "FLOAT",
                    {"default": 0.95, "min": 0.05, "max": 1.0, "step": 0.05},
                ),
                "max_tokens": (
                    "INT",
                    {"default": 320, "min": 64, "max": 1024, "step": 16},
                ),
                "context_size": (
                    "INT",
                    {"default": 4096, "min": 2048, "max": 32768, "step": 512},
                ),
                "cpu_threads": (
                    "INT",
                    {"default": default_threads, "min": 1, "max": 128, "step": 1},
                ),
                "gpu_layers": (
                    "INT",
                    {"default": 0, "min": -1, "max": 999, "step": 1},
                ),
                "log_directory": (
                    "STRING",
                    {"default": default_log_dir, "multiline": False},
                ),
                "save_logs": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("conditioning", "full_prompt", "scene_text", "log_file")
    FUNCTION = "generate_and_encode"
    CATEGORY = "Anima/Prompt"

    def generate_and_encode(
        self,
        clip,
        gguf_model,
        quality_tags,
        character_tags,
        scene_direction,
        extra_constraints,
        scene_profile,
        output_mode,
        seed,
        temperature,
        top_p,
        max_tokens,
        context_size,
        cpu_threads,
        gpu_layers,
        log_directory,
        save_logs,
    ):
        validate_adult_only(
            quality_tags,
            character_tags,
            scene_direction,
            extra_constraints,
        )
        model_path = _resolve_model_path(gguf_model)

        with _MODEL_LOCK:
            llm = _load_llm(
                model_path,
                context_size=context_size,
                cpu_threads=cpu_threads,
                gpu_layers=gpu_layers,
            )
            raw_output = _generate_scene(
                llm=llm,
                quality_tags=quality_tags,
                character_tags=character_tags,
                scene_direction=scene_direction,
                extra_constraints=extra_constraints,
                scene_profile=scene_profile,
                seed=seed,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )

        scene = parse_scene_response(raw_output)
        full_prompt = build_full_prompt(
            quality_tags=quality_tags,
            character_tags=character_tags,
            scene=scene,
            output_mode=output_mode,
        )
        validate_adult_only(full_prompt)

        tokens = clip.tokenize(full_prompt)
        conditioning = clip.encode_from_tokens_scheduled(tokens)

        scene_text = scene["tags"]
        if scene["tags"] and scene["description"]:
            scene_text = f"{scene['tags']}. {scene['description']}"
        elif scene["description"]:
            scene_text = scene["description"]

        log_file = ""
        if save_logs:
            resolved_log_directory = log_directory.strip() or os.environ.get(
                "ANIMA_SCENE_LOG_DIR",
                str(
                    Path(folder_paths.get_output_directory())
                    / "anima_auto_scene"
                    / "logs"
                ),
            )
            log_file = append_jsonl_log(
                resolved_log_directory,
                {
                    "seed": int(seed),
                    "gguf_model": gguf_model,
                    "scene_profile": scene_profile,
                    "output_mode": output_mode,
                    "scene_direction": scene_direction,
                    "extra_constraints": extra_constraints,
                    "raw_model_output": raw_output,
                    "parsed_scene": scene,
                    "full_prompt": full_prompt,
                },
            )

        return (conditioning, full_prompt, scene_text, log_file)
