#!/usr/bin/env python3
"""
ASPR Oracle Unified Launcher v1.0
• Servidor Web UI (index + dashboard)
• Conector JS embebido (resiliente, offline-first)
• Synth 8-bit corregido (pygame + numpy)
• Lanzador de demos (Detective, PvP, Nodo)
Estética C64 · Confianza estructural · Ed25519 ready
"""
import sys, os, time, threading, argparse, webbrowser, subprocess
import http.server, socketserver
import pygame, numpy as np

# ═══════════════════════════════════════════════════════════
# 1. HTML + JS EMBEBIDO (Conector corregido)
# ═══════════════════════════════════════════════════════════
BASE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
:root{--bg:#101040;--fg:#80ff80;--cyan:#54ffff;--yellow:#f0f050;--red:#ff5050;--dim:#8080c0;--grid:#1c1c58}
body{background:var(--bg);color:var(--fg);font-family:'Courier New',monospace;margin:0;padding:20px;line-height:1.5}
a{color:var(--cyan);text-decoration:none}a:hover{text-decoration:underline}
h1,h2{color:var(--yellow);margin:10px 0 5px;font-weight:normal}
.container{max-width:900px;margin:0 auto}
table{width:100%;border-collapse:collapse;margin:10px 0}
th,td{border:1px solid var(--grid);padding:6px 8px;text-align:left;font-size:13px}
th{color:var(--cyan);background:rgba(8,8,30,0.6)}
code{background:#0a0a20;padding:2px 6px;border-radius:3px;color:var(--yellow)}
.status{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0;font-size:13px}
.status span{background:#0a0a20;padding:3px 8px;border:1px solid var(--dim);border-radius:2px}
.lab-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:15px 0}
.lab-card{background:#0a0a20;border:1px solid var(--dim);padding:12px;border-radius:4px}
.lab-card h3{margin:0 0 6px;color:var(--cyan)}
.lab-card p{margin:0 0 10px;font-size:12px;color:var(--dim)}
.lab-btn{display:inline-block;padding:4px 10px;background:#101040;border:1px solid var(--fg);color:var(--fg);text-decoration:none;border-radius:2px;margin-right:6px}
.lab-btn:hover{background:var(--fg);color:var(--bg)}
.legend{border-top:1px dashed var(--dim);border-bottom:1px dashed var(--dim);padding:10px 0;margin:20px 0;text-align:center;color:var(--dim);font-size:12px;letter-spacing:1px}
@keyframes blink{50%{opacity:0}}.blink{animation:blink 1s step-end infinite}
footer{margin-top:30px;padding-top:15px;border-top:1px dashed var(--dim);font-size:11px;color:var(--dim)}
</style>
</head>
<body>
<div class="container">
  <h1>{title} <span class="blink">_</span></h1>
  <nav><a href="#status">Status</a> · <a href="#labs">Labs</a> · <a href="#protocol">Protocol</a> · <a href="mailto:asproraclenode@gmail.com">Contact</a></nav>
  <p>// open protocol · structural trust · ed25519</p>

  <section id="status">
    <h2>🖥️ ASPR Oracle Node v2.1</h2>
    <div class="status">
      <span><strong>Blocks:</strong> <span data-aspr="blocks">—</span></span>
      <span><strong>Karma Avg:</strong> <span data-aspr="karma">—</span></span>
      <span><strong>Online:</strong> <span data-aspr="online">—</span></span>
      <span><strong>Vault:</strong> <span data-aspr="vault">—</span></span>
      <span><strong>Fingerprint:</strong> <span data-aspr="fp">—</span></span>
    </div>
    <table>
      <thead><tr><th>device_id</th><th>ip</th><th>type</th><th>karma</th><th>latency</th><th>status</th></tr></thead>
      <tbody id="aspr-devices"><tr><td colspan="6" style="color:var(--dim);text-align:center">⏳ Sincronizando...</td></tr></tbody>
    </table>
  </section>

  <section id="labs">
    <h2>🧪 KIDSLAB & DEMOS</h2>
    <div class="lab-grid">
      <div class="lab-card"><h3>🔍 Detective Lab</h3><p>Matrices A+B=C · Lógica pura · Modo Solo</p><a class="lab-btn" href="https://github.com/ramigardner/aspr-gardener/raw/main/detective_lab.py">▼ Descargar .py</a></div>
      <div class="lab-card"><h3>⚔️ Kids Lab PvP</h3><p>Hackers vs Nerds · Logo Turtle · CPU Rival</p><a class="lab-btn" href="https://github.com/ramigardner/aspr-gardener/raw/main/kinderlabs_demo.py">▼ Descargar .py</a></div>
      <div class="lab-card"><h3>🎵 Oracle Synth</h3><p>8-bit Karma Sonoro · Offline/LAN</p><a class="lab-btn" href="#run-synth">▶ Abrir Synth</a></div>
    </div>
  </section>

  <div class="legend">// CONFIANZA VERIFICABLE · NO POR CONSENSO · FIRMA ED25519 · K = M·0.30 + C·0.25 + A·0.20 + E·0.15 + R·0.10</div>

  <section id="protocol">
    <h2>📜 Protocol Architecture</h2>
    <p><code>K = M·0.30 + C·0.25 + A·0.20 + E·0.15 + R·0.10</code></p>
    <p>Federation: <code>K_fed = Σ(K_node × K_local) / Σ(K_node)</code> · LocIVault Chain · Ed25519 Signed</p>
  </section>

  <footer>
    <p>ASPR Oracle Node v2.1 · Protocol v1.1 · <a href="https://github.com/ramigardner/aspr-gardener">ramigardner</a></p>
    <p>Support: <code>Solana J2mevaG4qz1vFSyGcJ3fPsKnBip7o8pYKm5r9TaUycDZ</code></p>
  </footer>
</div>
<script>
(function(){
const $=s=>document.querySelector(s),$$=s=>document.querySelectorAll(s);
let ep=null,online=false,delay=2500;
async function get(p){try{const c=new AbortController();const t=setTimeout(()=>c.abort(),3000);const r=await fetch(ep+p,{signal:c.signal,headers:{Accept:'application/json'}});clearTimeout(t);return r.ok?await r.json():null}catch{return null}}
async function discover(){for(const c of[window.location.origin,"http://localhost:7771"]){if(await get("/api/state")){ep=c;return true}}return false}
function render(d){if(!d)return;const dv=d.devices||{};const vl=Object.values(dv);const k=vl.map(v=>v.karma||0);const avg=k.length?(k.reduce((a,b)=>a+b,0)/k.length).toFixed(3):'—';
$$('[data-aspr="blocks"]').forEach(e=>e.textContent=d.vault_entries);
$$('[data-aspr="karma"]').forEach(e=>e.textContent=avg);
$$('[data-aspr="online"]').forEach(e=>e.textContent=vl.filter(v=>v.online).length);
$$('[data-aspr="vault"]').forEach(e=>e.textContent=d.vault_ok?'✅ INTEGRIDAD OK':'❌ FALLO');
$$('[data-aspr="fp"]').forEach(e=>e.textContent=d.public_key?`${d.public_key.slice(8,16)}...`:'—');
const tb=$('#aspr-devices');
if(tb)tb.innerHTML=vl.map(v=>`<tr><td>${v.id}</td><td>${v.ip}</td><td>${v.tipo||'—'}</td><td>${(v.karma||0).toFixed(3)}</td><td>${v.latency||'—'}ms</td><td style="color:${v.online?'#80ff80':'#ff5050'}">${v.online?'ONLINE':'OFFLINE'}</td></tr>`).join('')}
async function tick(){if(!ep){if(!(await discover())){delay=Math.min(delay*1.4,10000);setTimeout(tick,delay);return}delay=2500}
const s=await get("/api/state");
if(s){online=true;delay=2500;localStorage.setItem('aspr_c',JSON.stringify({t:Date.now(),d:s}));render(s)}else{online=false;delay=Math.min(delay*1.5,10000);const c=JSON.parse(localStorage.getItem('aspr_c')||'null');if(c?.d)render(c.d)}
setTimeout(tick,delay)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',tick);else tick()})();
</script>
</body></html>"""

# ═══════════════════════════════════════════════════════════
# 2. SERVIDOR WEB (Puerto 8000)
# ═══════════════════════════════════════════════════════════
def start_web(port=8000):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                html = BASE_HTML.format(title="ASPR Oracle Network")
            elif self.path == "/dashboard.html":
                html = BASE_HTML.format(title="🌿 ASPR ORACLE DASHBOARD")
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200); self.send_header("Content-type","text/html")
            self.end_headers(); self.wfile.write(html.encode())
        def log_message(self, format, *args): pass
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"🌐 UI Web: http://localhost:{port} (Index + Dashboard)")
        try: webbrowser.open(f"http://localhost:{port}")
        except: pass
        httpd.serve_forever()

# ═══════════════════════════════════════════════════════════
# 3. SYNTH 8-BIT CORREGIDO (Offline + LAN opcional)
# ═══════════════════════════════════════════════════════════
class OracleSynth:
    def __init__(self, lan=False):
        pygame.init()
        try: pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except: print("⚠️ Mixer no disponible. Audio silencioso.")
        self.screen = pygame.display.set_mode((800, 400))
        pygame.display.set_caption("🎵 ASPR Oracle Synth v1.0")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 14)
        self.font_lg = pygame.font.SysFont("monospace", 18)
        self.karma = {"M":0.30,"C":0.25,"A":0.20,"E":0.15,"R":0.10}
        self.active = []
        self.lan = lan

    def _play(self, freq, dur=0.15, vol=0.3, mod=0.0):
        try:
            sr, n = 22050, int(22050*dur)
            t = np.linspace(0, dur, n, endpoint=False)
            wave = np.where((t*freq)%1.0 < 0.5, 1.0, -1.0)
            if mod > 0: wave *= np.sin(2*np.pi*mod*t)
            env = np.ones(n); env[:int(n*0.05)] = np.linspace(0,1,int(n*0.05)); env[int(n*0.05):] = np.linspace(1,0.01,len(env)-int(n*0.05))
            snd = (wave*env*vol*32767).astype(np.int16)
            stereo = np.column_stack((snd, snd))
            sound = pygame.sndarray.make_sound(stereo)
            sound.play()
            self.active.append({"snd":sound, "t":time.time()+dur})
        except: pass

    def run(self):
        mapping = {pygame.K_a:("M",261.63), pygame.K_s:("C",293.66), pygame.K_d:("A",329.63),
                   pygame.K_f:("E",349.23), pygame.K_g:("R",392.00), pygame.K_h:("C",440.00)}
        labels = ["M:Memory","C:Cycles","A:Anchor","E:Efficiency","R:Correction","C:Harmony"]
        running = True
        while running:
            self.clock.tick(60)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: running=False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE: running=False
                    elif ev.key in mapping:
                        comp, freq = mapping[ev.key]
                        self._play(freq, vol=self.karma[comp], mod=0.12 if comp=="R" else 0.0)
                    elif ev.key == pygame.K_o: self.lan = not self.lan
            now = time.time()
            self.active = [n for n in self.active if n["t"] > now]
            self.screen.fill((16,16,64))
            for i in range(0,800,32): pygame.draw.line(self.screen,(28,28,88),(i,0),(i,400))
            for i in range(0,400,32): pygame.draw.line(self.screen,(28,28,88),(0,i),(800,i))
            for i,(k,w) in enumerate(self.karma.items()):
                c = ((84,255,255),(240,240,80),(112,255,112),(255,160,40),(220,80,220))[i]
                pygame.draw.rect(self.screen, (10,10,40), (80, 100+i*30, 120, 12))
                pygame.draw.rect(self.screen, c, (80, 100+i*30, int(120*w), 12))
                self.screen.blit(self.font.render(f"{k} ({w:.2f}) {labels[i]}", True, c), (210, 98+i*30))
            mode = "🌐 LAN ON" if self.lan else "🔒 OFFLINE"
            col = (84,255,255) if self.lan else (240,240,80)
            self.screen.blit(self.font_lg.render("🎵 ASPR ORACLE SYNTH v1.0", True, (240,240,80)), (250, 30))
            self.screen.blit(self.font.render(f"[A][S][D][F][G][H] · [O] LAN · {mode}", True, col), (150, 60))
            t = pygame.time.get_ticks()/1000
            for i in range(1,400):
                y1 = 280 + int(np.sin(t*5 + i*0.05)*20)
                y2 = 280 + int(np.sin(t*5 + (i+1)*0.05)*20)
                pygame.draw.line(self.screen, (84,255,255), (50+i, y1), (50+i+1, y2), 2)
            pygame.display.flip()
        pygame.quit()

# ═══════════════════════════════════════════════════════════
# 4. LANZADOR
# ═══════════════════════════════════════════════════════════
def run_game(name):
    if not os.path.exists(name): print(f"❌ {name} no encontrado en esta carpeta."); return
    print(f"🚀 Ejecutando {name}...")
    subprocess.run([sys.executable, name])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default="menu", choices=["web","synth","detective","pvp","node","menu"])
    args = parser.parse_args()
    if args.mode == "web": start_web()
    elif args.mode == "synth": OracleSynth().run()
    elif args.mode == "detective": run_game("detective_lab.py")
    elif args.mode == "pvp": run_game("kinderlabs_demo.py")
    elif args.mode == "node": run_game("aspr_oracle_node_v2_1.py")
    else:
        print("\n🌿 ASPR ORACLE UNIFIED v1.0")
        print("python aspr_unified.py web       # Abre Index + Dashboard (puerto 8000)")
        print("python aspr_unified.py synth     # Abre Synth 8-bit (teclas A-H)")
        print("python aspr_unified.py detective # Lanza Detective Lab")
        print("python aspr_unified.py pvp       # Lanza Kids Lab PvP")
        print("python aspr_unified.py node      # Inicia tu nodo API (puerto 7771)")
        print("\n💡 El dashboard se conecta automáticamente a http://localhost:7771/api/state")
        print("🔒 Confianza estructural · Offline-first · Firma Ed25519\n")