# ASPR Gardener

### Adaptive Structural Regulation for AI Systems

**ASPR (Adaptive Structural Pruning & Reporting)** is a regulatory framework designed to control structural complexity in AI inference systems.

Instead of relying on static cleanup, ASPR introduces a **continuous regulation layer** ("Gardener") that observes system behavior and maintains equilibrium through adaptive pruning.

![License: MIT](LICENSE) ![Python 3.8+](https://www.python.org/) ![arXiv](#paper)

---

## 🧠 Abstract

Modern AI systems tend to accumulate structural complexity over time. Components that are no longer functionally relevant remain active, consuming resources and degrading overall system efficiency.

ASPR introduces a continuous regulatory mechanism that:

* observes usage patterns
* detects underutilized or idle structures
* applies adaptive, reversible pruning

The result is a system that **self-regulates instead of passively growing**.

---

## ⚠️ Problem Statement

AI systems exhibit **monotonic growth without natural decay**:

* Obsolete components persist indefinitely
* Resource consumption increases without proportional utility
* Structural noise accumulates silently
* System efficiency degrades over time

There is currently **no standard mechanism for runtime structural regulation** in AI systems.

---

## 💡 Approach

ASPR introduces a parallel agent ("Gardener") that operates continuously:

* detects low-usage clusters
* removes unnecessary components
* stabilizes the system dynamically
* reports efficiency metrics

It does not modify the core system — it regulates it.

---

## 🔁 System Dynamics

Without ASPR:

```
growth → accumulation → inefficiency → degradation
```

With ASPR:

```
growth → detection → pruning → stabilization
```

👉 Result: **dynamic equilibrium instead of uncontrolled expansion**

---

## 📊 Experimental Results

Simulation: **10 million requests**, standard parameters

| Metric             | Baseline | ASPR    | Delta   |
| ------------------ | -------- | ------- | ------- |
| Avg Clusters       | 24.0     | 20.8    | −13.3%  |
| Energy Consumption | 2400 u.  | 2082 u. | −13.28% |
| Latency p50        | 5.17 ms  | 5.17 ms | 0       |
| Latency p95        | 5.53 ms  | 5.53 ms | 0       |
| Latency p99        | 5.61 ms  | 5.61 ms | 0       |

**Key result:**
Structural and energy reduction **without latency degradation**

---

## 📈 Structural Evolution (Simulated)

Cluster evolution over time:

```
Clusters
 30 |            ████
 28 |           ██████
 26 |          ████████
 24 | ██████████████████   ← baseline (unbounded growth)
 22 | ████████████████
 20 | ██████████████       ← ASPR stabilizes
 18 | ███████████
 16 |
    +--------------------------------
      0   20   40   60   80   100 epochs
```

👉 Without ASPR: cumulative growth
👉 With ASPR: progressive stabilization

---

## ⚠️ Not Just Pruning

ASPR is not a static cleanup tool.

Traditional approaches rely on:

* fixed thresholds
* one-time deletion
* no system awareness

ASPR introduces:

* continuous structural regulation
* behavior-aware pruning
* system-level equilibrium

👉 The goal is not deletion — it is **stability under evolution**
ASPR is not a threshold-based cleanup system.

It operates as a continuous regulatory loop that adapts to system dynamics,
preventing structural drift rather than reacting to it.
---

## 🧱 Architecture

```
aspr-gardener/
│
├── mvp_compare.py   # Simulation engine
├── launch.py        # Launcher + dashboard
├── data/            # Generated CSV results
├── logs/            # Runtime logs
└── lib/             # Optional dependencies
```

---

## 🚀 Usage

### Run simulation

```bash
python mvp_compare.py
```

### Custom parameters

```bash
python mvp_compare.py --requests 1000000 --epochs 50 --clusters 48
```

---

### Dashboard

```bash
pip install flask plotly
python launch.py --dashboard
```

Open:

```
http://localhost:7771
```

---

## 📊 Output

Each run generates:

```
data/results_YYYYMMDD_HHMMSS.csv
```

Format:

```
metric,baseline,aspr,delta_pct
```

Compatible with **GHG Protocol Scope 3 reporting**.

---

## 🧪 Production Integration

ASPR is designed as a **sidecar process**:

### Observation mode

```python
aspr = System(enable_pruning=False)
```

### Active mode

```python
aspr = System(enable_pruning=True)
```

✔ Non-intrusive
✔ Fully reversible
✔ Auditable

---

## 🧬 Future — Ghost Registry

Next iteration introduces a memory layer:

* tracks historical pruning patterns
* identifies recurring structural failures
* prevents re-emergence of inefficient configurations

👉 This transforms ASPR from **reactive pruning** to **evolutionary regulation**

---

## 📄 Paper (in progress)

**ASPR: Adaptive Structural Regulation for AI System Efficiency**
Ramiro Guevara, 2025

---

## 📌 Project Status

* ✅ Baseline vs ASPR simulation
* ✅ Interactive dashboard
* ✅ CSV export
* 🚧 Ghost Registry (memory layer)
* 🚧 Production validation
* 🚧 Kubernetes sidecar

---

## 🤝 Contributions

Areas of interest:

* hardware-level metrics (RAPL, IPMI)
* Kubernetes integration
* GHG / ISO measurement frameworks
* real-world deployment cases

---

## 🧪 Pilot Program

Looking for early adopters to validate ASPR in real infrastructure.

Contact: **[ramiguevara@gmail.com](mailto:ramiguevara@gmail.com)**

---

## 📜 License

MIT License

---

## 🧠 Closing Thought

> Systems that only grow will eventually collapse under their own complexity.
> Systems that regulate themselves can evolve.## Public Key
Fingerprint SHA-256:
5482f712f89270b7755219a75cef214e0b137ea7fd9ee012dbe504875d600769
> 
> 
