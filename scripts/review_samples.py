#!/usr/bin/env python3
"""ASR assistance for developer QA only; never a gallery upload action."""
import json
import re
import time
from pathlib import Path
from generate_samples import api, ROOT


def normalized(text):
    text=re.sub(r'\[[^\]]*\]|<[^>]+>', '', text)
    return ''.join(c.lower() for c in text if c.isalnum())


def main():
    for path in sorted((ROOT/'.generation').glob('*-chef-*.json')):
        state=json.loads(path.read_text())
        if state.get('status')!='completed' or state.get('transcript_review'):continue
        file=state['output_file']; audio=(file.get('subfolder','')+'/'+file['filename']).lstrip('/')+' [output]'
        prompt={
          '1':{'class_type':'LoadAudio','inputs':{'audio':audio}},
          '2':{'class_type':'Qwen3ASRLoader','inputs':{'model_name':'qwen3_asr_0.6b_bf16.safetensors'}},
          '3':{'class_type':'Qwen3ASRTranscribe','inputs':{'model':['2',0],'audio':['1',0],'language':'Chinese','context':'语音图库','max_new_tokens':512}},
          '4':{'class_type':'PreviewAny','inputs':{'source':['3',0]}},
        }
        if not state.get('review_prompt_id'):
            state['review_prompt_id']=api('/prompt',{'prompt':prompt,'client_id':'tts-gallery-review'})['prompt_id']
            path.write_text(json.dumps(state,ensure_ascii=False,indent=2))
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            hist=api('/history/'+state['review_prompt_id']).get(state['review_prompt_id'])
            if hist:
                if hist['status']['status_str']!='success':raise RuntimeError(str(hist['status'])[:1600])
                recognized=' '.join(hist['outputs']['4']['text'])
                state['transcript_review']={'status':'asr_checked' if normalized(state['text'])==normalized(recognized) else 'mismatch', 'expected':state['text'],'recognized':recognized,'prompt_id':state['review_prompt_id'],'note':'ASR assistance only; not a human listening assessment.'}
                path.write_text(json.dumps(state,ensure_ascii=False,indent=2))
                print(state['id'],state['transcript_review']['status'],recognized,flush=True);break
            time.sleep(2)
        else:raise TimeoutError('Resume to continue waiting for the same ASR job')

if __name__=='__main__': main()
