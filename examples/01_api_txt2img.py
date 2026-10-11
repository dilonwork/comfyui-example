#!/usr/bin/env python3
"""Queue a text-to-image workflow on a running ComfyUI server via its HTTP + WebSocket API.

Usage:
    python 01_api_txt2img.py [--prompt "your prompt"] [--seed 123] [--out result.png]

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

SERVER = os.environ.get("COMFYUI_SERVER", "127.0.0.1:8188")
WORKFLOW = os.path.join(os.path.dirname(__file__), "..", "workflows", "01_txt2img_basic.json")


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="beautiful scenery, nature, glass bottle landscape, purple galaxy inside the bottle, highly detailed")
    ap.add_argument("--negative", default="text, watermark, blurry, low quality")
    ap.add_argument("--seed", type=int, default=random.randint(0, 2**31))
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--out", default="result.png")
    args = ap.parse_args()

    with open(WORKFLOW) as f:
        prompt = json.load(f)

    # Node ids follow workflows/01_txt2img_basic.json:
    # 2 = positive CLIPTextEncode, 3 = negative, 5 = KSampler.
    prompt["2"]["inputs"]["text"] = args.prompt
    prompt["3"]["inputs"]["text"] = args.negative
    prompt["5"]["inputs"]["seed"] = args.seed
    prompt["5"]["inputs"]["steps"] = args.steps

    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(prompt, client_id)
    print(f"queued prompt {prompt_id}, waiting for execution...")
    wait_for_done(prompt_id, client_id)
    download_result(prompt_id, args.out)


if __name__ == "__main__":
    main()
