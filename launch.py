"""
ASPR Gardener — Launcher de pendrive
=====================================
Corre desde cualquier OS con Python 3.8+.
No requiere instalación en la máquina destino.
Las dependencias se instalan en el pendrive mismo.

Uso:
    python launch.py              # menú interactivo
    python launch.py --sim        # solo simulación
    python launch.py --dashboard  # solo dashboard
    python launch.py --sim --dashboard  # ambos
"""

import sys
import os
import subprocess
import argparse
import platform
import time

# ─── Rutas relativas al pendrive ──────────────────────────────────────────────

ROOT    = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(ROOT, "lib")
LOGS_DIR = os.path.join(ROOT, "logs")
DATA_DIR = os.path.join(ROOT, "data")

for d in (LIB_DIR, LOGS_DIR, DATA_DIR):
    os.makedirs(d, exist_ok=True)

# Inyectar lib/ al path para que las dependencias se encuentren
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

# ─── Colores de terminal (cross-platform) ─────────────────────────────────────

if platform.system() == "Windows":
    os.system("color")  # habilita ANSI en Windows 10+

G  = "\033[32m"
B  = "\033[34m"
Y  = "\033[33m"
R  = "\033[31m"
W  = "\033[0m"
BD = "\033[1m"

# ─── Dependencias requeridas ──────────────────────────────────────────────────

REQUIREMENTS = {
    "flask":    "flask>=2.0",
    "plotly":   "plotly>=5.0",
}

# ─── Utilidades ───────────────────────────────────────────────────────────────

def banner():
    print(f"""
{G}{BD}╔══════════════════════════════════════════╗
║         ASPR Gardener  v1.0              ║
║  Adaptive Structural Pruning & Reporting ║
╚══════════════════════════════════════════╝{W}
  OS detectado : {platform.system()} {platform.release()}
  Python       : {sys.version.split()[0]}
  Pendrive     : {ROOT}
""")


def check_python():
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 8):
        print(f"{R}ERROR: Se requiere Python 3.8+. Versión actual: {major}.{minor}{W}")
        sys.exit(1)


def install_dependencies():
    """Instala dependencias en lib/ dentro del pendrive."""
    missing = []
    for pkg, spec in REQUIREMENTS.items():
        try:
            __import__(pkg)
        except ImportError:
            missing.append(spec)

    if not missing:
        print(f"{G}✓ Dependencias OK{W}")
        return

    print(f"{Y}Instalando dependencias en el pendrive: {', '.join(missing)}{W}")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", LIB_DIR,
        "--quiet",
        "--disable-pip-version-check",
    ] + missing

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{R}Error instalando dependencias:\n{result.stderr}{W}")
        sys.exit(1)

    # Reimportar desde lib/
    import importlib
    for pkg in REQUIREMENTS:
        try:
            importlib.import_module(pkg)
        except ImportError:
            pass

    print(f"{G}✓ Dependencias instaladas en {LIB_DIR}{W}")


# ─── Simulación ───────────────────────────────────────────────────────────────

def run_simulation(requests=10_000_000, epochs=100, save_csv=True):
    """Corre mvp_compare.py y opcionalmente guarda resultados en data/."""
    sim_path = os.path.join(ROOT, "mvp_compare.py")
    if not os.path.exists(sim_path):
        print(f"{R}ERROR: mvp_compare.py no encontrado en {ROOT}{W}")
        sys.exit(1)

    print(f"\n{BD}── Simulación ──────────────────────────────────{W}")

    # Importar directamente para capturar resultados
    import importlib.util
    spec = importlib.util.spec_from_file_location("mvp_compare", sim_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from mvp_compare import Config, simulate, print_report
    cfg = Config(total_requests=requests, epochs=epochs)
    baseline, aspr = simulate(cfg)
    print_report(baseline, aspr)

    if save_csv:
        _save_results(baseline, aspr, cfg)

    return baseline, aspr


def _save_results(baseline, aspr, cfg):
    import csv, datetime
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"results_{ts}.csv")
    keys = list(baseline.keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "baseline", "aspr", "delta_pct"])
        w.writeheader()
        for k in keys:
            bv, av = baseline[k], aspr[k]
            if isinstance(bv, (int, float)) and bv != 0:
                delta = round((av - bv) / bv * 100, 2)
            else:
                delta = "N/A"
            w.writerow({"metric": k, "baseline": bv, "aspr": av, "delta_pct": delta})
    print(f"{G}✓ Resultados guardados en {path}{W}")
    return path


# ─── Dashboard Flask + Plotly ─────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASPR Gardener — Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f8f7f4; color: #1a1a18; }
  header { background: #fff; border-bottom: 1px solid #e5e3de; padding: 1rem 2rem;
           display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 18px; font-weight: 500; }
  header span { font-size: 12px; color: #888; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
          padding: 1.5rem 2rem 0; }
  .metric { background: #fff; border: 1px solid #e5e3de; border-radius: 10px;
            padding: 1rem 1.25rem; }
  .metric-label { font-size: 12px; color: #888; margin-bottom: 4px; }
  .metric-value { font-size: 24px; font-weight: 500; }
  .green { color: #3B6D11; }
  .blue  { color: #185FA5; }
  .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
            padding: 1rem 2rem; }
  .chart-card { background: #fff; border: 1px solid #e5e3de; border-radius: 10px;
                padding: 1rem; }
  .chart-title { font-size: 13px; font-weight: 500; margin-bottom: .5rem; color: #555; }
  .full { grid-column: 1 / -1; }
  .run-form { padding: 0 2rem 1rem; display: flex; gap: 12px; align-items: flex-end;
              flex-wrap: wrap; }
  .run-form label { font-size: 13px; color: #555; display: flex; flex-direction: column;
                    gap: 4px; }
  .run-form input { border: 1px solid #ddd; border-radius: 6px; padding: 6px 10px;
                    font-size: 13px; width: 140px; }
  .run-form button { background: #3B6D11; color: #fff; border: none; border-radius: 6px;
                     padding: 8px 18px; font-size: 13px; cursor: pointer; }
  .run-form button:hover { background: #27500A; }
  #status { font-size: 13px; color: #888; padding: 0 2rem .5rem; min-height: 20px; }
  footer { text-align: center; font-size: 12px; color: #aaa; padding: 1.5rem; }
</style>
</head>
<body>

<header>
  <h1>ASPR Gardener &mdash; Dashboard</h1>
  <span id="ts">cargando...</span>
</header>

<div class="run-form">
  <label>Requests totales
    <input type="number" id="req" value="10000000" step="1000000" min="100000">
  </label>
  <label>Epochs
    <input type="number" id="ep" value="100" min="10" max="500">
  </label>
  <button onclick="runSim()">Correr simulación</button>
</div>
<div id="status"></div>

<div class="grid" id="metrics">
  <div class="metric"><div class="metric-label">Clusters reducidos</div>
    <div class="metric-value green" id="m-clusters">—</div></div>
  <div class="metric"><div class="metric-label">Energía ahorrada</div>
    <div class="metric-value blue" id="m-energy">—</div></div>
  <div class="metric"><div class="metric-label">Impacto latencia p50</div>
    <div class="metric-value" id="m-latency">—</div></div>
</div>

<div class="charts">
  <div class="chart-card"><div class="chart-title">Clusters promedio</div>
    <div id="ch-clusters" style="height:220px"></div></div>
  <div class="chart-card"><div class="chart-title">Energía total</div>
    <div id="ch-energy" style="height:220px"></div></div>
  <div class="chart-card full"><div class="chart-title">Latencia p50 / p95 / p99 (ms)</div>
    <div id="ch-latency" style="height:240px"></div></div>
</div>

<footer>ASPR Gardener &mdash; corriendo desde pendrive &mdash; <span id="root"></span></footer>

<script>
const fmt = (n, dec=2) => typeof n === 'number' ? n.toFixed(dec) : n;
const pct  = (b, a) => b !== 0 ? ((a - b) / b * 100).toFixed(2) + '%' : 'N/A';

async function loadData() {
  const r = await fetch('/api/results');
  if (!r.ok) return null;
  return r.json();
}

async function runSim() {
  const req = document.getElementById('req').value;
  const ep  = document.getElementById('ep').value;
  document.getElementById('status').textContent = 'Corriendo simulación... puede tardar unos segundos.';
  const r = await fetch('/api/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({requests: parseInt(req), epochs: parseInt(ep)})
  });
  const data = await r.json();
  document.getElementById('status').textContent = data.message || '';
  renderData(data);
}

function renderData(data) {
  if (!data || !data.baseline) return;
  const b = data.baseline, a = data.aspr;

  const clDelta = pct(b.avg_clusters, a.avg_clusters);
  const enDelta = pct(b.total_energy, a.total_energy);
  const latDiff = Math.abs(a.lat_p50 - b.lat_p50).toFixed(3);

  document.getElementById('m-clusters').textContent = clDelta;
  document.getElementById('m-energy').textContent   = enDelta;
  document.getElementById('m-latency').textContent  = latDiff + ' ms';
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();

  const layout = (yaxis) => ({
    margin: {t:10, b:30, l:40, r:10},
    legend: {orientation:'h', y:-0.2},
    plot_bgcolor:'#fff', paper_bgcolor:'#fff',
    font: {family:'system-ui', size:12, color:'#555'},
    yaxis
  });
  const cfg = {responsive: true, displayModeBar: false};

  Plotly.newPlot('ch-clusters', [
    {name:'Baseline', x:['Baseline'], y:[b.avg_clusters], type:'bar', marker:{color:'#B4B2A9'}},
    {name:'ASPR',     x:['ASPR'],     y:[a.avg_clusters], type:'bar', marker:{color:'#3B6D11'}},
  ], layout({title:'promedio'}), cfg);

  Plotly.newPlot('ch-energy', [
    {name:'Baseline', x:['Baseline'], y:[b.total_energy], type:'bar', marker:{color:'#B4B2A9'}},
    {name:'ASPR',     x:['ASPR'],     y:[a.total_energy], type:'bar', marker:{color:'#185FA5'}},
  ], layout({title:'unidades'}), cfg);

  Plotly.newPlot('ch-latency', [
    {name:'Baseline p50', x:['p50','p95','p99'],
     y:[b.lat_p50, b.lat_p95, b.lat_p99], type:'bar', marker:{color:'#B4B2A9'}},
    {name:'ASPR p50',     x:['p50','p95','p99'],
     y:[a.lat_p50, a.lat_p95, a.lat_p99], type:'bar', marker:{color:'#378ADD'}},
  ], {...layout({title:'ms'}), barmode:'group'}, cfg);
}

async function init() {
  document.getElementById('root').textContent = window.location.origin;
  const data = await loadData();
  if (data) renderData(data);
}
init();
</script>
</body>
</html>
"""


def run_dashboard(baseline=None, aspr=None, port=7771):
    """Levanta servidor Flask con dashboard Plotly."""
    try:
        from flask import Flask, jsonify, request as freq
    except ImportError:
        print(f"{R}Flask no disponible. Corré primero la simulación para instalar dependencias.{W}")
        sys.exit(1)

    import importlib.util, webbrowser, threading

    sim_path = os.path.join(ROOT, "mvp_compare.py")
    spec = importlib.util.spec_from_file_location("mvp_compare", sim_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    app = Flask(__name__)
    state = {"baseline": baseline, "aspr": aspr}

    @app.route("/")
    def index():
        from flask import Response
        return Response(DASHBOARD_HTML, mimetype="text/html")

    @app.route("/api/results")
    def results():
        if state["baseline"] is None:
            return jsonify({}), 204
        return jsonify({"baseline": state["baseline"], "aspr": state["aspr"]})

    @app.route("/api/run", methods=["POST"])
    def run():
        data = freq.get_json(force=True)
        requests_n = int(data.get("requests", 10_000_000))
        epochs_n   = int(data.get("epochs", 100))
        cfg = mod.Config(total_requests=requests_n, epochs=epochs_n)
        b, a = mod.simulate(cfg)
        state["baseline"] = b
        state["aspr"]     = a
        _save_results(b, a, cfg)
        return jsonify({
            "message": f"Simulación completada: {requests_n:,} requests, {epochs_n} epochs.",
            "baseline": b, "aspr": a
        })

    @app.route("/api/ping")
    def ping():
        return jsonify({"ok": True})

    url = f"http://127.0.0.1:{port}"
    print(f"\n{BD}── Dashboard ────────────────────────────────────{W}")
    print(f"{G}✓ Servidor iniciado en {url}{W}")
    print(f"  Presioná {BD}Ctrl+C{W} para detener.\n")

    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    log = open(os.path.join(LOGS_DIR, "dashboard.log"), "a")
    import logging
    log_handler = logging.StreamHandler(log)
    logging.getLogger("werkzeug").addHandler(log_handler)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


# ─── Menú interactivo ─────────────────────────────────────────────────────────

def menu():
    print(f"{BD}¿Qué querés hacer?{W}\n")
    print("  1. Correr simulación (terminal)")
    print("  2. Abrir dashboard (browser)")
    print("  3. Simulación + dashboard")
    print("  4. Salir\n")
    choice = input("  Opción [1-4]: ").strip()
    return choice


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--sim",       action="store_true")
    p.add_argument("--dashboard", action="store_true")
    p.add_argument("--requests",  type=int, default=10_000_000)
    p.add_argument("--epochs",    type=int, default=100)
    p.add_argument("--port",      type=int, default=7771)
    p.add_argument("--help", "-h", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    banner()
    check_python()

    if args.help:
        print(__doc__)
        sys.exit(0)

    install_dependencies()

    # Modo flags directos
    if args.sim or args.dashboard:
        baseline = aspr = None
        if args.sim:
            baseline, aspr = run_simulation(args.requests, args.epochs)
        if args.dashboard:
            run_dashboard(baseline, aspr, args.port)
        return

    # Menú interactivo
    choice = menu()
    if choice == "1":
        run_simulation()
    elif choice == "2":
        run_dashboard()
    elif choice == "3":
        b, a = run_simulation()
        run_dashboard(b, a)
    elif choice == "4":
        print("Hasta luego.")
    else:
        print(f"{Y}Opción inválida.{W}")
        main()


if __name__ == "__main__":
    main()
