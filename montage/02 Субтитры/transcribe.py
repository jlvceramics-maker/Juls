"""transcribe.py <video> <out.json> — faster-whisper word timestamps (run with flexi venv)."""
import sys, json, subprocess, os, tempfile
from faster_whisper import WhisperModel

src, out = sys.argv[1], sys.argv[2]
wav = os.path.join(tempfile.gettempdir(), os.path.basename(src) + ".wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
m = WhisperModel("large-v3", device="cpu", compute_type="int8")
segs, _ = m.transcribe(wav, language="ru", word_timestamps=True, vad_filter=True,
                       vad_parameters={"min_silence_duration_ms": 500}, condition_on_previous_text=False,
                       initial_prompt="Claude, Клод, Claude Code, промпт, скилл, нейросеть, ChatGPT, Instagram, рилс.")
words = [{"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for s in segs for w in s.words]
json.dump({"words": words, "text": " ".join(w["text"] for w in words)}, open(out, "w"), ensure_ascii=False, indent=1)
print(os.path.basename(src), len(words), "words")
