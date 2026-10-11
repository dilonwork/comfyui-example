#!/usr/bin/env python3
"""Image-to-image via the ComfyUI API: upload an input image, then queue the workflow.

Usage:
    cp .env.example .env   # then edit settings
    python 02_api_img2img.py --input photo.png [--prompt "..."] [--denoise 0.75] [--out result.png]

Settings come from .env (see .env.example); explicit CLI flags override them.

Steps:
    1. POST /upload/image to put the input image into ComfyUI's input folder.
    2. Load workflows/02_img2img.json, point its LoadImage node (id 4) at the
       uploaded filename, patch prompt / denoise / seed.
    3. Queue, wait on websocket, download the result (same helpers as 01).
"""

import argparse
import io
import json
import os
import random
import uuid

import requests  # pip install requests
import websocket  # pip install websocket-client
from dotenv import load_dotenv  # pip install python-dotenv

# Load repo-root .env (if present); explicit CLI flags override these values.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SERVER = os.environ.get("COMFYUI_SERVER", "127.0.0.1:8188")
WORKFLOW = os.path.join(os.path.dirname(__file__), "..", "workflows", "02_img2img.json")

DEFAULT_PROMPT = "masterpiece, best quality, vibrant colors, highly detailed"


def upload_image(path: str) -> str:
    with open(path, "rb") as f:
        files = {"image": (os.path.basename(path), f, "image/png")}
        resp = requests.post(f"http://{SERVER}/upload/image", files=files,
                             data={"overwrite": "true"})
    resp.raise_for_status()
    return resp.json()["name"]


def queue_prompt(prompt: dict, client_id: str) -> str:
    resp = requests.post(f"http://{SERVER}/prompt",
                         json={"prompt": prompt, "client_id": client_id})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_done(prompt_id: str, client_id: str) -> None:
    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER}/ws?clientId={client_id}")
    try:
        while True:
            msg = ws.recv()
            if isinstance(msg, str):
                data = json.loads(msg)
                if data.get("type") == "executing":
                    d = data["data"]
                    if d.get("node") is None and d.get("prompt_id") == prompt_id:
                        return
    finally:
        ws.close()


def download_result(prompt_id: str, out_path: str) -> None:
    history = requests.get(f"http://{SERVER}/history/{prompt_id}").json()[prompt_id]
    for node_id, node_out in history["outputs"].items():
        for img in node_out.get("images", []):
            r = requests.get(f"http://{SERVER}/view", params={
                "filename": img["filename"],
                "subfolder": img["subfolder"],
                "type": img["type"],
            })
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            print(f"saved {out_path} (from node {node_id})")
            return
    raise RuntimeError("no images found in prompt history")


def _env_int(name):
    v = os.environ.get(name)
    return int(v) if v not in (None, "") else None


def _env_float(name):
    v = os.environ.get(name)
    return float(v) if v not in (None, "") else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="overrides IMG2IMG_INPUT")
    ap.add_argument("--prompt", default=None, help="overrides IMG2IMG_PROMPT")
    ap.add_argument("--denoise", type=float, default=None, help="overrides IMG2IMG_DENOISE")
    ap.add_argument("--seed", type=int, default=None, help="overrides IMG2IMG_SEED")
    ap.add_argument("--out", default=None, help="overrides IMG2IMG_OUT")
    args = ap.parse_args()

    input_path = args.input or os.environ.get("IMG2IMG_INPUT")
    if not input_path:
        ap.error("--input is required (or set IMG2IMG_INPUT in .env)")
    prompt_text = args.prompt or os.environ.get("IMG2IMG_PROMPT") or DEFAULT_PROMPT
    denoise = args.denoise if args.denoise is not None else _env_float("IMG2IMG_DENOISE")
    if denoise is None:
        denoise = 0.75
    seed = args.seed if args.seed is not None else _env_int("IMG2IMG_SEED")
    if seed is None:
        seed = random.randint(0, 2**31)
    out = args.out or os.environ.get("IMG2IMG_OUT") or "result_img2img.png"

    uploaded = upload_image(input_path)
    print(f"uploaded as {uploaded}")

    with open(WORKFLOW) as f:
        prompt = json.load(f)

    # Node ids follow workflows/02_img2img.json:
    # 2 = positive CLIPTextEncode, 4 = LoadImage, 6 = KSampler.
    prompt["2"]["inputs"]["text"] = prompt_text
    prompt["4"]["inputs"]["image"] = uploaded
    prompt["6"]["inputs"]["seed"] = seed
    prompt["6"]["inputs"]["denoise"] = denoise

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(prompt, client_id)
    print(f"queued prompt {prompt_id} (seed={seed}, denoise={denoise}), waiting for execution...")
    wait_for_done(prompt_id, client_id)
    download_result(prompt_id, out)


if __name__ == "__main__":
    main()
