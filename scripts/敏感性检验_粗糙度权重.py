# -*- coding: utf-8 -*-
"""
粗糙度权重敏感性检验
对四种粗糙度权重方案（W0标准、W1×0.8、W2峰值微调、W3峰值上调），
计算三段的物理 Δ 均值与负值占比。
输出：可直接填入附录4表D3。
"""

import csv
import math

# ================= 1. 时间轴（与主脚本一致） =================
measure_lengths = {
    1: 3.0, 2: 4.5, 3: 3.0, 4: 2.5, 5: 2.5, 6: 2.5, 7: 4.0, 8: 4.5, 9: 3.0, 10: 2.0,
    11: 2.5, 12: 3.5, 13: 2.5, 14: 2.5, 15: 4.0, 16: 3.0, 17: 2.0, 18: 4.0, 19: 5.0, 20: 2.5,
    21: 4.0, 22: 3.0, 23: 3.5, 24: 5.5, 25: 5.5, 26: 3.0, 27: 4.0, 28: 5.5, 29: 4.0, 30: 4.0, 31: 4.0
}
measure_start_beat = {}
current_start = 0.0
for m in range(1, 32):
    measure_start_beat[m] = current_start
    current_start += measure_lengths.get(m, 4.0)

# ================= 2. 读取 CSV（与主声学脚本一致） =================
rows_raw = []
with open(r'data/往事二三_详细参数表_v3.csv',
          mode='r', encoding='utf-8-sig') as f:
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

# ================= 3. 分组（与主声学脚本一致） =================
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

# ================= 4. 物理模型（参数化粗糙度表） =================
TAU = 4.0
SIGMA = 50.0

def calc_net_support(target_midi, context, rough_table):
    """匹配均值 - 冲突均值，与主脚本逻辑一致，仅 rough_table 参数化。"""
    if not context:
        return 0.0
    total_g = 0.0
    total_d = 0.0
    total_w = 0.0
    
    for c in context:
        w = math.exp(-c["dist"] / TAU)
        total_w += w
        
        avg_g = 0.0
        avg_d = 0.0
        for ctx_m in c["midis"]:
            # 匹配：前10谐波，高斯核 σ=50音分，取最大值
            best_g = 0.0
            for k in range(1, 11):
                h = ctx_m + 12 * math.log2(k)
                cents = abs(target_midi - h) * 100
                g = math.exp(-0.5 * (cents / SIGMA) ** 2)
                if g > best_g:
                    best_g = g
            avg_g += best_g
            
            # 冲突：最小环绕距离查粗糙度表
            pc_dist = abs(target_midi - ctx_m) % 12
            min_dist = min(pc_dist, 12 - pc_dist)
            d = rough_table.get(int(round(min_dist)), 0.0)
            avg_d += d
            
        # 对和弦内的音求平均
        avg_g /= len(c["midis"])
        avg_d /= len(c["midis"])
        
        total_g += w * avg_g
        total_d += w * avg_d
        
    if total_w == 0:
        return 0.0
    return total_g / total_w - total_d / total_w


def compute_deltas(rough_table):
    """对每个含人声的 onset，计算 Delta = Score_VP - Score_V。"""
    results = []
    for i, target in enumerate(grouped):
        if target["voice_midi"] is None:
            continue
        ctx_V = []
        ctx_VP = []
        for j in range(i):
            past = grouped[j]
            dist = target["onset"] - past["onset"]
            if dist > 15.0:
                continue
            if past["voice_midi"] is not None:
                ctx_V.append({"midis": [past["voice_midi"]], "dist": dist})
                ctx_VP.append({"midis": [past["voice_midi"]], "dist": dist})
            if past["piano_chord"]:
                ctx_VP.append({"midis": past["piano_chord"], "dist": dist})
        sv = calc_net_support(target["voice_midi"], ctx_V, rough_table)
        svp = calc_net_support(target["voice_midi"], ctx_VP, rough_table)
        results.append({"onset": target["onset"], "delta": svp - sv})
    return results

# ================= 5. 分段（按 onset） =================
SECTIONS = {
    "第一段": (measure_start_beat[5], measure_start_beat[15]),
    "第二段": (measure_start_beat[17], measure_start_beat[24]),
    "第三段": (measure_start_beat[24], measure_start_beat[31]),
}

def summarize(results):
    out = {}
    for name, (lo, hi) in SECTIONS.items():
        sel = [r["delta"] for r in results if lo <= r["onset"] < hi]
        if not sel:
            out[name] = (None, None, 0)
            continue
        mean = sum(sel) / len(sel)
        neg = sum(1 for v in sel if v < 0)
        out[name] = (mean, neg / len(sel) * 100, len(sel))
    return out

# ================= 6. 四种粗糙度权重方案 =================
SCHEMES = {
    "W0 标准":     {0: 0.0, 1: 1.0, 2: 0.4, 3: 0.2, 4: 0.1, 5: 0.05, 6: 0.6},
    "W1 ×0.8":     {0: 0.0, 1: 0.8, 2: 0.32, 3: 0.16, 4: 0.08, 5: 0.04, 6: 0.48},
    "W2 峰值微调": {0: 0.0, 1: 0.9, 2: 0.4, 3: 0.2, 4: 0.1, 5: 0.05, 6: 0.5},
    "W3 峰值上调": {0: 0.0, 1: 1.2, 2: 0.4, 3: 0.2, 4: 0.1, 5: 0.05, 6: 0.7},
}

# ================= 7. 输出 =================
print("=" * 90)
print("表8  粗糙度权重的敏感性检验：声学参照差值 Δ 均值与负值占比")
print("=" * 90)
header = f"{'方案':<14}{'第一段均值':>12}{'第一段负值%':>13}{'第二段均值':>12}{'第二段负值%':>13}{'第三段均值':>12}{'第三段负值%':>13}"
print(header)
print("-" * len(header))

for name, table in SCHEMES.items():
    deltas = compute_deltas(table)
    s = summarize(deltas)
    line = f"{name:<14}"
    for seg in ["第一段", "第二段", "第三段"]:
        mean, ratio, n = s[seg]
        if mean is None:
            line += f"{'—':>12}{'—':>13}"
        else:
            line += f"{mean:>12.4f}{ratio:>12.1f}%"
    print(line)

print("\n" + "=" * 90)
print("说明：")
print("  W0 应与主声学脚本输出一致（第一段0.007、第二段0.020、第三段0.050）。")
print("  若 W1—W3 与 W0 的均值差异 <0.01、负值占比差异 <2%，")
print("  则表1的段落比较结论对粗糙度权重的具体数值不敏感。")
print("=" * 90)