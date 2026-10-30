#!/usr/bin/env python3
"""Clickly reel engine.  python3 build.py spec.json OUT_DIR  ->  OUT_DIR/reel.mp4 + cover.jpg
spec.json: {"scenes":[{"type":"hook"|"card"|"pop"|"list"|"trio"|"cta"|"logo", "say":"texto para la voz", ...}]}
Ver README.md para los campos de cada escena."""
import json, os, sys, wave, subprocess, shutil, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kok
spec = json.load(open(sys.argv[1], encoding='utf-8')); OUT = os.path.abspath(sys.argv[2]); os.makedirs(OUT, exist_ok=True)
V = os.environ.get('VOICE', 'em_alex'); SP = float(os.environ.get('SPEED', '1.08')); FPS = 30
SC = spec['scenes']
if SC[-1]['type'] != 'logo': SC.append({'type': 'logo'})
MIN = {'hook': 3.0, 'card': 3.0, 'pop': 2.8, 'list': 4.5, 'trio': 3.6, 'cta': 3.4, 'logo': 2.9, 'clip': 5.5}

def rw(p, sr_out=None):
    w = wave.open(p); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32767; sr = w.getframerate()
    if sr_out: a = np.interp(np.arange(int(len(a) * sr_out / sr)) * sr / sr_out, np.arange(len(a)), a)
    return a

# ---------- voz + tiempos ----------
os.makedirs(f'{OUT}/vo', exist_ok=True); D = []; W = []
for i, s in enumerate(SC):
    txt = s.get('say', '').strip()
    if not txt or s['type'] == 'logo': W.append([]); D.append(s.get('min', MIN[s['type']])); continue
    say = txt.replace('PREVENTA', 'preventa').replace('CLIC', 'clic').replace('3D', 'tres D')
    kok.synth(say, f'{OUT}/vo/{i}.wav', V, SP)
    a = rw(f'{OUT}/vo/{i}.wav'); idx = np.where(np.abs(a) > 0.02)[0]; s0, s1 = idx[0] / 24000, idx[-1] / 24000
    words = txt.split(); wt = np.array([max(1, len([c for c in w if c.isalnum()])) for w in words], float); wt /= wt.sum()
    cum = np.concatenate([[0], np.cumsum(wt)]); tm = [s0 + (s1 - s0) * c for c in cum]
    W.append([dict(w=w, t0=tm[k], t1=tm[k + 1]) for k, w in enumerate(words)])
    D.append(max(s.get('min', MIN[s['type']]), s1 + 0.55))
st = [0.0]
for d in D[:-1]: st.append(st[-1] + d)
clicks = []
for i, s in enumerate(SC):
    if s['type'] in ('card', 'pop') and s.get('pop'): clicks.append(dict(s=i, t=st[i] + D[i] - 0.32))
    if s['type'] == 'list' and s.get('pop'): clicks.append(dict(s=i, t=st[i] + D[i] - 0.32))
    if s['type'] == 'trio': clicks += [dict(s=i, t=st[i] + 0.15 + k * 0.42) for k in range(min(3, len(s.get('pops', []))))]
    if s['type'] == 'clip': clicks += [dict(s=i, t=st[i] + x) for x in s.get('clicks', [])]
    if s['type'] == 'hook' and s.get('clicks'): clicks += [dict(s=i, t=st[i] + 1.75 + k * 0.3) for k in range(len(s.get('pops', [])))]
logoclick = st[-1] + 1.25; total = sum(D)
plan = dict(scenes=SC, st=st, d=D, words=W, clicks=clicks, logoclick=logoclick, total=total,
            logo=json.load(open(f'{HERE}/assets/logo.json')), pops=json.load(open(f'{HERE}/pops.json', encoding='utf-8')))
json.dump(plan, open(f'{OUT}/plan.json', 'w'), ensure_ascii=False)
print('escenas', [round(x, 2) for x in D], 'total', round(total, 2), flush=True)

# ---------- audio ----------
SR = 44100; R = np.random.default_rng
mix = np.zeros(int(total * SR) + SR); venv = np.zeros_like(mix)
def put(t, x, a, buf=None):
    b = mix if buf is None else buf; j = int(t * SR)
    if j < 0: x = x[-j:]; j = 0
    n = min(len(x), len(b) - j)
    if n > 0: b[j:j + n] += x[:n] * a
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, k): return np.convolve(x, np.ones(k) / k, 'same')
def verb(x, dec=0.6):
    ir = R(11).standard_normal(int(dec * SR)) * np.exp(-tt(dec) / (dec / 5)); ir = lp(ir, 8)
    y = np.convolve(x, ir); return y / np.abs(y).max()
for i in range(len(SC)):
    if W[i]: a = rw(f'{OUT}/vo/{i}.wav', SR); put(st[i] + 0.02, a, 1.0); put(st[i] + 0.02, np.ones(len(a)), 1, venv)
def whoosh(d=0.5, seed=1):
    n = R(seed).standard_normal(int(d * SR)); t = tt(d); return (lp(n, 6) - lp(n, 40)) * np.sin(np.pi * t / d) ** 3
def click(seed):
    t = tt(0.06); r = R(seed)
    return r.standard_normal(len(t)) * np.exp(-t / 0.0015) * 0.9 + np.sin(2 * np.pi * 3600 * t) * np.exp(-t / 0.006) * 0.6 + np.sin(2 * np.pi * 1900 * t) * np.exp(-t / 0.01) * 0.35 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.014) * 0.6
def boom(): t = tt(0.6); return np.sin(2 * np.pi * (90 * np.exp(-t * 4) + 38) * t) * np.exp(-t / 0.18)
def popfx(): t = tt(0.14); return np.sin(2 * np.pi * (260 + 1100 * t / 0.14) * t) * np.exp(-t / 0.05)
def sparkle(seed):
    out = np.zeros(int(0.7 * SR))
    for k in range(6):
        f = 2000 + R(seed + k).random() * 3000; t = tt(0.25); s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.06); j = int(k * 0.07 * SR); out[j:j + len(s)] += s[:len(out) - j]
    return out
def riser(d=1.0):
    t = tt(d); n = lp(R(4).standard_normal(len(t)), 3) * (t / d) ** 2.5; return n * 0.7 + np.sin(2 * np.pi * (180 + 900 * (t / d) ** 2) * t) * 0.35 * (t / d) ** 2
def impact():
    t = tt(1.2); y = np.zeros(len(t)); b = boom(); y[:len(b)] += b; n = R(8).standard_normal(len(t)) * np.exp(-t / 0.05) * 0.6; y += n; return y + verb(n * 0.5, 1.0)[:len(t)] * 0.3
L0 = st[-1]
for k in range(1, len(SC) - 1): put(st[k] - 0.34, whoosh(0.5, k), 0.55)
put(L0 - 0.5, whoosh(0.7, 40), 0.6)
for k in range(7): put(L0 + 0.38 + k * 0.075, popfx(), 0.25)
put(logoclick, click(77), 1.0); put(logoclick + 0.18, click(78) * 0.6, 0.5); put(logoclick, impact(), 0.45); put(logoclick + 0.05, sparkle(9), 0.15)
for k in range(3): put(0.05 + k * 0.1, whoosh(0.3, 10 + k), 0.35)
for c in clicks:
    t0 = c['t']; put(t0, click(int(t0 * 100)), 0.9); put(t0 + 0.18, click(int(t0 * 100) + 1) * 0.6, 0.5); put(t0, boom(), 0.35); put(t0 + 0.05, sparkle(int(t0 * 10)), 0.08)
for i, s in enumerate(SC):
    if s['type'] in ('card', 'pop'): put(st[i] + 0.08, popfx(), 0.35)
    if s['type'] == 'hook':
        for k in range(len(s.get('pops', []))): put(st[i] + 1.2 + k * 0.18, popfx(), 0.3)
    if s['type'] == 'list':
        for k in range(len(s.get('items', []))): put(st[i] + 0.35 + k * max(0.35, (D[i] - 1) / max(1, len(s['items'])) * 0.8), popfx(), 0.3)
    if s['type'] == 'trio': put(st[i] - 1.0, riser(1.0), 0.3)
    if s['type'] == 'cta': put(st[i], impact(), 0.6)
bpm = 118; bt = 60 / bpm; music = np.zeros_like(mix); side = np.ones_like(mix)
kick = np.sin(2 * np.pi * (120 * np.exp(-tt(0.3) * 18) + 48) * tt(0.3)) * np.exp(-tt(0.3) / 0.12)
clap = lp(R(5).standard_normal(int(0.2 * SR)), 2) * np.exp(-tt(0.2) / 0.04); clap -= lp(clap, 6)
hat = R(6).standard_normal(int(0.08 * SR)) * np.exp(-tt(0.08) / 0.012); hat -= lp(hat, 3)
prog = [(146.8, 185, 220, 293.7), (123.5, 146.8, 185, 246.9), (98, 123.5, 146.8, 196), (110, 138.6, 164.8, 220)]
def stab(ch, d):
    t = tt(d); y = sum(np.sign(np.sin(2 * np.pi * f * 2 * t)) * 0.3 + np.sin(2 * np.pi * f * 2 * t) for f in ch[1:]); return lp(y, 10) * np.exp(-t / 0.18)
def bass(f, d): t = tt(d); y = np.sin(2 * np.pi * f / 2 * t) + 0.4 * np.sign(np.sin(2 * np.pi * f / 2 * t)); return lp(y, 30) * np.exp(-t / 0.25)
b = 0.0; k = 0; hookend = st[1] if len(st) > 1 else 0
while b < logoclick - 0.05:
    inhook = b < hookend - 0.05; ch = prog[(k // 4) % 4]
    if not inhook or k % 2 == 0: put(b, kick, 0.55, music)
    if k % 2 == 1 and not inhook: put(b, clap, 0.25, music)
    put(b + bt / 2, hat, 0.12, music)
    if not inhook: put(b + bt / 4 * 3, hat, 0.06, music)
    put(b + bt / 2, bass(ch[0], bt / 2), 0.22, music)
    if k % 2 == 0: put(b, stab(ch, bt), 0.10, music)
    j = int(b * SR); n = int(0.25 * SR); seg = side[j:j + n]; side[j:j + n] = np.minimum(seg, 0.45 + 0.55 * (tt(0.25) / 0.25)[:len(seg)])
    b += bt; k += 1
venv = lp(venv, 4000); duck = 1 - 0.5 * np.clip(venv * 3, 0, 1)
mix += music * side * duck * 0.7
mix = mix[:int(total * SR)]; fade = np.ones_like(mix); fade[-int(0.4 * SR):] = np.linspace(1, 0, int(0.4 * SR)); mix *= fade
mix = np.tanh(mix * 1.3); mix = mix / np.abs(mix).max() * 0.95
w = wave.open(f'{OUT}/audio.wav', 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print('audio ok', flush=True)

# ---------- frames ----------
html = open(f'{HERE}/page.html', encoding='utf-8').read().replace('const P=PLAN', 'const P=' + json.dumps(plan, ensure_ascii=False))
open(f'{HERE}/_run.html', 'w', encoding='utf-8').write(html)
fr = f'{OUT}/fr'; shutil.rmtree(fr, ignore_errors=True); os.makedirs(fr)
N = int(total * FPS); WK = int(os.environ.get('WORKERS', '4'))
ps = [subprocess.Popen(['node', f'{HERE}/render.js', f'{HERE}/_run.html', fr, str(N), str(k), str(WK)]) for k in range(WK)]
if any(p.wait() for p in ps): sys.exit('render falló')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', f'{fr}/%05d.jpg', '-i', f'{OUT}/audio.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', f'{OUT}/reel.mp4'], check=True)
cov = int(min(total - 0.1, st[0] + 2.4) * FPS); shutil.copy(f'{fr}/{cov:05d}.jpg', f'{OUT}/cover.jpg')
print('LISTO', f'{OUT}/reel.mp4', round(total, 1), 's')
