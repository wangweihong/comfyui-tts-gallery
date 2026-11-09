"""Shared model/mode templates, exported as UI or API workflows."""
import copy
import json
import uuid
from pathlib import Path

from .catalog import BASE, LibraryError, library, localized

BREEZE_LOADER = {"model": "int8 hybrid (recommended)", "dtype": "bf16", "device": "cuda", "attention": "sdpa", "decode_mode": "cuda_graphs", "download_if_missing": False}
BREEZE_CONTROLS = {"cfg_scale": 1.0, "max_new_tokens": 1000, "temperature": 0.85, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.1, "depth_temperature": 0.9, "depth_top_k": 50, "depth_top_p": 1.0, "seed": 20261028}
DRAMA_LOADER = {"model_name": "drama3_fp8experts_bf16.safetensors", "experts": "in RAM", "expert_cache_gb": 0.0, "second_gpu": "none", "split_layer": 0}
DRAMA_CONTROLS = {"seed": 20261109, "temperature": 1.0, "top_p": 0.9, "top_k": 0, "max_frames": 600, "split_long_text": True, "speakers": "one take per line"}
SOURCES = {"breeze": "https://huggingface.co/BreezeBlue/Breeze-TTS-2", "drama3": "https://github.com/PedroMarinhoDev/ComfyUI-Drama3\n模型说明: https://huggingface.co/fishaudio/drama-3"}


def prompt_for(row, model=None, voice_id=None, lib=None):
    lib = lib or library
    if row["kind"] == "voice":
        model = model or "breeze"
        mode = "clone"
        voice_id = row["id"]
        text, instruction, params = "你好，我是火辣大厨。现在可以在语音图库中试听、选择和复用声音了。", "", {}
        if row["id"] != "huola-dachu":
            text = "你好，欢迎使用语音图库。这是一段新的声音克隆测试。" if row["language"] != "en" else "Hello! This is a new voice cloning test from TTS Gallery."
    else:
        model, mode = row["model"], row["mode"]
        voice_id = row.get("voice_id")
        text, instruction, params = row["text"], row.get("instruction", ""), row["parameters"]
    if model not in ("breeze", "drama3"):
        raise LibraryError("不支持的模型 / Unsupported model")
    if model == "breeze" and mode not in ("design", "clone", "direction") or model == "drama3" and mode not in ("clone", "tags", "generate", "dialogue"):
        raise LibraryError("不支持的生成模式 / Unsupported generation mode")
    refs = copy.deepcopy(row.get("voice_ids", {})) if row["kind"] == "example" else {}
    if not refs and voice_id:
        refs = {"voice0": voice_id}
    if not isinstance(refs, dict) or len(refs) > 2 or set(refs) != {f"voice{i}" for i in range(len(refs))}:
        raise LibraryError("当前工作流支持连续编号的1至2个参考音色 / Invalid voice slots")
    if mode == "dialogue" and (len(refs) != 2 or len(set(refs.values())) != 2):
        raise LibraryError("双人对话需要两个不同的参考音色 / Dialogue requires two distinct voice references")
    if model == "breeze" and len(refs) > 1:
        raise LibraryError("此Breeze模板只接收一个参考音色 / This Breeze template accepts one voice")
    p = {}
    def add(identifier, cls, inputs, purpose):
        p[str(identifier)] = {"class_type": cls, "inputs": copy.deepcopy(inputs), "_meta": {"title": f"{cls} - {purpose}"}}
    add(1, "PrimitiveStringMultiline", {"value": text}, "输入要朗读的文案")
    controls = copy.deepcopy(params.get("generation", BREEZE_CONTROLS if model == "breeze" else DRAMA_CONTROLS))
    add(2, "PrimitiveInt", {"value": controls["seed"]}, "随机种子，固定以便对照")
    add(3, "PrimitiveFloat", {"value": controls["temperature"]}, "采样温度")
    controls.update(text=["1", 0], seed=["2", 0], temperature=["3", 0])
    for index, identifier in enumerate(refs.values()):
        reference = lib.record(identifier, "voice")
        add(4 if index == 0 else 7, "TTSVoiceGallery", {"reference_id": identifier, "language": "zh"},
            f"角色{index}参考：{localized(reference, 'name', 'zh')}" if mode == "dialogue" else "选择克隆参考音色")
    if model == "breeze":
        loader = params.get("loader", BREEZE_LOADER)
        add(10, "BreezeTTS2LoadModel", loader, "加载语音模型")
        add(5, "PrimitiveFloat", {"value": controls["cfg_scale"]}, "指令强度，克隆建议1，设计或控制建议4")
        controls.update(breeze_model=["10", 0], cfg_scale=["5", 0])
        if mode != "design":
            if not voice_id:
                raise LibraryError("克隆示例缺少参考声音 / Missing reference voice")
            controls.update(reference_audio=["4", 0], reference_text=["4", 1])
        if mode in ("design", "direction"):
            add(6, "PrimitiveStringMultiline", {"value": instruction}, "声音设计或表达指令")
            controls["instruction"] = ["6", 0]
        if mode == "direction":
            controls.setdefault("stitch_reference", "none")
        cls = {"design": "BreezeTTS2VoiceDesign", "clone": "BreezeTTS2VoiceClone", "direction": "BreezeTTS2VoiceDirection"}[mode]
        add(20, cls, controls, "按文案与参数生成语音")
        output = ["20", 0]
    else:
        add(10, "Drama3Loader", params.get("loader", DRAMA_LOADER), "加载语音模型，专家放内存")
        add(11, "Drama3CodecLoader", {"codec_name": params.get("codec_name", "drama3_codec.safetensors")}, "加载音频编解码器")
        voices = {}
        for index, slot in enumerate(refs):
            reference_node, encode_node = (4, 12) if index == 0 else (7, 13)
            add(encode_node, "Drama3EncodeVoice", {"codec": ["11", 0], "audio": [str(reference_node), 0], "transcript": [str(reference_node), 1]}, f"编码角色{index}的参考声音")
            voices[slot] = [str(encode_node), 0]
        controls.update(model=["10", 0], voices=voices)
        add(20, "Drama3Generate", controls, "使用参考音色与文本标签生成")
        add(21, "Drama3Decode", {"codec": ["11", 0], "codes": ["20", 0], **params.get("decode", {"shorten_long_pauses": True})}, "解码生成语音")
        output = ["21", 0]
    add(30, "SaveAudio", {"audio": output, "filename_prefix": f"audio/{'breeze-tts-2' if model == 'breeze' else 'drama3'}/tts-gallery/{row['id']}"}, "保存最终FLAC语音")
    return p, model, mode


def graph_from_prompt(prompt, schemas, *, identifier, title, note=""):
    nodes, links = [], []
    positions = {"1": [40, 40], "6": [40, 300], "4": [40, 600], "2": [490, 40], "3": [490, 210], "5": [490, 380],
                 "10": [850, 40], "11": [850, 550], "12": [1310, 650], "7": [40, 1100], "13": [1310, 1080], "20": [1310, 40], "21": [1780, 420], "30": [2240, 40]}
    for key, entry in prompt.items():
        cls, values = entry["class_type"], entry["inputs"]
        schema = schemas[cls]
        node = {"id": int(key), "type": cls, "title": entry["_meta"]["title"], "pos": positions.get(key, [850, 1000]),
                "size": [300 if key in ("2", "3", "5") else 330 if key == "30" else 410, 460 if key == "1" and "7" in prompt else 250 if cls == "PrimitiveStringMultiline" else 420 if cls == "TTSVoiceGallery" else 560 if key == "20" else 110 if key in ("2", "3", "5") else 330],
                "flags": {}, "order": len(nodes), "mode": 0, "inputs": [], "outputs": [],
                "properties": {"Node name for S&R": cls}, "widgets_values": []}
        for section in ("required", "optional"):
            for name, spec in schema.get("input", {}).get(section, {}).items():
                if name not in values:
                    continue
                value, typ = values[name], spec[0]
                options = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
                if typ == "COMFY_AUTOGROW_V3":
                    for vn, link in value.items():
                        node["inputs"].append({"name": f"{name}.{vn}", "type": "DRAMA3_VOICE", "link": None, "_source": link})
                    # Keep one spare input so the native autogrow widget can add another voice.
                    node["inputs"].append({"name": f"{name}.voice{len(value)}", "type": "DRAMA3_VOICE", "link": None})
                    continue
                scalar = isinstance(typ, list) or typ in ("STRING", "FLOAT", "INT", "BOOLEAN", "COMBO")
                connected = isinstance(value, list) and len(value) == 2 and str(value[0]) in prompt and isinstance(value[1], int)
                if not scalar or connected:
                    inp = {"name": name, "type": "COMBO" if isinstance(typ, list) else typ, "link": None}
                    if connected:
                        inp["_source"] = value
                    if scalar:
                        inp["widget"] = {"name": name}
                    node["inputs"].append(inp)
                if scalar:
                    default = options.get("default", typ[0] if isinstance(typ, list) else "" if typ in ("STRING", "COMBO") else False if typ == "BOOLEAN" else 0)
                    node["widgets_values"].append(default if connected else value)
                    if name == "seed" or options.get("control_after_generate"):
                        node["widgets_values"].append("fixed")
        for index, typ in enumerate(schema.get("output", [])):
            node["outputs"].append({"name": schema.get("output_name", schema["output"])[index], "type": typ, "links": []})
        nodes.append(node)
    by_id = {str(n["id"]): n for n in nodes}
    for node in nodes:
        for slot, inp in enumerate(node["inputs"]):
            source = inp.pop("_source", None)
            if source is None:
                continue
            origin, output = str(source[0]), source[1]
            link_id = len(links) + 1
            links.append([link_id, int(origin), output, node["id"], slot, inp["type"]])
            inp["link"] = link_id
            by_id[origin]["outputs"][output]["links"].append(link_id)
    nodes.append({"id": 40, "type": "Note", "title": "Note - 示例说明与来源链接", "pos": [850, 1500 if "7" in prompt else 1000], "size": [720, 300],
                  "flags": {}, "order": len(nodes), "mode": 0, "inputs": [], "outputs": [], "properties": {}, "widgets_values": [note]})
    return {"id": str(uuid.uuid4()), "revision": 0, "version": 0.4, "last_node_id": 40, "last_link_id": len(links), "nodes": nodes, "links": links,
            "groups": [{"title": "输入与参数 - 文案、参考声音、种子与常用控制", "bounding": [20, 0, 800, 1550 if "7" in prompt else 1050], "color": "#5b5bd6", "font_size": 24, "flags": {}}],
            "config": {}, "extra": {"tts_gallery": {"reference_id": identifier, "name": title}, "ds": {"scale": 0.62, "offset": [60, 180 if "7" in prompt else 250]}}}


def export(identifier, model=None, format="ui", language="zh", lib=None):
    lib = lib or library
    row = lib.record(identifier)
    # User references belong to this library, never to a model-specific encoded cache.
    if row["kind"] == "voice" and lib is not library:
        row = copy.deepcopy(row)
    prompt, selected_model, mode = prompt_for(row, model, lib=lib)
    for entry in prompt.values():
        if entry["class_type"] == "TTSVoiceGallery":
            entry["inputs"]["language"] = language
    if format == "api":
        return prompt
    if format != "ui":
        raise LibraryError("格式应为 ui 或 api / Invalid workflow format")
    schemas = json.loads((BASE / "library" / "schemas.json").read_text("utf-8"))
    title = localized(row, "name", language)
    note = (f"{title}\n模型: {selected_model} / {mode}\n修改最左侧文案和参数后手动运行。切换示例请从图库重新打开完整配置。\n"
            "示例音频是生成结果，音色参考是克隆输入；不要混接。\n"
            "固定种子便于比较，不保证跨版本逐位一致；音色相似度与表达效果需要试听判断。\n\n"
            f"模型用法来源: {SOURCES[selected_model]}\n素材来源: {row.get('source', '')}\n参考编号: {identifier}\n"
            f"验证状态: {json.dumps(row.get('validation', {}), ensure_ascii=False)}")
    if row.get("voice_ids"):
        cast = [f"<|speaker:{slot.removeprefix('voice')}|> → {localized(lib.record(voice, 'voice'), 'name', language)} ({voice})" for slot, voice in row["voice_ids"].items()]
        note += "\n\n角色与参考音色：\n" + "\n".join(cast)
        if row.get("mode") == "dialogue":
            note += "\n每个角色使用独立的参考节点和编码节点。修改台词时保留 speaker 标签；可在左侧参考节点切换对应角色音色。"
    return graph_from_prompt(prompt, schemas, identifier=identifier, title=title, note=note)
