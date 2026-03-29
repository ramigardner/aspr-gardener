# ASPR Gardener

**Adaptive Structural Pruning \& Reporting** — agente de poda para controlar la acumulación de complejidad en sistemas de inferencia de IA.

[!\[License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[!\[Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[!\[arXiv](https://img.shields.io/badge/paper-arXiv-red.svg)](#paper)

\---

## El problema

Los sistemas de IA tienden a crecer sin eliminar componentes obsoletos. Con el tiempo, clusters que dejaron de recibir requests permanecen activos: consumen energía, generan ruido estructural y degradan la eficiencia sin que nadie lo note.

No existe un mecanismo estándar para detectar y eliminar este desperdicio en tiempo de ejecución.

## La solución

ASPR introduce un agente "jardinero" que corre en paralelo al sistema principal:

1. **Detecta** clusters con uso igual o menor al umbral configurado
2. **Elimina** los componentes innecesarios de forma segura y reversible
3. **Estabiliza** el sistema en un estado de menor complejidad
4. **Reporta** métricas de ahorro exportables para informes de sostenibilidad (GHG Protocol Scope 3)

## Resultados

Simulación de **10 millones de requests** con parámetros estándar:

|Métrica|Baseline|ASPR|Delta|
|-|-|-|-|
|Clusters promedio|24.0|20.8|**−13.3%**|
|Energía consumida|2,400 u.|2,082 u.|**−13.28%**|
|Latencia p50|5.17 ms|5.17 ms|**0 ms**|
|Latencia p95|5.53 ms|5.53 ms|**0 ms**|
|Latencia p99|5.61 ms|5.61 ms|**0 ms**|

> Reducción significativa de energía y complejidad estructural sin impacto en latencia.

\---

## Instalación

No requiere dependencias externas para el núcleo de simulación.

```bash
git clone https://github.com/tu-usuario/aspr-gardener
cd aspr-gardener
python mvp\_compare.py
```

Para el dashboard interactivo (opcional):

```bash
pip install flask plotly
python launch.py --dashboard
```

\---

## Uso

### Simulación en terminal

```bash
# Simulación estándar (10M requests)
python mvp\_compare.py

# Parámetros custom
python mvp\_compare.py --requests 1\_000\_000 --epochs 50 --clusters 48

# Ver todas las opciones
python mvp\_compare.py --help
```

### Launcher con dashboard

```bash
# Menú interactivo
python launch.py

# Simulación + dashboard en browser
python launch.py --sim --dashboard

# Solo dashboard (puerto custom)
python launch.py --dashboard --port 8080
```

El dashboard se abre en `http://localhost:7771` y permite correr simulaciones y visualizar resultados sin salir del browser.

### Desde un pendrive

El launcher instala dependencias localmente en el pendrive sin tocar la máquina host:

```bash
# Primera vez (requiere internet)
python launch.py

# Ejecuciones siguientes (offline)
python launch.py --sim --dashboard
```

\---

## Arquitectura

```
aspr-gardener/
├── mvp\_compare.py   # Motor de simulación: Config, Cluster, System
├── launch.py        # Launcher multiplataforma con dashboard Flask+Plotly
├── data/            # Resultados CSV generados automáticamente
├── logs/            # Logs del dashboard
└── lib/             # Dependencias opcionales (se instalan aquí, no en el sistema)
```

### Componentes principales

**`Config`** — parámetros de simulación: requests totales, epochs, clusters iniciales, tasa de deriva, umbral de poda.

**`Cluster`** — unidad básica del sistema. Cada cluster tiene un `usage` que evoluciona por epoch. Cuando cae por debajo del umbral, es candidato a poda.

**`System`** — gestiona la colección de clusters. En modo `baseline` solo crece. En modo `aspr` ejecuta el agente jardinero en cada epoch.

\---

## Parámetros de configuración

|Parámetro|Default|Descripción|
|-|-|-|
|`--requests`|10,000,000|Total de requests a simular|
|`--epochs`|100|Número de epochs de evaluación|
|`--clusters`|24|Clusters iniciales|
|`--idle-rate`|0.133|Tasa de deriva hacia idle|
|`--idle-threshold`|0.0|Uso mínimo para considerar activo|
|`--seed`|42|Semilla aleatoria (reproducibilidad)|

\---

## Integración en producción

ASPR está diseñado para integrarse como proceso paralelo, sin modificar el sistema principal.

**Modo observación** (recomendado para comenzar):

```python
from mvp\_compare import Config, System

cfg = Config(total\_requests=1\_000\_000, epochs=10)
aspr = System(name="ASPR", cfg=cfg, enable\_pruning=False)  # solo reporta
```

**Modo activo:**

```python
aspr = System(name="ASPR", cfg=cfg, enable\_pruning=True)
```

**Rollback:** cada cluster eliminado queda registrado en el log de auditoría. La restauración es inmediata.

\---

## Métricas exportadas

Cada simulación genera un CSV en `data/results\_YYYYMMDD\_HHMMSS.csv`:

```
metric,baseline,aspr,delta\_pct
avg\_clusters,24.0,20.8,-13.3
total\_energy,2400.0,2082.0,-13.28
lat\_p50,5.17,5.17,0.0
lat\_p95,5.53,5.53,0.0
lat\_p99,5.61,5.61,0.0
pruning\_cycles,0,12,N/A
pruned\_total,0,38,N/A
```

El formato es compatible con GHG Protocol Scope 3 para informes de sostenibilidad.

\---

## Paper

> \*\*ASPR: Adaptive Structural Pruning for AI System Efficiency\*\*
> \[ramiro guevara], \[2025]
> \[Enlace a arXiv cuando esté disponible]

Si usás ASPR en tu investigación:

```bibtex
@software{aspr\_gardener,
  author  = {Ramiro Guevara},
  title   = {ASPR Gardener: Adaptive Structural Pruning for AI Systems},
  year    = {2025},
  url     = {https://github.com/ramigardner/aspr-gardener},
  license = {MIT}
}
```

\---

## Estado del proyecto

* \[x] Simulación baseline vs ASPR
* \[x] Dashboard interactivo (Flask + Plotly)
* \[x] Launcher multiplataforma (Windows / macOS / Linux)
* \[x] Exportación CSV compatible con GHG Protocol
* \[ ] Validación en producción real ← *buscando early adopters*
* \[ ] Paper con datos de producción
* \[ ] Integración como sidecar de Kubernetes
* \[ ] Soporte para métricas de hardware (RAPL, IPMI)

\---

## Contribuciones

Las contribuciones son bienvenidas. Áreas prioritarias:

* **Instrumentación real**: adaptadores para leer consumo de hardware (RAPL en Linux, IPMI, DCMI)
* **Integración con orquestadores**: Kubernetes sidecar, Docker Compose
* **Metodologías de medición**: alineación con estándares ISO 14064 / GHG Protocol
* **Casos de uso**: si lo desplegás y tenés resultados, un issue con los datos es enormemente valioso

Para contribuir: fork → branch → PR con descripción del cambio y, si aplica, métricas antes/después.

\---

## Piloto en producción

Si operás infraestructura de inferencia y querés validar ASPR en producción real, estoy buscando los primeros early adopters.

Lo que ofrezco: código + documentación + soporte técnico asíncrono durante 30 días.  
Lo que necesito: que lo corras en tu infra y compartas las métricas (podés anonimizarlas).

Contacto: **\[ramiguevara@gmail.com]**

\---

## Licencia

MIT — libre para usar, modificar y distribuir. Ver [LICENSE](LICENSE).

\---

*"Los sistemas de IA deberían poder podar lo que ya no necesitan. Los jardines también."*

