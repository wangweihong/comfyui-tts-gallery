"""Reference nodes do not load TTS models or enqueue generation."""
import json

from .audio import decode
from .catalog import language as validate_language, library, localized


def audio(identifier, kind):
    import torch
    samples, rate = decode(library.asset(identifier, kind=kind))
    return {"waveform": torch.from_numpy(samples.copy()).unsqueeze(0), "sample_rate": rate}


class ReferenceNode:
    KIND = "example"
    DEFAULT = "breeze-design-zh-female"
    FUNCTION = "load_reference"
    CATEGORY = "audio/TTS Gallery"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"reference_id": ("STRING", {"default": cls.DEFAULT}),
                             "language": (["zh", "en"], {"default": "zh"})}}

    @classmethod
    def VALIDATE_INPUTS(cls, reference_id, language="zh"):
        try:
            validate_language(language)
            library.asset(reference_id, kind=cls.KIND)
            decode(library.asset(reference_id, kind=cls.KIND))
            return True
        except (ValueError, OSError) as exc:
            return str(exc)

    @classmethod
    def IS_CHANGED(cls, reference_id, language="zh"):
        return library.fingerprint(reference_id, kind=cls.KIND) + ":" + validate_language(language)


class TTSExampleGallery(ReferenceNode):
    RETURN_TYPES = ("AUDIO", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("preview_audio", "example_text", "instruction", "parameters_json", "description")
    DESCRIPTION = "试听模型示例并查看原始文案、指令和参数；打开示例工作流应用完整配置。"

    def load_reference(self, reference_id, language="zh"):
        validate_language(language)
        row = library.record(reference_id, "example")
        return (audio(reference_id, "example"), row["text"], row.get("instruction", ""),
                json.dumps(row["parameters"], ensure_ascii=False, indent=2), localized(row, "description", language))


class TTSVoiceGallery(ReferenceNode):
    KIND = "voice"
    DEFAULT = "huola-dachu"
    RETURN_TYPES = ("AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("reference_audio", "reference_text", "description")
    DESCRIPTION = "输出已保存的克隆参考音频、准确逐字稿与音色描述。"

    def load_reference(self, reference_id, language="zh"):
        validate_language(language)
        row = library.record(reference_id, "voice")
        return audio(reference_id, "voice"), row["reference_text"], localized(row, "description", language)
