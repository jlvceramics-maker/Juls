"""Build reels: pause-trimmed segments -> concat -> karaoke ASS subs -> title overlay -> loudnorm.

Layout of a reel folder (ROOT = parent of scripts/):
  inbox/<CLIP>.MOV       source takes from the phone
  edit/fonts/ReelSub.ttf subtitle font
  scripts/build.py, scripts/title.mjs
Fill REELS and TITLES below, then: python3 scripts/build.py [reel_name]
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDIT = f"{ROOT}/edit"
OUT = f"{EDIT}/out"
TMP = f"{EDIT}/clips"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

REELS = {
    # "reel_name": ["CLIP_1", "CLIP_2"],  # files in inbox/ without .MOV, in order
    "example": ["IMG_0001"],
}
TITLES = {
    # "reel_name": ("line 1", "line 2 with [accent]"),
    "example": ("Первая строка", "вторая [акцент]"),
}
END_LIMIT = {}
START_AT = {}
TITLE_END = {}  # reel_name -> seconds when the title fades out (default: end of hook)
CARDS = {}
ICONS = {}  # reel_name -> ["obsidian"] adds a second tile next to Claude

GRADE = "null"
BADGE_CY = 250  # no grade: clean iPhone image

PAUSE_MAX = 0.5   # silences longer than this get shortened
KEEP_AFTER = 0.15  # keep after speech end
KEEP_BEFORE = 0.20  # keep before next speech start
HEAD_PAD = 0.12
TAIL_PAD = 0.25


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:]); sys.exit(1)
    return r


def silences(src):
    r = subprocess.run(["ffmpeg", "-i", src, "-af", "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(s, e))


def duration(src):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]).stdout)


def segments(name):
    src = f"{ROOT}/inbox/{name}.MOV"
    dur = END_LIMIT.get(name, duration(src))
    sil = silences(src)
    words = json.load(open(f"{EDIT}/transcripts/{name}.json"))["words"]
    first_w, last_w = words[0]["start"], min(words[-1]["end"], dur)
    # speech start: end of leading silence, else first word
    start = first_w
    for a, b in sil:
        if a <= 0.05: start = max(b, 0) ; break
    start = max(0, min(start, first_w) - HEAD_PAD)
    start = START_AT.get(name, start)
    # speech end: start of trailing silence
    end = last_w
    for a, b in sil:
        if a > last_w - 0.6 and a < dur: end = a; break
    end = min(dur, max(end, start + 0.5) + TAIL_PAD)
    segs, cur = [], start
    for a, b in sil:
        if a <= start + 0.05 or b >= end - 0.05: continue
        if b - a > PAUSE_MAX:
            segs.append((cur, a + KEEP_AFTER)); cur = b - KEEP_BEFORE
    segs.append((cur, end))
    return src, segs, words


FIX = [
    (r"^[Кк]лод[а-я]*", "Claude"), (r"^Репозитория$", "Репозиторий"), (r"^100-200$", "100–200"),
    (r"^[Ии]нстаграм[а-я]*", "Instagram"), (r"твоем", "твоём"), (r"моем", "моём"), (r"^все$", "всё"), (r"^берешь$", "берёшь"),
    (r"^5-10$", "5–10"),
]
KEEP_TOGETHER = {("claude", "code"), ("ssh", "ключ"), ("ssh", "подключения"), ("в", "codex")}


def fix_words(words):
    text = " ".join(w["text"] for w in words)
    # apply fixes on joined tokens, then re-split while keeping timing per original token
    out = []
    i = 0
    while i < len(words):
        w = dict(words[i])
        if i + 1 < len(words) and words[i + 1]["text"].startswith("-"):
            # merge hyphen continuation tokens
            j = i + 1; txt = w["text"]
            while j < len(words) and words[j]["text"].startswith("-"):
                txt += words[j]["text"]; j += 1
            w["text"] = txt; w["end"] = words[j - 1]["end"]; i = j
        else:
            i += 1
        out.append(w)
    m = []
    for w in out:
        if m and m[-1]["text"].lower() == "по" and w["text"].lower().startswith("жизненн"):
            m[-1] = {**m[-1], "text": "пожизненной" + w["text"][9:], "end": w["end"]}
        else:
            m.append(w)
    out = m
    for w in out:
        for a, b in FIX:
            w["text"] = re.sub(a, b, w["text"])
    # split "Prompt Motion" token into two? keep as one token
    return out


def chunk(words):
    """<=3 words, break after punctuation, no dangling single word, keep pairs."""
    chunks, cur = [], []
    MAXC = 17
    for k, w in enumerate(words):
        if cur and len(" ".join(x["text"] for x in cur + [w])) > MAXC:
            chunks.append(cur); cur = []
        cur.append(w)
        t = w["text"]
        nxt = words[k + 1]["text"] if k + 1 < len(words) else None
        pair = nxt and (re.sub(r"\W", "", t).lower(), re.sub(r"\W", "", nxt).lower()) in KEEP_TOGETHER
        punct = bool(re.search(r"[.,!?…:]$", t))
        length = sum(len(x["text"]) for x in cur)
        if pair:
            continue
        if punct or len(cur) >= 3 or length >= MAXC - 2:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    # merge single-word chunks into neighbour when short
    merged = []
    for c in chunks:
        if merged and len(c) == 1 and len(merged[-1]) < 3 and not re.search(r"[.!?]$", merged[-1][-1]["text"]) \
                and len(" ".join(x["text"] for x in merged[-1] + c)) <= 17:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return merged


def to_out(t, segs, offs):
    for (a, b), o in zip(segs, offs):
        if t < a: return o
        if t <= b: return o + (t - a)
    return offs[-1] + segs[-1][1] - segs[-1][0]


def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


WHITE = "&H00FFFFFF"
ACTIVE = "{\\c&H00A3F4FF&}"  # #FFF4A3, active word
RESET = "{\\c&H00FFFFFF&}"
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


def clean(t):
    t = re.sub(r"[.,!…:;]+$", "", t)
    return t.upper()


def build(reel, names):
    seg_files, events, offset = [], [], 0.0
    hook_end = None
    cards = []
    for name in names:
        src, segs, words = segments(name)
        words = fix_words(words)
        offs = []
        for i, (a, b) in enumerate(segs):
            d = b - a
            f = f"{TMP}/{reel}_{name}_{i}_g0.mp4"
            if not os.path.exists(f): run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-i", src, "-t", f"{d:.3f}",
                 "-vf", f"scale=1080:1920:flags=lanczos,fps=30,{GRADE},format=yuv420p",
                 "-af", f"aresample=48000,afade=t=in:st=0:d=0.03,afade=t=out:st={d-0.03:.3f}:d=0.03",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-c:a", "aac", "-b:a", "192k",
                 "-ar", "48000", "-ac", "2", f])
            offs.append(offset + sum(s[1] - s[0] for s in segs[:i]))
            seg_files.append(f)
        clip_end = offset + sum(b - a for a, b in segs)
        words = [w for w in words if w["start"] < segs[-1][1] - 0.1]
        for c in chunk(words):
            st = to_out(c[0]["start"], segs, offs)
            en = to_out(c[-1]["end"], segs, offs)
            events.append([st, max(en, st + 0.35), [clean(w["text"]) for w in c], [to_out(w["start"], segs, offs) for w in c]])
        for a, b, png in CARDS.get(name, []):
            cards.append([to_out(a, segs, offs), clip_end if b is None else to_out(b, segs, offs), png])
        offset = clip_end
        if hook_end is None: hook_end = clip_end
    # sequential, no overlap, fill tiny gaps
    events.sort()
    for i in range(len(events) - 1):
        nxt = events[i + 1][0]
        if events[i][1] > nxt or nxt - events[i][1] < 0.25:
            events[i][1] = nxt
    events[-1][1] = min(events[-1][1] + 0.3, offset)
    ass = f"{EDIT}/{reel}.ass"
    with open(ass, "w") as fh:
        fh.write(ASS_HEAD)
        for st, en, toks, wts in events:
            bounds = [st] + [min(max(t, st), en) for t in wts[1:]] + [en]
            for i in range(len(toks)):
                a, b = bounds[i], bounds[i + 1]
                if b - a < 0.01: continue
                txt = " ".join((ACTIVE + t + RESET) if j == i else t for j, t in enumerate(toks))
                fh.write(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,{txt}\n")
    lst = f"{TMP}/{reel}.txt"
    open(lst, "w").write("".join(f"file '{f}'\n" for f in seg_files))
    base = f"{TMP}/{reel}_base.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    final = f"{OUT}/{reel}.mp4"
    title = f"{EDIT}/titles/{reel}.png"
    T = TITLE_END.get(reel, hook_end)
    badge = f"{EDIT}/titles/icons_{reel}.png"
    pop = "if(lt(t,0.4),0.5+0.5*(1+2.70158*pow(t/0.4-1,3)+1.70158*pow(t/0.4-1,2)),1)"
    vf = (f"[1:v]format=rgba,fade=t=out:st={T-0.3:.2f}:d=0.3:alpha=1[t];"
          f"[2:v]format=rgba,scale=w='trunc(iw*{pop}/2)*2':h=-2:eval=frame,"
          f"fade=t=in:st=0:d=0.12:alpha=1,fade=t=out:st={T-0.3:.2f}:d=0.3:alpha=1[ic];"
          f"[0:v]null[vb];"
          f"[vb][ic]overlay=x='(W-w)/2':y='250-h/2':eval=frame:shortest=1[vi];[vi][t]overlay=0:0:shortest=1[c0];")
    ins = []
    for k, (a, b, png) in enumerate(cards):
        fin = k == 0 or a - cards[k - 1][1] > 0.05
        fout = k == len(cards) - 1 or cards[k + 1][0] - b > 0.05
        f = "format=rgba"
        if fin: f += f",fade=t=in:st={a:.3f}:d=0.18:alpha=1"
        if fout: f += f",fade=t=out:st={b-0.18:.3f}:d=0.18:alpha=1"
        y = f"if(lt(t,{a+0.22:.3f}),40*pow(1-(t-{a:.3f})/0.22,2),0)" if fin else "0"
        vf += f"[{3+k}:v]{f}[k{k}];[c{k}][k{k}]overlay=0:'{y}':eval=frame:enable='between(t,{a:.3f},{b:.3f})'[c{k+1}];"
        ins += ["-loop", "1", "-t", f"{offset:.3f}", "-i", f"{EDIT}/cards/{png}.png"]
    vf += f"[c{len(cards)}]subtitles='{ass}':fontsdir='{EDIT}/fonts'[v]"
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-loop", "1", "-i", title, "-loop", "1", "-i", badge, *ins,
         "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", final])
    print(f"{reel}: {offset:.2f}s, {len(events)} subs")


if __name__ == "__main__":
    only = sys.argv[1:] or list(REELS)
    for r in only:
        l1, l2 = TITLES[r]
        run(["node", f"{ROOT}/scripts/title.mjs", f"{EDIT}/titles/icons_{r}.png", f"{EDIT}/titles/{r}.png", l1, l2, *ICONS.get(r, [])])
        build(r, REELS[r])
