"""Talking-head reel with screen-recording b-roll windows.

Folder: scripts/build.py, scripts/title.mjs, config.json, inbox/ (takes), broll/ (screen recordings), edit/fonts/ReelSub.ttf.

Drop takes into inbox/ (sorted by name = order in reel), then:
    python3 scripts/build.py            # transcribe -> trim long pauses -> plan b-roll -> render
    python3 scripts/build.py --plan     # only print/write the b-roll plan, no render

B-roll windows are placed by trigger words from config.json. To fix placement by hand,
edit edit/plan.json, set "manual": true and run again.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDIT, INBOX, BROLL = f"{ROOT}/edit", f"{ROOT}/inbox", f"{ROOT}/broll"
OUT, TMP, TR, TITLES = f"{EDIT}/out", f"{EDIT}/clips", f"{EDIT}/transcripts", f"{EDIT}/titles"
for d in (OUT, TMP, TR, TITLES): os.makedirs(d, exist_ok=True)
CFG = json.load(open(f"{ROOT}/config.json"))
VENV_PY = os.environ.get("VENV_PY", "python3")  # python with faster-whisper
REMOTION = os.environ.get("NODE_PROJECT", ROOT)  # folder with playwright-core installed

PAUSE_MAX = CFG.get("pause_max", 0.5)
KEEP_AFTER, KEEP_BEFORE, HEAD_PAD, TAIL_PAD = 0.15, 0.20, 0.12, 0.25
CARD_H, CARD_Y, RADIUS = 1400, 140, 44

# b-roll sources: name -> (file, ffmpeg recipe)
BROLL_SPECS = {
    # name: (file in broll/, [(start, end) pieces to keep], optional ffmpeg crop)
    # phone screen recording, two pieces glued together
    "phone": ("phone-demo.mp4", [(1.8, 15.5), (35.5, 40.5)], None),
    # desktop recording, cropped to the panel that matters
    "desktop": ("desktop-demo.mp4", [(1.5, 20.7)], "crop=400:792:2152:640"),
}
CLIP_OF = {"phone": "phone", "desktop_prompt": "desktop", "desktop_answer": "desktop"}  # config window -> source
MAX_SPEED = 2.0  # "fit" windows speed the clip up to show the whole flow, never faster than this


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        print(" ".join(map(str, cmd))[:400]); print(r.stderr[-3000:]); sys.exit(1)
    return r


def duration(src):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]).stdout)


def vsize(src):
    w, h = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", src]).stdout.strip().split(",")[:2]
    return int(w), int(h)


# ---------- b-roll prep ----------
def prep_broll():
    for name, (src, parts, crop) in BROLL_SPECS.items():
        out = f"{BROLL}/{name}.mp4"
        if os.path.exists(out): continue
        s = f"{BROLL}/src/{src}"
        chains = []
        for i, (a, b) in enumerate(parts):
            f = (crop + "," if crop else "") + f"fps=30,scale=-2:{CARD_H}:flags=lanczos,setsar=1"
            chains.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,{f}[p{i}]")
        fc = ";".join(chains) + ";" + "".join(f"[p{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[v]"
        run(["ffmpeg", "-y", "-v", "error", "-i", s, "-filter_complex", fc, "-map", "[v]", "-an",
             "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", out])
        w, h = vsize(out)
        r = RADIUS
        expr = f"if(lte(pow(max(max({r}-X\\,X-(W-1-{r}))\\,0)\\,2)+pow(max(max({r}-Y\\,Y-(H-1-{r}))\\,0)\\,2)\\,{r*r})\\,255\\,0)"
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:d=1",
             "-vf", f"format=gray,geq=lum='{expr}'", "-frames:v", "1", f"{BROLL}/{name}_mask.png"])
        print(f"broll {name}: {w}x{h}, {duration(out):.1f}s")


# ---------- takes ----------
def takes():
    exts = (".mov", ".mp4", ".m4v")
    return sorted(f for f in os.listdir(INBOX) if f.lower().endswith(exts) and not f.startswith("."))


def transcript(name):
    out = f"{TR}/{os.path.splitext(name)[0]}.json"
    if not os.path.exists(out):
        print("transcribing", name, flush=True)
        run([VENV_PY, f"{ROOT}/scripts/transcribe.py", f"{INBOX}/{name}", out])
    return json.load(open(out))["words"]


def silences(src):
    r = subprocess.run(["ffmpeg", "-i", src, "-af", "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(s, e))


def segments(src, words):
    dur = duration(src)
    sil = silences(src)
    first_w, last_w = words[0]["start"], min(words[-1]["end"], dur)
    start = first_w
    for a, b in sil:
        if a <= 0.05: start = max(b, 0); break
    start = max(0, min(start, first_w) - HEAD_PAD)
    end = last_w
    for a, b in sil:
        if last_w - 0.6 < a < dur: end = a; break
    end = min(dur, max(end, start + 0.5) + TAIL_PAD)
    segs, cur = [], start
    for a, b in sil:
        if a <= start + 0.05 or b >= end - 0.05: continue
        if b - a > PAUSE_MAX:
            segs.append((cur, a + KEEP_AFTER)); cur = b - KEEP_BEFORE
    segs.append((cur, end))
    return segs


def fix_words(words):
    out, i = [], 0
    while i < len(words):
        w = dict(words[i])
        j = i + 1
        while j < len(words) and words[j]["text"].startswith("-"):
            w["text"] += words[j]["text"]; w["end"] = words[j]["end"]; j += 1
        i = j
        for a, b in CFG.get("fixes", []):
            w["text"] = re.sub(a, b, w["text"])
        out.append(w)
    return out


def to_out(t, segs, offs):
    for (a, b), o in zip(segs, offs):
        if t < a: return o
        if t <= b: return o + (t - a)
    return offs[-1] + segs[-1][1] - segs[-1][0]


# ---------- subtitles (approved karaoke style) ----------
def chunk(words):
    chunks, cur, MAXC = [], [], 17
    for w in words:
        if cur and len(" ".join(x["text"] for x in cur + [w])) > MAXC:
            chunks.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,!?…:]$", w["text"]) or len(cur) >= 3 or sum(len(x["text"]) for x in cur) >= MAXC - 2:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    merged = []
    for c in chunks:
        if merged and len(c) == 1 and len(merged[-1]) < 3 and not re.search(r"[.!?]$", merged[-1][-1]["text"]) \
                and len(" ".join(x["text"] for x in merged[-1] + c)) <= 17:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return merged


def ass_time(t):
    t = max(0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


ACTIVE, RESET, WHITE = "{\\c&H00A3F4FF&}", "{\\c&H00FFFFFF&}", "&H00FFFFFF"
ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,ReelSub,78,{WHITE},{WHITE},&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(words, total, path):
    events = []
    for c in chunk(words):
        st, en = c[0]["o_start"], c[-1]["o_end"]
        events.append([st, max(en, st + 0.35), [re.sub(r"[.,!…:;]+$", "", w["text"]).upper() for w in c],
                       [w["o_start"] for w in c]])
    events.sort()
    for i in range(len(events) - 1):
        nxt = events[i + 1][0]
        if events[i][1] > nxt or nxt - events[i][1] < 0.25: events[i][1] = nxt
    events[-1][1] = min(events[-1][1] + 0.3, total)
    with open(path, "w") as fh:
        fh.write(ASS_HEAD)
        for st, en, toks, wts in events:
            bounds = [st] + [min(max(t, st), en) for t in wts[1:]] + [en]
            for i in range(len(toks)):
                a, b = bounds[i], bounds[i + 1]
                if b - a < 0.01: continue
                txt = " ".join((ACTIVE + t + RESET) if j == i else t for j, t in enumerate(toks))
                fh.write(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,{txt}\n")
    return len(events)


# ---------- plan ----------
def norm(t): return re.sub(r"[^\w ]", "", t.lower())


def find(words, triggers, after):
    for k, w in enumerate(words):
        if w["o_start"] < after: continue
        pair = norm(w["text"]) + " " + (norm(words[k + 1]["text"]) if k + 1 < len(words) else "")
        if any(norm(t) in (pair if " " in t else norm(w["text"])) for t in triggers):
            return w["o_start"]
    return None


def make_plan(words, total):
    path = f"{EDIT}/plan.json"
    if os.path.exists(path):
        p = json.load(open(path))
        if p.get("manual"): print("plan.json manual: true — using as is"); return p
    lens = {n: duration(f"{BROLL}/{n}.mp4") for n in BROLL_SPECS}
    cta = find(words, CFG["cta_triggers"], 0) or total
    # title holds through the hook: first sentence end after 1.5s, capped
    title_end = CFG.get("title_max_sec", 6.0)
    for w in words:
        if w["o_end"] > 1.5 and re.search(r"[.!?]$", w["text"]):
            title_end = min(title_end, w["o_end"] + 0.2); break
    wins, last = [], title_end
    for name, spec in CFG["broll"].items():
        after = max(spec.get("min_start", 0), last + spec.get("min_gap", 0) if wins else title_end)
        s = find(words, spec["triggers"], after)
        if s is None or s >= cta - 1.0: continue
        wins.append({"name": name, "clip": CLIP_OF[name], "in": spec["in"], "start": round(s, 2),
                     "fit": bool(spec.get("fit"))}); last = s
    wins.sort(key=lambda w: w["start"])
    for i, w in enumerate(wins):
        nxt = wins[i + 1]["start"] if i + 1 < len(wins) else cta - 0.1
        w["end"] = round(min(nxt, w["start"] + lens[w["clip"]] - w["in"] + 1.5), 2)
        rest = lens[w["clip"]] - w["in"]
        w["speed"] = round(min(MAX_SPEED, max(1.0, rest / (w["end"] - w["start"]))), 2) if w["fit"] else 1.0
    wins = [w for w in wins if w["end"] - w["start"] >= 1.0]
    title_end = min(title_end, wins[0]["start"]) if wins else title_end
    p = {"manual": False, "total": round(total, 2), "title_end": round(title_end, 2), "cta": round(cta, 2), "windows": wins}
    json.dump(p, open(path, "w"), ensure_ascii=False, indent=1)
    return p


# ---------- render ----------
def titles():
    icons, title = f"{TITLES}/icons.png", f"{TITLES}/title.png"
    run(["node", f"{ROOT}/scripts/title.mjs", icons, title, CFG["title_line1"], CFG["title_line2"]], cwd=REMOTION)
    cta = f"{TITLES}/cta.png"
    run(["node", f"{ROOT}/scripts/title.mjs", f"{TITLES}/_unused_icons.png", cta, CFG["cta_line1"], CFG["cta_line2"]], cwd=REMOTION)
    return icons, title, cta


def main(plan_only=False):
    prep_broll()
    names = takes()
    if not names: print("inbox/ пуст — положи туда видео с айфона"); sys.exit(1)
    seg_files, allw, offset = [], [], 0.0
    for n in names:
        src = f"{INBOX}/{n}"
        words = fix_words(transcript(n))
        segs = segments(src, words)
        offs = [offset + sum(b - a for a, b in segs[:i]) for i in range(len(segs))]
        for w in words:
            if w["start"] >= segs[-1][1] - 0.1: continue
            w["o_start"], w["o_end"] = to_out(w["start"], segs, offs), to_out(w["end"], segs, offs)
            allw.append(w)
        if not plan_only:
            for i, (a, b) in enumerate(segs):
                d = b - a
                f = f"{TMP}/{os.path.splitext(n)[0]}_{i}_{a:.2f}.mp4"
                if not os.path.exists(f):
                    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-i", src, "-t", f"{d:.3f}",
                         "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
                         "-af", f"aresample=48000,afade=t=in:st=0:d=0.03,afade=t=out:st={d - 0.03:.3f}:d=0.03",
                         "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "aac", "-b:a", "192k",
                         "-ar", "48000", "-ac", "2", f])
                seg_files.append(f)
        cut = sum(b - a for a, b in segs)
        print(f"{n}: {len(segs) - 1} склеек, {cut:.1f}s")
        offset += cut
    total = offset
    plan = make_plan(allw, total)
    print(f"\nпросто лицо до {plan['title_end']}s (заголовок), CTA с {plan['cta']}s, всего {total:.1f}s")
    for w in plan["windows"]:
        print(f"  {w['start']:6.2f}–{w['end']:6.2f}  {w['name']} (клип {w['clip']} с {w['in']}s, x{w.get('speed', 1.0)})")
    if plan_only: return

    dz = CFG.get("dolly_zoom")
    if dz:  # vertigo on the hook: first piece of the first take, background grows, face stays
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import dollyzoom
        src = seg_files[0]
        out = src.replace(".mp4", f"_dz{dz['start']}-{dz['end']}x{dz['scale']}.mp4")
        if not os.path.exists(out): dollyzoom.apply(src, out, dz["start"], dz["end"], dz["scale"])
        seg_files[0] = out
    lst = f"{TMP}/list.txt"
    open(lst, "w").write("".join(f"file '{f}'\n" for f in seg_files))
    base = f"{TMP}/base.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    ass = f"{EDIT}/subs.ass"
    nsubs = write_ass(allw, total, ass)
    icons, title, cta_png = titles()

    inputs = ["-i", base, "-loop", "1", "-t", f"{total:.2f}", "-i", title, "-loop", "1", "-t", f"{total:.2f}", "-i", icons,
              "-loop", "1", "-t", f"{total:.2f}", "-i", cta_png]
    T = plan["title_end"]
    pop = "if(lt(t,0.4),0.5+0.5*(1+2.70158*pow(t/0.4-1,3)+1.70158*pow(t/0.4-1,2)),1)"
    fc = [f"[1:v]format=rgba,fade=t=out:st={T - 0.3:.2f}:d=0.3:alpha=1[t]",
          f"[2:v]format=rgba,scale=w='trunc(560*{pop}/2)*2':h=-2:eval=frame,fade=t=in:st=0:d=0.12:alpha=1,"
          f"fade=t=out:st={T - 0.3:.2f}:d=0.3:alpha=1[ic]",
          f"[3:v]format=rgba,fade=t=in:st={plan['cta']:.2f}:d=0.25:alpha=1[ct]",
          "[0:v]split[face][bgsrc]", "[bgsrc]boxblur=40:2,eq=brightness=-0.10[bg0]"]
    cur, k = "bg0", 4
    for i, w in enumerate(plan["windows"]):
        d = w["end"] - w["start"]
        sp = w.get("speed", 1.0)
        inputs += ["-ss", f"{w['in']:.2f}", "-t", f"{d * sp:.2f}", "-i", f"{BROLL}/{w['clip']}.mp4",
                   "-loop", "1", "-t", f"{d:.2f}", "-i", f"{BROLL}/{w['clip']}_mask.png"]
        fc += [f"[{k}:v]setpts=(PTS-STARTPTS)/{sp},fps=30,tpad=stop_mode=clone:stop_duration={d:.2f},trim=duration={d:.2f},setpts=PTS-STARTPTS[cv{i}]",
               f"[{k + 1}:v]format=gray,setpts=PTS-STARTPTS[m{i}]",
               f"[cv{i}][m{i}]alphamerge,fade=t=in:st=0:d=0.15:alpha=1,setpts=PTS+{w['start']:.3f}/TB[c{i}]",
               f"[{cur}][c{i}]overlay=x=(W-w)/2:y={CARD_Y}:eof_action=pass[bg{i + 1}]"]
        cur, k = f"bg{i + 1}", k + 2
    on = "+".join(f"between(t,{w['start']:.3f},{w['end']:.3f})" for w in plan["windows"]) or "0"
    label = CFG.get("ad_label", "")
    draw = (f",drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='{label}':fontsize=30:fontcolor=white@0.85:"
            f"x=44:y=70:shadowcolor=black@0.5:shadowx=1:shadowy=1") if label else ""
    fc += [f"[face][{cur}]overlay=0:0:enable='{on}'[mix]",
           f"[mix][ic]overlay=x='(W-w)/2':y='250-h/2':eval=frame[m1]",
           f"[m1][t]overlay=0:0[m2]",
           f"[m2][ct]overlay=0:0:enable='gte(t,{plan['cta']:.2f})'{draw},subtitles='{ass}':fontsdir='{EDIT}/fonts'[v]"]
    video = f"{TMP}/video.mp4"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-an",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
         "-pix_fmt", "yuv420p", "-t", f"{total:.3f}", video])
    # loudnorm as a separate audio-only pass (in one graph with video it eats memory)
    audio = f"{TMP}/audio.m4a"
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", audio])
    final = f"{OUT}/reel.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c", "copy",
         "-shortest", "-movflags", "+faststart", final])
    print(f"\nготово: {final} ({total:.1f}s, {nsubs} субтитров, {len(plan['windows'])} вставок)")


if __name__ == "__main__":
    main(plan_only="--plan" in sys.argv)
