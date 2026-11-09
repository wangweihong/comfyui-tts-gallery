import { words, local, normalizeLanguage, matches, onePlayer } from './core.mjs';
const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const root = location.pathname.replace(/\/gallery\/?$/, '');
let lang = normalizeLanguage(params.get('lang') || localStorage.getItem('tts-gallery-language'));
const target = ['example', 'voice'].includes(params.get('target')) ? params.get('target') : null;
const embedded = window.parent !== window;
const token = params.get('token');
const filters = { kind: params.get('kind') === 'voice' || target === 'voice' ? 'voice' : 'example', q: '' };
let expansion = null;
const extensionRoot = root.replace(/\/tts_gallery$/, '') + '/extensions/comfyui-tts-gallery';
let records = [], selected = null, editing = null, playing = null, toastTimer;
const player = $('player');
const t = key => words[lang][key] || key;
const api = path => root + path;
const audioURL = (row, role = 'preview') => api(`/audio/${encodeURIComponent(row.id)}/${role}`) + `?v=${encodeURIComponent(row.sha256)}-${row.revision || 0}`;
function send(type, data = {}) { if (embedded) parent.postMessage({ type, token, ...data }, location.origin); }
function el(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
function button(text, cls, fn) { const node = el('button', cls, text); node.type = 'button'; node.onclick = fn; return node; }
function toast(message) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false; toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6000); }
async function request(path, options) {
  const response = await fetch(api(path), options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function applyLanguage() {
  document.documentElement.lang = lang;
  localStorage.setItem('tts-gallery-language', lang);
  document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-placeholder]').forEach(node => { node.placeholder = t(node.dataset.placeholder); node.setAttribute('aria-label', t(node.dataset.placeholder)); });
  document.querySelectorAll('[data-i18n-aria]').forEach(node => { node.setAttribute('aria-label', t(node.dataset.i18nAria)); });
  $('zh').classList.toggle('active', lang === 'zh'); $('en').classList.toggle('active', lang === 'en');
  $('playing-name').textContent = playing ? local(playing, 'name', lang) : t('choose');
  renderFilters(); renderCards();
  if (selected && $('detail').open) renderDetail(selected);
  send('tts-gallery-language', { language: lang });
}
function filterKeys() { return filters.kind === 'example' ? ['model', 'mode', 'category', 'language'] : ['origin', 'language', 'tag']; }
function labelValue(key, value) { if (key === 'model') return value === 'breeze' ? 'Breeze TTS 2' : 'Drama 3'; return t(value); }
function renderFilters() {
  $('filters').replaceChildren();
  for (const key of filterKeys()) {
    const label = el('label', '', t(key)); const select = el('select'); select.setAttribute('aria-label', t(key));
    const rows = records.filter(row => row.kind === filters.kind);
    const values = [...new Set(rows.flatMap(row => key === 'tag' ? row.tags || [] : row[key] ? [row[key]] : []))];
    const all = el('option', '', t('all')); all.value = ''; select.append(all);
    for (const value of values) { const option = el('option', '', labelValue(key, value)); option.value = value; select.append(option); }
    select.value = filters[key] || '';
    select.onchange = () => { filters[key] = select.value; renderCards(); };
    label.append(select); $('filters').append(label);
  }
}
function wave(row) {
  const box = el('div', 'wave'); box.setAttribute('aria-hidden', 'true');
  for (const value of row.waveform || []) { const bar = el('i'); bar.style.height = `${Math.max(3, Math.min(100, value * 100))}%`; box.append(bar); }
  return box;
}
function renderExpansion() {
  const box = $('expansion-status'); box.replaceChildren();
  box.hidden = !expansion || expansion.status === 'complete' || filters.kind !== 'example' || filters.model && filters.model !== 'drama3';
  if (box.hidden) return;
  const queued = expansion.status === 'queued';
  const text = lang === 'zh' ? (queued ? `Drama3 新增 ${expansion.total} 条扩展已排在现有任务之后，尚未入库试听。` : `Drama3 已新增 ${expansion.completed} 条，${expansion.failed} 条生成失败，未用其他音频替代。`) : (queued ? `${expansion.total} new Drama3 examples are queued after the existing jobs. Their audio is not available yet.` : `${expansion.completed} Drama3 examples added; ${expansion.failed} generations failed. No substitute audio is used.`);
  box.append(el('p', '', text));
  const details = el('details'); details.append(el('summary', '', lang === 'zh' ? '查看扩展示例清单' : 'See the expansion list'));
  const list = el('ul'); for (const row of expansion.recipes) list.append(el('li', '', local(row, 'name', lang)));
  details.append(list); box.append(details);
  const link = el('a', '', lang === 'zh' ? '下载双人对话工作流（可直接导入使用） ↗' : 'Download the two-speaker workflow (ready to import) ↗');
  link.href = extensionRoot + '/templates/drama3_dialogue.json'; link.download = 'drama3_dialogue.json'; box.append(link);
}
function renderCards() {
  renderExpansion();
  const rows = records.filter(row => matches(row, filters));
  $('examples').setAttribute('aria-selected', String(filters.kind === 'example'));
  $('voices').setAttribute('aria-selected', String(filters.kind === 'voice'));
  $('cards').setAttribute('aria-label', t(filters.kind === 'example' ? 'examples' : 'voices'));
  $('hint').textContent = t(filters.kind === 'example' ? 'audioHint' : 'voiceHint') + (target ? ' ' + t('targetHint') : '');
  $('summary').replaceChildren(el('strong', '', String(rows.length)), document.createTextNode(t('count')));
  $('cards').replaceChildren();
  $('empty').hidden = rows.length !== 0; $('empty').textContent = t('empty');
  for (const row of rows) {
    const card = el('article', 'card'); card.dataset.id = row.id;
    card.classList.toggle('playing', row.id === playing?.id && !player.paused);
    const top = el('div', 'card-top'); top.append(el('span', `model-badge ${row.model || ''}`, row.kind === 'voice' ? t(row.origin) + ' / VOICE' : labelValue('model', row.model).toUpperCase()), el('span', 'duration', `${row.duration.toFixed(2)}s`));
    const title = el('h2', '', local(row, 'name', lang)); title.title = title.textContent;
    const desc = el('p', 'card-description', local(row, 'description', lang));
    const tags = el('div', 'card-tags'); for (const tag of [row.category ? t(row.category) : t(row.language), ...(row.tags || []).slice(0, 2)]) tags.append(el('span', 'chip', tag));
    const foot = el('div', 'card-footer');
    const play = button(`${row.id === playing?.id && !player.paused ? 'Ⅱ' : '▶'}  ${t(row.id === playing?.id && !player.paused ? 'pause' : 'play')}`, 'play', () => playRecord(row));
    play.disabled = row.available === false; if (play.disabled) play.title = t('missing');
    foot.append(play, button(t('details') + ' ↗', 'detail-link', () => openDetail(row)));
    card.append(top, title, desc, wave(row), tags, foot); $('cards').append(card);
  }
}
async function playRecord(row) {
  const same = playing?.id === row.id;
  playing = row;
  $('playing-name').textContent = local(row, 'name', lang);
  $('playing-meta').textContent = `${row.model ? labelValue('model', row.model) : t('voices')} / ${row.duration.toFixed(2)}s`;
  $('playing-details').disabled = false;
  try { await onePlayer(player, audioURL(row), same); } catch (error) { toast(`${t('error')}: ${error.message}`); }
  renderCards();
}
function section(name, value, code = false) {
  const box = el('section', 'field'); const header = el('div', 'field-header'); header.append(el('h3', '', t(name)));
  header.append(button(t('copy'), 'text-button', async event => {
    const copyButton = event.currentTarget;
    try { await navigator.clipboard.writeText(value); copyButton.textContent = t('copied'); } catch (error) { toast(error.message); }
  }));
  box.append(header, el('pre', code ? 'code' : '', value || '—')); return box;
}
function workflowURL(row, model) {
  const q = new URLSearchParams({ lang, download: '1' }); if (model) q.set('model', model);
  return api(`/workflow/${encodeURIComponent(row.id)}?${q}`);
}
function openWorkflow(row, model) {
  if (embedded) { send('tts-gallery-workflow', { id: row.id, model, language: lang }); return; }
  const url = new URL(root.replace(/\/tts_gallery$/, '/') || '/', location.origin);
  url.searchParams.set('tts_gallery_example', row.id); url.searchParams.set('tts_gallery_lang', lang);
  if (model) url.searchParams.set('tts_gallery_model', model);
  window.open(url.href, '_blank', 'noopener,noreferrer');
}
function renderDetail(row) {
  const content = $('detail-body'); content.replaceChildren();
  const head = el('div', 'detail-heading'); const badges = el('div', 'card-tags');
  for (const value of [row.model ? labelValue('model', row.model) : t('voices'), t(row.language), `${row.duration.toFixed(2)}s`, `${row.sample_rate / 1000} kHz`]) badges.append(el('span', 'chip', value));
  head.append(badges, el('h2', '', local(row, 'name', lang)), el('p', '', local(row, 'description', lang)));
  const actions = el('div', 'detail-actions'); actions.append(button('▶ ' + t('play'), 'secondary', () => playRecord(row)));
  const use = button(t('use'), 'primary', () => send('tts-gallery-select', { id: row.id, kind: row.kind, language: lang }));
  use.disabled = !embedded || !target || target !== row.kind || row.available === false;
  use.title = !embedded || !target ? t('disconnected') : ''; actions.append(use);
  for (const model of row.kind === 'voice' ? ['breeze', 'drama3'] : [null]) {
    const btn = button(t('workflow') + (model ? ` · ${labelValue('model', model)}` : ''), 'secondary', () => openWorkflow(row, model));
    btn.disabled = row.available === false; actions.append(btn);
  }
  const grid = el('div', 'detail-grid'); const left = el('div'); const right = el('div');
  left.append(section(row.kind === 'voice' ? 'transcript' : 'text', row.reference_text || row.text));
  if (row.voice_ids) {
    const cast = Object.entries(row.voice_ids).map(([slot, id]) => { const voice = records.find(item => item.id === id); return `<|speaker:${slot.replace('voice', '')}|> → ${voice ? local(voice, 'name', lang) : id} (${id})`; }).join('\n');
    left.append(section('cast', cast));
  }
  if (row.kind === 'example') { left.append(section('instruction', row.instruction || '')); right.append(section('parameters', JSON.stringify(row.parameters, null, 2), true)); }
  const provenance = el('section', 'field'); provenance.append(el('h3', '', t('source')), el('pre', '', row.source || '—'));
  const validation = el('div', 'validation'); validation.append(el('h3', '', t('validation')));
  const labels = { execution: lang === 'zh' ? '执行' : 'Execution', transcript: lang === 'zh' ? '文字完整性' : 'Transcript', listening: lang === 'zh' ? '听感' : 'Listening' };
  const statuses = { success: t('passed'), decoded: lang === 'zh' ? '解码通过' : 'Decoded', unreviewed: t('unreviewed'), user_supplied: lang === 'zh' ? '用户提供，待核对' : 'User supplied; verify', source_transcript: lang === 'zh' ? '随原参考保存' : 'Original reference transcript', asr_checked: lang === 'zh' ? 'ASR辅助核对' : 'ASR checked', pending: lang === 'zh' ? '待核对' : 'Pending', mismatch: lang === 'zh' ? 'ASR存在差异，请试听核对' : 'ASR mismatch; listen to verify' };
  for (const key of Object.keys(labels)) validation.append(el('p', '', `${labels[key]}: ${statuses[row.validation?.[key]] || row.validation?.[key] || '—'}`));
  validation.append(el('code', '', row.id)); right.append(provenance, validation);
  const minor = el('div', 'minor-actions');
  const original = el('a', '', t('original')); original.href = audioURL(row, 'original'); original.download = row.original_filename || row.id; minor.append(original);
  for (const model of row.kind === 'voice' ? ['breeze', 'drama3'] : [null]) { const download = el('a', '', t('download') + (model ? ` · ${labelValue('model', model)}` : '')); download.href = workflowURL(row, model); download.download = `${row.id}.json`; minor.append(download); }
  if (row.origin === 'user') {
    minor.append(button(t('edit'), '', () => editVoice(row)));
    minor.append(button(t('delete'), 'danger', async () => {
      if (!confirm(t('deleteConfirm'))) return;
      try {
        await request(`/voices/${row.id}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ revision: row.revision }) });
        if (playing?.id === row.id) { player.pause(); player.removeAttribute('src'); player.load(); playing = null; $('playing-name').textContent = t('choose'); $('playing-details').disabled = true; }
        $('detail').close(); await refresh(); toast(t('deleted'));
      } catch (error) { toast(error.message); }
    }));
  }
  left.append(minor); grid.append(left, right); content.append(head, actions, grid, el('p', 'hint', t('newTab')));
  content.lastChild.style.padding = '0 28px 18px';
}
function openDetail(row) { selected = row; renderDetail(row); if (!$('detail').open) $('detail').showModal(); }
function editVoice(row = null) {
  editing = row; $('voice-form').reset(); $('form-error').textContent = ''; $('file-field').hidden = !!row;
  $('audio-file').required = !row; $('editor-title').textContent = t(row ? 'edit' : 'import');
  if (row) for (const key of ['name_zh', 'name_en', 'reference_text', 'description_zh', 'language', 'tags']) $('voice-form').elements[key].value = key === 'tags' ? (row.tags || []).join(', ') : row[key] || '';
  $('editor').showModal();
}
$('voice-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true; $('form-error').textContent = '';
  const values = Object.fromEntries(new FormData($('voice-form'))); values.tags = values.tags.split(/[,，]/).map(v => v.trim()).filter(Boolean);
  if (editing) { values.revision = editing.revision; values.description_en = editing.description_en || ''; }
  try {
    let result;
    if (editing) result = await request(`/voices/${editing.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
    else {
      const file = $('audio-file').files[0];
      if (!file) throw new Error(t('file'));
      if (file.size > 25 * 1024 * 1024) throw new Error('25 MiB max');
      const form = new FormData(); form.append('audio', file); form.append('metadata', JSON.stringify(values));
      result = await request('/voices', { method: 'POST', body: form });
    }
    $('editor').close(); clearFilters('voice'); await refresh(); openDetail(result.record); toast(t('saved'));
  } catch (error) { $('form-error').textContent = error.message; } finally { $('save').disabled = false; }
};
function clearFilters(kind = filters.kind) { for (const key of Object.keys(filters)) delete filters[key]; Object.assign(filters, { kind, q: '' }); $('search').value = ''; }
async function refresh() { const result = await request('/catalog'); records = result.records; renderFilters(); renderCards(); }
$('import').onclick = () => editVoice();
$('examples').onclick = () => { clearFilters('example'); renderFilters(); renderCards(); };
$('voices').onclick = () => { clearFilters('voice'); renderFilters(); renderCards(); };
$('reset').onclick = () => { clearFilters(); renderFilters(); renderCards(); };
$('search').oninput = () => { filters.q = $('search').value; renderCards(); };
$('playing-details').onclick = () => { if (playing) openDetail(playing); };
for (const value of ['zh', 'en']) $(value).onclick = () => { lang = value; applyLanguage(); };
document.querySelectorAll('.close').forEach(node => { node.onclick = () => node.closest('dialog').close(); });
for (const event of ['play', 'pause', 'ended']) player.addEventListener(event, renderCards);
player.addEventListener('error', () => { if (playing) toast(t('missing')); });
window.addEventListener('message', event => {
  if (!embedded || event.source !== parent || event.origin !== location.origin || event.data?.token !== token) return;
  if (event.data.type === 'tts-gallery-error') toast(event.data.error);
});
document.addEventListener('keydown', event => { if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(event.target.tagName)) { event.preventDefault(); $('search').focus(); } });
window.addEventListener('pagehide', () => player.pause());
if (embedded) document.body.classList.add('embedded');
for (let i = 0; i < 49; i++) { const bar = el('i'); bar.style.height = `${12 + Math.sin(i * .72) ** 2 * 40 + Math.sin(i * .28) ** 2 * 24}px`; document.querySelector('.hero-wave').append(bar); }
applyLanguage(); $('empty').hidden = false; $('empty').textContent = t('loading');
try {
  try { const response = await fetch(extensionRoot + '/expansion.json', { cache: 'no-store' }); if (response.ok) expansion = await response.json(); } catch {}
  await refresh(); send('tts-gallery-ready'); } catch (error) { $('empty').hidden = false; $('empty').textContent = error.message; }
