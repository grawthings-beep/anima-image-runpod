"""Optional Anima NegPiP using the image's pinned ComfyUI-ppm implementation."""


def patch_legacy_anima_attention(model):
    import inspect
    import torch
    from comfy.ldm.cosmos.predict2 import Attention

    if "transformer_options" in inspect.signature(Attention.compute_qkv).parameters:
        return  # New ComfyUI runs PPM's attn2_patch natively.
    if model.model_options.get("anima_negpip_legacy_attention"):
        return

    def wrap(block, previous):
        def forward(x, context=None, rope_emb=None, transformer_options=None):
            options = transformer_options or {}
            mask = options.get("ppm_negpip_mask")
            if mask is None:
                return previous(x, context, rope_emb, options)
            q, k, v = block.compute_qkv(x, context, rope_emb=rope_emb)
            # Older Cosmos lacks attn2 hooks. With bias-free V and Identity norm,
            # sign inversion after projection is equivalent to PPM's input patch.
            v = v * mask.to(v).unsqueeze(-1)
            return block.compute_attention(q, k, v, transformer_options=options)
        return forward

    count = 0
    for name, block in model.get_model_object("diffusion_model").named_modules():
        if isinstance(block, Attention) and not block.is_selfattn:
            if block.v_proj.bias is not None or not isinstance(block.v_norm, torch.nn.Identity):
                raise RuntimeError("Unsupported legacy Anima attention. Update ComfyUI before enabling NegPiP.")
            path = f"diffusion_model.{name}.forward"
            if path in model.object_patches:
                raise RuntimeError("Connect NegPiP before AttentionCouplePPM or other attention patches.")
            model.add_object_patch(path, wrap(block, model.get_model_object(path)))
            count += 1
    if not count:
        raise RuntimeError("No compatible Anima cross-attention found for NegPiP.")
    model.model_options["anima_negpip_legacy_attention"] = True


class AnimaNegPipToggle:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("MODEL",),
            "clip": ("CLIP",),
            "enabled": ("BOOLEAN", {"default": False}),
        }}

    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "apply"
    CATEGORY = "Anima/conditioning"

    def apply(self, model, clip, enabled):
        if not enabled:
            return model, clip

        import nodes
        from comfy.model_base import Anima

        if not isinstance(model.model, Anima):
            raise ValueError("Anima NegPiP requires an Anima/WAI-ANIMA model. Turn it off for other model types.")
        negpip = nodes.NODE_CLASS_MAPPINGS.get("CLIPNegPip")
        if negpip is None:
            raise RuntimeError("CLIPNegPip is unavailable. Install the bundled ComfyUI-ppm and restart ComfyUI.")
        result = negpip.execute(model=model, clip=clip)
        patched_model, patched_clip = result[0], result[1]
        if not (patched_model.model_options.get("ppm_negpip")
                and patched_clip.patcher.model_options.get("ppm_negpip")):
            raise RuntimeError("NegPiP was not applied. Use the Anima Qwen text encoder and the bundled PPM version.")
        patch_legacy_anima_attention(patched_model)
        return patched_model, patched_clip


NODE_CLASS_MAPPINGS = {"AnimaNegPipToggle": AnimaNegPipToggle}
NODE_DISPLAY_NAME_MAPPINGS = {"AnimaNegPipToggle": "Anima NegPiP (ON/OFF)"}
