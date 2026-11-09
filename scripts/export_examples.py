#!/usr/bin/env python3
"""Export the five shared workflow entry points, without importing ComfyUI."""
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
for name,identifier,model in [
 ('breeze_design','breeze-design-zh-female',None),
 ('breeze_clone','huola-dachu','breeze'),
 ('breeze_direction','breeze-chef-happy',None),
 ('drama3_clone','huola-dachu','drama3'),
 ('drama3_tags','drama3-chef-scoped',None),
]:
 for fmt,suffix in [('ui','.json'),('api','.api.json')]:
  graph=workflows.export(identifier,model,fmt)
  (ROOT/'example_workflows'/(name+suffix)).write_text(json.dumps(graph,ensure_ascii=False,indent=2))
print('Exported 5 UI and 5 API workflow templates')
