import csv
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['SimHei'] # 解决图表中文显示问题（Mac用户可改为 'Arial Unicode MS'）
matplotlib.rcParams['axes.unicode_minus'] = False # 解决负号显示问题
plt.rcParams['mathtext.fontset'] = 'stix'

# ==========================================
# 配置区：使用其他作品时，只需修改以下内容
# ==========================================

# 1. 数据文件路径
CSV_FILE_PATH = 'data/往事二三_详细参数表_v3.csv'

# 2. 小节时长表
MEASURE_LENGTHS = {
    1: 3.0, 2: 4.5, 3: 3.0, 4: 2.5, 5: 2.5, 6: 2.5, 7: 4.0, 8: 4.5, 9: 3.0, 10: 2.0,
    11: 2.5, 12: 3.5, 13: 2.5, 14: 2.5, 15: 4.0, 16: 3.0, 17: 2.0, 18: 4.0, 19: 5.0, 20: 2.5,
    21: 4.0, 22: 3.0, 23: 3.5, 24: 5.5, 25: 5.5, 26: 3.0, 27: 4.0, 28: 5.5, 29: 4.0, 30: 4.0, 31: 4.0
}

# 3. 物理模型参数
TAU = 4.0  # 时间衰减常数（拍）
# 粗糙度对照表（基于音级距离 0-6），用于计算频率冲突得分
# 0: 八度/同度; 1: 小二度 (峰值); 6: 三全音
ROUGHNESS_TABLE = {0: 0.0, 1: 1.0, 2: 0.4, 3: 0.2, 4: 0.1, 5: 0.05, 6: 0.6}

# 4. 绘图特定配置
# 需要在图上用紫色圆圈高亮标注的关键汉字
TARGET_CHARS_TO_ANNOTATE = ['林', '空']
# 绘图分段配置（小节号, 段落名称）
SECTIONS = [
    (1, '引子'), (5, '第一段'), (15, '间奏'),
    (17, '第二段'), (24, '第三段'), (31, '尾声')
]
# X轴刻度显示的小节号
TICK_MEASURES = [5, 10, 15, 17, 20, 25, 30]

# ==========================================
# 核心算法区：以下代码通用，无需修改
# ==========================================

# ================= 1. 重建时间轴 =================
measure_start_beat = {}
current_start = 0.0
max_measure = max(MEASURE_LENGTHS.keys())
for m in range(1, max_measure + 1):
    measure_start_beat[m] = current_start
    current_start += MEASURE_LENGTHS.get(m, 4.0)

# ================= 2. 读取CSV =================
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
            'lyric': r.get('LYRICS', '').strip().lstrip('~'),
            'measure': m,
            'beat': beat,
            'duration': float(r['duration']),
            'dynamic': r['dynamic'].strip(),
            'is_chord': r['is_chord'].strip().upper() == 'TRUE',
            'tie': r.get('tie', '').strip().upper() == 'TRUE',
        })

rows_raw.sort(key=lambda x: x['onset'])

# 合并延音线
rows = []
for r in rows_raw:
    if r['tie'] and rows:
        for prev in reversed(rows):
            if prev['part'] == r['part'] and prev['midi'] == r['midi']:
                prev['duration'] += r['duration']
                break
        continue
    rows.append(r)

# ================= 3. 分组 =================
grouped = []
current_onset = -1
current_measure = -1
current_voice_midi = None
current_piano_midis = []
current_lyric = ""

for r in rows:
    if abs(r['onset'] - current_onset) > 0.01:
        if current_onset >= 0:
            grouped.append({
                'onset': current_onset,
                'measure': current_measure,
                'voice_midi': current_voice_midi,
                'piano_chord': list(set(current_piano_midis)),
                'lyric': current_lyric,
            })
        current_onset = r['onset']
        current_measure = r['measure']
        current_voice_midi = None
        current_piano_midis = []
        current_lyric = ""

    if r['part'] == 'Voice':
        current_voice_midi = r['midi']
        current_lyric = r['lyric']
    else:
        current_piano_midis.append(r['midi'])

if current_onset >= 0:
    grouped.append({
        'onset': current_onset,
        'measure': current_measure,
        'voice_midi': current_voice_midi,
        'piano_chord': list(set(current_piano_midis)),
        'lyric': current_lyric,
    })

# ================= 4. 物理声场模型 =================
def calc_net_support(target_midi, context):
    """
    计算当前音在给定声场中的“声学参照差值”
    声学参照差值 = 平均泛音匹配得分 - 平均频率冲突得分
    """
    if not context:
        return 0.0
        
    total_harmonic_match = 0.0
    total_freq_conflict = 0.0
    total_weight = 0.0
    
    for c in context:
        w = math.exp(-c['dist'] / TAU)
        avg_match = 0.0
        avg_conflict = 0.0
        for ctx_m in c['midis']:
            best_match = 0.0
            for k in range(1, 11):
                h_midi = ctx_m + 12 * math.log2(k)
                cents_diff = abs(target_midi - h_midi) * 100
                match_score = math.exp(-0.5 * (cents_diff / 50.0) ** 2)
                if match_score > best_match:
                    best_match = match_score
            avg_match += best_match

            pitch_class_dist = abs(target_midi - ctx_m) % 12
            min_dist = min(pitch_class_dist, 12 - pitch_class_dist)
            avg_conflict += ROUGHNESS_TABLE.get(int(round(min_dist)), 0.0)

        avg_match /= len(c['midis'])
        avg_conflict /= len(c['midis'])
        total_harmonic_match += w * avg_match
        total_freq_conflict += w * avg_conflict
        total_weight += w

    if total_weight == 0:
        return 0.0

    # 求加权平均
    final_match = total_harmonic_match / total_weight
    final_conflict = total_freq_conflict / total_weight
    
    return final_match - final_conflict

# ================= 5. 计算并对比 =================
results = []
for i, target in enumerate(grouped):
    if target['voice_midi'] is None:
        continue

    context_V = []
    context_VP = []

    for j in range(i):
        past = grouped[j]
        dist = target['onset'] - past['onset']
        if dist > 15.0:
            continue
        if past['voice_midi'] is not None:
            context_V.append({'midis': [past['voice_midi']], 'dist': dist})
            context_VP.append({'midis': [past['voice_midi']], 'dist': dist})
        if past['piano_chord']:
            context_VP.append({'midis': past['piano_chord'], 'dist': dist})

    Score_V = calc_net_support(target['voice_midi'], context_V)
    Score_VP = calc_net_support(target['voice_midi'], context_VP)
    Delta = Score_VP - Score_V

    results.append({
        'onset': target['onset'],
        'measure': target['measure'],
        'Score_V': Score_V,
        'Score_VP': Score_VP,
        'Delta': Delta,
        'char': target['lyric']
    })

# ================= 6. 可视化 =================
onsets = [r['onset'] for r in results]
deltas = [r['Delta'] for r in results]
Score_V = [r['Score_V'] for r in results]
Score_VP = [r['Score_VP'] for r in results]
chars = [r['char'] for r in results]

fig, ax1 = plt.subplots(figsize=(18, 7))

colors = ['green' if v > 0 else 'red' for v in deltas]
bars = ax1.bar(onsets, deltas, width=0.4, color=colors, alpha=0.5, label=r'声学参照差值增量 \(\Delta\)')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax1.set_ylabel(r'声学参照差值增量 (\(\Delta\))', fontsize=12)
ax1.set_xlabel('小节数', fontsize=12)
ax1.set_title('钢琴声部的声学反馈：泛音匹配得分与频率冲突得分', fontsize=14)

ax1.fill_between([min(onsets), max(onsets)], 0, max(deltas) if max(deltas)>0 else 0, color='green', alpha=0.05)
ax1.fill_between([min(onsets), max(onsets)], min(deltas) if min(deltas)<0 else 0, 0, color='red', alpha=0.05)

ax2 = ax1.twinx()
ax2.plot(onsets, Score_V, label=r'纯人声参照得分（$Score_V$）', color='blue', alpha=0.6, linewidth=1.5, linestyle='--')
ax2.plot(onsets, Score_VP, label=r'人声+钢琴联合参照得分 （$Score_{V+P}$）', color='orange', alpha=0.8, linewidth=1.5)
ax2.set_ylabel('平均参照得分（泛音匹配得分 - 频率冲突得分）', fontsize=12)

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend([lines_1[0], lines_2[0], lines_2[1]], 
           [labels_1[0], labels_2[0], labels_2[1]], 
           loc='lower right', bbox_to_anchor=(0.99, 0.02), fontsize=11, framealpha=0.9)

# 精确标注关键汉字（调用配置区）
for i, (x_val, char, y_val) in enumerate(zip(onsets, chars, deltas)):
    if char in TARGET_CHARS_TO_ANNOTATE:
        if y_val < 0:
            text_y = y_val - 0.05 
            va_align = 'top'
        else:
            text_y = y_val + 0.05
            va_align = 'bottom'
            
        ax1.annotate(char, 
                     xy=(x_val, y_val), 
                     xytext=(x_val, text_y), 
                     ha='center', va=va_align,
                     fontsize=14, fontweight='bold', color='purple',
                     bbox=dict(boxstyle="circle,pad=0.3", fc="white", ec="purple", alpha=0.9, lw=1.5))

# 添加段落分界线与名称（调用配置区）
max_y = ax1.get_ylim()[1]
for m, name in SECTIONS:
    boundary = measure_start_beat[m]
    ax1.axvline(x=boundary, color='red', linestyle=':', alpha=0.6)
    ax1.text(boundary + 0.5, max_y * 0.85, name, color='red', fontsize=11, fontweight='normal')

# 更改 X 轴刻度（调用配置区）
tick_positions = [measure_start_beat[m] for m in TICK_MEASURES]
ax1.set_xticks(tick_positions)
ax1.set_xticklabels([str(m) for m in TICK_MEASURES])
ax1.set_xlim(measure_start_beat[1], measure_start_beat[max_measure])

plt.tight_layout()
plt.savefig('figures/声学参照差值图.svg', format='svg', bbox_inches='tight')

# ===== 导出物理支撑度逐音数据 =====
with open('data/声学参照差值_逐音.csv', mode='w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(
        f,
        fieldnames=['onset', 'measure', 'Score_V', 'Score_VP', 'Delta', 'char']
    )
    writer.writeheader()
    for r in results:
        writer.writerow({
            'onset': r['onset'],
            'measure': r['measure'],
            'Score_V': r['Score_V'],
            'Score_VP': r['Score_VP'],
            'Delta': r['Delta'],
            'char': r.get('char', ''),
        })
print('已导出 声学参照差值_逐音.csv')
plt.show()