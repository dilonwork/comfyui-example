# API examples

Drive a running ComfyUI server from Python — no browser needed.

```bash
pip install -r ../requirements.txt

# Text to image (uses workflows/01_txt2img_basic.json)
python 01_api_txt2img.py --prompt "a cozy cabin in the snow" --out result.png

# Image to image (uploads the input first, uses workflows/02_img2img.json)
python 02_api_img2img.py --input photo.png --denoise 0.75 --out result2.png
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
