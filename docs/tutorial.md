# ComfyUI Tutorial: the mental model

This is the 10-minute version. If you only read one file in `docs/`, read this one.

## 1. What ComfyUI actually is

ComfyUI is a **node graph interface** for diffusion models (Stable Diffusion,
SDXL, Flux, …). Instead of filling a form and clicking "Generate", you wire
small functional blocks ("nodes") together:

```
[Load Checkpoint] ──MODEL──▶ [KSampler] ──LATENT──▶ [VAE Decode] ──IMAGE──▶ [Save]
        │                        ▲
        └─CLIP──▶ [Text Encode] ─┘
```

Each node is a function. Each edge carries typed data (MODEL, CLIP, LATENT,
IMAGE, …). Pressing **Queue** executes the graph front-to-back. That's the
whole mental model — everything else is detail.

## 2. The 7 nodes of the basic workflow

`workflows/01_txt2img_basic.json` is the smallest useful graph. It does
text-to-image in 7 nodes:

| # | Node | What it does |
|---|------|--------------|
| 1 | CheckpointLoaderSimple | Loads the `.safetensors` model file; outputs MODEL, CLIP, VAE |
| 2 | CLIPTextEncode | Turns your **positive** prompt into a conditioning vector (via CLIP) |
| 3 | CLIPTextEncode | Turns your **negative** prompt into a conditioning vector |
| 4 | EmptyLatentImage | Creates blank noise in latent space (512×512 here) |
| 5 | KSampler | The diffusion loop: denoises the latent, guided by both prompts (this is where the magic and the waiting happen) |
| 6 | VAEDecode | Converts the finished latent back to pixels |
| 7 | SaveImage | Writes the PNG to `ComfyUI/output/` |

Change the prompt → edit node 2. Change the seed → edit node 5. Everything
you've ever done in AUTOMATIC1111 maps to some node here; ComfyUI just makes
the plumbing visible.

## 3. Two workflow formats

ComfyUI has **two** JSON formats — this confuses everyone once:

- **UI format** (`{"nodes": [...], "links": [...]}`): what you get from
  *Save* in the UI. Contains layout info (positions, colors). Human-friendly.
- **API format** (`{"1": {"class_type": ..., "inputs": {...}}}`): what you get
  from *Save (API Format)*. No layout, just the graph. This is what `/prompt`
  accepts.

The files in `workflows/` are **API format** — they load in the UI *and* work
with the API examples directly.

## 4. Queue, cache, and re-execution

- **Queue Prompt** runs the graph. ComfyUI caches node outputs: if you only
  change the seed, only downstream nodes re-run. This is why iteration is fast.
- **Extra options** (the gear next to Queue): *auto-queue*,
  *batch count*, etc.
- Right-click a node → **Bypass** to skip it, **Mute** to disable a branch.

## 5. The API (for automation)

The UI is just a client. Everything goes through HTTP + WebSocket:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Queue a workflow (`{"prompt": {...}, "client_id": ...}`) |
| `/ws?clientId=…` | WS | Live execution events; `executing` with `node: null` = done |
| `/history/{prompt_id}` | GET | Outputs of a finished prompt |
| `/view` | GET | Download an image (`filename`, `subfolder`, `type`) |
| `/upload/image` | POST | Upload an input image (for img2img) |
| `/object_info` | GET | Schema of every installed node (great for discovery) |

`examples/01_api_txt2img.py` and `02_api_img2img.py` implement this flow
end-to-end. Set `COMFYUI_SERVER` env var if your server isn't on
`127.0.0.1:8188`.

## 6. Custom nodes & Manager

The ecosystem lives in **custom nodes** (ControlNet helpers, upscalers,
Flux wrappers, …). Install **ComfyUI-Manager** (via `custom_nodes/`), then
*Manager → Install Custom Nodes* in the UI. Restart the server after
installing.

## 7. Practical tips

- **Models go in** `ComfyUI/models/checkpoints/` (`.safetensors` preferred).
  VAE / LoRA / ControlNet have their own subfolders.
- **No GPU?** Start with `python main.py --cpu`. It's slow (minutes per
  512×512 image) but works — that's how the screenshots in this repo were made.
- **fp16 vs fp32**: fp16 checkpoints (`*-fp16.safetensors`) halve VRAM/RAM.
  On CPU it mostly saves RAM.
- **Queue stays responsive**: generation runs async; the UI never blocks.
- **Embeddings**: textual-inversion embeddings go in `models/embeddings/`,
  referenced as `embedding:name` in prompts.
