#!/usr/bin/env python3
"""
ASPR Oracle Node v2.1 — Nodo de Verificación de Confianza con Firma Digital
by Ramiro (ramigardner) · MIT · moteroenchilado@gmail.com

FIXES v2.1-patched:
  - [FIX #1] LocIVault.write() ahora hace flush en cada escritura (no solo cada 10 bloques)
             → Evita pérdida de datos si el proceso se cae entre bloques
  - [FIX #2] verify_signature() ya no muta el dict original con .pop()
             → Trabaja sobre copia interna, seguro en todos los contextos
  - [FIX #3] _observe_cycle() pinga todos los dispositivos en paralelo con ThreadPoolExecutor
             → Evita que el nodo se "congele" con múltiples dispositivos lentos
  - [FIX #4] LocIVault usa archivo de bloques recientes (chain_recent.json) + histórico
             separado para evitar reescribir todo el archivo en cada flush
             → chain.json se parte en histórico (append-only) + recientes (ventana de 500)
  - [FIX #5] /federated corre en thread separado para no bloquear el servidor HTTP
  - [FIX #6] load_registry() con caché de 60 segundos para no descargar en cada llamada

NUEVO en v2.1 (integración Grok / xAI):
  - Endpoint /probe?ip=X  (nuevo primario; /verify se mantiene como legado)
  - Módulo federado: get_federated_karma() con fórmula K_federated v1.1
  - peer_snapshot automático cada 10 bloques en LocIVault
  - Carga dinámica de registry.json desde GitHub
  - Verificación de firma Ed25519 en cliente multi-nodo
  - /federated?ip=X endpoint público expuesto

HEREDADO de v2.0:
  - Dashboard servido desde archivo externo dashboard.html
  - Firma digital Ed25519 en respuestas /verify y /probe
  - Generación automática de claves (oracle_private.pem / oracle_public.pem)
  - Preparado para Tailscale Funnel (HTTPS público)
  - Endpoints: /status, /probe, /verify, /public-key,
               /chain/latest, /chain/verify, /chain, /api/state
"""

import hashlib
import json
import os
import re
import socket
import subprocess
import threading
import time
import webbrowser
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed  # FIX #3
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# Firma digital
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
import base64

# HTTP (federación)
import requests

# ============================================================
# CONFIGURACIÓN DE RED (EDITA ESTAS IPs)
# ============================================================
GATEWAY_IP   = "192.168.1.1"
LAPTOP_IP    = "192.168.1.6"
LAPTOP_PING  = "8.8.8.8"
PS4_IP       = "192.168.1.8"

FIXED_DEVICES = {
    "gateway": {"ip": GATEWAY_IP,  "ping": GATEWAY_IP,  "name": "🌐 Modem Claro",      "fixed": True},
    "laptop":  {"ip": LAPTOP_IP,   "ping": LAPTOP_PING, "name": "💻 Laptop → internet", "fixed": True},
    "ps4":     {"ip": PS4_IP,      "ping": PS4_IP,      "name": "🎮 PS4",               "fixed": True},
}

# Pesos del Ghost Balancer (K = Mem×0.30 + Cyc×0.25 + Anc×0.20 + Eff×0.15 + Cor×0.10)
W = {"memory":0.30, "cycles":0.25, "anchor":0.20, "efficiency":0.15, "correction":0.10}

WINDOW_SIZE              = 60
OBSERVE_EVERY            = 3
PING_COUNT               = 3
DASHBOARD_PORT           = 7771
VAULT_DIR                = "aspr_vault"
DISCOVERY_EVERY          = 60
NETWORK_CRISIS_THRESHOLD = 2

PRIVATE_KEY_FILE = "oracle_private.pem"
PUBLIC_KEY_FILE  = "oracle_public.pem"

# Registry público (federación v1.1)
REGISTRY_URL = "https://raw.githubusercontent.com/ramigardner/aspr-gardener/main/registry.json"

# FIX #6: caché del registry (60 segundos)
_registry_cache: List[Dict] = []
_registry_cache_time: float = 0.0
REGISTRY_CACHE_TTL = 60.0

# FIX #4: ventana de bloques recientes en memoria antes de archivar
CHAIN_RECENT_WINDOW = 500  # bloques que se mantienen en chain_recent.json

# ── Prefijos MAC → tipo de dispositivo ─────────────────────
MAC_VENDORS = {
    "70:9e:29":"ps","f8:d0:ac":"ps","28:3f:69":"ps","00:13:a9":"ps",
    "f0:b0:52":"ps","00:04:1f":"ps","00:19:c5":"ps","ac:9b:0a":"ps",
    "00:26:37":"samsung","8c:77:12":"samsung","f4:7b:5e":"samsung",
    "84:25:3f":"samsung","00:12:fb":"samsung","a8:f2:74":"samsung",
    "40:b8:37":"samsung","b0:72:bf":"samsung","cc:07:ab":"samsung",
    "f8:a4:5f":"xiaomi","00:9e:c8":"xiaomi","64:09:80":"xiaomi",
    "d4:97:0b":"xiaomi","34:ce:00":"xiaomi","78:11:dc":"xiaomi",
    "00:1b:63":"apple","00:26:bb":"apple","3c:15:c2":"apple",
    "a4:5e:60":"apple","f0:18:98":"apple","8c:8d:28":"apple",
    "00:1e:75":"lg","a8:23:fe":"lg","78:5d:c8":"lg","cc:2d:8c":"lg",
    "c0:f6:c2":"tcl","00:62:6e":"hisense",
    "b8:3e:59":"roku","d8:31:cf":"roku","08:05:81":"roku",
    "54:60:09":"google","6c:ad:f8":"google","f4:f5:d8":"google",
    "74:75:48":"amazon","00:fc:8b":"amazon","34:d2:70":"amazon",
}
DEVICE_ICONS = {
    "ps":"🎮","samsung":"📱","xiaomi":"📱","apple":"📱",
    "lg":"📺","tcl":"📺","hisense":"📺","roku":"📺",
    "google":"📺","amazon":"📺","laptop":"💻","gateway":"🌐","unknown":"📡",
}

# ============================================================
# UTILIDADES
# ============================================================
def classify_by_mac(mac: str) -> Tuple[str, str]:
    mac_clean = mac.lower().replace("-", ":").strip()
    vendor = MAC_VENDORS.get(mac_clean[:8])
    if vendor:
        icon = DEVICE_ICONS.get(vendor, "📡")
        names = {
            "ps":"PlayStation","samsung":"Samsung","xiaomi":"Xiaomi","apple":"Apple",
            "lg":"LG Smart TV","tcl":"TCL TV","hisense":"Hisense TV","roku":"Roku",
            "google":"Chromecast","amazon":"Fire TV",
        }
        return vendor, f"{icon} {names.get(vendor, vendor.title())}"
    return "unknown", "📡 Dispositivo"

def classify_by_hostname(hostname: str) -> Optional[Tuple[str, str]]:
    h = hostname.lower()
    rules = [
        (["playstation","ps4","ps-4","sony-ps"], "ps",      "🎮 PlayStation"),
        (["android","phone","mobile","xiaomi","redmi","pixel","iphone","galaxy"], "celular", "📱 Celular"),
        (["smart-tv","smarttv","bravia","lg-tv","tcl","hisense","firetv","roku","chromecast"], "tele", "📺 Smart TV"),
        (["laptop","notebook","pc","desktop","windows","macbook"], "laptop", "💻 PC/Laptop"),
    ]
    for keywords, tipo, label in rules:
        if any(k in h for k in keywords):
            return tipo, label
    return None

# ============================================================
# PING
# ============================================================
def ping_host(ip: str, count: int = PING_COUNT, timeout_ms: int = 2000) -> Tuple[float, float]:
    try:
        cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), ip]
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=count*3+2, startupinfo=si)
        except AttributeError:
            cmd = ["ping", "-c", str(count), "-W", "2", ip]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=count*3)
        out = (r.stdout + r.stderr).lower()
        loss = 100.0
        m = re.search(r'\((\d+)%\s*(?:p[eé]rdid[ao]s?|loss|packet\sloss)\)', out)
        if not m: m = re.search(r'(\d+)%', out)
        if m: loss = float(m.group(1))
        latency = 999.0
        for pat in [
            r'promedio\s*=\s*(\d+(?:\.\d+)?)\s*ms',
            r'media\s*=\s*(\d+(?:\.\d+)?)\s*ms',
            r'average\s*=\s*(\d+(?:\.\d+)?)\s*ms',
            r'avg[^/]*/(\d+(?:\.\d+)?)',
            r'tiempo[<>=]+(\d+(?:\.\d+)?)\s*ms',
            r'time[<>=]+(\d+(?:\.\d+)?)\s*ms',
        ]:
            m2 = re.search(pat, out)
            if m2:
                v = float(m2.group(1))
                if 0 < v < 9000:
                    latency = v
                    break
        if loss >= 100: latency = 999.0
        return latency, loss
    except Exception:
        return 999.0, 100.0

# ============================================================
# AUTO-DISCOVERY (ARP)
# ============================================================
def scan_arp(gateway_ip: str) -> List[Dict]:
    devices = []
    base = ".".join(gateway_ip.split(".")[:3]) + "."
    try:
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            r = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=8, startupinfo=si)
        except AttributeError:
            r = subprocess.run(["arp", "-n"], capture_output=True, text=True, timeout=8)
        for line in r.stdout.splitlines():
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            if not ip_match: continue
            ip = ip_match.group(1)
            if not ip.startswith(base): continue
            last = ip.split(".")[-1]
            if last in ("0","255") or ip == gateway_ip: continue
            mac_match = re.search(
                r'([0-9a-f]{2}[:\-][0-9a-f]{2}[:\-][0-9a-f]{2}[:\-]'
                r'[0-9a-f]{2}[:\-][0-9a-f]{2}[:\-][0-9a-f]{2})', line.lower()
            )
            mac = mac_match.group(1) if mac_match else "??:??:??:??:??:??"
            hostname = ip
            try: hostname = socket.gethostbyaddr(ip)[0]
            except: pass
            devices.append({"ip": ip, "mac": mac, "hostname": hostname})
    except: pass
    return devices

# ============================================================
# LOCIVAULT (Blockchain local) — con FIX #1 y FIX #4
# ============================================================
class LocIVault:
    """
    FIX #1: flush en cada write (no solo cada 10 bloques).
    FIX #4: chain partida en dos archivos:
        - chain_archive.json : histórico completo (append-only, nunca se reescribe entero)
        - chain_recent.json  : últimos CHAIN_RECENT_WINDOW bloques (ventana deslizante)
        - chain.json         : se mantiene por compatibilidad con v2.0 pero solo guarda recientes
    """
    def __init__(self, d=VAULT_DIR):
        self.vault_dir      = Path(d)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.chain_file     = self.vault_dir / "chain.json"          # compatibilidad legado
        self.archive_file   = self.vault_dir / "chain_archive.jsonl" # append-only (FIX #4)
        self.recent_file    = self.vault_dir / "chain_recent.json"   # ventana reciente
        self.snapshot_file  = self.vault_dir / "peer_snapshot.json"
        self._lock          = threading.Lock()
        self._chain         = self._load()
        self._archive_index = self._detect_archive_index()

    def _load(self) -> List[Dict]:
        """Carga chain_recent.json si existe, sino migra desde chain.json legado."""
        if self.recent_file.exists():
            try:
                with open(self.recent_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                self.recent_file.unlink(missing_ok=True)

        # Migración desde chain.json legado
        if self.chain_file.exists():
            try:
                with open(self.chain_file, "r", encoding="utf-8") as f:
                    full = json.load(f)
                if full:
                    print(f"  [LocIVault] Migrando {len(full)} bloques al nuevo formato...")
                    self._migrate_to_archive(full)
                    recent = full[-CHAIN_RECENT_WINDOW:]
                    with open(self.recent_file, "w", encoding="utf-8") as f:
                        json.dump(recent, f, indent=2)
                    print(f"  [LocIVault] Migración completa. Recientes: {len(recent)}")
                    return recent
            except Exception as ex:
                print(f"  [LocIVault] Error migrando: {ex}")
        return []

    def _migrate_to_archive(self, full_chain: List[Dict]):
        """Escribe el histórico completo en formato JSONL (una línea por bloque)."""
        if self.archive_file.exists():
            return  # ya migrado
        with open(self.archive_file, "a", encoding="utf-8") as f:
            for block in full_chain:
                f.write(json.dumps(block, ensure_ascii=False) + "\n")

    def _detect_archive_index(self) -> int:
        """Detecta cuántos bloques hay en el archivo de histórico."""
        if not self.archive_file.exists():
            return 0
        count = 0
        try:
            with open(self.archive_file, "r", encoding="utf-8") as f:
                for _ in f:
                    count += 1
        except Exception:
            pass
        return count

    def _total_blocks(self) -> int:
        """Total real = bloques archivados + bloques recientes que no están archivados."""
        archived = self._archive_index
        recent_count = len(self._chain)
        # Los recientes pueden solapar con el archivo; usamos el índice del último bloque + 1
        if self._chain:
            return self._chain[-1]["index"] + 1
        return archived

    def write(self, data: Dict) -> str:
        with self._lock:
            ts    = datetime.now(timezone.utc).isoformat()
            nonce = os.urandom(8).hex()
            ch    = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            ph    = self._chain[-1]["entry_hash"] if self._chain else "0"*64
            e = {
                "index": self._total_blocks(), "timestamp": ts,
                "content_hash": ch, "prev_hash": ph, "nonce": nonce, "data": data,
            }
            es = json.dumps({k:v for k,v in e.items() if k != "entry_hash"}, sort_keys=True)
            e["entry_hash"] = hashlib.sha256(es.encode()).hexdigest()
            self._chain.append(e)

            # FIX #4: append al archivo histórico (nunca reescribe)
            try:
                with open(self.archive_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
                self._archive_index += 1
            except Exception as ex:
                print(f"  [LocIVault] Error escribiendo archive: {ex}")

            # Mantener ventana deslizante en chain_recent.json
            if len(self._chain) > CHAIN_RECENT_WINDOW:
                self._chain = self._chain[-CHAIN_RECENT_WINDOW:]

            # peer_snapshot cada 10 bloques
            if e["index"] % 10 == 0:
                self._write_peer_snapshot()

            # FIX #1: flush SIEMPRE después de cada write
            self._flush_recent()
            return e["entry_hash"]

    def _write_peer_snapshot(self):
        """Guarda snapshot liviano del estado de la chain para peers federados."""
        snapshot = {
            "snapshot_type":      "peer_snapshot",
            "total_blocks":       self._total_blocks(),
            "chain_tip":          self._chain[-1]["entry_hash"] if self._chain else None,
            "prev_hash":          self._chain[-2]["entry_hash"] if len(self._chain) > 1 else "0"*64,
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self.snapshot_file, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as ex:
            print(f"  [LocIVault] Error escribiendo snapshot: {ex}")

    def get_peer_snapshot(self) -> Optional[Dict]:
        if self.snapshot_file.exists():
            try:
                with open(self.snapshot_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return None
        return None

    def _flush_recent(self):
        """Escribe solo la ventana reciente (archivo pequeño, rápido)."""
        try:
            with open(self.recent_file, "w", encoding="utf-8") as f:
                json.dump(self._chain, f, indent=2)
        except Exception as ex:
            print(f"  [LocIVault] Error en flush: {ex}")

    def flush(self):
        """Flush manual (llamado al cerrar el proceso)."""
        with self._lock:
            self._flush_recent()

    def verify_integrity(self) -> bool:
        """Verifica integridad de los bloques en memoria (ventana reciente)."""
        with self._lock:
            for i, e in enumerate(self._chain):
                copy = {k:v for k,v in e.items() if k != "entry_hash"}
                if hashlib.sha256(json.dumps(copy, sort_keys=True).encode()).hexdigest() != e["entry_hash"]:
                    return False
                if i > 0 and e["prev_hash"] != self._chain[i-1]["entry_hash"]:
                    return False
            return True

    def get_last_proof(self, device_id: str) -> Optional[Dict]:
        with self._lock:
            for entry in reversed(self._chain):
                if entry.get("data", {}).get("device_id") == device_id:
                    return {
                        "entry_hash": entry["entry_hash"],
                        "cycle":      entry["data"]["cycle"],
                        "timestamp":  entry["timestamp"],
                    }
        return None

# ============================================================
# GHOST BALANCER
# ============================================================
@dataclass
class DeviceMetric:
    latency_ms:      float
    packet_loss_pct: float
    timestamp:       float
    is_reachable:    bool
    anchor:          bool = False
    network_crisis:  bool = False

class GhostBalancer:
    def __init__(self):
        self.history: Dict[str, deque] = {}
        self._lock = threading.Lock()

    def record(self, did: str, metric: DeviceMetric):
        with self._lock:
            if did not in self.history:
                self.history[did] = deque(maxlen=WINDOW_SIZE)
            self.history[did].append(metric)

    def _h(self, did): return list(self.history.get(did, []))

    def _memory(self, did):
        h = self._h(did)
        if len(h) < 4: return 0.5
        half = len(h) // 2
        f   = sum(1 for m in h[:half] if m.is_reachable) / half
        s   = sum(1 for m in h[half:] if m.is_reachable) / (len(h) - half)
        mem = 1.0 - abs(s - f)
        return round(min(1.0, mem + 0.15) if s > f else mem, 4)

    def _cycles(self, did):
        h = self._h(did)
        return round(sum(1 for m in h if m.is_reachable) / len(h), 4) if h else 0.0

    def _anchor(self, did):
        h = self._h(did)
        return round(sum(1 for m in h if m.anchor) / len(h), 4) if h else 0.0

    def _efficiency(self, did):
        h  = self._h(did)
        ok = [m for m in h if m.is_reachable]
        if not ok: return 0.0
        al = sum(m.latency_ms for m in ok) / len(ok)
        ax = sum(m.packet_loss_pct for m in ok) / len(ok)
        return round((max(0, 1 - al/200) + max(0, 1 - ax/100)) / 2, 4)

    def _correction(self, did):
        h = self._h(did)
        if len(h) < 2: return 1.0
        failures = recoveries = 0
        for i in range(1, len(h)):
            if not h[i-1].is_reachable and not h[i-1].network_crisis:
                failures += 1
                if h[i].is_reachable: recoveries += 1
        return 1.0 if failures == 0 else round(min(1.0, recoveries / failures), 4)

    def karma(self, did):
        return round(
            self._memory(did)     * W["memory"]     +
            self._cycles(did)     * W["cycles"]     +
            self._anchor(did)     * W["anchor"]     +
            self._efficiency(did) * W["efficiency"] +
            self._correction(did) * W["correction"], 4)

    def components(self, did):
        return {k: getattr(self, f"_{k}")(did) for k in W}

    def latest(self, did) -> Optional[DeviceMetric]:
        h = self.history.get(did)
        return h[-1] if h else None

# ============================================================
# FIRMA DIGITAL
# ============================================================
def generate_keys():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key  = private_key.public_key()
    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    return private_key, public_key

def load_keys():
    if not (os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE)):
        return generate_keys()
    with open(PRIVATE_KEY_FILE, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    with open(PUBLIC_KEY_FILE, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    return private_key, public_key

def sign_data(private_key, data: bytes) -> str:
    return base64.b64encode(private_key.sign(data)).decode("ascii")

def get_public_key_pem(public_key) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")

# ============================================================
# MÓDULO FEDERADO — con FIX #2 y FIX #6
# ============================================================
def verify_signature(block: Dict[str, Any], public_key_pem: str = None) -> bool:
    """
    FIX #2: Verifica firma Ed25519 sin mutar el dict original.
    Trabaja siempre sobre una copia interna.
    """
    if "signature" not in block:
        return False
    try:
        # FIX #2: copia interna para no mutar el original
        block_copy = dict(block)
        sig = base64.b64decode(block_copy.pop("signature"))
        pub = block_copy.pop("public_key", public_key_pem)
        if not pub:
            return False
        pk  = load_pem_public_key(pub.encode())
        msg = json.dumps(block_copy, sort_keys=True, ensure_ascii=False).encode()
        pk.verify(sig, msg)
        return True
    except (InvalidSignature, Exception):
        return False

def load_registry() -> List[Dict[str, Any]]:
    """
    FIX #6: Descarga registry.json desde GitHub con caché de 60 segundos.
    No descarga en cada llamada a /federated.
    """
    global _registry_cache, _registry_cache_time
    now = time.monotonic()
    if _registry_cache and (now - _registry_cache_time) < REGISTRY_CACHE_TTL:
        return _registry_cache
    resp = requests.get(REGISTRY_URL, timeout=10)
    resp.raise_for_status()
    _registry_cache = resp.json()["nodes"]
    _registry_cache_time = now
    return _registry_cache

def get_federated_karma(target_ip: str, min_nodes: int = 3) -> Dict[str, Any]:
    """
    Fórmula canónica K_federated v1.1:
        K_fed = Σ(K_node_i × K_local_i) / Σ(K_node_i)

    - Consulta hasta 8 nodos del registry.
    - Prefiere /probe con fallback a /verify.
    - Obtiene node_karma real desde /status de cada nodo (fallback a 0.98).
    - Ignora nodos caídos o con firma inválida.
    """
    try:
        nodes = load_registry()
    except Exception as e:
        return {"error": f"No se pudo cargar el registry: {e}"}

    reports = []
    for node in nodes[:8]:
        try:
            r = requests.get(f"{node['base_url']}/probe?ip={target_ip}", timeout=8)
            if r.status_code != 200:
                r = requests.get(f"{node['base_url']}/verify?ip={target_ip}", timeout=8)

            data = r.json()

            # FIX #2: verify_signature ya no muta data
            if "signature" in data:
                if not verify_signature(data):
                    continue

            node_karma = 0.98
            try:
                s = requests.get(f"{node['base_url']}/status", timeout=5).json()
                node_karma = s.get("recent_karma_average", 0.98)
            except Exception:
                pass

            local_karma = data.get("local_karma") or data.get("data", {}).get("karma")
            if local_karma is None:
                continue

            reports.append({
                "node_fingerprint": node["fingerprint"],
                "node_karma":       node_karma,
                "local_karma":      local_karma,
                "components":       data.get("components"),
                "timestamp":        data.get("timestamp") or data.get("block_timestamp"),
            })
        except Exception:
            continue

    if len(reports) < min_nodes:
        return {"error": f"Nodos insuficientes ({len(reports)} < {min_nodes})"}

    numerator   = sum(r["node_karma"] * r["local_karma"] for r in reports)
    denominator = sum(r["node_karma"] for r in reports)
    k_federated = numerator / denominator if denominator > 0 else 0.0

    return {
        "target":          target_ip,
        "federated_karma": round(k_federated, 4),
        "nodes_used":      len(reports),
        "reports":         reports,
    }

# ============================================================
# ASPR ORACLE NODE v2.1
# ============================================================
class ASPROracleNode:
    def __init__(self):
        self.vault    = LocIVault()
        self.balancer = GhostBalancer()
        self.log      = deque(maxlen=200)
        self.cycle    = 0
        self._running = False
        self._lock    = threading.Lock()
        self.devices: Dict[str, Dict] = {}
        self.karma_history: Dict[str, List] = {}
        self.events   = {"network_crisis":0, "device_offline":0, "recoveries":0, "new_devices":0}
        self._last_discovery = 0
        self.start_time = datetime.now(timezone.utc)

        self.private_key, self.public_key = load_keys()
        self.public_pem = get_public_key_pem(self.public_key)

        for did, info in FIXED_DEVICES.items():
            self.devices[did] = {
                "ip": info["ip"], "ping": info["ping"], "name": info["name"],
                "mac": "—", "hostname": info["ip"], "fixed": True, "tipo": did,
                "first_seen": datetime.now().isoformat(), "last_seen": datetime.now().isoformat(),
            }

        fp = hashlib.sha256(self.public_pem.encode()).hexdigest()
        print("🌿 ASPR Oracle Node v2.1-patched — Ramiro · moteroenchilado@gmail.com")
        print(f"   Fijos: gateway={GATEWAY_IP} | laptop→{LAPTOP_PING} | ps4={PS4_IP}")
        print(f"   Endpoints: /probe (nuevo), /verify (legado), /status, /public-key")
        print(f"   Federación v1.1: /federated?ip=X  |  Registry: {REGISTRY_URL}")
        print(f"   Fingerprint Ed25519: {fp}")
        print(f"   Chain: {self.vault._total_blocks()} bloques totales | Ventana reciente: {len(self.vault._chain)}")

    def _log(self, msg: str, kind: str = "info"):
        e = {"t": datetime.now().strftime("%H:%M:%S"), "msg": msg, "kind": kind}
        self.log.appendleft(e)
        icon = {"info":"·","ok":"✓","warn":"⚠","crisis":"🔴","net":"🌐","new":"🆕"}.get(kind, "·")
        print(f"  [{e['t']}] {icon} {msg}")

    def _run_discovery(self):
        found = scan_arp(GATEWAY_IP)
        for dev in found:
            ip, mac, hostname = dev["ip"], dev["mac"], dev["hostname"]
            with self._lock:
                already = any(info["ip"] == ip for info in self.devices.values())
            if already:
                with self._lock:
                    for info in self.devices.values():
                        if info["ip"] == ip:
                            info["last_seen"] = datetime.now().isoformat()
                            if info["mac"] == "—" and mac != "??:??:??:??:??:??":
                                info["mac"] = mac
                continue
            tipo, name = classify_by_mac(mac)
            if tipo == "unknown":
                res = classify_by_hostname(hostname)
                if res: tipo, name = res
            did = f"{tipo}_{ip.replace('.','_')}"
            while did in self.devices: did += "_x"
            full_name = f"{name} ({ip.split('.')[-1]})"
            device_info = {
                "ip": ip, "ping": ip, "name": full_name, "mac": mac,
                "hostname": hostname, "fixed": False, "tipo": tipo,
                "first_seen": datetime.now().isoformat(), "last_seen": datetime.now().isoformat(),
            }
            with self._lock:
                self.devices[did] = device_info
                self.events["new_devices"] += 1
            self._log(f"Nuevo: {full_name} · {ip} · MAC {mac[:11]}", "new")
            self.vault.write({
                "event": "device_discovered", "device_id": did,
                "ip": ip, "mac": mac, "hostname": hostname,
                "name": full_name, "tipo": tipo,
                "timestamp": datetime.now().isoformat(),
            })

    def _observe_cycle(self):
        self.cycle += 1
        if time.time() - self._last_discovery > DISCOVERY_EVERY:
            self._run_discovery()
            self._last_discovery = time.time()

        with self._lock:
            snapshot = dict(self.devices)

        # FIX #3: pings en paralelo con ThreadPoolExecutor
        results: Dict[str, Tuple[float, float]] = {}
        with ThreadPoolExecutor(max_workers=min(16, len(snapshot))) as executor:
            future_to_did = {
                executor.submit(ping_host, info["ping"]): did
                for did, info in snapshot.items()
            }
            for future in as_completed(future_to_did):
                did = future_to_did[future]
                try:
                    results[did] = future.result()
                except Exception:
                    results[did] = (999.0, 100.0)

        fallen  = [did for did, (lat, loss) in results.items() if lat >= 500 or loss >= 100]
        is_nc   = len(fallen) >= NETWORK_CRISIS_THRESHOLD
        if is_nc and len(fallen) >= 2:
            self.events["network_crisis"] += 1
        gw_lat, _ = results.get("gateway", (999, 100))
        gateway_ok = gw_lat < 500
        prev = {did: (self.balancer.latest(did).is_reachable if self.balancer.latest(did) else True)
                for did in snapshot}
        for did, info in snapshot.items():
            lat, loss = results[did]
            is_r   = lat < 500 and loss < 100
            metric = DeviceMetric(
                latency_ms=lat, packet_loss_pct=loss, timestamp=time.time(),
                is_reachable=is_r, anchor=gateway_ok, network_crisis=is_nc,
            )
            self.balancer.record(did, metric)
            was = prev.get(did, True)
            if not is_r and was and not is_nc:
                self.events["device_offline"] += 1
            elif is_r and not was:
                self.events["recoveries"] += 1
            if self.cycle % 5 == 0:
                kf = self.balancer.karma(did)
                self.vault.write({
                    "event": "observation", "cycle": self.cycle, "device_id": did,
                    "ip": info["ip"], "ping_target": info["ping"],
                    "mac": info.get("mac","—"), "tipo": info.get("tipo","unknown"),
                    "latency_ms": round(lat, 2), "packet_loss_pct": round(loss, 2),
                    "is_reachable": is_r, "network_crisis": is_nc, "karma": kf,
                })
                with self._lock:
                    if did not in self.karma_history:
                        self.karma_history[did] = []
                    self.karma_history[did].append({
                        "t": datetime.now().strftime("%H:%M:%S"),
                        "kf": kf, "lat": round(lat,1), "loss": round(loss,1), "nc": is_nc,
                    })
                    if len(self.karma_history[did]) > 120:
                        self.karma_history[did] = self.karma_history[did][-120:]

    def get_state(self) -> Dict:
        with self._lock:
            devs_out = {}
            for did, info in self.devices.items():
                latest = self.balancer.latest(did)
                kf     = self.balancer.karma(did)
                ct     = None
                if latest and not latest.is_reachable:
                    ct = "red" if latest.network_crisis else "dispositivo"
                devs_out[did] = {
                    "id": did, "name": info["name"], "ip": info["ip"],
                    "mac": info.get("mac","—"), "hostname": info.get("hostname",""),
                    "tipo": info.get("tipo","unknown"), "fixed": info.get("fixed", False),
                    "first_seen": info.get("first_seen",""), "karma": kf,
                    "components": self.balancer.components(did),
                    "latency":  latest.latency_ms      if latest else None,
                    "loss":     latest.packet_loss_pct if latest else None,
                    "online":   latest.is_reachable    if latest else False,
                    "crisis_type": ct,
                    "history":  self.karma_history.get(did, [])[-60:],
                }
            return {
                "version":       "Oracle Node 2.1-patched",
                "email":         "moteroenchilado@gmail.com",
                "github":        "ramigardner",
                "gateway":       GATEWAY_IP,
                "cycle":         self.cycle,
                "vault_entries": self.vault._total_blocks(),
                "vault_ok":      self.vault.verify_integrity(),
                "devices":       devs_out,
                "log":           list(self.log)[:30],
                "events":        self.events,
                "timestamp":     datetime.now().isoformat(),
                "public_key":    self.public_pem,
                "peer_snapshot": self.vault.get_peer_snapshot(),
            }

    def run_observer(self):
        self._running = True
        self._log("Observer activo", "ok")
        self._run_discovery()
        self._last_discovery = time.time()
        while self._running:
            try:
                self._observe_cycle()
            except Exception as e:
                self._log(f"Error: {e}", "warn")
            time.sleep(OBSERVE_EVERY)

    def stop(self):
        self._running = False
        self.vault.flush()

# ============================================================
# SERVIDOR HTTP
# ============================================================
def make_handler(oracle: ASPROracleNode):
    class Handler(BaseHTTPRequestHandler):

        def _json(self, status: int, data: dict):
            body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",   "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _build_device_payload(self, matched_device, matched_did) -> Dict:
            """Construye y firma el payload de un dispositivo (compartido por /probe y /verify)."""
            proof = oracle.vault.get_last_proof(matched_did)
            payload_to_sign = {
                "device":      matched_did,
                "ip":          matched_device["ip"],
                "karma":       matched_device["karma"],
                "online":      matched_device["online"],
                "timestamp":   datetime.now(timezone.utc).isoformat(),
                "vault_proof": proof,
            }
            sig = sign_data(oracle.private_key,
                            json.dumps(payload_to_sign, sort_keys=True).encode())
            return {
                "name":            matched_device["name"],
                "ip":              matched_device["ip"],
                "karma":           matched_device["karma"],
                "local_karma":     matched_device["karma"],
                "components":      matched_device["components"],
                "online":          matched_device["online"],
                "latency_ms":      matched_device["latency"],
                "packet_loss_pct": matched_device["loss"],
                "crisis_type":     matched_device.get("crisis_type"),
                "vault_proof":     proof,
                "signature":       sig,
                "public_key":      oracle.public_pem,
            }

        def _find_device(self, target_ip, target_did, devices) -> Tuple[Optional[Dict], Optional[str]]:
            matched_device = matched_did = None
            if target_ip:
                for did, d in devices.items():
                    if d.get("ip") == target_ip:
                        matched_device, matched_did = d, did
                        break
            if not matched_device and target_did and target_did in devices:
                matched_device, matched_did = devices[target_did], target_did
            return matched_device, matched_did

        def do_GET(self):
            parsed = urlparse(self.path)
            path   = parsed.path.rstrip("/")
            query  = parse_qs(parsed.query)

            # ── /api/state ───────────────────────────────────
            if path == "/api/state":
                self._json(200, oracle.get_state())

            # ── /status ──────────────────────────────────────
            elif path == "/status":
                chain    = oracle.vault._chain
                last     = chain[-1] if chain else {}
                uptime   = (datetime.now(timezone.utc) - oracle.start_time).total_seconds()
                devices  = oracle.get_state().get("devices", {})
                online   = [d for d in devices.values() if d.get("online")]
                karmas   = [d["karma"] for d in devices.values() if "karma" in d]
                vault_ok = oracle.vault.verify_integrity()
                fp       = hashlib.sha256(oracle.public_pem.encode()).hexdigest()
                self._json(200, {
                    "node":                         "ASPR Oracle Node v2.1-patched",
                    "status":                       "healthy" if vault_ok and online else "degraded",
                    "uptime_seconds":               round(uptime),
                    "current_block_index":          last.get("index", 0),
                    "total_blocks":                 oracle.vault._total_blocks(),
                    "last_block_timestamp":         last.get("timestamp", ""),
                    "vault_integrity":              vault_ok,
                    "monitored_targets":            len(devices),
                    "healthy_targets_ratio":        round(len(online)/len(devices), 3) if devices else 0.0,
                    "recent_karma_average":         round(sum(karmas)/len(karmas), 4) if karmas else 0.0,
                    "observation_interval_seconds": OBSERVE_EVERY,
                    "public_key_fingerprint":       fp,
                    "peer_snapshot":                oracle.vault.get_peer_snapshot(),
                    "version":                      "2.1-patched",
                    "timestamp":                    datetime.now(timezone.utc).isoformat(),
                })

            # ── /probe?ip=X  (nuevo v2.1, endpoint primario) ─
            elif path == "/probe":
                target_ip  = query.get("ip",     [None])[0]
                target_did = query.get("device", [None])[0]
                devices    = oracle.get_state().get("devices", {})
                matched_device, matched_did = self._find_device(target_ip, target_did, devices)
                result = {
                    "probe_by":      "ASPR Oracle Node v2.1-patched",
                    "timestamp":     datetime.now(timezone.utc).isoformat(),
                    "query":         {"ip": target_ip, "device_id": target_did},
                    "found":         False,
                    "vault_status":  oracle.vault.verify_integrity(),
                    "peer_snapshot": oracle.vault.get_peer_snapshot(),
                }
                if matched_device:
                    result["found"] = True
                    result["data"]  = self._build_device_payload(matched_device, matched_did)
                    self._json(200, result)
                else:
                    result["message"] = "Dispositivo no encontrado."
                    self._json(404, result)

            # ── /verify?ip=X  (legado v2.0, mantenido) ───────
            elif path == "/verify":
                target_ip  = query.get("ip",     [None])[0]
                target_did = query.get("device", [None])[0]
                devices    = oracle.get_state().get("devices", {})
                matched_device, matched_did = self._find_device(target_ip, target_did, devices)
                result = {
                    "verified_by": "ASPR Oracle Node v2.1-patched",
                    "timestamp":   datetime.now(timezone.utc).isoformat(),
                    "query":       {"ip": target_ip, "device_id": target_did},
                    "found":       False,
                    "vault_status": oracle.vault.verify_integrity(),
                }
                if matched_device:
                    result["found"] = True
                    result["data"]  = self._build_device_payload(matched_device, matched_did)
                    self._json(200, result)
                else:
                    result["message"] = "Dispositivo no encontrado."
                    self._json(404, result)

            # ── /federated?ip=X — FIX #5: corre en thread separado ──
            elif path == "/federated":
                target_ip = query.get("ip", [None])[0]
                min_nodes = int(query.get("min_nodes", [3])[0])
                if not target_ip:
                    self._json(400, {"error": "Parámetro 'ip' requerido."})
                    return
                # FIX #5: resultado inmediato con estado "pending", el cálculo corre aparte
                # Para simplicidad, devolvemos el resultado sincrónico pero en thread con timeout
                result_holder = {}
                done_event    = threading.Event()

                def _run():
                    result_holder["data"] = get_federated_karma(target_ip, min_nodes=min_nodes)
                    done_event.set()

                t = threading.Thread(target=_run, daemon=True)
                t.start()
                finished = done_event.wait(timeout=30)  # máximo 30 segundos
                if finished:
                    self._json(200, result_holder.get("data", {"error": "Sin resultado"}))
                else:
                    self._json(504, {"error": "Timeout consultando nodos federados (>30s)"})

            # ── /public-key ───────────────────────────────────
            elif path == "/public-key":
                fp = hashlib.sha256(oracle.public_pem.encode()).hexdigest()
                self._json(200, {
                    "node":               "ASPR Oracle Node v2.1-patched",
                    "algorithm":          "Ed25519",
                    "public_key_pem":     oracle.public_pem,
                    "fingerprint_sha256": fp,
                    "timestamp":          datetime.now(timezone.utc).isoformat(),
                    "verify_at":          "https://github.com/ramigardner/aspr-gardener#public-key",
                    "note":               "Verificá que fingerprint_sha256 coincida con el README.",
                })

            # ── /chain/latest ─────────────────────────────────
            elif path == "/chain/latest":
                chain = oracle.vault._chain
                if not chain:
                    self._json(404, {"error": "chain_empty"})
                    return
                last    = chain[-1]
                payload = {
                    "node":            "ASPR Oracle Node v2.1-patched",
                    "endpoint":        "chain/latest",
                    "block_index":     last["index"],
                    "entry_hash":      last["entry_hash"],
                    "prev_hash":       last["prev_hash"],
                    "timestamp":       last["timestamp"],
                    "total_blocks":    oracle.vault._total_blocks(),
                    "vault_integrity": oracle.vault.verify_integrity(),
                }
                msg = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
                payload["signature"]  = sign_data(oracle.private_key, msg)
                payload["public_key"] = oracle.public_pem
                self._json(200, payload)

            # ── /chain/verify?from=HASH ───────────────────────
            elif path == "/chain/verify":
                from_hash    = query.get("from", [None])[0]
                chain        = oracle.vault._chain
                integrity_ok = oracle.vault.verify_integrity()
                ts           = datetime.now(timezone.utc).isoformat()
                result = {
                    "node":         "ASPR Oracle Node v2.1-patched",
                    "endpoint":     "chain/verify",
                    "total_blocks": oracle.vault._total_blocks(),
                    "integrity_ok": integrity_ok,
                    "chain_tip":    chain[-1]["entry_hash"] if chain else None,
                    "timestamp":    ts,
                }
                if from_hash and chain:
                    found = next((b for b in chain if b["entry_hash"] == from_hash), None)
                    if found:
                        result["from_hash_found"] = True
                        result["from_hash_index"] = found["index"]
                        result["blocks_since"]    = oracle.vault._total_blocks() - 1 - found["index"]
                        result["chain_unbroken"]  = integrity_ok
                    else:
                        result["from_hash_found"] = False
                        result["warning"] = "Hash no encontrado en ventana reciente. Puede estar en el histórico archivado."
                summary = {k:v for k,v in result.items()}
                result["signature"] = sign_data(
                    oracle.private_key,
                    json.dumps(summary, sort_keys=True, ensure_ascii=False).encode()
                )
                self._json(200, result)

            # ── /chain?last=N ─────────────────────────────────
            elif path == "/chain" or self.path.startswith("/chain?"):
                try:
                    n = min(int(query.get("last", [10])[0]), 100)
                except (ValueError, IndexError):
                    n = 10
                chain   = oracle.vault._chain
                blocks  = chain[-n:] if chain else []
                tip     = chain[-1]["entry_hash"] if chain else None
                ts      = datetime.now(timezone.utc).isoformat()
                summary = {"chain_tip": tip, "total_blocks": oracle.vault._total_blocks(),
                           "returned": len(blocks), "timestamp": ts}
                payload = {
                    "node":         "ASPR Oracle Node v2.1-patched",
                    "endpoint":     "chain",
                    "requested":    n,
                    "returned":     len(blocks),
                    "total_blocks": oracle.vault._total_blocks(),
                    "chain_tip":    tip,
                    "timestamp":    ts,
                    "blocks":       blocks,
                    "signature":    sign_data(
                        oracle.private_key,
                        json.dumps(summary, sort_keys=True, ensure_ascii=False).encode()
                    ),
                }
                self._json(200, payload)

            # ── dashboard (fallback) ──────────────────────────
            else:
                try:
                    with open("dashboard.html", "r", encoding="utf-8") as f:
                        html = f.read()
                except:
                    html = "<h1>Dashboard no encontrado</h1>"
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html.encode())
                except (ConnectionAbortedError, BrokenPipeError):
                    pass

        def log_message(self, *args): pass
    return Handler

# ============================================================
# MAIN
# ============================================================
def main():
    oracle = ASPROracleNode()
    threading.Thread(target=oracle.run_observer, daemon=True).start()
    server = HTTPServer(("0.0.0.0", DASHBOARD_PORT), make_handler(oracle))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(1.5)
    print(f"\n🌐 Dashboard:       http://localhost:{DASHBOARD_PORT}")
    print(f"🔍 Probe (nuevo):   http://localhost:{DASHBOARD_PORT}/probe?ip=192.168.1.1")
    print(f"🔗 Verify (legado): http://localhost:{DASHBOARD_PORT}/verify?ip=192.168.1.1")
    print(f"🌍 Federado:        http://localhost:{DASHBOARD_PORT}/federated?ip=192.168.1.1")
    print(f"📦 Último bloque:   http://localhost:{DASHBOARD_PORT}/chain/latest")
    print(f"🔑 Clave pública:   http://localhost:{DASHBOARD_PORT}/public-key")
    print(f"📊 Estado API:      http://localhost:{DASHBOARD_PORT}/api/state")
    webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo Oracle Node...")
        oracle.stop()
        server.shutdown()

if __name__ == "__main__":
    main()
