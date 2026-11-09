#!/usr/bin/env python3
"""Export shared model/mode workflow entry points, without importing ComfyUI."""
import importlib
import json
import sys
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
package=types.ModuleType('tts_export');package.__path__=[str(ROOT)];sys.modules['tts_export']=package
catalog=importlib.import_module('tts_export.catalog'); workflows=importlib.import_module('tts_export.workflows')
# Built-in exports must not depend on a running ComfyUI or machine-specific user paths.
catalog.library._user=ROOT/'.generation'/'export-user'
sys.path.insert(0,str(ROOT/'scripts'))
from drama3_presets import presets
recipes={row['id']:row for row in presets()}
class ExportLibrary:
 def record(self,identifier,kind=None):
  return recipes[identifier] if identifier in recipes else catalog.library.record(identifier,kind)
export_library=ExportLibrary()
entries=[
 ('breeze_design','breeze-design-zh-female',None),
 ('breeze_clone','huola-dachu','breeze'),
 ('breeze_direction','breeze-chef-happy',None),
 ('drama3_clone','huola-dachu','drama3'),
 ('drama3_tags','drama3-chef-scoped',None),
 ('drama3_dialogue','drama3-extra-dialogue-natural',None),
]
for name,identifier,model in entries:
 for fmt,suffix in [('ui','.json'),('api','.api.json')]:
  graph=workflows.export(identifier,model,fmt,lib=export_library)
  (ROOT/'example_workflows'/(name+suffix)).write_text(json.dumps(graph,ensure_ascii=False,indent=2))
print(f'Exported {len(entries)} UI and {len(entries)} API workflow templates')
