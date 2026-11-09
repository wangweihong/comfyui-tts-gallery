#!/usr/bin/env python3
"""Rebuild bundled samples from recorded runs, preserving their real settings.

External paths are build-time inputs; the installed plugin never reads them.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
 'design_en_female': ('温暖女声 · 英文', 'Warm female · English'), 'design_en_male': ('低沉男声 · 英文', 'Deep male · English'),
 'design_lively_en': ('活泼女声 · 英文', 'Lively female · English'), 'design_lively_zh': ('活泼女声 · 中文', 'Lively female · Chinese'),
 'design_zh_female': ('温暖女声 · 中文', 'Warm female · Chinese'), 'design_zh_male': ('低沉男声 · 中文', 'Deep male · Chinese'),
 'text_abbreviation': ('英文缩写', 'English abbreviations'), 'text_mixed': ('中英混读', 'Mixed Chinese and English'),
 'text_multisentence': ('多句朗读', 'Multiple sentences'), 'text_numbers': ('日期、数字与金额', 'Dates, numbers and amounts'), 'text_punctuation': ('标点与对话', 'Punctuation and dialogue'),
}


def digest(p):
 return hashlib.sha256(p.read_bytes()).hexdigest()


def assets(source, identifier):
 target=ROOT/'library'/'audio'/(identifier+source.suffix.lower())
 if source.resolve()!=target.resolve(): shutil.copyfile(source,target)
 metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(target)]))
 stream=next(x for x in metadata['streams'] if x['codec_type']=='audio')
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-map','0:a:0','-ac','1','-ar','24000','-f','f32le','pipe:1'])
 pcm=np.frombuffer(raw,dtype='<f4')
 if not len(pcm) or not np.isfinite(pcm).all() or np.max(np.abs(pcm)) < 1e-4: raise ValueError('Invalid or silent sample: '+identifier)
 peaks=np.array([float(np.max(np.abs(x))) for x in np.array_split(pcm,48)])
 peaks=(peaks / max(float(peaks.max()),1e-6)).round(4).tolist()
 preview=ROOT/'library'/'audio'/(identifier+'.wav')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(target),'-map','0:a:0','-ac','1','-c:a','pcm_s16le',str(preview)],check=True)
 return {'audio':str(target.relative_to(ROOT/'library')),'preview':str(preview.relative_to(ROOT/'library')),'sha256':digest(target),
         'duration':round(len(pcm)/24000,5),'sample_rate':int(stream['sample_rate']),'channels':stream['channels'],'waveform':peaks}


def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--breeze-root',type=Path,required=True); ap.add_argument('--chef-root',type=Path,required=True); ap.add_argument('--output-root',type=Path,required=True); args=ap.parse_args()
 records=[]; inventory=[]; seen=set()
 voice=json.loads((args.chef_root/'voice.json').read_text())
 records.append({'id':'huola-dachu','kind':'voice','origin':'builtin','name_zh':'火辣大厨','name_en':'Spicy Chef', 'language':'zh',
   'description_zh':'清楚明亮、温暖亲切的成年男声，普通话标准，适合技术讲解。复用冻结样音，不重新设计声线。',
   'description_en':'A clear, bright and warm adult male Mandarin voice for technical narration. Reuse this frozen sample.',
   'reference_text':(args.chef_root/'transcript.txt').read_text().strip(),'tags':['成年男声','普通话','技术讲解'],
   'source':'User-owned synthetic voice, designed with Breeze TTS 2 on 2026-10-29; frozen reference SHA-256 '+voice['reference_sha256'],
   'validation':{'execution':'decoded','transcript':'source_transcript','listening':'unreviewed'},'design_provenance':voice['design_provenance'],
   **assets(args.chef_root/'reference.flac','huola-dachu')})
 results=json.loads((args.breeze_root/'all_results.json').read_text())
 quality=json.loads((args.breeze_root/'quality_review.json').read_text())
 reviews={r['source_case']:r for r in quality.get('asr_reviews',[])}
 for result in results:
  case=result.get('case',{}); prompt=case.get('prompt',{}); case_id=result['id']; category=result['category']
  status='excluded: diagnostic, performance, private reference or out of curated scope'
  generators=[v for v in prompt.values() if v['class_type']=='BreezeTTS2VoiceDesign']
  if category in ('design','vocal_event','text') and result['status']=='completed' and len(generators)==1 and len(result.get('audio',[]))==1:
   gen=generators[0]['inputs']; controls={k:v for k,v in gen.items() if k not in ('breeze_model','text','instruction')}
   fingerprint=json.dumps([gen['text'],gen['instruction'],controls],ensure_ascii=False,sort_keys=True)
   source=args.breeze_root/'audio'/result['audio'][0]['file']
   if fingerprint in seen:status='excluded: duplicate configuration'
   elif not source.is_file():status='excluded: audio missing'
   elif result['audio'][0]['duration']>60:status='excluded: over 60 seconds'
   else:
    seen.add(fingerprint); identifier='breeze-'+case_id.replace('_','-')
    if category=='vocal_event':
     language='zh' if '_zh_' in case_id else 'en'; n=int(case_id.rsplit('_',1)[1]); zh=['自然基线','笑声','咳嗽','清嗓子','叹气'][n]; en=['Natural baseline','Laugh','Cough','Clear throat','Sigh'][n]
     names=(zh+' · '+('中文' if language=='zh' else '英文'),en+' · '+('Chinese' if language=='zh' else 'English'))
    else:
     language='zh' if re.search('[\u4e00-\u9fff]',gen['text']) else 'en'; names=NAMES[case_id]
    loader=next(v['inputs'] for v in prompt.values() if v['class_type']=='BreezeTTS2LoadModel')
    rec={'id':identifier,'kind':'example','origin':'builtin','model':'breeze','mode':'design','category':{'design':'voice','vocal_event':'event','text':'content'}[category],
      'name_zh':names[0],'name_en':names[1],'language':language,'text':gen['text'],'instruction':gen['instruction'],
      'description_zh':gen['instruction'] if category=='design' else '已有本地实测示例。保留原始文案、指令及采样设置；效果请以试听为准。',
      'description_en':gen['instruction'] if language=='en' and category=='design' else 'Recorded local sample with its original text, instruction and settings. Listen to assess the effect.',
      'tags':['声音设计' if category=='design' else '原始语法','中文' if language=='zh' else 'English'],
      'parameters':{'loader':loader,'generation':controls},'source':'Local Breeze TTS 2 recorded test: '+case_id+'; https://huggingface.co/BreezeBlue/Breeze-TTS-2',
      'validation':{'execution':'success','transcript':'asr_checked' if reviews.get(case_id,{}).get('normalized_character_error_rate',1)==0 else 'pending','listening':'unreviewed'},
      'provenance':{'case_id':case_id,'prompt_id':result.get('prompt_id'),'source_audio_sha256':result['audio'][0]['sha256']},**assets(source,identifier)}
    if rec['sha256'] != result['audio'][0]['sha256']:raise ValueError('Source checksum mismatch: '+identifier)
    records.append(rec);status='included: '+identifier
  inventory.append({'source':'local-breeze','id':case_id,'category':category,'disposition':status})
 for file in sorted((ROOT/'.generation').glob('*-chef-*.json')):
  state=json.loads(file.read_text())
  if state.get('status')!='completed':continue
  identifier=state['id']; model=state['model']; output=state['output_file']; source=args.output_root/output.get('subfolder','')/output['filename']
  validation={'execution':'success','transcript':'pending','listening':'unreviewed'}
  if state.get('transcript_review'): validation['transcript']=state['transcript_review']['status']
  records.append({'id':identifier,'kind':'example','origin':'builtin','model':model,'mode':state['mode'],'category':state['category'],
    'name_zh':state['name_zh']+' · 火辣大厨','name_en':state['name_en']+' · Spicy Chef','language':'zh','voice_id':'huola-dachu',
    'text':state['text'],'instruction':state['instruction'],'parameters':state['parameters'],'tags':['火辣大厨','固定参考对照'],
    'description_zh':'使用同一份火辣大厨样音与固定采样设置。'+('自然克隆基线。' if state['mode']=='clone' else '控制语法：'+state['instruction'])+' 听感效果待验收。',
    'description_en':'Same frozen Spicy Chef reference and fixed sampling settings. '+('Natural cloning baseline.' if state['mode']=='clone' else 'Cue: '+state['instruction'])+' Listening assessment pending.',
    'source':'Generated locally for TTS Gallery; '+('https://huggingface.co/BreezeBlue/Breeze-TTS-2' if model=='breeze' else 'https://github.com/PedroMarinhoDev/ComfyUI-Drama3'),
    'validation':validation,'provenance':{'prompt_id':state['prompt_id'],'transcript_review':state.get('transcript_review')},**assets(source,identifier)})
  inventory.append({'source':'tts-gallery-generation','id':identifier,'disposition':'included'})
 for n in ['brian','lois','peter','stewie']:
  inventory.append({'source':'upstream-breeze','id':n+'.wav','disposition':'excluded: first voice-reference library contains Spicy Chef only'})
 inventory.append({'source':'upstream-drama3','disposition':'Installed source has no bundled audio; documented cue syntax used for new controlled samples'})
 # A second existing synthetic reference enables actual two-voice dialogue.
 female = next(r for r in records if r['id'] == 'breeze-design-zh-female')
 fields = ['audio','preview','sha256','duration','sample_rate','channels','waveform']
 records.append({'id':'warm-female-zh','kind':'voice','origin':'builtin','name_zh':'温暖女声','name_en':'Warm Female',
   'language':'zh','reference_text':female['text'],'description_zh':'已有Breeze声音设计生成的温暖成年女声，用作双人对话的角色1，与火辣大厨使用不同的原始样音。',
   'description_en':'An existing synthetic warm adult female voice, reused as speaker 1 in dialogue with a different recording from Spicy Chef.',
   'tags':['成年女声','普通话','双人对话'],'source':'Existing user-owned synthetic Breeze design: design_zh_female; reused without redesign.',
   'validation':{'execution':'decoded','transcript':'asr_checked','listening':'unreviewed'},**{k:female[k] for k in fields}})
 inventory.append({'source':'existing-synthetic-voice','id':'warm-female-zh','disposition':'included: distinct second reference for dialogue'})
 for file in sorted((ROOT/'.generation').glob('drama3-extra-*.json')):
  state=json.loads(file.read_text())
  if state.get('status')!='completed':continue
  preset=state['preset']; output=state['output_file']; source=args.output_root/output.get('subfolder','')/output['filename']
  validation={'execution':'success','transcript':state.get('transcript_review',{}).get('status','pending'),'listening':'unreviewed'}
  records.append({**preset,'source':'Generated locally for TTS Gallery; https://github.com/PedroMarinhoDev/ComfyUI-Drama3',
    'validation':validation,'provenance':{'prompt_id':state['prompt_id'],'transcript_review':state.get('transcript_review')},**assets(source,preset['id'])})
  inventory.append({'source':'tts-gallery-generation','id':preset['id'],'disposition':'included'})
 for row in records:
  if row['id'] in ('drama3-chef-whisper','drama3-chef-scoped'):row['category']='whisper'
 records.sort(key=lambda r:(r['kind']!='example',r.get('model')!='breeze',r['language']!='zh',r['category']!='voice' if 'category' in r else False,r['id']))
 (ROOT/'library'/'catalog.json').write_text(json.dumps({'version':1,'records':records},ensure_ascii=False,indent=2))
 (ROOT/'library'/'SOURCE.json').write_text(json.dumps({'version':1,'inventory':inventory,'scope':'Complete inventory of recorded local Breeze tests and installed upstream audio; curated voice-design, vocal-event and text examples, plus new Spicy Chef controls. No private voices imported.','counts':{'records':len(records),'examples':sum(r['kind']=='example' for r in records),'voices':sum(r['kind']=='voice' for r in records)}},ensure_ascii=False,indent=2))
 print('Built',len(records),'records; inventory',len(inventory),'items')


if __name__=='__main__': main()
