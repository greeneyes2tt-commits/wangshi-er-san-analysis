import csv
import os

# ==========================================
# 配置区
# ==========================================
CSV_PATH = "data/往事二三_详细参数表_v3.csv"
OUTPUT_A_CSV = "data/同音级提示.csv"
OUTPUT_D_CSV = "data/演奏提示.csv"

DYNAMIC_SCORE = {"f": 15, "mf": 12, "mp": 8, "p": 5, "pp": 2, "": 5}
PIANO_PARTS = ("P2-Staff1", "P2-Staff2")
BASS_PARTS = ("P2-Staff2",)

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

def load():
    voice, piano = [], []
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        raw = []
        for row in csv.DictReader(f):
            part = row["part"].strip()
            m = int(row["measure"])
            beat = float(row["beat_in_measure"])
            raw.append(dict(
                part=part,
                midi=int(row["midi"]),
                pc=int(row["pc"]),
                onset=measure_start_beat.get(m, 0) + beat,
                duration=float(row["duration"]),
                dynamic=row["dynamic"].strip(),
                is_chord=row["is_chord"].strip().upper() == "TRUE",
                lyric=row["LYRICS"].strip().lstrip("~"),
                measure=m,
                beat=beat,
                tie=row.get("tie", "").strip().upper() == "TRUE",
                accent=row.get("accent", "").strip().upper() == "TRUE",
            ))
    raw.sort(key=lambda x: x["onset"])
    merged = []
    for r in raw:
        if r["tie"] and merged:
            for prev in reversed(merged):
                if prev["part"] == r["part"] and prev["midi"] == r["midi"]:
                    prev["duration"] += r["duration"]
                    prev["accent"] = prev["accent"] or r["accent"]
                    break
            continue
        merged.append(r)
    for r in merged:
        if r["part"] == "Voice":
            voice.append(r)
        elif r["part"] in PIANO_PARTS:
            piano.append(r)
    return voice, piano

def voice_status(p, v, voice_all):
    overlap = False
    sounding_at_start = False
    for other in voice_all:
        if other is v:
            continue
        o_start = other["onset"]
        o_end = other["onset"] + other["duration"]
        if o_start < v["onset"] and o_end > p["onset"]:
            overlap = True
        if o_start <= p["onset"] < o_end:
            sounding_at_start = True
    if not overlap:
        return "安静窗口", 30
    if not sounding_at_start:
        return "人声进入前", 10
    return "与人声重叠", 0


def score_A(v, p, voice_all):
    gs = v["onset"] - p["onset"]
    ge = v["onset"] - (p["onset"] + p["duration"])
    vw, bonus = voice_status(p, v, voice_all)

    if p["midi"] == v["midi"]:
        if ge <= 1.0:
            s = 0
            s += 30 if ge <= 0 else max(0, 30 - 20 * ge)
            s += max(0, 25 - 12 * gs)
            s += DYNAMIC_SCORE.get(p["dynamic"], 5)
            s += 15 if p["is_chord"] else 0
            s += min(15, 12 * p["duration"])
            s += bonus
            return s, gs, ge, vw, "即时同度提示"

        s = 40
        if 48 <= p["midi"] <= 72: s += 10
        elif p["midi"] < 48: s += 6
        s += min(15, 15 * p["duration"])
        s += DYNAMIC_SCORE.get(p["dynamic"], 5) * 0.5
        if p["is_chord"]: s += 10
        s -= min(45, 5.0 * gs)
        s += bonus
        return s, gs, ge, vw, "延迟同度提示"

    s = 30
    diff = p["midi"] - v["midi"]
    octave_dist = abs(diff) / 12
    if p.get("accent"): s += 15
    if 0.9 <= octave_dist <= 1.1:
        s += 15 if diff > 0 else 5
    elif 1.9 <= octave_dist <= 2.1:
        s += 5 if diff > 0 else 2
    s += min(15, 15 * p["duration"])
    s += DYNAMIC_SCORE.get(p["dynamic"], 5)
    s += min(20, (p.get("repeat_count", 1) - 1) * 10)
    s -= min(45, 5.0 * gs)
    s += bonus
    return s, gs, ge, vw, "八度转位提示"

def score_D(v, p, piano, voice_all):
    gs = v["onset"] - p["onset"]
    ge = v["onset"] - (p["onset"] + p["duration"])
    s = 0
    if p["midi"] <= 48: s += 25
    elif p["midi"] <= 55: s += 20
    elif p["midi"] <= 60: s += 15
    elif p["midi"] <= 64: s += 8
    
    if p["midi"] == v["midi"]: s += 40
    elif p["pc"] == v["pc"]: s += 25
    
    s += min(15, 15 * p["duration"])
    if gs <= 1: s += 15
    elif gs <= 2: s += 12
    elif gs <= 3: s += 8
    elif gs <= 4: s += 5
    
    if p["part"] in BASS_PARTS: s += 5
    if not p["is_chord"]: s += 5
    if ge <= 1: s += 10
    elif ge <= 2: s += 5
    
    interference = 0
    for other in piano:
        if other is p: continue
        if other["onset"] >= p["onset"] and other["onset"] < v["onset"]:
            interference += 1
    s -= min(10, interference * 2)
    
    vw, bonus = voice_status(p, v, voice_all)
    s += bonus
    return s, gs, ge, interference, vw

def export_to_csv(filename, rows, cols):
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"已成功导出：{filename}")

if __name__ == "__main__":
    voice_all, piano = load()
    for p in piano:
        count = 1
        for q in piano:
            if q is p: continue
            if q["midi"] == p["midi"] and 0 < p["onset"] - q["onset"] <= 2.0:
                count += 1
        p["repeat_count"] = count

    voice_targets = [v for v in voice_all if v["lyric"]]

    # 同音级提示
    rows_A = []
    for v in voice_targets:
        cands = [p for p in piano if p["pc"] == v["pc"] and p["onset"] < v["onset"] and (v["onset"] - p["onset"]) <= 8]
        if not cands: continue
        scored = []
        for p in cands:
            s, gs, ge, vw, a_type = score_A(v, p, voice_all)
            scored.append((s, gs, ge, vw, a_type, p))
        scored.sort(key=lambda x: -x[0])
        for s, gs, ge, vw, a_type, p in scored[:2]:
            rows_A.append(dict(
                lyric=v["lyric"], measure=v["measure"], beat=round(v["beat"], 2),
                grace=(v["duration"] == 0), target_midi=v["midi"], hint_midi=p["midi"],
                hint_part=p["part"], target_onset=round(v["onset"], 3),
                hint_onset=round(p["onset"], 3), gap_s=round(gs, 2), gap_e=round(ge, 2),
                dyn=p["dynamic"], chord=p["is_chord"], voice_window=vw, a_type=a_type, score=round(s, 1),
            ))

    # 演奏提示
    rows_D = []
    for v in voice_targets:
        cands = [p for p in piano if p["onset"] < v["onset"] and p["pc"] == v["pc"] and p["midi"] <= 67 and (v["onset"] - p["onset"]) <= 6]
        if not cands: continue
        scored = []
        for p in cands:
            s, gs, ge, interf, vw = score_D(v, p, piano, voice_all)
            scored.append((s, gs, ge, interf, vw, p))
        scored.sort(key=lambda x: -x[0])
        for s, gs, ge, interf, vw, p in scored[:2]:
            rows_D.append(dict(
                lyric=v["lyric"], measure=v["measure"], beat=round(v["beat"], 2),
                grace=(v["duration"] == 0), target_midi=v["midi"], hint_part=p["part"],
                target_onset=round(v["onset"], 3), hint_midi=p["midi"], hint_onset=round(p["onset"], 3),
                gap_s=round(gs, 2), gap_e=round(ge, 2), same_midi=(p["midi"] == v["midi"]),
                voice_window=vw, interf=interf, score=round(s, 1),
                pedal=f"在 {p['onset']:.2f} 踩踏板，保持到 {v['onset']:.2f}",
            ))

    rows_D.sort(key=lambda r: -r["score"])

    cols_A = ["lyric", "measure", "beat", "grace", "target_midi", "hint_midi", "hint_part", "hint_onset", "gap_s", "gap_e", "dyn", "chord", "voice_window", "a_type", "score", "target_onset"]
    export_to_csv(OUTPUT_A_CSV, rows_A, cols_A)

    cols_D = ["lyric", "measure", "beat", "grace", "target_midi", "hint_part", "hint_midi", "hint_onset", "gap_s", "gap_e", "same_midi", "voice_window", "interf", "score", "pedal", "target_onset"]
    export_to_csv(OUTPUT_D_CSV, rows_D, cols_D)