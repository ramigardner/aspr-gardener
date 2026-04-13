// aspr-sync.js · ASPR Oracle Network Connector v1.0
// Vanilla JS · Offline-first · C64 Aesthetic · Structural Trust
(function() {
  "use strict";
  const CFG = {
    endpoints: [window.location.origin, "http://localhost:7771", "http://127.0.0.1:7771"],
    poll: 2500, maxPoll: 12000, cacheKey: "aspr_state_v1"
  };

  let ep = null, online = false, delay = CFG.poll;
  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  // ── UI Helpers ───────────────────────────────────────────────
  function set(selector, val) {
    $$(selector).forEach(el => {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.value = val;
      else el.textContent = val ?? '—';
    });
  }

  function statusBadge(msg, color, state) {
    let badge = $('#aspr-status-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.id = 'aspr-status-badge';
      badge.style.cssText = `position:fixed;top:12px;right:12px;padding:4px 10px;background:rgba(8,8,30,0.92);border:1px solid var(--c);color:var(--c);font:12px 'Courier New',monospace;z-index:9999;letter-spacing:1px;transition:all .3s;`;
      document.body.prepend(badge);
    }
    badge.style.setProperty('--c', color);
    badge.innerHTML = `${msg}<span style="animation:blink 1s step-end infinite">_</span>`;
    document.body.dataset.asprState = state;
  }

  // ── Fetch seguro ─────────────────────────────────────────────
  async function safeGet(path) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 3500);
    try {
      const r = await fetch(`${ep}${path}`, { signal: ctrl.signal, headers: {'Accept':'application/json'} });
      clearTimeout(t);
      return r.ok ? await r.json() : null;
    } catch { clearTimeout(t); return null; }
  }

  // ── Descubrimiento ───────────────────────────────────────────
  async function discover() {
    statusBadge("🔄 ESCANEANDO PUERTOS...", "#ffff80", "scanning");
    for (const candidate of CFG.endpoints) {
      ep = candidate;
      if (await safeGet("/api/state")) return true;
    }
    ep = null;
    statusBadge("🔴 NODO NO DETECTADO", "#ff5050", "offline");
    return false;
  }

  // ── Renderizado Estructural ──────────────────────────────────
  function render(state) {
    if (!state) return;
    const devs = state.devices || {};
    const devList = Object.values(devs);
    const karmas = devList.map(d => d.karma || 0);
    const avg = karmas.length ? (karmas.reduce((a,b)=>a+b,0)/karmas.length).toFixed(3) : '—';
    const onlineCount = devList.filter(d => d.online).length;
    const fp = state.public_key ? `${state.public_key.slice(8,16)}...${state.public_key.slice(-8)}` : '—';

    set('[data-aspr="blocks"]', state.vault_entries);
    set('[data-aspr="cycle"]', state.cycle);
    set('[data-aspr="karma"]', avg);
    set('[data-aspr="vault"]', state.vault_ok ? '✅ INTEGRIDAD OK' : '❌ FALLO');
    set('[data-aspr="fp"]', fp);
    set('[data-aspr="online"]', onlineCount);
    set('[data-aspr="events"]', `${state.events?.network_crisis||0} crisis · ${state.events?.recoveries||0} rec`);

    // Tabla de dispositivos
    const tbody = $('#aspr-devices');
    if (tbody) {
      tbody.innerHTML = devList.map(d => `
        <tr style="font:13px monospace;border-bottom:1px solid #282860">
          <td style="padding:4px">${d.id}</td>
          <td style="padding:4px;color:#80ff80">${d.ip}</td>
          <td style="padding:4px">${d.tipo||'—'}</td>
          <td style="padding:4px;color:#ffff80">${(d.karma||0).toFixed(3)}</td>
          <td style="padding:4px">${d.latency||'—'}ms</td>
          <td style="padding:4px;color:${d.online?'#80ff80':'#ff5050'}">${d.online?'ONLINE':'OFFLINE'}</td>
        </tr>`).join('');
    }

    statusBadge("🟢 ONLINE · NODO ACTIVO", "#80ff80", "online");
  }

  // ── Loop Principal ───────────────────────────────────────────
  async function tick() {
    if (!ep) {
      if (!(await discover())) { delay = Math.min(delay*1.4, CFG.maxPoll); setTimeout(tick, delay); return; }
      delay = CFG.poll;
    }

    const state = await safeGet("/api/state");
    if (state) {
      online = true; delay = CFG.poll;
      localStorage.setItem(CFG.cacheKey, JSON.stringify({t:Date.now(), d:state}));
      render(state);
    } else {
      online = false; delay = Math.min(delay*1.5, CFG.maxPoll);
      statusBadge("🔴 OFFLINE · REINTENTANDO...", "#ff5050", "offline");
      // Fallback caché
      const c = JSON.parse(localStorage.getItem(CFG.cacheKey) || 'null');
      if (c?.d) render(c.d);
    }
    setTimeout(tick, delay);
  }

  // ── Init ─────────────────────────────────────────────────────
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tick);
  else tick();
})();