#!/usr/bin/env python3
"""Generate only missing, small gallery samples through the existing ComfyUI API.

No installs, restarts or queue cancellation. Interrupted runs resume by prompt ID.
"""
import argparse
import copy
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8188"
VOICE_PATH = "breeze_voices/huola-dachu/reference_29c7b2b6dede.flac"
TRANSCRIPT = "大家好，我是火辣大厨。今天我们一起学习，怎样在康菲里挑选姿势，把参考线稿变成自然的人物照片。"
TEXT = "你好，欢迎来到语音图库。选好声音，我们就开始吧。"
BREEZE = {"cfg_scale": 1.0, "max_new_tokens": 504, "temperature": 0.85, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.1, "depth_temperature": 0.9, "depth_top_k": 50, "depth_top_p": 1.0, "seed": 20261109}
BL = {"model": "int8 hybrid (recommended)", "dtype": "bf16", "device": "cuda", "attention": "sdpa", "decode_mode": "cuda_graphs", "download_if_missing": False}
DL = {"model_name": "drama3_fp8experts_bf16.safetensors", "experts": "in RAM", "expert_cache_gb": 0.0, "second_gpu": "none", "split_layer": 0}
DRAMA = {"seed": 20261109, "temperature": 1.0, "top_p": 0.9, "top_k": 0, "max_frames": 360, "split_long_text": True, "speakers": "one take per line"}


def api(path, data=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode()) from exc


def specs():
    breeze = [
        ("clone", "自然克隆", "Natural clone", "clone", "voice", "", TEXT),
        ("happy", "轻快兴奋", "Bright excitement", "direction", "emotion", "保持参考音色，用轻快、兴奋的语气说话。", TEXT),
        ("slow", "放慢语速", "Slower pace", "direction", "pace", "保持参考音色，缓慢地说，句间清楚停顿。", TEXT),
        ("loud", "提高音量", "Louder delivery", "direction", "volume", "保持参考音色，提高音量，清晰响亮地说话。", TEXT),
        ("whisper", "悄声耳语", "Whisper", "direction", "delivery", "保持参考音色，用低声耳语的方式说话。", TEXT),
        ("laugh", "句首笑声", "Inline laugh", "direction", "event", "保持参考音色，自然地说话，表现文案中的笑声。", "[笑] " + TEXT),
        ("combo", "温柔低声与慢速", "Gentle, quiet and slow", "direction", "combination", "保持参考音色，放低音量，用温柔、缓慢的语气说话。", TEXT),
    ]
    drama = [
        ("clone", "自然克隆", "Natural clone", "clone", "voice", "", TEXT),
        ("happy", "轻快兴奋", "Bright excitement", "tags", "emotion", "[with bright eager excitement]", "[with bright eager excitement] " + TEXT),
        ("slow", "放慢语速", "Slower pace", "tags", "pace", "[speak slowly]", "[speak slowly] " + TEXT),
        ("loud", "提高音量", "Louder delivery", "tags", "volume", "[speaking loudly]", "[speaking loudly] " + TEXT),
        ("whisper", "悄声耳语", "Whisper", "tags", "delivery", "[whispers]", "[whispers] " + TEXT),
        ("laugh", "句首笑声", "Inline laugh", "tags", "event", "[laughs]", "[laughs] " + TEXT),
        ("scoped", "局部耳语", "Scoped whisper", "tags", "scope", "<whisper>...</whisper>", "你好，欢迎来到语音图库。<whisper>选好声音</whisper>，我们就开始吧。"),
        ("combo", "叹气与温柔慢速", "Sigh, gentle and slow", "tags", "combination", "[sighs] [soft and slow]", "[sighs] [soft and slow] " + TEXT),
    ]
    return [(model, item) for model, items in [("breeze", breeze), ("drama3", drama)] for item in items]


def run(model, item, work):
    key, zh, en, mode, category, instruction, text = item
    identifier = f"{model}-chef-{key}"
    record = work / f"{identifier}.json"
    if record.exists():
        state = json.loads(record.read_text())
        if state.get("status") == "completed":
            print("reuse", identifier, flush=True)
            return
    else:
        state = {}
    prompt = {"1": {"class_type": "LoadAudio", "inputs": {"audio": VOICE_PATH}}}
    def add(n, cls, inputs):
        prompt[str(n)] = {"class_type": cls, "inputs": inputs}
    if model == "breeze":
        params = {**BREEZE, "cfg_scale": 1.0 if mode == "clone" else 4.0}
        add(2, "BreezeTTS2LoadModel", BL)
        inputs = {**params, "breeze_model": ["2", 0], "reference_audio": ["1", 0], "reference_text": TRANSCRIPT, "text": text}
        if mode == "direction":
            inputs.update(instruction=instruction, stitch_reference="none")
            params["stitch_reference"] = "none"
        add(3, "BreezeTTS2VoiceClone" if mode == "clone" else "BreezeTTS2VoiceDirection", inputs)
        output = ["3", 0]
        parameters = {"loader": BL, "generation": params}
    else:
        add(2, "Drama3Loader", DL)
        add(3, "Drama3CodecLoader", {"codec_name": "drama3_codec.safetensors"})
        add(4, "Drama3EncodeVoice", {"codec": ["3", 0], "audio": ["1", 0], "transcript": TRANSCRIPT})
        add(5, "Drama3Generate", {**DRAMA, "model": ["2", 0], "text": text, "voices": {"voice0": ["4", 0]}})
        add(6, "Drama3Decode", {"codec": ["3", 0], "codes": ["5", 0], "shorten_long_pauses": True})
        output = ["6", 0]
        parameters = {"loader": DL, "codec_name": "drama3_codec.safetensors", "generation": DRAMA, "decode": {"shorten_long_pauses": True}}
    add(9, "SaveAudio", {"audio": output, "filename_prefix": f"audio/{'breeze-tts-2' if model == 'breeze' else 'drama3'}/tts-gallery/{identifier}"})
    for entry in prompt.values():
        entry["_meta"] = {"title": entry["class_type"] + " - 语音图库示例实测"}
    state.update(id=identifier, model=model, mode=mode, category=category, name_zh=zh, name_en=en, text=text, instruction=instruction, parameters=parameters, prompt=prompt)
    if not state.get("prompt_id"):
        state["prompt_id"] = api("/prompt", {"prompt": prompt, "client_id": "tts-gallery-samples"})["prompt_id"]
        record.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print("queued", identifier, state["prompt_id"], flush=True)
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        history = api("/history/" + state["prompt_id"]).get(state["prompt_id"])
        if history:
            state["history"] = history
            if history["status"]["status_str"] != "success":
                state["status"] = "error"
                record.write_text(json.dumps(state, ensure_ascii=False, indent=2))
                raise RuntimeError(json.dumps(history["status"], ensure_ascii=False)[:2500])
            file = history["outputs"]["9"]["audio"][0]
            state["output_file"] = file
            state["status"] = "completed"
            record.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            print("done", identifier, file["filename"], flush=True)
            return
        time.sleep(3)
    raise TimeoutError("Still running; resume this script, do not requeue")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["breeze", "drama3", "all"], default="all")
    args = ap.parse_args()
    work = ROOT / ".generation"
    work.mkdir(exist_ok=True)
    for model, item in specs():
        if args.model in (model, "all"):
            run(model, item, work)


if __name__ == "__main__":
    main()
