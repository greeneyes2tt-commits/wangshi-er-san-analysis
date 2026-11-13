# -*- coding: utf-8 -*-
"""
表1统计脚本：按 onset 分段，统计语言支撑、物理支撑、有效锚点
分段标准：引子1-4，第一段5-14，间奏15-16，第二段17-23，第三段24-30，尾声31
onset 阈值由 measure_start_beat 推出
"""
import csv
from statistics import mean

# ===== 时间轴（与主脚本一致） =====
measure_lengths = {
    1: 3.0, 2: 4.5, 3: 3.0, 4: 2.5, 5: 2.5, 6: 2.5, 7: 4.0, 8: 4.5, 9: 3.0, 10: 2.0,
    11: 2.5, 12: 3.5, 13: 2.5, 14: 2.5, 15: 4.0, 16: 3.0, 17: 2.0, 18: 4.0, 19: 5.0, 20: 2.5,
    21: 4.0, 22: 3.0, 23: 3.5, 24: 5.5, 25: 5.5, 26: 3.0, 27: 4.0, 28: 5.5, 29: 4.0, 30: 4.0, 31: 4.0
}
measure_start = {}
cur = 0.0
for m in range(1, 32):
    measure_start[m] = cur
    cur += measure_lengths.get(m, 4.0)

# ===== 分段（按 onset） =====
sections = {
    '第一段': (measure_start[5], measure_start[15]),
    '第二段': (measure_start[17], measure_start[24]),
    '第三段': (measure_start[24], measure_start[31]),
}

# ===== 语言支撑 =====
lang_rows = []
with open('data/声调匹配与泛音匹配_逐音.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if not r['char'].strip():
            continue
        lang_rows.append({
            'onset': float(r['onset']),
            'support': float(r['support']),
            'char': r['char'],
        })

print('=' * 60)
print('声调匹配（按 onset 分段，仅计有 char 的音节）')
print('=' * 60)
print(f"{'段落':<8} {'音节数':<6} {'均值':<10} {'正向数':<6} {'正向占比':<10}")
for name, (lo, hi) in sections.items():
    sel = [r for r in lang_rows if lo <= r['onset'] < hi]
    if not sel:
        continue
    vals = [r['support'] for r in sel]
    pos = sum(1 for v in vals if v > 0)
    print(f"{name:<8} {len(sel):<6} {mean(vals):<10.4f} {pos:<6} {pos/len(sel)*100:.1f}%")
    print(f"  音节：{''.join(r['char'] for r in sel)}")

# ===== 物理支撑 =====
phys_rows = []
with open('data/声学参照差值_逐音.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        phys_rows.append({
            'onset': float(r['onset']),
            'delta': float(r['Delta']),
        })

print('\n' + '=' * 60)
print('声学参照差值（按 onset 分段，含所有含人声起音的音响事件）')
print('=' * 60)
print(f"{'段落':<8} {'事件数':<6} {'Δ均值':<10} {'负值数':<6} {'负值占比':<10}")
for name, (lo, hi) in sections.items():
    sel = [r for r in phys_rows if lo <= r['onset'] < hi]
    if not sel:
        continue
    vals = [r['delta'] for r in sel]
    neg = sum(1 for v in vals if v < 0)
    print(f"{name:<8} {len(sel):<6} {mean(vals):<10.4f} {neg:<6} {neg/len(sel)*100:.1f}%")

# ===== 同音级提示与演奏提示 =====
print('\n' + '=' * 60)
print('有效提示（score >= 50 且 voice_window == "安静窗口"）')
print('=' * 60)

def count_anchors(filename):
    rows = []
    with open(filename, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if float(r['score']) >= 50 and r['voice_window'] == '安静窗口':
                rows.append(r)
    return rows

for label, fname in [('同音级提示', '声调匹配与泛音匹配_逐音.csv'), ('演奏提示', '声学参照差值_逐音.csv')]:
    anchors = count_anchors(fname)
    print(f"\n{label}：")
    for name, (lo, hi) in sections.items():
        sel = [r for r in anchors if lo <= float(r['target_onset']) < hi]
        # 去重：同一字在同一段落只计一次
        seen = set()
        chars = []
        for r in sel:
            lyric = (r.get('lyric') or r.get('\ufefflyric', '')).strip()
            if lyric and lyric not in seen:
                seen.add(lyric)
                chars.append(lyric)
        print(f"  {name}: {len(chars)} 个 —— {''.join(chars) if chars else '（无）'}")

print('\n统计完成。')