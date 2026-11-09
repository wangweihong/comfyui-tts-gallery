"""Curated Drama3 control recipes. Directions are model prompts, not guarantees."""
from copy import deepcopy
from generate_samples import TEXT, DRAMA, DL

FEMALE_ID = 'warm-female-zh'


def presets():
    rows = []
    def add(key, zh, en, category, cue, text=None, *, mode='tags', voice_ids=None, speakers='one take per line', note_zh='', note_en=''):
        generation = {**DRAMA, 'speakers': speakers}
        rows.append({
            'id': 'drama3-extra-' + key, 'kind': 'example', 'origin': 'builtin', 'model': 'drama3', 'mode': mode,
            'category': category, 'name_zh': zh, 'name_en': en, 'language': 'zh',
            'text': text if text is not None else cue + ' ' + TEXT, 'instruction': cue,
            'voice_ids': voice_ids or {'voice0': 'huola-dachu'},
            'parameters': {'loader': deepcopy(DL), 'codec_name': 'drama3_codec.safetensors', 'generation': generation, 'decode': {'shorten_long_pauses': True}},
            'description_zh': note_zh or '与自然克隆基线使用同一参考声线和采样参数，比较这段指令带来的表达变化。模型响应强弱请以试听为准。',
            'description_en': note_en or 'Same reference voice and sampling settings as the natural baseline. Listen to compare how this instruction changes delivery.',
            'tags': ['双人对话', '双声线'] if mode == 'dialogue' else [zh, '固定参考对照'],
        })
    for key, zh, en, cue in [
        ('serious', '语气 · 严肃认真', 'Tone · serious', '[with a serious, focused tone]'),
        ('sad', '语气 · 低落伤感', 'Tone · sadness', '[with a sad, disappointed tone]'),
        ('angry', '语气 · 克制愤怒', 'Tone · restrained anger', '[with restrained anger]'),
        ('surprised', '语气 · 惊讶意外', 'Tone · surprise', '[with genuine surprise]'),
        ('worried', '语气 · 紧张担心', 'Tone · worried', '[with a nervous, worried tone]'),
        ('confident', '语气 · 自信笃定', 'Tone · confident', '[with a confident, assured tone]'),
        ('doubtful', '语气 · 迟疑疑问', 'Tone · doubtful', '[with a hesitant, questioning tone]'),
        ('comforting', '语气 · 温柔安慰', 'Tone · comforting', '[with a gentle, comforting tone]'),
        ('impatient', '语气 · 不耐烦', 'Tone · impatient', '[with an impatient tone]'),
        ('sarcastic', '语气 · 轻微讽刺', 'Tone · mild sarcasm', '[with dry, mild sarcasm]'),
    ]:
        add(key, zh, en, 'emotion', cue)
    add('whisper-close', '耳语 · 近距离轻声', 'Whisper · close and soft', 'whisper', '[in a close, soft whisper]')
    add('whisper-tense', '耳语 · 紧张保密', 'Whisper · tense secrecy', 'whisper', '[in a tense, urgent whisper]', text='[in a tense, urgent whisper] 别出声，有人来了。先躲在这里，等我回来。')
    add('whisper-transition', '耳语 · 正常转耳语再恢复', 'Whisper · normal, whisper, normal', 'whisper', '<whisper>...</whisper>', text='你好，欢迎来到语音图库。<whisper>这个声音，只说给你听。</whisper>好了，我们继续吧。')
    add('whisper-director', '耳语 · 导演指令写法', 'Whisper · director instruction', 'whisper', 'Direction: whisper softly, as if sharing a secret.\nLine:', text='Direction: whisper softly, as if sharing a secret.\nLine: '+TEXT,
        note_zh='用 Direction / Line 分开导演指令与台词；指令应控制表达，不应被朗读。与点标签和局部耳语比较。')
    for key, zh, en, cue in [
        ('news', '表达 · 新闻播报', 'Delivery · newsreader', '[with a clear, formal newsreader delivery]'),
        ('storytelling', '表达 · 故事讲述', 'Delivery · storyteller', '[with an engaging, warm storytelling delivery]'),
        ('formal', '表达 · 正式致辞', 'Delivery · formal address', '[with a composed, formal delivery]'),
        ('playful', '表达 · 俏皮轻松', 'Delivery · playful', '[with a light, playful delivery]'),
        ('tired', '表达 · 疲惫困倦', 'Delivery · tired', '[with a tired, sleepy delivery]'),
    ]:
        add(key, zh, en, 'delivery', cue)
    add('fast', '语速 · 快速利落', 'Pace · brisk', 'pace', '[speak briskly and clearly]')
    add('pauses', '节奏 · 清楚停顿', 'Rhythm · clear pauses', 'pace', '[with deliberate pauses between sentences]')
    add('scoped-slow', '局部控制 · 放慢关键句', 'Scoped control · slow phrase', 'scope', '<slow>...</slow>', text='你好，欢迎来到语音图库。<slow>选好声音</slow>，我们就开始吧。')
    for key, zh, en, cue in [
        ('sigh', '发声 · 叹气', 'Vocal event · sigh', '[sighs]'),
        ('gasp', '发声 · 惊讶吸气', 'Vocal event · gasp', '[gasps]'),
        ('throat', '发声 · 清嗓子', 'Vocal event · clear throat', '[clears throat]'),
        ('cough', '发声 · 咳嗽', 'Vocal event · cough', '[coughs]'),
    ]:
        add(key, zh, en, 'event', cue)
    add('emphasis', '局部控制 · 强调关键词', 'Scoped control · emphasis', 'scope', '<emphasis>...</emphasis>', text='你好，欢迎来到语音图库。<emphasis>选好声音</emphasis>，我们就开始吧。')
    add('laugh-middle', '发声 · 句中笑声', 'Vocal event · mid-sentence laugh', 'event', '[laughs]', text='你好，欢迎来到语音图库。[laughs] 选好声音，我们就开始吧。')
    add('director-comfort', '组合 · 安慰与慢速', 'Combined · comforting and slow', 'combination', 'Direction: gentle, reassuring and slow.\nLine:', text='Direction: gentle, reassuring and slow.\nLine: 没关系，我们慢慢来。先深呼吸，一切都会好起来的。')
    cast = {'voice0': 'huola-dachu', 'voice1': FEMALE_ID}
    dialogues = [
        ('dialogue-natural', '双人对话 · 日常问答', 'Dialogue · everyday Q&A', '<|speaker:N|>',
         '<|speaker:0|> 你好，今天想试试什么声音？\n<|speaker:1|> 我想找一种温柔又自然的声音。\n<|speaker:0|> 好，我们先听一段，再决定。\n<|speaker:1|> 就这么办，开始吧。', 'one take per line'),
        ('dialogue-reunion', '双人对话 · 兴奋重逢', 'Dialogue · excited reunion', '<|speaker:N|> + emotional prefixes',
         '<|speaker:0|> [with happy surprise] 真的是你！好久不见！\n<|speaker:1|> [with warm excitement] 我回来了，没想到你还在这里。\n<|speaker:0|> 快进来，我们慢慢聊。\n<|speaker:1|> 好，今天有好多故事想告诉你。', 'one take per line'),
        ('dialogue-secret', '双人对话 · 低声秘密', 'Dialogue · whispered secret', '<|speaker:N|> + [whispers]',
         '<|speaker:0|> [whispers] 先别开灯，礼物藏在桌子下面。\n<|speaker:1|> [whispers] 我看到了，等她进来再拿出来。\n<|speaker:0|> [whispers] 好，听到我的信号再行动。\n<|speaker:1|> [whispers] 明白，我准备好了。', 'one take per line'),
        ('dialogue-reconcile', '双人对话 · 分歧与和解', 'Dialogue · disagreement and repair', '<|speaker:N|> + changing emotions',
         '<|speaker:0|> [with restrained frustration] 你怎么没有提前告诉我？\n<|speaker:1|> [with an apologetic tone] 对不起，我本来想给你一个惊喜。\n<|speaker:0|> [with a softer tone] 好吧，下次我们一起商量。\n<|speaker:1|> [with relief] 一定，下次不会了。', 'one take per line'),
        ('dialogue-interview', '双人对话 · 主持人访谈', 'Dialogue · interview', '<|speaker:N|> + role-specific delivery',
         '<|speaker:0|> [with a clear hosting tone] 欢迎来到今天的访谈。你最喜欢这份工作的哪一点？\n<|speaker:1|> [with a thoughtful tone] 我喜欢把复杂的问题解释清楚，帮助别人迈出第一步。\n<|speaker:0|> [with warm interest] 很棒，有什么建议想送给刚开始的朋友？\n<|speaker:1|> [with an encouraging tone] 别怕慢，先试一次，再一点点改进。', 'one take per line'),
        ('dialogue-together', '双人对话 · 整段联合生成', 'Dialogue · together mode', '<|speaker:N|> / speakers=together',
         '<|speaker:0|> 准备好了吗？\n<|speaker:1|> 准备好了，我们从哪里开始？\n<|speaker:0|> 先试听，再选择你喜欢的音色。\n<|speaker:1|> 好，我来试试。', 'together'),
    ]
    for key, zh, en, cue, text, strategy in dialogues:
        add(key, zh, en, 'dialogue', cue, text, mode='dialogue', voice_ids=deepcopy(cast), speakers=strategy,
            note_zh='角色0：火辣大厨；角色1：温暖女声。两份不同的合成参考样音分别编码，按 speaker 标签分配台词。'+('整段联合生成，适合比较对话连贯性；角色保持需试听确认。' if strategy=='together' else '每句独立生成后按脚本顺序合并，减少角色串音。'),
            note_en='Speaker 0: Spicy Chef; speaker 1: Warm Female. Two different synthetic reference recordings are encoded and mapped to their speaker slots. '+('The whole dialogue is generated together; listen to check voice identity.' if strategy=='together' else 'Lines are generated separately and assembled in script order.'))
    return rows
