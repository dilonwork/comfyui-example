#!/usr/bin/env python3
"""Queue a text-to-image workflow on a running ComfyUI server via its HTTP + WebSocket API.

Usage:
    cp .env.example .env   # then edit settings
    python 01_api_txt2img.py [--prompt "your prompt"] [--seed 123] [--out result.png]

Settings come from .env (see .env.example); explicit CLI flags override them.

Requires a ComfyUI server on 127.0.0.1:8188 with a Stable Diffusion checkpoint
in ComfyUI/models/checkpoints/ (see workflows/01_txt2img_basic.json for the
checkpoint filename this example expects).

Flow:
    1. Load the workflow JSON (API format) and patch prompt / seed.
    2. POST /prompt to queue it.
    3. Listen on /ws until this prompt finishes executing.
    4. GET /history/{prompt_id}, then GET /view to download the image.
"""

import argparse
import json
import os
import random
import urllib.parse
import urllib.request
import uuid

import websocket  # pip install websocket-client
from dotenv import load_dotenv  # pip install python-dotenv

# Load repo-root .env (if present); explicit CLI flags override these values.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SERVER = os.environ.get("COMFYUI_SERVER", "127.0.0.1:8188")
WORKFLOW = os.path.join(os.path.dirname(__file__), "..", "workflows", "01_txt2img_basic.json")

DEFAULT_PROMPT = "beautiful scenery, nature, glass bottle landscape, purple galaxy inside the bottle, highly detailed"
DEFAULT_NEGATIVE = "text, watermark, blurry, low quality"


def queue_prompt(prompt: dict, client_id: str) -> str:
    body = json.dumps({"prompt": prompt, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(f"http://{SERVER}/prompt", data=body)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["prompt_id"]


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
                        return  # the whole prompt finished
    finally:
        ws.close()


def download_result(prompt_id: str, out_path: str) -> None:
    with urllib.request.urlopen(f"http://{SERVER}/history/{prompt_id}") as resp:
        history = json.loads(resp.read())[prompt_id]
    # Find the SaveImage node's outputs.
    for node_id, node_out in history["outputs"].items():
        for img in node_out.get("images", []):
            params = urllib.parse.urlencode(
                {"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]}
            )
            with urllib.request.urlopen(f"http://{SERVER}/view?{params}") as resp:
                data = resp.read()
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"saved {out_path} (from node {node_id})")
            return
    raise RuntimeError("no images found in prompt history")


def _env_int(name):
    v = os.environ.get(name)
    return int(v) if v not in (None, "") else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=None, help="overrides TXT2IMG_PROMPT")
    ap.add_argument("--negative", default=None, help="overrides TXT2IMG_NEGATIVE")
    ap.add_argument("--seed", type=int, default=None, help="overrides TXT2IMG_SEED")
    ap.add_argument("--steps", type=int, default=None, help="overrides TXT2IMG_STEPS")
    ap.add_argument("--out", default=None, help="overrides TXT2IMG_OUT")
    args = ap.parse_args()

    prompt_text = args.prompt or os.environ.get("TXT2IMG_PROMPT") or DEFAULT_PROMPT
    negative_text = args.negative or os.environ.get("TXT2IMG_NEGATIVE") or DEFAULT_NEGATIVE
    seed = args.seed if args.seed is not None else _env_int("TXT2IMG_SEED")
    if seed is None:
        seed = random.randint(0, 2**31)
    steps = args.steps if args.steps is not None else _env_int("TXT2IMG_STEPS") or 20
    out = args.out or os.environ.get("TXT2IMG_OUT") or "result.png"

    with open(WORKFLOW) as f:
        prompt = json.load(f)

    # Node ids follow workflows/01_txt2img_basic.json:
    # 2 = positive CLIPTextEncode, 3 = negative, 5 = KSampler.
    prompt["2"]["inputs"]["text"] = prompt_text
    prompt["3"]["inputs"]["text"] = negative_text
    prompt["5"]["inputs"]["seed"] = seed
    prompt["5"]["inputs"]["steps"] = steps

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(prompt, client_id)
    print(f"queued prompt {prompt_id} (seed={seed}, steps={steps}), waiting for execution...")
    wait_for_done(prompt_id, client_id)
    download_result(prompt_id, out)


if __name__ == "__main__":
    main()
