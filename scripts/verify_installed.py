#!/usr/bin/env python3
"""Exercise the installed gallery node in both complete cloning templates."""
import json
import time
from generate_samples import api, ROOT


def main():
 for model in ['breeze','drama3']:
  prompt=api(f'/tts_gallery/workflow/huola-dachu?model={model}&format=api')
  prompt['1']['inputs']['value']='我是火辣大厨。这一次，我们直接从图库节点读取参考声音，让新的文字开口说话。'
  prompt['30']['inputs']['filename_prefix']=f"audio/{'breeze-tts-2' if model=='breeze' else 'drama3'}/tts-gallery/installed-clone-test"
  state_file=ROOT/'.generation'/f'installed-{model}.json'
  if state_file.exists():
   state=json.loads(state_file.read_text())
   if state.get('status')=='completed':print('reuse',model);continue
  else:
   state={'prompt':prompt,'prompt_id':api('/prompt',{'prompt':prompt,'client_id':'tts-gallery-installed-validation'})['prompt_id']}
   state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2))
  deadline=time.monotonic()+1800
  while time.monotonic()<deadline:
   history=api('/history/'+state['prompt_id']).get(state['prompt_id'])
   if history:
    state['history']=history;state['status']='completed' if history['status']['status_str']=='success' else 'error'
    state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    if state['status']=='error':raise RuntimeError(str(history['status'])[:2000])
    print('Installed node clone passed:',model,history['outputs']['30']['audio'],flush=True);break
   time.sleep(3)
  else:raise TimeoutError('Resume this script to continue waiting')

if __name__=='__main__':main()
