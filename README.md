# comfyui-example

A minimal, working introduction to [ComfyUI](https://github.com/comfyanonymous/ComfyUI) —
the node-graph interface for Stable Diffusion and friends. Two runnable
workflows, two API examples, one short tutorial. Everything here actually runs.

![ComfyUI with the basic txt2img workflow loaded](docs/images/02-workflow.png)

## What is ComfyUI?

Instead of a form with a "Generate" button, you build image generation as a
graph of nodes: load model → encode prompt → sample → decode → save. Each node
is a function, each edge carries typed data. Press **Queue** and the graph
executes front-to-back, caching intermediate results so iteration is fast.

![Empty ComfyUI canvas on first launch](docs/images/01-empty.png)

## Quickstart

```bash
# 1. Install ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu  # or CUDA build
pip install -r requirements.txt

# 2. Download a checkpoint into ComfyUI/models/checkpoints/
#    (e.g. v1-5-pruned-emaonly-fp16.safetensors from Hugging Face)

# 3. Start the server (add --cpu if you have no GPU)
python main.py --listen 127.0.0.1 --port 8188
```

Open http://127.0.0.1:8188, drag `workflows/01_txt2img_basic.json` onto the
canvas, press **Queue Prompt**.

## What's inside

| Path | Contents |
|------|----------|
| `workflows/` | Two API-format workflows: basic txt2img and img2img |
| `examples/` | Python scripts driving ComfyUI over its HTTP + WebSocket API |
| `docs/tutorial.md` | The 10-minute mental model: nodes, queue, API, custom nodes, tips |

## The basic workflow, node by node

`workflows/01_txt2img_basic.json` — 7 nodes, text to image:

1. **CheckpointLoaderSimple** — loads the `.safetensors` model (outputs MODEL, CLIP, VAE)
2. **CLIPTextEncode** — positive prompt → conditioning vector
3. **CLIPTextEncode** — negative prompt → conditioning vector
4. **EmptyLatentImage** — blank 512×512 noise in latent space
5. **KSampler** — the diffusion loop (seed, 20 steps, euler) — this is where the waiting happens
6. **VAEDecode** — latent → pixels
7. **SaveImage** — writes the PNG

Change the prompt in node 2, the seed in node 5, queue again. Only downstream
nodes re-run thanks to caching.

## Drive it from Python (no browser)

```bash
pip install -r requirements.txt
python examples/01_api_txt2img.py --prompt "a cozy cabin in the snow" --out result.png
python examples/02_api_img2img.py --input photo.png --denoise 0.75 --out result2.png
```

The scripts queue the workflow via `POST /prompt`, wait on the websocket for
completion, then download the result with `GET /view`. Point at a remote
server with `COMFYUI_SERVER=host:8188`.

## Sample output

Generated on CPU with the basic workflow (slow but real):

![Sample output from the basic txt2img workflow](docs/images/03-output.png)

## Notes

- Workflows are in **API format**: they load in the UI *and* work with the API examples directly.
- Screenshots in `docs/images/` are real captures of ComfyUI running locally (CPU mode).
- Tested against ComfyUI latest (Oct 2026). Custom nodes are not required for anything here.
