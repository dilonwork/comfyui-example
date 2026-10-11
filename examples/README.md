# API examples

Drive a running ComfyUI server from Python — no browser needed.

```bash
pip install -r ../requirements.txt

# Put all settings in one place (optional but recommended)
cp ../.env.example ../.env   # then edit

# Text to image (uses workflows/01_txt2img_basic.json)
python 01_api_txt2img.py

# Image to image (uploads the input first, uses workflows/02_img2img.json)
python 02_api_img2img.py
```

Settings live in the repo-root `.env` (see `.env.example`); any explicit CLI
flag overrides the `.env` value:

```bash
python 01_api_txt2img.py --prompt "a cozy cabin in the snow" --seed 42 --out result.png
python 02_api_img2img.py --input photo.png --denoise 0.75
```

If ComfyUI isn't on `127.0.0.1:8188`:

```bash
COMFYUI_SERVER=192.168.1.10:8188 python 01_api_txt2img.py
```

Both scripts follow the same flow — queue → wait on websocket → download:

1. `POST /prompt` with the workflow JSON and a `client_id`
2. Listen on `/ws?clientId=…` until an `executing` event arrives with `node: null`
3. `GET /history/{prompt_id}` to find output filenames
4. `GET /view?filename=…` to download the PNG

See `docs/tutorial.md` §5 for the full endpoint reference.
