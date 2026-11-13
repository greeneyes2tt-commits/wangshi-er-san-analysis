import csv
import pandas as pd
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['SimHei'] # 解决图表中文显示问题（Mac用户可改为 'Arial Unicode MS'，Linux用户请安装中文字体）
matplotlib.rcParams['axes.unicode_minus'] = False # 解决负号显示问题

# ==========================================
# 配置区：使用其他作品时，只需修改以下内容
# ==========================================

# 1. 数据文件路径
CSV_FILE_PATH = 'data/往事二三_详细参数表_v3.csv'

# 2. 小节时长表（如果你只分析乐谱，不涉及速度变化，保持每小节4拍即可）
MEASURE_LENGTHS = {
    1: 3.0, 2: 4.5, 3: 3.0, 4: 2.5, 5: 2.5, 6: 2.5, 7: 4.0, 8: 4.5, 9: 3.0, 10: 2.0,
    11: 2.5, 12: 3.5, 13: 2.5, 14: 2.5, 15: 4.0, 16: 3.0, 17: 2.0, 18: 4.0, 19: 5.0, 20: 2.5,
    21: 4.0, 22: 3.0, 23: 3.5, 24: 5.5, 25: 5.5, 26: 3.0, 27: 4.0, 28: 5.5, 29: 4.0, 30: 4.0, 31: 4.0
}

# 3. 歌词本调字典（1=阴平, 2=阳平, 3=上声, 4=去声, 0=轻声）
# 迁移时：替换为你所研究作品的汉字及声调
BASE_TONE_DICT = {
    '一':1, '只':1, '打':3, '翻':1, '的':0, '酒':3, '盅':1,
    '石':2, '路':4, '在':4, '月':4, '光':1, '下':4, '浮':2, '动':4,
    '青':1, '草':3, '压':1, '倒':3, '地':4, '方':1,
    '遗':2, '落':4, '枝':1, '映':4, '山':1, '红':2,
    '桉':1, '树':4, '林':2, '旋':2, '转':3, '起':3, '来':0,
    '繁':2, '星':1, '拼':1, '成':2, '了':0, '万':4, '花':1, '筒':3,
    '生':1, '锈':4, '铁':3, '锚':2, '上':4,
    '眼':3, '睛':1, '晕':1, '眩':4, '天':1, '空':1,
    '竖':4, '书':1, '本':3, '挡':3, '住':4, '烛':2,
    '手':3, '指':3, '轻':1, '衔':2, '口':3, '中':1,
    '脆':4, '薄':2, '寂':4, '静':4, '里':3,
    '做':4, '半':4, '明':2, '昧':4, '梦':4
}

# 4. 乐句划分规则
# 短语结束字（遇到这些字，或字后有长休止，视为乐句结束）
PHRASE_END_CHARS = set('盅动方红来筒上空光中里梦')
# 短语起始字（遇到这些字，视为乐句起始，不计入跨字过渡）
PHRASE_START_CHARS = set('石青遗桉繁生眼竖手脆做')

# 5. 绘图分段配置（小节号, 段落名称）
SECTIONS = [(5, '第一段'), (17, '第二段'), (24, '第三段')]
TICK_MEASURES = [5, 10, 15, 20, 25, 30]

# ==========================================
# 核心算法区：以下代码通用，无需修改
# ==========================================

# ================= 1. 重建时间轴 =================
measure_lengths = MEASURE_LENGTHS
measure_start_beat = {}
current_start = 0.0
for m in range(1, 32):
    measure_start_beat[m] = current_start
    current_start += measure_lengths.get(m, 4.0)

# ================= 2. 本调字典 =================
def wudu_to_semitone(v):
    return {1: 0, 2: 2, 3: 4, 4: 5, 5: 7}.get(v, 3)

# ================= 3. 读取CSV =================
rows_raw = []
with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if float(r['duration']) == 0 and not r['LYRICS'].strip():
            continue
        m = int(r['measure'])
        beat = float(r['beat_in_measure'])
        rows_raw.append({
            'part': 'Voice' if r['part'] == 'Voice' else 'Piano',
            'onset': measure_start_beat.get(m, 0) + beat,
            'midi': int(r['midi']),
            'lyric': r.get('LYRICS', '').strip(),
            'measure': m,
            'beat': beat,
            'duration': float(r['duration']),
            'dynamic': r['dynamic'].strip(),
            'is_chord': r['is_chord'].strip().upper() == 'TRUE',
            'tie': r.get('tie', '').strip().upper() == 'TRUE',
        })

rows_raw.sort(key=lambda x: x['onset'])

# 合并延音线：tie=TRUE 的音，把 duration 加给前一个同声部、同 MIDI 的音
rows = []
for r in rows_raw:
    if r['tie'] and rows:
        for prev in reversed(rows):
            if prev['part'] == r['part'] and prev['midi'] == r['midi']:
                prev['duration'] += r['duration']
                break
        continue
    rows.append(r)

# ================= 3. 解析音节（~ 前缀 = 拖腔）=================
syllables = []
for r in rows:
    if r['part'] != 'Voice':
        continue
    lyric = r['lyric']
    if not lyric:
        continue

    is_prolong = lyric.startswith('~')
    char = lyric[1:] if is_prolong else lyric
    if not char:
        continue

    # 拖腔：合并到前一个同字音节
    if is_prolong and syllables and syllables[-1]['char'] == char:
        syllables[-1]['mids'].append(r['midi'])
        continue

    # 非拖腔：作为新音节
    syllables.append({
        'char': char,
        'mids': [r['midi']],
        'onset': r['onset'],
        'measure': r['measure']
    })

# ================= 4. 短语结尾判定与调值生成 =================
phrase_end_chars = PHRASE_END_CHARS
phrase_end_indices = set()
for i, s in enumerate(syllables):
    if s['char'] in phrase_end_chars:
        phrase_end_indices.add(i)
    if i < len(syllables) - 1:
        gap = syllables[i+1]['onset'] - s['onset']
        if gap > 1.0:
            phrase_end_indices.add(i)

def get_actual_tone_contour(idx):
    char = syllables[idx]['char']
    base_tone = BASE_TONE_DICT.get(char, 0)
    prev_char = syllables[idx-1]['char'] if idx > 0 else None
    next_char = syllables[idx+1]['char'] if idx < len(syllables)-1 else None

    if char == '一':
        if next_char is None: return [5, 5]
        next_tone = BASE_TONE_DICT.get(next_char, 0)
        if next_tone == 4: return [3, 5]
        elif next_tone in (1, 2, 3): return [5, 1]
        else: return [5, 5]
    if char == '不':
        if next_char is None: return [5, 1]
        next_tone = BASE_TONE_DICT.get(next_char, 0)
        if next_tone == 4: return [3, 5]
        elif next_tone in (1, 2, 3): return [5, 1]
        else: return [5, 1]

    if base_tone == 3:
        if next_char is None: return [2, 1, 4]
        next_tone = BASE_TONE_DICT.get(next_char, 0)
        if next_tone == 0: return [2, 1]
        elif next_tone == 3: return [3, 5]
        else: return [2, 1]

    if base_tone == 4:
        if next_char is not None and BASE_TONE_DICT.get(next_char, 0) == 4:
            return [5, 3]
        else:
            return [5, 1]

    if base_tone == 0:
        if prev_char is not None:
            prev_tone = BASE_TONE_DICT.get(prev_char, 0)
            if prev_tone == 1: return [3]
            elif prev_tone == 2: return [3]
            elif prev_tone == 3: return [4]
            elif prev_tone == 4: return [1]
        return [3]

    if base_tone == 1: return [5, 5]
    if base_tone == 2: return [3, 5]
    return [3]

# 缓存实际调值
for i in range(len(syllables)):
    syllables[i]['tone_contour'] = get_actual_tone_contour(i)
    # 短语结尾且本调为上声，强制读全上
    if i in phrase_end_indices and BASE_TONE_DICT.get(syllables[i]['char'], 0) == 3:
        syllables[i]['tone_contour'] = [2, 1, 4]

# ================= 5. 判断短语起点 =================
def is_phrase_start(idx):
    if idx == 0: return True
    prev_char = syllables[idx-1]['char']
    current_char = syllables[idx]['char']
    if prev_char in PHRASE_END_CHARS or current_char in PHRASE_START_CHARS:
        return True
    return False

# ================= 6. 计算声调匹配度 =================
def calc_tone_support(idx):
    if is_phrase_start(idx): return 0.0

    curr_syl = syllables[idx]
    prev_syl = syllables[idx-1]
    mids = curr_syl['mids']
    prev_mids = prev_syl['mids']
    curr_contour = curr_syl['tone_contour']
    prev_contour = prev_syl['tone_contour']
    curr_char = curr_syl['char']
    prev_char = prev_syl['char']

    curr_base_tone = BASE_TONE_DICT.get(curr_char, 0)
    prev_base_tone = BASE_TONE_DICT.get(prev_char, 0)

    actual_transition = mids[0] - prev_mids[-1]

    # 同调值二度容差
    if curr_base_tone == prev_base_tone and curr_base_tone != 0:
        if abs(actual_transition) <= 2:
            return 0.7

    # 轻声专属规则
    if curr_base_tone == 0:
        if abs(actual_transition) <= 4: return 0.7
        else: return -0.5

    is_upper_shang = (curr_contour[0] == 2 and len(curr_contour) > 1 and curr_contour[1] == 1)
    is_prev_qing_sheng = (len(prev_contour) == 1 and prev_contour[0] in [1, 3, 4])

    curr_start = curr_contour[0]
    curr_end = curr_contour[-1]
    prev_end = prev_contour[-1]

    inner_score = 0.0
    if len(mids) > 1 and len(curr_contour) > 1:
        actual_inner = mids[-1] - mids[0]
        expected_inner = wudu_to_semitone(curr_end) - wudu_to_semitone(curr_start)
        if abs(expected_inner) >= 2:
            if (actual_inner > 0 and expected_inner > 0) or (actual_inner < 0 and expected_inner < 0):
                inner_score = 0.3
            elif actual_inner == 0:
                inner_score = 0.0
            else:
                inner_score = -0.3

    transition_score = 0.0
    if is_upper_shang or is_prev_qing_sheng:
        if actual_transition <= 0: transition_score = 0.7
        elif actual_transition > 2: transition_score = -0.5
        else: transition_score = 0.0
    else:
        expected_transition = wudu_to_semitone(curr_start) - wudu_to_semitone(prev_end)
        if expected_transition > 0:
            if actual_transition > 0: transition_score = 0.7
            elif actual_transition == 0: transition_score = 0.0
            else: transition_score = -0.8
        elif expected_transition < 0:
            if actual_transition < 0: transition_score = 0.7
            elif actual_transition == 0: transition_score = 0.0
            else: transition_score = -0.8
        else:
            if abs(actual_transition) <= 2: transition_score = 0.7
            else: transition_score = -0.5

    total = transition_score + inner_score
    return max(-1.0, min(1.0, total))

# ================= 7. 分组、泛音计算 =================
TAU = 4.0
SIGMA_CENTS = 50.0

def calc_harmonic_prob(target_midi, context):
    if not context: return 1e-6
    best_prob = 0.0
    for c in context:
        w = math.exp(-c['dist'] / TAU)
        harmonics = [c['midi'] + 12 * math.log2(k) for k in range(1, 11)]
        best_cents_diff = min(abs(target_midi - h) * 100 for h in harmonics)
        match_score = math.exp(-0.5 * (best_cents_diff / SIGMA_CENTS) ** 2)
        if match_score * w > best_prob:
            best_prob = match_score * w
    return max(best_prob, 1e-6)

grouped = []
current_onset = -1
current_voice = None
current_piano = []

for r in rows:
    if abs(r['onset'] - current_onset) > 0.01:
        if current_onset >= 0:
            grouped.append({
                'onset': current_onset,
                'measure': r['measure'], 'beat': r['beat'],
                'voice_midi': current_voice,
                'piano_top_midi': max(current_piano) if current_piano else None
            })
        current_onset = r['onset']
        current_voice = None
        current_piano = []
    if r['part'] == 'Voice':
        current_voice = r['midi']
    else:
        current_piano.append(r['midi'])

if current_onset >= 0:
    grouped.append({
        'onset': current_onset,
        'measure': r['measure'], 'beat': r['beat'],
        'voice_midi': current_voice,
        'piano_top_midi': max(current_piano) if current_piano else None
    })

results = []
for i, target in enumerate(grouped):
    if target['voice_midi'] is None: continue

    tone_support = 0.0
    current_char = ""
    for idx, s in enumerate(syllables):
        if abs(s['onset'] - target['onset']) < 0.2:
            tone_support = calc_tone_support(idx)
            current_char = s['char']
            break

    context_V, context_VP = [], []
    for j in range(i):
        past = grouped[j]
        dist = target['onset'] - past['onset']
        if dist > 15.0: continue
        if past['voice_midi'] is not None:
            context_V.append({'midi': past['voice_midi'], 'dist': dist})
            context_VP.append({'midi': past['voice_midi'], 'dist': dist})
        if past['piano_top_midi'] is not None:
            context_VP.append({'midi': past['piano_top_midi'], 'dist': dist})

    p_V = calc_harmonic_prob(target['voice_midi'], context_V)
    p_VP = calc_harmonic_prob(target['voice_midi'], context_VP)
    
    # 如果纯人声概率极小，说明前文根本没有泛音参照，增益记为 0
    if p_V < 1e-3:
        delta_base = 0.0
    else:
        delta_base = -math.log(p_V) - (-math.log(p_VP))

    results.append({
        'onset': target['onset'],
        'measure': target['measure'], 
        'beat': target['beat'],
        'base': delta_base,
        'total': delta_base + tone_support,
        'support': tone_support,
        'char': current_char,
        'tone_contour': syllables[idx]['tone_contour'] if current_char else []
    })

# ================= 8. 最终可视化 =================
x = [r['onset'] for r in results]  # 使用绝对物理时间
base = [r['base'] for r in results]
total = [r['total'] for r in results]
support = [r['support'] for r in results]
chars = [r['char'] for r in results]
contours = [r['tone_contour'] for r in results]

fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True,
                         gridspec_kw={'height_ratios': [2, 1.2]})

# 上图
axes[0].bar(x, base, width=0.4, label='泛音匹配对数似然比增益', color='lightgray', alpha=0.9)
axes[0].axhline(y=0, color='red', linestyle='--', linewidth=1)
axes[0].set_ylabel('泛音匹配对数似然比增益（指标A）', fontsize=12)
axes[0].set_title('声调—旋律匹配与泛音匹配增益（物理时间轴）', fontsize=14)
axes[0].legend(loc='upper right', fontsize=11)

# 下图
colors = ['green' if v > 0.1 else ('red' if v < -0.1 else 'gray') for v in support]
bars = axes[1].bar(x, support, width=0.3, color=colors, alpha=0.8)
axes[1].axhline(y=0, color='black', linestyle='-', linewidth=1)
axes[1].set_ylabel('声调—旋律匹配得分', fontsize=12)
axes[1].set_xlabel('小节数 / 时间（绝对拍数）', fontsize=12)

# 文字防重叠逻辑
for i, (xi, char, eff, contour) in enumerate(zip(x, chars, support, contours)):
    if not char: continue
    tone_str = ''.join(str(v) for v in contour) if contour else ''
    label = f"{char}\n{tone_str}" if tone_str else char
    
    # 严格根据正负方向放置文字
    if eff >= 0:
        pos_y = 0.85 if i % 2 == 0 else 0.55
        va = 'bottom'
    else:
        pos_y = -0.85 if i % 2 == 0 else -0.55
        va = 'top'
        
    axes[1].text(xi, pos_y, label, ha='center', va=va,
                 fontsize=8, color='black', fontweight='normal')

axes[1].set_ylim(-1.2, 1.2)

# 标出小节刻度
tick_measures = TICK_MEASURES
tick_positions = [measure_start_beat[m] for m in tick_measures]
axes[1].set_xticks(tick_positions)
axes[1].set_xticklabels([str(m) for m in tick_measures])
axes[1].set_xlim(measure_start_beat[4], measure_start_beat[31])

# 段落分界线
sections = SECTIONS
for i, ax in enumerate(axes):
    for m, name in sections:
        boundary_time = measure_start_beat[m]
        ax.axvline(x=boundary_time, color='red', linestyle=':', alpha=0.6)
        
        # 仅在第一个子图（上图）添加文字标识
        if i == 0:
            ymax = ax.get_ylim()[1]
            ax.text(boundary_time + 1, ymax * 0.9, name, color='red', fontsize=11, fontweight='bold')

plt.subplots_adjust(left=0.06, right=0.96, top=0.92, bottom=0.10, hspace=0.25)
plt.savefig('figures/声调匹配与泛音匹配图.svg', format='svg', bbox_inches='tight')

# ===== 导出逐音数据 =====
pd.DataFrame(results).to_csv('data/声调匹配与泛音匹配_逐音.csv', index=False)
print('已导出 声调匹配与泛音匹配_逐音.csv')
plt.show()