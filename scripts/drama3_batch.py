#!/usr/bin/env python3
"""Queue new Drama3 examples at the END, then import finished media automatically.

The watcher never interrupts, cancels, clears, reorders, or restarts a busy queue.
State lives in .generation/ so a restart can resume the same prompt IDs.
"""
import argparse
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import time
import types
import urllib.error
from pathlib import Path

from generate_samples import api, ROOT
from drama3_presets import presets

STATE = ROOT / '.generation'
MANIFEST = STATE / 'drama3-batch.json'
CONTAINER = 'comfyui-test-cu130-megapak-pt211'
SOURCE_OUTPUT = Path('/media/wwhvw/备份/comfyui/output')


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.replace(temporary, path)


def load_factory():
    package = types.ModuleType('tts_batch')
    package.__path__ = [str(ROOT)]
    sys.modules['tts_batch'] = package
    catalog = importlib.import_module('tts_batch.catalog')
    catalog.library._user = STATE / 'export-user'
    return importlib.import_module('tts_batch.workflows')


def spoken_text(text):
    text = re.sub(r'(?m)^Direction:[^\n]*(?:\n|$)', '', text)
    text = re.sub(r'(?m)^Line:\s*', '', text)
    return re.sub(r'\[[^\]]*\]|<[^>]+>', '', text)


def normalized(text):
    return ''.join(c.lower() for c in spoken_text(text) if c.isalnum())


def enqueue():
    STATE.mkdir(exist_ok=True)
    factory = load_factory()
    ids = []
    for recipe in presets():
        path = STATE / (recipe['id'] + '.json')
        if path.exists():
            old = json.loads(path.read_text())
            if old.get('preset') != recipe:
                raise RuntimeError('Recipe changed after submission; do not overwrite a queued job: ' + recipe['id'])
            if old.get('prompt_id'):
                ids.append(old['id'])
                continue
        prompt, _, _ = factory.prompt_for(recipe)
        # Validation uses the installed gallery node, including both real reference IDs.
        reply = api('/prompt', {'prompt': prompt, 'client_id': 'tts-gallery-drama3-expansion', 'front': False})
        state = {'id': recipe['id'], 'preset': recipe, 'prompt': prompt, 'prompt_id': reply['prompt_id'], 'queue_number': reply['number'], 'status': 'queued'}
        write(path, state)
        ids.append(recipe['id'])
        print('queued at end', recipe['id'], reply['number'], flush=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest.update(stage='queued', ids=ids, total=len(ids), completed=0, errors=[], deployment='waiting_for_generation', updated_at=time.time())
    write(MANIFEST, manifest)
    return manifest


def refresh(state):
    history = api('/history/' + state['prompt_id']).get(state['prompt_id'])
    if not history:
        return False
    state['history'] = history
    if history['status']['status_str'] != 'success':
        state['status'] = 'error'
    else:
        state['output_file'] = history['outputs']['30']['audio'][0]
        state['status'] = 'completed'
    write(STATE / (state['id'] + '.json'), state)
    return True


def queue_review(state):
    output = state['output_file']
    audio = (output.get('subfolder', '') + '/' + output['filename']).lstrip('/') + ' [output]'
    prompt = {
        '1': {'class_type': 'LoadAudio', 'inputs': {'audio': audio}},
        '2': {'class_type': 'Qwen3ASRLoader', 'inputs': {'model_name': 'qwen3_asr_0.6b_bf16.safetensors'}},
        '3': {'class_type': 'Qwen3ASRTranscribe', 'inputs': {'model': ['2', 0], 'audio': ['1', 0], 'language': 'Chinese', 'context': '语音图库', 'max_new_tokens': 1500}},
        '4': {'class_type': 'PreviewAny', 'inputs': {'source': ['3', 0]}},
    }
    state['review_prompt_id'] = api('/prompt', {'prompt': prompt, 'client_id': 'tts-gallery-drama3-review', 'front': False})['prompt_id']
    write(STATE / (state['id'] + '.json'), state)


def refresh_review(state):
    history = api('/history/' + state['review_prompt_id']).get(state['review_prompt_id'])
    if not history:
        return False
    if history['status']['status_str'] == 'success':
        recognized = ' '.join(history['outputs']['4']['text'])
        review = {'status': 'asr_checked' if normalized(state['preset']['text']) == normalized(recognized) else 'mismatch',
                  'expected': spoken_text(state['preset']['text']), 'recognized': recognized, 'prompt_id': state['review_prompt_id'],
                  'note': 'ASR checks content only, not speaker identity, voice similarity, or keyword effectiveness.'}
    else:
        review = {'status': 'pending', 'error': 'ASR execution failed', 'prompt_id': state['review_prompt_id']}
    state['transcript_review'] = review
    write(STATE / (state['id'] + '.json'), state)
    return True


def install_catalog():
    args = [sys.executable, str(ROOT / 'scripts/build_catalog.py'), '--breeze-root', '/home/wwhvw/文档/ChatGPT/生图/tts/breeze/bree',
            '--chef-root', '/home/wwhvw/.codex/skills/hyperframes-breeze-video/assets/voices/huola-dachu', '--output-root', str(SOURCE_OUTPUT)]
    subprocess.run(args, check=True)
    data = json.loads((ROOT / 'library/catalog.json').read_text())['records']
    count = sum(row['kind'] == 'example' for row in data)
    voices = sum(row['kind'] == 'voice' for row in data)
    expansion = sum(row['id'].startswith('drama3-extra-') for row in data)
    readme_path = ROOT / 'README.md'
    readme = readme_path.read_text()
    readme = re.sub(r'\*\*\d+ 条可试听模型示例、\d+ 条可克隆音色参考\*\*', f'**{count} 条可试听模型示例、{voices} 条可克隆音色参考**', readme)
    status = f'**Drama3扩展已入库{expansion}/35条。** 详情保留真实生成参数和ASR辅助核对状态，人工听感仍待试听验收。'
    readme = re.sub(r'(?s)(<!-- drama3-expansion:start -->).*?(<!-- drama3-expansion:end -->)', lambda match: match[1]+'\n'+status+'\n'+match[2], readme)
    readme = readme.replace('| Drama3 扩展语气、耳语及双人对话 | 0/35，等待队列生成 |', f'| Drama3 扩展语气、耳语及双人对话 | {expansion}/35 |')
    readme_path.write_text(readme)
    detail_path = ROOT / 'docs/drama3-expansion.md'
    detail = detail_path.read_text()
    detail = re.sub(r'当前阶段：[^\n]+', f'当前阶段：已入库{expansion}/35条，图库共有{count}条模型示例、{voices}条音色参考。失败条目保留错误记录；听感仍待人工验收。', detail)
    detail_path.write_text(detail)
    expansion_path = ROOT / 'web/expansion.json'
    expansion_info = json.loads(expansion_path.read_text())
    expansion_info.update(status='complete' if expansion == 35 else 'complete_with_errors', completed=expansion, failed=35-expansion)
    write(expansion_path, expansion_info)
    # Copy only this plugin. User libraries and other custom_nodes are untouched.
    archive = subprocess.Popen(['tar', '-C', str(ROOT), '--exclude=.generation', '--exclude=__pycache__', '--exclude=.pytest_cache', '-cf', '-', '.'], stdout=subprocess.PIPE)
    try:
        subprocess.run(['docker', 'exec', '-i', CONTAINER, 'tar', '-xf', '-', '-C', '/root/ComfyUI/custom_nodes/comfyui-tts-gallery'], stdin=archive.stdout, check=True)
    finally:
        archive.stdout.close()
    if archive.wait():
        raise RuntimeError('Plugin archive copy failed')


def watch():
    manifest = json.loads(MANIFEST.read_text())
    manifest.update(pid=os.getpid(), stage='waiting_for_generation')
    write(MANIFEST, manifest)
    while True:
        states = [json.loads((STATE / (identifier + '.json')).read_text()) for identifier in manifest['ids']]
        for state in states:
            if state['status'] == 'queued':
                refresh(state)
        manifest.update(completed=sum(s['status'] == 'completed' for s in states), errors=[s['id'] for s in states if s['status'] == 'error'], updated_at=time.time())
        write(MANIFEST, manifest)
        if all(s['status'] in ('completed', 'error') for s in states):
            break
        time.sleep(45)
    manifest['stage'] = 'checking_transcripts'; write(MANIFEST, manifest)
    for state in states:
        if state['status'] == 'completed' and not state.get('review_prompt_id') and not state.get('transcript_review'):
            queue_review(state)
    while True:
        waiting = 0
        for state in states:
            if state['status'] != 'completed' or state.get('transcript_review'):
                continue
            if not refresh_review(state):
                waiting += 1
        manifest.update(reviewed=sum(bool(s.get('transcript_review')) for s in states), updated_at=time.time())
        write(MANIFEST, manifest)
        if not waiting:
            break
        time.sleep(45)
    # Templates require a Python reload. Wait for an idle queue; never interrupt an unrelated job.
    manifest.update(stage='waiting_for_idle_deploy', deployment='waiting_for_idle'); write(MANIFEST, manifest)
    while api('/prompt')['exec_info']['queue_remaining']:
        time.sleep(45)
    install_catalog()
    if api('/prompt')['exec_info']['queue_remaining'] == 0:
        subprocess.run(['docker', 'restart', CONTAINER], check=True)
        manifest['deployment'] = 'installed_and_restarted'
    else:
        # New work arrived while files were copying: preserve it and defer reload.
        while api('/prompt')['exec_info']['queue_remaining']:
            time.sleep(45)
        subprocess.run(['docker', 'restart', CONTAINER], check=True)
        manifest['deployment'] = 'installed_and_restarted'
    manifest.update(stage='complete_with_errors' if manifest['errors'] else 'complete', updated_at=time.time())
    write(MANIFEST, manifest)
    print(json.dumps(manifest, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['enqueue', 'watch', 'status', 'start-watcher']); args = parser.parse_args()
    if args.action == 'enqueue':
        enqueue()
    elif args.action == 'watch':
        while True:
            try:
                watch(); break
            except (OSError, TimeoutError, urllib.error.URLError) as error:
                print('Temporary connection/file error; retrying without requeue:', error, flush=True)
                time.sleep(45)
            except Exception as error:
                manifest = json.loads(MANIFEST.read_text())
                manifest.update(stage='worker_error', error=str(error), updated_at=time.time())
                write(MANIFEST, manifest)
                raise
    elif args.action == 'status':
        print(MANIFEST.read_text() if MANIFEST.exists() else 'Not submitted')
    else:
        manifest = json.loads(MANIFEST.read_text())
        pid = manifest.get('pid')
        if pid:
            try:
                command = Path(f'/proc/{pid}/cmdline').read_bytes()
                if b'drama3_batch.py' in command and b'watch' in command:
                    print('Watcher already active', pid); return
            except OSError:
                pass
        with (STATE / 'drama3-batch.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), 'watch'], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        manifest['pid'] = process.pid; write(MANIFEST, manifest); print('Watcher started', process.pid)


if __name__ == '__main__':
    main()
