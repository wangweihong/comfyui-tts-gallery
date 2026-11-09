import importlib.util
import sys
import tempfile
import types
from pathlib import Path
from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
# Import the real plugin entry point without starting a second ComfyUI process.
server = types.ModuleType('server')
server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
sys.modules['server'] = server
folder_paths = types.ModuleType('folder_paths')
folder_paths.get_user_directory = lambda: str(ROOT / '.generation' / 'unused-user')
sys.modules['folder_paths'] = folder_paths
spec = importlib.util.spec_from_file_location('tts_gallery_test', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
from tts_gallery_test import catalog, nodes, workflows, routes, audio
