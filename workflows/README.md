# Workflows

API-format workflows (loadable in the UI *and* usable with the API examples).

| File | What it does | Key nodes |
|------|--------------|-----------|
| `01_txt2img_basic.json` | Text → image, 512×512, 20 steps | CheckpointLoader → 2× CLIPTextEncode → EmptyLatent → KSampler → VAEDecode → SaveImage |
| `02_img2img.json` | Image → image (`denoise` 0.75) | LoadImage → VAEEncode → KSampler → VAEDecode → SaveImage |

## Load in the UI

Drag the JSON file onto the ComfyUI canvas, or use the *Load* button.
The graph appears with all nodes wired — press **Queue Prompt** to run.

Both workflows expect a Stable Diffusion 1.5 checkpoint named
`v1-5-pruned-emaonly-fp16.safetensors` in `ComfyUI/models/checkpoints/`.
Rename the `ckpt_name` in node 1 if your file is called something else.

For img2img, place your source picture at `ComfyUI/input/input.png`
(or change node 4's `image` field).
