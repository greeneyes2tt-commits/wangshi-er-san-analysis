# -*- coding: utf-8 -*-
"""
语言评分权重敏感性检验
对五种评分权重方案（S0标准、S1整体×0.8、S2整体×1.2、S3正×0.8负×1.2、S4正×1.2负×0.8），
计算三段的语言支撑均值与正向占比。
输出：可直接填入附录4表D4。
"""

import csv

# ================= 1. 时间轴（与主脚本一致） =================
measure_lengths = {
    1: 3.0, 2: 4.5, 3: 3.0, 4: 2.5, 5: 2.5, 6: 2.5, 7: 4.0, 8: 4.5, 9: 3.0, 10: 2.0,
    11: 2.5, 12: 3.5, 13: 2.5, 14: 2.5, 15: 4.0, 16: 3.0, 17: 2.0, 18: 4.0, 19: 5.0, 20: 2.5,
    21: 4.0, 22: 3.0, 23: 3.5, 24: 5.5, 25: 5.5, 26: 3.0, 27: 4.0, 28: 5.5, 29: 4.0, 30: 4.0, 31: 4.0
}
measure_start_beat = {}
_current = 0.0
for _m in range(1, 32):
    measure_start_beat[_m] = _current
    _current += measure_lengths.get(_m, 4.0)

# ================= 2. 读取 CSV =================
CSV_PATH = "data/往事二三_详细参数表_v3.csv"
rows_raw = []
with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        if float(r["duration"]) == 0 and not r["LYRICS"].strip():
            continue
        m = int(r["measure"])
        beat = float(r["beat_in_measure"])
        rows_raw.append({
            "part": "Voice" if r["part"] == "Voice" else "Piano",
            "onset": measure_start_beat.get(m, 0) + beat,
            "midi": int(r["midi"]),
            "lyric": r.get("LYRICS", "").strip(),
            "measure": m,
            "beat": beat,
        })
rows_raw.sort(key=lambda x: x["onset"])

# ================= 3. 本调字典 =================
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

def wudu_to_semitone(v):
    return {1: 0, 2: 2, 3: 4, 4: 5, 5: 7}.get(v, 3)

# ================= 4. 解析音节（~ 前缀 = 拖腔） =================
syllables = []
for r in rows_raw:
    if r["part"] != "Voice":
        continue
    lyric = r["lyric"]
    if not lyric:
        continue
    is_prolong = lyric.startswith("~")
    char = lyric[1:] if is_prolong else lyric
    if not char:
        continue
    if is_prolong and syllables and syllables[-1]["char"] == char:
        syllables[-1]["mids"].append(r["midi"])
        continue
    syllables.append({
        "char": char,
        "mids": [r["midi"]],
        "onset": r["onset"],
        "measure": r["measure"],
    })

# ================= 5. 短语结尾与调值 =================
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

# ================= 6. 短语起点 =================
def is_phrase_start(idx):
    if idx == 0: return True
    prev_char = syllables[idx-1]["char"]
    current_char = syllables[idx]["char"]
    boundaries = set('盅动方红来筒上空光中里梦')
    if prev_char in boundaries or current_char in set('石青遗桉繁生眼竖手脆做'):
        return True
    return False

# ================= 7. 参数化评分函数 =================
def calc_tone_support(idx, W):
    if is_phrase_start(idx):
        return 0.0
    curr = syllables[idx]
    prev = syllables[idx-1]
    mids = curr["mids"]
    prev_mids = prev["mids"]
    curr_contour = curr["tone_contour"]
    prev_contour = prev["tone_contour"]
    curr_char = curr["char"]
    prev_char = prev["char"]
    curr_base = BASE_TONE_DICT.get(curr_char, 0)
    prev_base = BASE_TONE_DICT.get(prev_char, 0)
    actual_transition = mids[0] - prev_mids[-1]

    # 同调值二度容差
    if curr_base == prev_base and curr_base != 0:
        if abs(actual_transition) <= 2:
            return W["tolerant"]

    # 轻声
    if curr_base == 0:
        if abs(actual_transition) <= 4:
            return W["qing_pos"]
        else:
            return W["neutral_neg"]

    is_upper_shang = (curr_contour[0] == 2 and len(curr_contour) > 1 and curr_contour[1] == 1)
    is_prev_qing = (len(prev_contour) == 1 and prev_contour[0] in [1, 3, 4])

    curr_start = curr_contour[0]
    curr_end = curr_contour[-1]
    prev_end = prev_contour[-1]

    inner_score = 0.0
    if len(mids) > 1 and len(curr_contour) > 1:
        actual_inner = mids[-1] - mids[0]
        expected_inner = wudu_to_semitone(curr_end) - wudu_to_semitone(curr_start)
        if abs(expected_inner) >= 2:
            if (actual_inner > 0 and expected_inner > 0) or (actual_inner < 0 and expected_inner < 0):
                inner_score = W["inner"]
            elif actual_inner == 0:
                inner_score = 0.0
            else:
                inner_score = W["inner_neg"]

    transition_score = 0.0
    if is_upper_shang or is_prev_qing:
        if actual_transition <= 0:
            transition_score = W["qing_pos"]
        elif actual_transition > 2:
            transition_score = W["neutral_neg"]
        else:
            transition_score = 0.0
    else:
        expected_transition = wudu_to_semitone(curr_start) - wudu_to_semitone(prev_end)
        if expected_transition > 0:
            if actual_transition > 0: transition_score = W["pos"]
            elif actual_transition == 0: transition_score = 0.0
            else: transition_score = W["neg"]
        elif expected_transition < 0:
            if actual_transition < 0: transition_score = W["pos"]
            elif actual_transition == 0: transition_score = 0.0
            else: transition_score = W["neg"]
        else:
            if abs(actual_transition) <= 2:
                transition_score = W["tolerant"]
            else:
                transition_score = W["neutral_neg"]

    total = transition_score + inner_score
    return max(-1.0, min(1.0, total))

# ================= 8. 五种权重方案 =================
S0 = {
    "pos": 0.7, "neg": -0.8, "inner": 0.3, "inner_neg": -0.3,
    "tolerant": 0.7, "qing_pos": 0.7, "neutral_neg": -0.5,
}
SCHEMES = {
    "S0 标准": S0,
    "S1 整体×0.8": {k: v * 0.8 for k, v in S0.items()},
    "S2 整体×1.2": {k: v * 1.2 for k, v in S0.items()},
    "S3 正×0.8 负×1.2": {
        "pos": 0.56, "neg": -0.96, "inner": 0.24, "inner_neg": -0.36,
        "tolerant": 0.56, "qing_pos": 0.56, "neutral_neg": -0.6,
    },
    "S4 正×1.2 负×0.8": {
        "pos": 0.84, "neg": -0.64, "inner": 0.36, "inner_neg": -0.24,
        "tolerant": 0.84, "qing_pos": 0.84, "neutral_neg": -0.4,
    },
}

# ================= 9. 分段与输出 =================
SECTIONS = {
    "第一段": (measure_start_beat[5], measure_start_beat[15]),
    "第二段": (measure_start_beat[17], measure_start_beat[24]),
    "第三段": (measure_start_beat[24], measure_start_beat[31]),
}

print("=" * 90)
print("表D4  语言评分权重的敏感性检验：三段均值与正向占比")
print("=" * 90)
header = f"{'方案':<18}{'第一段均值':>12}{'第一段正向%':>13}{'第二段均值':>12}{'第二段正向%':>13}{'第三段均值':>12}{'第三段正向%':>13}"
print(header)
print("-" * len(header))

for name, W in SCHEMES.items():
    supports = []
    for i in range(len(syllables)):
        supports.append((syllables[i]["onset"], calc_tone_support(i, W)))
    line = f"{name:<18}"
    for seg in ["第一段", "第二段", "第三段"]:
        lo, hi = SECTIONS[seg]
        sel = [v for o, v in supports if lo <= o < hi]
        if not sel:
            line += f"{'—':>12}{'—':>13}"
        else:
            mean = sum(sel) / len(sel)
            pos = sum(1 for v in sel if v > 0)
            line += f"{mean:>12.4f}{pos / len(sel) * 100:>12.1f}%"
    print(line)

print("\n" + "=" * 90)
print("说明：")
print("  S0 应与主语言脚本输出一致（第一段0.290、第二段0.136、第三段0.128）。")
print("  检查段落排序是否在所有方案下保持：第一段均值最高、第三段均值最低。")
print("=" * 90)