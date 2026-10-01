#!/usr/bin/env python3
"""Generate ordinary editor JSON with native App Builder bindings."""

import copy
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workflows" / "source"
DEST = ROOT / "workflows" / "apps"
NAMESPACE = uuid.UUID("7851bc10-64be-4b61-a140-551dad6129de")
LORA_DEFAULTS = (
    ("anima-turbo-lora-v0.2.safetensors", 0.6),
    ("(none)", 0.9),
    ("anima/Skin Texture Detail.safetensors", 0.45),
)


class Graph:
    def __init__(self, source=None):
        self.w = copy.deepcopy(source) if source else {"nodes": [], "links": [], "groups": [], "config": {}, "extra": {}, "version": 0.4}
        self.w["extra"] = {}
        self.inputs = []
        self.w["nodes"] = [n for n in self.w["nodes"] if n["type"] not in ("MarkdownNote", "Note")]

    def node(self, node_id):
        return next(n for n in self.w["nodes"] if n["id"] == node_id)

    def add(self, kind, title, values, inputs=(), outputs=()):
        node_id = max((n["id"] for n in self.w["nodes"]), default=0) + 1
        n = {"id": node_id, "type": kind, "title": title, "pos": [0, 0], "size": [340, 200], "flags": {}, "order": 0, "mode": 0,
             "inputs": [{"name": name, "type": type_, "link": None} for name, type_ in inputs],
             "outputs": [{"name": name, "type": type_, "links": [], "slot_index": i} for i, (name, type_) in enumerate(outputs)],
             "properties": {"Node name for S&R": kind}, "widgets_values": values}
        self.w["nodes"].append(n)
        return node_id

    def connect(self, source, slot, target, name, type_=None, widget=False):
        n = self.node(target)
        index = next((i for i, item in enumerate(n.get("inputs", [])) if item["name"] == name), None)
        if index is None:
            index = len(n.setdefault("inputs", []))
            n["inputs"].append({"name": name, "type": type_, "link": None, **({"widget": {"name": name}} if widget else {})})
        old = n["inputs"][index].get("link")
        self.w["links"] = [link for link in self.w["links"] if link[0] != old]
        link_id = max((link[0] for link in self.w["links"]), default=0) + 1
        output_type = self.node(source)["outputs"][slot]["type"]
        self.w["links"].append([link_id, source, slot, target, index, type_ or output_type])
        n["inputs"][index]["link"] = link_id

    def remove(self, ids):
        ids = set(ids)
        self.w["nodes"] = [n for n in self.w["nodes"] if n["id"] not in ids]
        self.w["links"] = [link for link in self.w["links"] if link[1] not in ids and link[3] not in ids]
        self.rebuild()

    def keep_ancestors(self, outputs):
        keep = set(outputs)
        while True:
            more = {link[1] for link in self.w["links"] if link[3] in keep}
            if more <= keep:
                break
            keep |= more
        self.remove({n["id"] for n in self.w["nodes"]} - keep)
        for n in self.w["nodes"]:
            n["mode"] = 0

    def expose(self, node_id, name, label, description="", height=None):
        config = {"description": description} if description else {}
        if height:
            config["height"] = height
        self.inputs.append((node_id, name, label, config))
        # Frontend 1.54 persists display labels on the widget's input slot;
        # the second linearData tuple item alone does not render a label.
        n = self.node(node_id)
        slot = next((item for item in n.get("inputs", []) if item["name"] == name), None)
        if slot is None:
            integer = {"long_edge", "seed", "steps", "scene_limit", "start_in_range", "base_seed"}
            decimal = {"strength", "cfg", "denoise", "scale_by", "overlap_percent", "feather_percent"}
            text = {"text", "value", "scene_prompts", "positive", "negative"}
            boolean = {"auto_download"}
            type_ = "INT" if name in integer else "FLOAT" if name in decimal else "STRING" if name in text else "BOOLEAN" if name in boolean else "COMBO"
            slot = {"name": name, "type": type_, "widget": {"name": name}, "link": None}
            n.setdefault("inputs", []).append(slot)
        slot["label"] = label

    def rebuild(self):
        node_ids = {n["id"] for n in self.w["nodes"]}
        self.w["links"] = [link for link in self.w["links"] if link[1] in node_ids and link[3] in node_ids]
        for n in self.w["nodes"]:
            for i, output in enumerate(n.get("outputs", [])):
                output["links"] = [link[0] for link in self.w["links"] if link[1:3] == [n["id"], i]] or None
            for i, input_ in enumerate(n.get("inputs", [])):
                input_["link"] = next((link[0] for link in self.w["links"] if link[3:5] == [n["id"], i]), None)

    def finish(self, filename, outputs):
        filename = filename.removesuffix(".json") + ".app.json"
        self.rebuild()
        graph_id = str(uuid.uuid5(NAMESPACE, filename))
        self.w["id"] = graph_id
        self.w["revision"] = 0
        self.w["last_node_id"] = max(n["id"] for n in self.w["nodes"])
        self.w["last_link_id"] = max((link[0] for link in self.w["links"]), default=0)
        self.w["extra"] = {"linearMode": True, "linearData": {
            "inputs": [[f"{graph_id}:{node_id}:{name}", label, config] for node_id, name, label, config in self.inputs],
            "outputs": [str(x) for x in outputs]}, "frontendVersion": "1.54.8"}
        # Arrange the editable graph as well as its app interface.
        for i, n in enumerate(self.w["nodes"]):
            n["pos"] = [(i % 5) * 380, (i // 5) * 340]
            n["order"] = i
        (DEST / filename).write_text(json.dumps(self.w, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(name):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def resolution(g, target, width="width", height="height", long_edge=1536):
    node = g.add("AnimaAppResolution", "縦横比・解像度", ["3:4 縦", long_edge], outputs=(("width", "INT"), ("height", "INT")))
    g.connect(node, 0, target, width, "INT", True)
    g.connect(node, 1, target, height, "INT", True)
    g.expose(node, "aspect_ratio", "縦横比")
    g.expose(node, "long_edge", "長辺（px）", "高解像度化する場合は、ここで指定した生成サイズから拡大します。")
    return node


def models(g):
    for n in g.w["nodes"]:
        if n["type"] == "UNETLoader":
            n["widgets_values"][0] = "waiANIMA_v10Base10.safetensors"
            g.expose(n["id"], "unet_name", "モデル")


def loras(g, model, targets, existing=None, character=False, shared_targets=()):
    slots = []
    for i, defaults in enumerate(LORA_DEFAULTS):
        title = f"LoRA {i + 1}" + ("（今回の人物）" if character and i == 1 else "")
        node = (existing or {}).get(i)
        if node is None:
            node = g.add("AnimaAppLoRA", title, list(defaults), (("model", "MODEL"),), (("MODEL", "MODEL"),))
        else:
            n = g.node(node)
            n["type"] = "AnimaAppLoRA"
            n["title"] = title
            n["widgets_values"] = list(defaults)
        slots.append(node)
        description = "使わない欄は(none)。選んだLoRAのトリガーはプロンプトに入力してください。"
        if character and i == 1:
            description = "今回マスクで描き直す人物に適用します。使わない場合は(none)。"
        g.expose(node, "lora_name", title, description)
        g.expose(node, "strength", f"LoRA {i + 1} 強度")
    # Apply global Turbo/Skin before the character LoRA, so the final inpaint
    # hires pass can share both styles without applying B's LoRA to person A.
    order = (0, 2, 1) if character else (0, 1, 2)
    for i in order:
        g.connect(model, 0, slots[i], "model")
        model = slots[i]
    for target in targets:
        g.connect(model, 0, target, "model")
    for target in shared_targets:
        g.connect(slots[2], 0, target, "model")


def sampler(g, node_id, label, default=None, seed=True, steps=18, cfg=1):
    n = g.node(node_id)
    n["widgets_values"][2:4] = [steps, cfg]
    if default:
        n["widgets_values"][4:6] = list(default)
    if seed and not any(i["name"] == "seed" and i.get("link") for i in n.get("inputs", [])):
        g.expose(node_id, "seed", f"{label} シード")
    for field, title in (("sampler_name", "サンプラー"), ("scheduler", "スケジューラー"), ("steps", "ステップ"), ("cfg", "CFG"), ("denoise", "ノイズ除去強度")):
        g.expose(node_id, field, f"{label} {title}")


def prompts(g, positive, negative):
    g.expose(positive, "text", "プロンプト", height=180)
    g.expose(negative, "text", "ネガティブプロンプト", "CFGが1の場合、通常ネガティブは効きません。", 100)


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    # Every app starts with the same editable Turbo / character / Skin slots.
    g = Graph(load("anima_basic.json"))
    g.keep_ancestors([9])
    g.node(9)["type"] = "SaveImage"
    g.node(9)["title"] = "生成画像"
    g.node(9)["widgets_values"] = ["Anima_App/basic"]
    g.node(7)["widgets_values"][1] = "randomize"
    prompts(g, 4, 5)
    models(g)
    resolution(g, 6)
    loras(g, 1, [7])
    sampler(g, 7, "生成", ("res_multistep", "sgm_uniform"))
    g.finish("01_通常生成.json", [9])

    g = Graph(load("anima_hiresfix_latent_2pass.json"))
    g.remove([16, 17, 18])  # Retired pose LoRA is no longer downloaded by the RunPod manifest.
    g.expose(15, "scene_prompts", "プロンプト（一括）", "空行でシーンを区切ります。1シーンだけでも使えます。", 260)
    g.expose(5, "text", "ネガティブプロンプト", height=100)
    for field, label in (("scene_limit", "生成するシーン数の上限"), ("start_in_range", "開始位置"), ("batch_range", "ファイル番号の範囲"), ("base_seed", "開始シード")):
        g.expose(15, field, label)
    models(g)
    resolution(g, 6)
    loras(g, 1, [7, 11])
    sampler(g, 7, "初回", seed=False)
    sampler(g, 11, "高解像度化", seed=False, steps=8)
    g.expose(10, "scale_by", "latent拡大倍率")
    g.node(13)["widgets_values"] = [False]
    g.expose(13, "auto_download", "ZIP自動ダウンロード", "ONで全シーンの二段階目が完了した後にダウンロードします。OFFでもZIPはPodに保存されます。")
    g.node(15)["widgets_values"][3] = 1  # Do not submit hundreds of scenes on the first run.
    save = g.add("SaveImage", "生成画像", ["Anima_App/queue"], (("images", "IMAGE"),))
    g.connect(12, 0, save, "images")
    g.connect(15, 3, save, "filename_prefix", "STRING", True)
    g.finish("02_プロンプト一括_latent高解像度.json", [save])

    g = Graph(load("anima_two_character_hooks_hiresfix.json"))
    g.expose(4, "value", "共通プロンプト", height=160)
    g.expose(5, "value", "共通ネガティブ", "CFGが1の場合、通常ネガティブは効きません。", 100)
    models(g)
    resolution(g, 6)
    loras(g, 1, [54, 61], existing={0: 8, 2: 9})
    preset = g.add("AnimaAppRegionPreset", "領域配置", ["A・B 左右", 4, 4], outputs=(("layout", "STRING"),))
    g.connect(preset, 0, 6, "layout", "STRING", True)
    for field, label in (("preset", "領域配置"), ("overlap_percent", "領域の重なり（%）"), ("feather_percent", "境界のぼかし（%）")):
        g.expose(preset, field, label)
    for node_id, letter in ((10, "A"), (30, "B"), (40, "C"), (41, "D")):
        for field, title in (("lora_name", "LoRA"), ("strength", "LoRA強度"), ("positive", "プロンプト"), ("negative", "ネガティブ")):
            g.expose(node_id, field, f"{letter} {title}", "使う領域だけ入力してください。", 100 if field in ("positive", "negative") else None)
    sampler(g, 54, "初回")
    sampler(g, 61, "高解像度化", steps=8)
    g.expose(57, "scale_by", "latent拡大倍率")
    g.finish("03_領域別LoRA_A-D_実験的.json", [56, 63])

    original = load("anima_two_character_inpaint_hiresfix.json")
    for filename, output, prompt_id, sampler_ids, load_id, character in (
        ("04_2人描き直し_1構図.json", 16, 10, [14], None, None),
        ("05_2人描き直し_2人物A.json", 35, 11, [20], 17, 6),
        ("06_2人描き直し_3人物Bと高解像度.json", 29, 34, [43, 27], 36, 7),
    ):
        g = Graph(original)
        g.keep_ancestors([output])
        if load_id:
            g.node(load_id)["widgets_values"] = ["", "image"]
            g.expose(load_id, "image", "前段階の画像・マスク", "前段階のPNGをアップロードし、画像欄のマスク編集ボタンで今回の人物だけ塗ります。")
        prompts(g, prompt_id, 12)
        models(g)
        if not load_id:
            resolution(g, 13)
        elif output == 29:
            resolution(g, 25, long_edge=1536)
            g.node(25)["widgets_values"][3] = "center"
        existing = {0: 5}
        if character:
            existing[1] = character
        loras(g, 2, sampler_ids[:1] if character else sampler_ids,
              existing=existing, character=bool(character),
              shared_targets=sampler_ids[1:] if character else ())
        for i, node_id in enumerate(sampler_ids):
            sampler(g, node_id, "高解像度化" if i else "生成", steps=8 if i else 18)
        if output == 29:
            g.expose(23, "model_name", "拡大モデル")
        g.finish(filename, [output])


if __name__ == "__main__":
    build()
