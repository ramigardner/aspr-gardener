"""
ASPR Gardener — MVP Comparison
================================
Simula dos sistemas procesando N requests:
  - Baseline: sin podado (clusters acumulan complejidad)
  - ASPR:     con agente jardinero adaptativo

Métricas reportadas:
  - Clusters activos promedio
  - Energía consumida total
  - Latencia p50 / p95 / p99
  - Ciclos de podado ejecutados

Uso:
    python mvp_compare.py
    python mvp_compare.py --requests 1_000_000 --epochs 100
"""

import argparse
import random
import time
import math
from dataclasses import dataclass, field
from typing import List


# ─── Config ───────────────────────────────────────────────────────────────────

@dataclass
class Config:
    total_requests: int = 10_000_000
    epochs: int = 100                   # cada cuántos requests se evalúa
    initial_clusters: int = 24
    max_clusters: int = 40              # el baseline crece hasta acá
    idle_threshold: float = 0.0         # usage ≤ este valor → candidato a poda
    growth_rate: float = 0.05           # probabilidad de que nazca un cluster nuevo por epoch
    idle_rate: float = 0.133            # fracción de clusters que tienden a quedar idle
    energy_per_cluster: float = 1.0     # unidades de energía por cluster por epoch
    base_latency_ms: float = 5.0        # latencia base sin carga extra
    latency_per_cluster: float = 0.02   # ms adicionales por cluster idle (ruido estructural)
    seed: int = 42


# ─── Cluster ──────────────────────────────────────────────────────────────────

@dataclass
class Cluster:
    cid: int
    usage: float = 1.0      # 0.0 = idle, 1.0 = fully active
    age: int = 0            # epochs de vida

    def tick(self, idle_rate: float) -> None:
        """Evoluciona el uso del cluster en un epoch."""
        self.age += 1
        # Deriva aleatoria del uso; algunos clusters se vuelven idle con el tiempo
        drift = random.gauss(0, 0.08)
        if random.random() < idle_rate * 0.15:
            self.usage = max(0.0, self.usage - 0.3 + drift)
        else:
            self.usage = max(0.0, min(1.0, self.usage + drift * 0.5))


# ─── Sistema ──────────────────────────────────────────────────────────────────

@dataclass
class System:
    name: str
    cfg: Config
    enable_pruning: bool = False

    clusters: List[Cluster] = field(default_factory=list)
    epoch: int = 0
    pruning_cycles: int = 0

    # acumuladores de métricas
    total_energy: float = 0.0
    cluster_counts: List[int] = field(default_factory=list)
    latency_samples: List[float] = field(default_factory=list)
    pruned_total: int = 0

    def __post_init__(self):
        random.seed(self.cfg.seed)
        for i in range(self.cfg.initial_clusters):
            self.clusters.append(Cluster(cid=i, usage=random.uniform(0.4, 1.0)))

    # ── epoch ────────────────────────────────────────────────────────────────

    def run_epoch(self, requests_this_epoch: int) -> None:
        self.epoch += 1

        # 1. Evolucionar clusters
        for cl in self.clusters:
            cl.tick(self.cfg.idle_rate)

        # 2. Crecimiento orgánico (el baseline crece sin freno)
        if (len(self.clusters) < self.cfg.max_clusters
                and random.random() < self.cfg.growth_rate):
            new_id = max(cl.cid for cl in self.clusters) + 1
            self.clusters.append(Cluster(cid=new_id, usage=random.uniform(0.3, 0.9)))

        # 3. ASPR: detectar y eliminar clusters idle
        if self.enable_pruning:
            idle = [cl for cl in self.clusters if cl.usage <= self.cfg.idle_threshold]
            if idle:
                self.pruning_cycles += 1
                self.pruned_total += len(idle)
                pruned_ids = {cl.cid for cl in idle}
                self.clusters = [cl for cl in self.clusters if cl.cid not in pruned_ids]

        # 4. Calcular métricas del epoch
        n = len(self.clusters)
        idle_n = sum(1 for cl in self.clusters if cl.usage <= self.cfg.idle_threshold)

        energy = n * self.cfg.energy_per_cluster
        self.total_energy += energy

        # Latencia: base + ruido por clusters idle (estructural noise)
        latency = self.cfg.base_latency_ms + idle_n * self.cfg.latency_per_cluster
        latency += abs(random.gauss(0, 0.3))  # jitter natural
        self.latency_samples.append(latency)
        self.cluster_counts.append(n)

    # ── percentil ─────────────────────────────────────────────────────────────

    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = math.ceil(p / 100 * len(sorted_data)) - 1
        return sorted_data[max(0, idx)]

    # ── resumen ───────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "name": self.name,
            "avg_clusters": sum(self.cluster_counts) / len(self.cluster_counts) if self.cluster_counts else 0,
            "final_clusters": len(self.clusters),
            "total_energy": self.total_energy,
            "pruning_cycles": self.pruning_cycles,
            "pruned_total": self.pruned_total,
            "lat_p50": self.percentile(self.latency_samples, 50),
            "lat_p95": self.percentile(self.latency_samples, 95),
            "lat_p99": self.percentile(self.latency_samples, 99),
        }


# ─── Simulación ───────────────────────────────────────────────────────────────

def simulate(cfg: Config) -> tuple[dict, dict]:
    baseline = System(name="Baseline", cfg=cfg, enable_pruning=False)
    aspr     = System(name="ASPR Gardener", cfg=cfg, enable_pruning=True)

    requests_per_epoch = cfg.total_requests // cfg.epochs
    total_epochs = cfg.epochs

    print(f"\n{'─'*56}")
    print(f"  ASPR Gardener — Simulación MVP")
    print(f"{'─'*56}")
    print(f"  Requests totales : {cfg.total_requests:,}")
    print(f"  Epochs           : {total_epochs:,}")
    print(f"  Requests / epoch : {requests_per_epoch:,}")
    print(f"  Clusters iniciales: {cfg.initial_clusters}")
    print(f"{'─'*56}\n")

    t0 = time.perf_counter()
    bar_width = 40

    for ep in range(1, total_epochs + 1):
        baseline.run_epoch(requests_per_epoch)
        aspr.run_epoch(requests_per_epoch)

        if ep % max(1, total_epochs // 20) == 0 or ep == total_epochs:
            pct = ep / total_epochs
            filled = int(bar_width * pct)
            bar = "█" * filled + "░" * (bar_width - filled)
            elapsed = time.perf_counter() - t0
            print(f"\r  [{bar}] {pct*100:5.1f}%  epoch {ep}/{total_epochs}  "
                  f"({elapsed:.1f}s)", end="", flush=True)

    print(f"\n\n  Simulación completada en {time.perf_counter() - t0:.2f}s\n")
    return baseline.summary(), aspr.summary()


# ─── Reporte ──────────────────────────────────────────────────────────────────

def print_report(b: dict, a: dict) -> None:
    def delta(key: str, pct: bool = True) -> str:
        bv, av = b[key], a[key]
        if bv == 0:
            return "N/A"
        d = (av - bv) / bv * 100
        sign = "+" if d > 0 else ""
        tag = f"{sign}{d:.2f}%"
        return tag

    w = 56
    print(f"{'═'*w}")
    print(f"  {'MÉTRICA':<28} {'BASELINE':>10}  {'ASPR':>10}  {'DELTA':>8}")
    print(f"{'─'*w}")

    rows = [
        ("Clusters promedio",     "avg_clusters",    ".1f"),
        ("Clusters finales",      "final_clusters",  "d"),
        ("Energía total",         "total_energy",    ".0f"),
        ("Latencia p50 (ms)",     "lat_p50",         ".3f"),
        ("Latencia p95 (ms)",     "lat_p95",         ".3f"),
        ("Latencia p99 (ms)",     "lat_p99",         ".3f"),
    ]

    for label, key, fmt in rows:
        bv = b[key]
        av = a[key]
        bstr = f"{bv:{fmt}}"
        astr = f"{av:{fmt}}"
        dstr = delta(key)
        print(f"  {label:<28} {bstr:>10}  {astr:>10}  {dstr:>8}")

    print(f"{'─'*w}")
    print(f"  {'Ciclos de podado':<28} {'—':>10}  {a['pruning_cycles']:>10}  {'':>8}")
    print(f"  {'Clusters podados (total)':<28} {'—':>10}  {a['pruned_total']:>10}  {'':>8}")
    print(f"{'═'*w}")

    # Conclusión
    cluster_pct = (b["avg_clusters"] - a["avg_clusters"]) / b["avg_clusters"] * 100
    energy_pct  = (b["total_energy"] - a["total_energy"]) / b["total_energy"] * 100
    lat_delta   = abs(a["lat_p50"] - b["lat_p50"])

    print(f"""
  RESULTADO
  ─────────
  • Clusters reducidos  : {cluster_pct:.2f}%
  • Energía ahorrada    : {energy_pct:.2f}%
  • Impacto en latencia : {lat_delta:.3f} ms (p50)
  • Ciclos de podado    : {a['pruning_cycles']}
  • Clusters eliminados : {a['pruned_total']}
""")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="ASPR Gardener — comparación baseline vs podado adaptativo"
    )
    parser.add_argument("--requests",  type=int,   default=10_000_000,
                        help="Total de requests a simular (default: 10_000_000)")
    parser.add_argument("--epochs",    type=int,   default=100,
                        help="Número de epochs (default: 100)")
    parser.add_argument("--clusters",  type=int,   default=24,
                        help="Clusters iniciales (default: 24)")
    parser.add_argument("--idle-rate", type=float, default=0.133,
                        help="Tasa de deriva hacia idle (default: 0.133)")
    parser.add_argument("--seed",      type=int,   default=42,
                        help="Semilla aleatoria (default: 42)")
    args = parser.parse_args()

    return Config(
        total_requests=args.requests,
        epochs=args.epochs,
        initial_clusters=args.clusters,
        idle_rate=args.idle_rate,
        seed=args.seed,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg = parse_args()
    baseline_summary, aspr_summary = simulate(cfg)
    print_report(baseline_summary, aspr_summary)
