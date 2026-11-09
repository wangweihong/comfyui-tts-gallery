from .nodes import TTSExampleGallery, TTSVoiceGallery
from .routes import register_routes

NODE_CLASS_MAPPINGS = {"TTSExampleGallery": TTSExampleGallery, "TTSVoiceGallery": TTSVoiceGallery}
NODE_DISPLAY_NAME_MAPPINGS = {"TTSExampleGallery": "TTS 模型示例", "TTSVoiceGallery": "TTS 音色参考"}
WEB_DIRECTORY = "./web"

from server import PromptServer
register_routes(PromptServer.instance.routes)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
