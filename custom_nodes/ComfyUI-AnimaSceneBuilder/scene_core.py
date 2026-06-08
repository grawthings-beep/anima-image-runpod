import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path


BLOCKED_MINOR_PATTERNS = (
    
)

SCENE_TAGS_TO_DROP = {
    "masterpiece",
    "best quality",
    "good quality",
    "normal quality",
    "low quality",
    "worst quality",
    "safe",
    "sensitive",
    "nsfw",
    "explicit",
    "artist name",
}

PROFILE_HINTS = {
    "cinematic": "Prioritize cinematic staging, readable depth, and deliberate camera placement.",
    "dynamic": "Prioritize clear motion, energetic posing, and a strong diagonal composition.",
    "intimate": "Prioritize close spatial relationships, restrained framing, and expressive body language.",
    "slice of life": "Prioritize a believable everyday situation with natural posing and environmental detail.",
    "dramatic": "Prioritize visual tension, strong lighting contrast, and a decisive focal point.",
}

COMPOSITION_AXES = (
    "close framing with strong foreground depth",
    "full-body environmental composition",
    "low camera position",
    "high camera position",
    "over-the-shoulder framing",
    "asymmetrical diagonal composition",
    "side-view composition",
    "deep perspective with layered foreground and background",
)

MOTION_AXES = (
    "a quiet held pose",
    "a clearly readable physical action",
    "an interaction driven by body language",
    "a moment immediately before an action",
    "a moment immediately after an action",
    "a balanced pose with visible weight distribution",
)

SETTING_AXES = (
    "a private interior",
    "a richly detailed domestic space",
    "an urban night setting",
    "a natural outdoor setting",
    "a theatrical or staged environment",
    "an unusual but coherent fantasy location",
)


def validate_adult_only(*values):
    text = " ".join(str(value or "") for value in values).lower()
    for pattern in BLOCKED_MINOR_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise ValueError(
                "Anima Scene Builder only supports fictional adult characters. "
                f"Blocked age-related term matched: {pattern}"
            )


def strip_model_wrappers(content):
    text = str(content or "").strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _normalize_tag(tag):
    tag = re.sub(r"\s+", " ", str(tag or "").strip().lower())
    if not tag:
        return ""

    score_tokens = {}

    def protect_score(match):
        key = f"zzscoretoken{len(score_tokens)}zz"
        score_tokens[key] = match.group(0)
        return key

    tag = re.sub(r"\bscore_\d+\b", protect_score, tag)
    tag = tag.replace("_", " ")
    for key, value in score_tokens.items():
        tag = tag.replace(key, value)
    return tag.strip(" ,.;")


def normalize_scene_tags(tags):
    if isinstance(tags, list):
        candidates = tags
    else:
        candidates = re.split(r"[,;\n]+", str(tags or ""))

    normalized = []
    seen = set()
    for candidate in candidates:
        tag = _normalize_tag(candidate)
        if not tag or tag in SCENE_TAGS_TO_DROP or tag.startswith("score_"):
            continue
        if tag.startswith("@"):
            continue
        if tag not in seen:
            seen.add(tag)
            normalized.append(tag)
    return ", ".join(normalized)


def parse_scene_response(content):
    cleaned = strip_model_wrappers(content)
    try:
        payload = _extract_json(cleaned)
    except (json.JSONDecodeError, TypeError, ValueError):
        payload = {"tags": "", "description": cleaned}

    if not isinstance(payload, dict):
        payload = {"tags": "", "description": cleaned}

    tags = normalize_scene_tags(payload.get("tags", ""))
    description = re.sub(r"\s+", " ", str(payload.get("description", "")).strip())
    validate_adult_only(tags, description)
    return {"tags": tags, "description": description}


def build_full_prompt(quality_tags, character_tags, scene, output_mode):
    tag_sections = [
        str(quality_tags or "").strip(" ,"),
        str(character_tags or "").strip(" ,"),
    ]
    if output_mode != "natural language only":
        tag_sections.append(str(scene.get("tags", "")).strip(" ,"))

    tag_prompt = ", ".join(section for section in tag_sections if section)
    description = (
        str(scene.get("description", "")).strip()
        if output_mode != "tags only"
        else ""
    )

    if tag_prompt and description:
        return f"{tag_prompt}. {description}"
    return tag_prompt or description


def make_variation_hint(seed):
    rng = random.Random(int(seed))
    return (
        f"Composition axis: {rng.choice(COMPOSITION_AXES)}. "
        f"Motion axis: {rng.choice(MOTION_AXES)}. "
        f"Setting axis: {rng.choice(SETTING_AXES)}."
    )


def profile_instruction(profile):
    if profile == "random":
        return ""
    return PROFILE_HINTS.get(profile, "")


def append_jsonl_log(log_directory, record):
    directory = Path(log_directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "anima_scene_generations.jsonl"

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return str(log_path)
