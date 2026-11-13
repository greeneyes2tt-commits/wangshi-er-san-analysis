# -*- coding: utf-8 -*-
"""
五度映射敏感性检验
对标准映射 M0 与三种替代映射（M1/M2/M3），比较：
  1. 跨字过渡方向的符号判定
  2. 音节内部音程方向的符号判定
  3. 语言支撑度得分与段落均值
输出：表D1（方向一致率）、表D2（支撑度变化）
"""

import csv

CSV_PATH = "data/往事二三_详细参数表_v3.csv"
SKIP_GRACE = False      # 不跳过 duration=0 的 grace 音
MERGE_SYLLABLES = True # 不合并同字音节

# ================= 1. 时间轴重建（与原脚本一致） =================
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

rows = []
with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        if float(r['duration']) == 0 and not r['LYRICS'].strip():
            continue
        m = int(r["measure"])
        beat = float(r["beat_in_measure"])
        rows.append({
            "part": "Voice" if r["part"] == "Voice" else "Piano",
            "onset": measure_start_beat.get(m, 0) + beat,
            "midi": int(r["midi"]),
            "lyric": r.get("LYRICS", "").strip(),
            "measure": m,
            "beat": beat,
        })
rows.sort(key=lambda x: x["onset"])

# ================= 2. 本调字典 =================
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

# ================= 4. 变调规则（返回五度值序列，不涉及映射） =================
phrase_end_chars = set('盅动方红来筒上空光中里梦')
phrase_end_indices = set()
for i, s in enumerate(syllables):
    if s["char"] in phrase_end_chars:
        phrase_end_indices.add(i)
    if i < len(syllables) - 1:
        gap = syllables[i+1]["onset"] - s["onset"]
        if gap > 1.0:
            phrase_end_indices.add(i)

def get_actual_tone_contour(idx):
    char = syllables[idx]["char"]
    base_tone = BASE_TONE_DICT.get(char, 0)
    prev_char = syllables[idx-1]["char"] if idx > 0 else None
    next_char = syllables[idx+1]["char"] if idx < len(syllables)-1 else None

    if char == "一":
        if next_char is None: return [5, 5]
        next_tone = BASE_TONE_DICT.get(next_char, 0)
        if next_tone == 4: return [3, 5]
        elif next_tone in (1, 2, 3): return [5, 1]
        else: return [5, 5]
    if char == "不":
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

for i in range(len(syllables)):
    syllables[i]["tone_contour"] = get_actual_tone_contour(i)
    if i in phrase_end_indices and BASE_TONE_DICT.get(syllables[i]["char"], 0) == 3:
        syllables[i]["tone_contour"] = [2, 1, 4]

# ================= 5. 短语起点判定 =================
def is_phrase_start(idx):
    if idx == 0: return True
    prev_char = syllables[idx-1]["char"]
    current_char = syllables[idx]["char"]
    boundaries = set('盅动方红来筒上空光中里梦')
    if prev_char in boundaries or current_char in set('石青遗桉繁生眼竖手脆做'):
        return True
    return False

# ================= 6. 映射定义 =================
MAPPINGS = {
    "M0 标准": {1: 0, 2: 2, 3: 4, 4: 5, 5: 7},
    "M1 等距": {1: 0, 2: 2, 3: 4, 4: 6, 5: 8},
    "M2 紧凑": {1: 0, 2: 1, 3: 2, 4: 4, 5: 7},
    "M3 中段展开": {1: 0, 2: 2, 3: 3, 4: 5, 5: 7},
}

def sign(x):
    if x > 0: return 1
    if x < 0: return -1
    return 0

# ================= 7. 方向判定 =================
def expected_transition_sign(idx, mapping):
    if is_phrase_start(idx):
        return None
    curr = syllables[idx]
    prev = syllables[idx-1]
    curr_start = curr["tone_contour"][0]
    prev_end = prev["tone_contour"][-1]
    return sign(mapping[curr_start] - mapping[prev_end])

def expected_inner_sign(idx, mapping):
    if is_phrase_start(idx):
        return None
    curr = syllables[idx]
    if len(curr["mids"]) <= 1 or len(curr["tone_contour"]) <= 1:
        return None
    curr_start = curr["tone_contour"][0]
    curr_end = curr["tone_contour"][-1]
    return sign(mapping[curr_end] - mapping[curr_start])

# ================= 8. 参数化语言支撑度（用于表D2） =================
def calc_tone_support(idx, mapping):
    if is_phrase_start(idx):
        return 0.0
    curr_syl = syllables[idx]
    prev_syl = syllables[idx-1]
    mids = curr_syl["mids"]
    prev_mids = prev_syl["mids"]
    curr_contour = curr_syl["tone_contour"]
    prev_contour = prev_syl["tone_contour"]
    curr_char = curr_syl["char"]
    prev_char = prev_syl["char"]
    curr_base_tone = BASE_TONE_DICT.get(curr_char, 0)
    prev_base_tone = BASE_TONE_DICT.get(prev_char, 0)
    actual_transition = mids[0] - prev_mids[-1]

    if curr_base_tone == prev_base_tone and curr_base_tone != 0:
        if abs(actual_transition) <= 2:
            return 0.7
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
        expected_inner = mapping[curr_end] - mapping[curr_start]
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
        expected_transition = mapping[curr_start] - mapping[prev_end]
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

    return max(-1.0, min(1.0, transition_score + inner_score))

# ================= 9. 表D1：方向判定一致率 =================
print("=" * 70)
print("表D1  五度映射的敏感性检验：方向判定一致率")
print("=" * 70)

# 收集所有有效的方向判定（以M0为基准，只统计M0给出非None的音节）
transition_indices = []
inner_indices = []
for i in range(len(syllables)):
    if expected_transition_sign(i, MAPPINGS["M0 标准"]) is not None:
        transition_indices.append(i)
    if expected_inner_sign(i, MAPPINGS["M0 标准"]) is not None:
        inner_indices.append(i)

print(f"\n参与跨字过渡方向比较的音节数：{len(transition_indices)}")
print(f"参与内部音程方向比较的音节数：{len(inner_indices)}")

print(f"\n{'映射':<12} {'过渡方向一致率':<18} {'内部音程一致率':<18}")
print("-" * 50)
for name, mp in MAPPINGS.items():
    if name == "M0 标准":
        continue
    # 跨字过渡
    match_t = 0
    for i in transition_indices:
        s0 = expected_transition_sign(i, MAPPINGS["M0 标准"])
        sn = expected_transition_sign(i, mp)
        if s0 == sn:
            match_t += 1
    # 内部音程
    match_i = 0
    for i in inner_indices:
        s0 = expected_inner_sign(i, MAPPINGS["M0 标准"])
        sn = expected_inner_sign(i, mp)
        if s0 == sn:
            match_i += 1
    rate_t = match_t / len(transition_indices) * 100 if transition_indices else 0
    rate_i = match_i / len(inner_indices) * 100 if inner_indices else 0
    print(f"{name:<12} {rate_t:>8.1f}% ({match_t}/{len(transition_indices)})   "
          f"{rate_i:>8.1f}% ({match_i}/{len(inner_indices)})")

# ================= 10. 表D2：语言支撑均值变化 =================
print("\n" + "=" * 70)
print("表D2  五度映射的敏感性检验：语言支撑度变化")
print("=" * 70)

sections = {
    "第一段": (5, 14),
    "第二段": (17, 23),
    "第三段": (24, 30),
}

# 对每种映射，计算每个音节的support
supports = {}
for name, mp in MAPPINGS.items():
    vals = []
    for i in range(len(syllables)):
        v = calc_tone_support(i, mp)
        vals.append((i, v))
    supports[name] = vals

# 基准：M0
base_vals = supports["M0 标准"]
base_by_idx = {i: v for i, v in base_vals}

print(f"\n{'映射':<12} {'全曲均值':<12} {'第一段':<12} {'第二段':<12} {'第三段':<12} {'正向占比':<12}")
print("-" * 78)

def section_mean(vals, m_start, m_end):
    sel = [v for i, v in vals if m_start <= syllables[i]["measure"] <= m_end]
    return sum(sel) / len(sel) if sel else 0.0

for name, vals in supports.items():
    all_mean = sum(v for _, v in vals) / len(vals)
    m1 = section_mean(vals, 5, 14)
    m2 = section_mean(vals, 17, 23)
    m3 = section_mean(vals, 24, 30)
    pos_ratio = sum(1 for _, v in vals if v > 0) / len(vals) * 100
    print(f"{name:<12} {all_mean:>10.4f}   {m1:>10.4f}   {m2:>10.4f}   {m3:>10.4f}   {pos_ratio:>8.1f}%")

print("\n" + "-" * 78)
print("与M0的逐音节得分差异（仅列出有差异的音节）：")
for name, vals in supports.items():
    if name == "M0 标准":
        continue
    diffs = [(i, base_by_idx[i], v) for i, v in vals if abs(base_by_idx[i] - v) > 1e-6]
    if not diffs:
        print(f"  {name}: 无差异")
    else:
        print(f"  {name}: {len(diffs)} 个音节有差异")
        for i, b, v in diffs[:10]:  # 最多列10个
            print(f"    第{syllables[i]['measure']}小节 '{syllables[i]['char']}': M0={b:.2f}, {name}={v:.2f}")
        if len(diffs) > 10:
            print(f"    ……共{len(diffs)}个，仅列前10个")

print("\n检验完成。")