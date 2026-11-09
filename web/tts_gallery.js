import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { local, normalizeLanguage, validMessage, words } from './core.mjs';

let dialog, frame, channel, selectedNode;
async function catalog() {
  const response = await fetch(api.apiURL('/tts_gallery/catalog'), { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()).records;
}
async function openWorkflow(id, model, language) {
  const q = new URLSearchParams({ lang: language }); if (model) q.set('model', model);
  const response = await fetch(api.apiURL(`/tts_gallery/workflow/${encodeURIComponent(id)}?${q}`));
  const graph = await response.json(); if (!response.ok) throw new Error(graph.error || `HTTP ${response.status}`);
  // A unique name makes ComfyUI's workflow manager open a separate tab and retain the current graph.
  const name = `TTS Gallery - ${graph.extra.tts_gallery.name} - ${new Date().toISOString().slice(11, 23).replaceAll(':', '-')}`;
  closeGallery();
  const result = await app.loadGraphData(graph, true, true, name, { openSource: 'file_button' });
  if (result === false) throw new Error('ComfyUI could not load the workflow');
}
function closeGallery() {
  frame?.contentWindow.postMessage({ type: 'tts-gallery-stop', token: channel }, location.origin);
  window.removeEventListener('message', receive);
  dialog?.remove(); dialog = frame = selectedNode = channel = null;
}
async function receive(event) {
  if (!validMessage(event, frame?.contentWindow, location.origin, channel)) return;
  const data = event.data; const source = frame.contentWindow;
  try {
    if (data.type === 'tts-gallery-language' && selectedNode) {
      const widget = selectedNode.widgets.find(w => w.name === 'language'); widget.value = normalizeLanguage(data.language); selectedNode.ttsRefresh?.(); app.graph.change();
    } else if (data.type === 'tts-gallery-select' && selectedNode) {
      const kind = (selectedNode.comfyClass ?? selectedNode.type) === 'TTSVoiceGallery' ? 'voice' : 'example';
      const row = (await catalog()).find(row => row.id === data.id && row.kind === kind && row.available);
      if (!row || source !== frame?.contentWindow) return;
      const node = selectedNode; const id = node.widgets.find(w => w.name === 'reference_id'); id.value = row.id;
      node.widgets.find(w => w.name === 'language').value = normalizeLanguage(data.language);
      id.callback?.(row.id); node.ttsRefresh?.(); app.graph.change(); closeGallery();
    } else if (data.type === 'tts-gallery-workflow') {
      if (typeof data.id !== 'string' || data.model && !['breeze', 'drama3'].includes(data.model)) return;
      await openWorkflow(data.id, data.model, normalizeLanguage(data.language));
    }
  } catch (error) {
    if (frame?.contentWindow === source) source.postMessage({ type: 'tts-gallery-error', token: channel, error: error.message }, location.origin);
    else app.extensionManager.toast.add({ severity: 'error', summary: 'TTS Gallery', detail: error.message, life: 8000 });
  }
}
function browse(node = null) {
  closeGallery(); document.querySelectorAll('audio').forEach(audio => audio.pause()); selectedNode = node;
  const kind = node && (node.comfyClass ?? node.type) === 'TTSVoiceGallery' ? 'voice' : 'example';
  const language = normalizeLanguage(node?.widgets?.find(w => w.name === 'language')?.value || localStorage.getItem('tts-gallery-language'));
  channel = crypto.randomUUID();
  const q = new URLSearchParams({ kind, lang: language, token: channel }); if (node) q.set('target', kind);
  dialog = document.createElement('dialog'); dialog.style.cssText = 'width:96vw;height:94vh;max-width:1600px;max-height:96vh;border:1px solid #deddeb;border-radius:15px;padding:0;overflow:hidden;background:#f6f7fb;';
  const top = document.createElement('div'); top.style.cssText = 'height:40px;display:flex;justify-content:space-between;align-items:center;padding:0 18px;color:#666277;font:12px system-ui;background:white;border-bottom:1px solid #e5e7f0;';
  const title = document.createElement('span'); title.textContent = words[language].brand;
  const close = document.createElement('button'); close.textContent = '×'; close.ariaLabel = words[language].close; close.style.cssText = 'border:0;background:none;font-size:24px;cursor:pointer;color:#888;'; close.onclick = closeGallery;
  top.append(title, close); frame = document.createElement('iframe'); frame.src = api.apiURL('/tts_gallery/gallery?' + q); frame.title = words[language].brand;
  frame.style.cssText = 'width:100%;height:calc(100% - 40px);border:0;';
  dialog.append(top, frame); dialog.addEventListener('cancel', event => { event.preventDefault(); closeGallery(); });
  document.body.append(dialog); window.addEventListener('message', receive); dialog.showModal();
}
app.registerExtension({
  name: 'comfyui-tts-gallery.browser',
  actionBarButtons: [{ icon: 'pi pi-volume-up', label: '语音图库', tooltip: 'TTS Gallery · 语音示例与克隆参考', onClick: () => browse() }],
  async setup() {
    const params = new URLSearchParams(location.search); const id = params.get('tts_gallery_example');
    if (!id) return;
    const model = params.get('tts_gallery_model'); const lang = normalizeLanguage(params.get('tts_gallery_lang'));
    for (const key of ['tts_gallery_example', 'tts_gallery_model', 'tts_gallery_lang']) params.delete(key);
    history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
    // Wait for the initial workflow to finish restoring before opening the requested example.
    const open = async () => {
      try { await openWorkflow(id, model, lang); } catch (error) { app.extensionManager.toast.add({ severity: 'error', summary: 'TTS Gallery', detail: error.message, life: 8000 }); }
    };
    this.pendingOpen = open;
  },
  async afterLoadGraph() {
    const open = this.pendingOpen; if (!open) return; this.pendingOpen = null;
    setTimeout(open, 0);
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!['TTSExampleGallery', 'TTSVoiceGallery'].includes(nodeData.name)) return;
    const voice = nodeData.name === 'TTSVoiceGallery'; const kind = voice ? 'voice' : 'example';
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = created?.apply(this, arguments); const node = this;
      let removed = false, request = 0;
      const id = node.widgets.find(w => w.name === 'reference_id'); const language = node.widgets.find(w => w.name === 'language');
      const box = document.createElement('div'); box.style.cssText = 'display:flex;flex-direction:column;gap:13px;padding:16px;background:#f7f6fc;border-radius:10px;color:#4a435c;height:100%;box-sizing:border-box;font:12px system-ui;overflow:hidden;';
      const title = document.createElement('strong'); const status = document.createElement('span'); status.setAttribute('role', 'status'); status.style.cssText = 'font-size:11px;line-height:1.7;color:#9990a8;';
      const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.style.cssText = 'width:100%;min-height:40px;';
      const button = document.createElement('button'); button.style.cssText = 'background:#6256d9;color:white;padding:11px;border:0;border-radius:7px;cursor:pointer;margin-top:auto;'; button.onclick = () => browse(node);
      box.append(title, status, audio, button);
      audio.addEventListener('play', () => {
        document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); });
      });
      async function refresh() {
        const revision = ++request, value = id.value, lang = normalizeLanguage(language.value);
        title.textContent = value; status.textContent = words[lang].loading; button.textContent = words[lang][voice ? 'voices' : 'examples'];
        audio.pause(); audio.src = api.apiURL(`/tts_gallery/audio/${encodeURIComponent(value)}/preview`);
        try {
          const row = (await catalog()).find(row => row.id === value && row.kind === kind);
          if (removed || revision !== request) return;
          title.textContent = row ? local(row, 'name', lang) : value;
          status.textContent = row?.available ? local(row, 'description', lang) : words[lang].missing;
          audio.hidden = !row?.available;
        } catch (error) { if (!removed && revision === request) status.textContent = error.message; }
        node.setDirtyCanvas(true, true);
      }
      node.ttsRefresh = refresh;
      for (const widget of [id, language]) { const original = widget.callback; widget.callback = function () { original?.apply(this, arguments); refresh(); }; }
      node.addDOMWidget('tts_gallery_preview', 'html', box, { serialize: false, hideOnZoom: false, getMinHeight: () => 170, getMaxHeight: () => 250 });
      const configured = node.onConfigure; node.onConfigure = function () { configured?.apply(this, arguments); refresh(); };
      const onRemoved = node.onRemoved; node.onRemoved = function () { removed = true; request++; audio.pause(); audio.removeAttribute('src'); audio.load(); if (selectedNode === node) closeGallery(); onRemoved?.apply(this, arguments); };
      node.setSize([410, 330]); refresh(); return result;
    };
  },
});
