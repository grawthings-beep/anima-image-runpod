# Anima Manga Composer

Cloudflare Pages compatible static manga lettering/composition tool for Anima outputs.

It keeps the GPU image generation separate from the manga editing layer:

- RunPod + ComfyUI + Anima generate panel images.
- This Pages app lays out panels, speech bubbles, Japanese text, and SFX text.
- The finished page can be exported as PNG, and the layout can be saved as JSON.

## Local preview

Open `index.html` directly in a browser, or serve this directory with any static server.

```powershell
python -m http.server 8788 -d cloudflare/manga-composer
```

Then open:

```text
http://127.0.0.1:8788
```

## Cloudflare Pages deploy

This directory is static and can be deployed as a Pages project.

With Wrangler:

```powershell
wrangler pages deploy cloudflare/manga-composer --project-name anima-manga-composer
```

Or connect the GitHub repository in Cloudflare Pages and set:

```text
Build command: none
Build output directory: cloudflare/manga-composer
```

## Notes

- Panel images are embedded in saved JSON as data URLs for now.
- Japanese text is rendered by the browser using local/system fonts.
- A later server-side export path can use R2 for assets and a Worker or RunPod-side renderer for final high-resolution output.
