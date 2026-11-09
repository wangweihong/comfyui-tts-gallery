export const words = {
  zh: {
    brand: '语音图库', subtitle: 'TTS GALLERY', examples: '模型示例', voices: '音色参考',
    eyebrow: '先试听，再创作', hero: '找到你想要的声音。', intro: '把音色、表达指令与生成参数放在一起，让每一次选择都有声音可参考。',
    search: '搜索音色、关键词、描述…', model: '模型', mode: '用途', category: '控制类别', origin: '来源', language: '音频语言', tag: '声音标签', all: '全部',
    count: '条参考', builtin: '内置', user: '自定义', design: '声音设计', clone: '声音克隆', direction: '表达控制', tags: '文本标签', generate: '生成示例',
    voice: '音色', emotion: '情绪', pace: '语速', volume: '音量', delivery: '表达方式', event: '非语言发声', combination: '组合控制', scope: '局部控制', content: '文本内容', whisper: '耳语', dialogue: '双人对话', cast: '角色与参考音色',
    play: '试听', pause: '暂停', details: '查看详情', import: '导入音色', empty: '没有找到匹配的声音', reset: '重置筛选',
    text: '示例文案', transcript: '参考音频逐字稿', instruction: '原始指令 / 标签', parameters: '实际生成参数', source: '来源', validation: '验证状态',
    use: '使用此参考 → ComfyUI', workflow: '打开示例工作流', download: '下载工作流 JSON', original: '下载原始音频', copy: '复制', copied: '已复制', close: '关闭',
    edit: '编辑', delete: '删除', save: '保存', cancel: '取消', file: '参考音频', nameZh: '中文名称', nameEn: '英文名称（可选）', description: '声音描述',
    tagsLabel: '标签（逗号分隔）', help: 'WAV / FLAC / MP3 · 最长 60 秒 · 最大 25 MiB。请使用干净人声，并填写覆盖整段音频的准确逐字稿。',
    deleteConfirm: '删除这条自定义音色及其音频？已引用此编号的工作流将无法再读取它。', saved: '已保存音色', deleted: '已删除音色', missing: '音频缺失，无法使用',
    disconnected: '从 ComfyUI 节点打开图库，才能把选择写回该节点。', newTab: '工作流会在新的标签页打开，不会自动运行。',
    loading: '正在加载声音…', choose: '选择一条声音开始试听', reviewed: '已复核', unreviewed: '未做人工听感验收', passed: '执行成功',
    audioHint: '试听生成结果；克隆输入请到“音色参考”。', voiceHint: '原始参考音频和逐字稿一起复用。', error: '操作失败', exporting: '正在打开工作流…',
    zh: '中文', en: '英文', other: '其他', preview: '试听', back: '返回图库', targetHint: '当前节点只接收此类型的参考',
  },
  en: {
    brand: 'TTS Gallery', subtitle: 'VOICE REFERENCE LIBRARY', examples: 'Model examples', voices: 'Voice references',
    eyebrow: 'LISTEN BEFORE YOU CREATE', hero: 'Find the voice you have in mind.', intro: 'Explore voices, delivery cues and the exact settings behind every sample, all in one place.',
    search: 'Search voices, cues, descriptions…', model: 'Model', mode: 'Purpose', category: 'Control', origin: 'Source', language: 'Audio language', tag: 'Voice tag', all: 'All',
    count: 'references', builtin: 'Built-in', user: 'Custom', design: 'Voice design', clone: 'Voice cloning', direction: 'Voice direction', tags: 'Inline tags', generate: 'Generation sample',
    voice: 'Voice', emotion: 'Emotion', pace: 'Pace', volume: 'Volume', delivery: 'Delivery', event: 'Vocal events', combination: 'Combined controls', scope: 'Scoped control', content: 'Text content', whisper: 'Whisper', dialogue: 'Two-speaker dialogue', cast: 'Speakers and voice references',
    play: 'Listen', pause: 'Pause', details: 'View details', import: 'Import voice', empty: 'No matching voices', reset: 'Reset filters',
    text: 'Example text', transcript: 'Exact reference transcript', instruction: 'Original instruction / tags', parameters: 'Actual generation settings', source: 'Source', validation: 'Validation',
    use: 'Use reference → ComfyUI', workflow: 'Open example workflow', download: 'Download workflow JSON', original: 'Download original audio', copy: 'Copy', copied: 'Copied', close: 'Close',
    edit: 'Edit', delete: 'Delete', save: 'Save', cancel: 'Cancel', file: 'Reference audio', nameZh: 'Name', nameEn: 'English name (optional)', description: 'Voice description',
    tagsLabel: 'Tags (comma separated)', help: 'WAV / FLAC / MP3 · up to 60 seconds · 25 MiB max. Use clean speech and an exact transcript covering the entire clip.',
    deleteConfirm: 'Delete this custom voice and its audio? Workflows referencing this ID will no longer be able to load it.', saved: 'Voice saved', deleted: 'Voice deleted', missing: 'Audio missing; unavailable',
    disconnected: 'Open the gallery from a ComfyUI node to send a selection back to that node.', newTab: 'Opens in a new workflow tab. Generation starts only when you run it.',
    loading: 'Loading voices…', choose: 'Choose a voice to start listening', reviewed: 'Reviewed', unreviewed: 'Not human-auditioned', passed: 'Execution passed',
    audioHint: 'These are generated samples. Use Voice references for cloning inputs.', voiceHint: 'Reuse the original reference audio together with its exact transcript.', error: 'Operation failed', exporting: 'Opening workflow…',
    zh: 'Chinese', en: 'English', other: 'Other', preview: 'Listen', back: 'Back to gallery', targetHint: 'This node accepts references of this type only',
  },
};
export const normalizeLanguage = value => value === 'en' ? 'en' : 'zh';
export const local = (row, key, lang) => row[`${key}_${lang}`] || row[`${key}_zh`] || row[`${key}_en`] || '';
export function matches(row, filters) {
  if (row.kind !== filters.kind) return false;
  for (const key of ['model', 'mode', 'category', 'origin', 'language']) {
    if (filters[key] && row[key] !== filters[key]) return false;
  }
  if (filters.tag && !row.tags?.includes(filters.tag)) return false;
  const hay = JSON.stringify(row).toLocaleLowerCase();
  return (filters.q || '').trim().toLocaleLowerCase().split(/\s+/).every(word => hay.includes(word));
}
export function validMessage(event, source, origin, token) {
  return event.origin === origin && event.source === source && event.data?.token === token && typeof event.data?.type === 'string';
}
export function onePlayer(player, url, same) {
  if (same && !player.paused) { player.pause(); return; }
  if (!same) { player.pause(); player.src = url; }
  return player.play();
}
