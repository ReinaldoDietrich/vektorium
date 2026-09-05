// Status 423 (Locked) é usado SÓ pelo bloqueio de projeto fechado (ver
// backend/routers/_bloqueio_projeto.py) — nenhum outro erro do backend usa esse código. O bloqueio
// é SILENCIOSO no front (sem alerta): quando o projeto está fechado, o modo só-visualização já
// congela as telas dele (ver .projeto-bloqueado em style.css / aplicarModoProjetoFechado em main.js),
// então o usuário nem chega a tentar editar. O backend continua recusando como defesa dos dados
// (aprovado 2026-08-12).
async function _extrairErro(r) {
  try { const j = await r.json(); return j.detail || JSON.stringify(j); } catch (_) {}
  try { return await r.text(); } catch (_) {}
  return `HTTP ${r.status}`;
}
async function _falhaEscrita(r) {
  throw new Error(await _extrairErro(r));
}

// Anexa o token de sessão (se o usuário estiver logado) — usado pelos endpoints que precisam
// chamar a API remota de catálogo/cálculo (Fase 3). Sem login, esses endpoints continuam
// calculando local como sempre calcularam (ver backend/calc_service.py) — login só entra em
// jogo quando o backend local tenta usar a API remota e precisa repassar o token do usuário.
function _authHeader() {
  const token = (typeof AUTH !== 'undefined') ? AUTH.token() : null;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// --- Roteamento catálogo → Fly.io (ADR §7: toda leitura de catálogo passa pelo Supabase) ---
const REMOTE_API = 'https://vektorium-calc.fly.dev';

const _PREFIXOS_REMOTOS = [
  '/api/catalogos/ids-comerciais', '/api/catalogos/fabricantes',
  '/api/forcadores', '/api/condensadores', '/api/polinomios',
  '/api/calc', '/api/catalogo-comercial', '/api/valvulas-expansao',
  '/api/importacao',
  '/api/admin',
  '/api/luminotecnico/lampadas',
  '/api/uc/catalogos-detalhe', '/api/uc/unidades', '/api/uc/eletricas',
  '/api/uc/template', '/api/uc/documento', '/api/uc/preview',
  '/api/uc/confirmar', '/api/uc/exportar-bd', '/api/uc/opcoes',
];

const _ESCRITA_SEM_FALLBACK = [
  '/api/admin',
  '/api/uc/confirmar',
  '/api/forcadores/importar', '/api/forcadores/confirmar',
  '/api/condensadores/importar', '/api/condensadores/confirmar',
  '/api/importacao',
  '/api/catalogo-comercial',
  '/api/valvulas-expansao',
];

const _LEITURA_SEM_FALLBACK = [
  '/api/admin',
  '/api/forcadores', '/api/condensadores', '/api/polinomios',
  '/api/valvulas-expansao',
  '/api/catalogos/ids-comerciais', '/api/catalogos/fabricantes',
  '/api/luminotecnico/lampadas',
  '/api/uc/catalogos-detalhe', '/api/uc/unidades', '/api/uc/eletricas',
  '/api/uc/template', '/api/uc/documento', '/api/uc/preview',
  '/api/uc/opcoes',
];

async function _base(path) {
  if (typeof AUTH === 'undefined' || !AUTH.token()) return '';
  for (const p of _PREFIXOS_REMOTOS) {
    if (path === p || path.startsWith(p + '/') || path.startsWith(p + '?')) {
      await AUTH.garantirToken();
      if (!AUTH.token()) return '';
      return REMOTE_API;
    }
  }
  return '';
}

function _semFallback(path) {
  for (const p of _ESCRITA_SEM_FALLBACK) {
    if (path === p || path.startsWith(p + '/') || path.startsWith(p + '?')) return true;
  }
  return false;
}

function _semFallbackLeitura(path) {
  for (const p of _LEITURA_SEM_FALLBACK) {
    if (path === p || path.startsWith(p + '/') || path.startsWith(p + '?')) return true;
  }
  return false;
}

async function _fetchComTimeout(url, opts, timeoutMs) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...opts, signal: ctrl.signal });
    clearTimeout(timer);
    return r;
  } catch (e) {
    clearTimeout(timer);
    throw e;
  }
}

const api = {
  async get(path) {
    const base = await _base(path);
    if (base) {
      const noFbLeitura = _semFallbackLeitura(path);
      try {
        const r = await _fetchComTimeout(base + path, { headers: { ..._authHeader() } }, 8000);
        if (r.ok) return r.json();
        if (noFbLeitura) {
          const txt = await r.text().catch(() => r.status);
          throw new Error(`Erro ao carregar catálogo do servidor (${r.status}): ${txt}`);
        }
      } catch (e) {
        if (noFbLeitura) throw e;
      }
      const r2 = await fetch(path, { headers: {} });
      if (!r2.ok) throw new Error(await _extrairErro(r2));
      return r2.json();
    }
    const r = await fetch(path, { headers: { ..._authHeader() } });
    if (!r.ok) throw new Error(await _extrairErro(r));
    return r.json();
  },
  async post(path, body) {
    const base = await _base(path);
    if (base) {
      const noFb = _semFallback(path);
      try {
        const r = await _fetchComTimeout(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json', ..._authHeader() }, body: JSON.stringify(body || {}) }, noFb ? 60000 : 8000);
        if (r.ok) return r.json();
        if (noFb) throw new Error(await _extrairErro(r));
      } catch (e) { if (noFb) throw e; }
      const r2 = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
      if (!r2.ok) await _falhaEscrita(r2);
      return r2.json();
    }
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', ..._authHeader() }, body: JSON.stringify(body || {}) });
    if (!r.ok) await _falhaEscrita(r);
    return r.json();
  },
  async put(path, body) {
    const base = await _base(path);
    if (base) {
      const noFb = _semFallback(path);
      try {
        const r = await _fetchComTimeout(base + path, { method: 'PUT', headers: { 'Content-Type': 'application/json', ..._authHeader() }, body: JSON.stringify(body || {}) }, noFb ? 60000 : 8000);
        if (r.ok) return r.json();
        if (noFb) throw new Error(await _extrairErro(r));
      } catch (e) { if (noFb) throw e; }
      const r2 = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
      if (!r2.ok) await _falhaEscrita(r2);
      return r2.json();
    }
    const r = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json', ..._authHeader() }, body: JSON.stringify(body || {}) });
    if (!r.ok) await _falhaEscrita(r);
    return r.json();
  },
  async del(path) {
    const base = await _base(path);
    if (base) {
      const noFb = _semFallback(path);
      try {
        const r = await _fetchComTimeout(base + path, { method: 'DELETE', headers: { ..._authHeader() } }, noFb ? 60000 : 8000);
        if (r.ok) return r.json();
        if (noFb) throw new Error(await _extrairErro(r));
      } catch (e) { if (noFb) throw e; }
      const r2 = await fetch(path, { method: 'DELETE', headers: {} });
      if (!r2.ok) await _falhaEscrita(r2);
      return r2.json();
    }
    const r = await fetch(path, { method: 'DELETE', headers: { ..._authHeader() } });
    if (!r.ok) await _falhaEscrita(r);
    return r.json();
  },
  async upload(path, file, extraFields) {
    const base = await _base(path);
    const fd = new FormData();
    fd.append('arquivo', file);
    Object.entries(extraFields || {}).forEach(([k, v]) => fd.append(k, v));
    if (base) {
      const noFb = _semFallback(path);
      try {
        const r = await _fetchComTimeout(base + path, { method: 'POST', headers: { ..._authHeader() }, body: fd }, noFb ? 60000 : 8000);
        if (r.ok) {
          const resultado = await r.json();
          const fdLocal = new FormData();
          fdLocal.append('arquivo', file);
          Object.entries(extraFields || {}).forEach(([k, v]) => fdLocal.append(k, v));
          fetch(path, { method: 'POST', body: fdLocal }).catch(() => {});
          return resultado;
        }
        if (noFb) throw new Error(await _extrairErro(r));
      } catch (e) { if (noFb) throw e; }
      const fd2 = new FormData();
      fd2.append('arquivo', file);
      Object.entries(extraFields || {}).forEach(([k, v]) => fd2.append(k, v));
      const r2 = await fetch(path, { method: 'POST', body: fd2 });
      if (!r2.ok) throw new Error(await _extrairErro(r2));
      return r2.json();
    }
    const r = await fetch(path, { method: 'POST', headers: { ..._authHeader() }, body: fd });
    if (!r.ok) throw new Error(await _extrairErro(r));
    return r.json();
  },
  // Exportação Excel de tela de projeto: se o projeto tem "Pasta de Salvamento" (Tela 1), o backend
  // grava o arquivo direto na pasta e devolve JSON {salvo_em}; senão devolve o próprio arquivo (download).
  async baixarOuSalvar(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(await _extrairErro(r));
    const tipo = r.headers.get('Content-Type') || '';
    if (tipo.includes('application/json')) {
      const dados = await r.json();
      if (dados.salvo_em) { alert(`Arquivo salvo em:\n${dados.salvo_em}`); return; }
      return dados;
    }
    const blob = await r.blob();
    const nome = (r.headers.get('Content-Disposition') || '').match(/filename=([^;]+)/);
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nome ? nome[1].trim() : 'arquivo.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  },
};
