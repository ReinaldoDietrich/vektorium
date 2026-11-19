const state = {
  projetoId: null,
  projetoGen: 0,
  sistemas: [],
  // Gancho de PERFIL (espelha backend/perfil.py). HOJE local/mono-usuário → sempre master, tudo
  // liberado. TODO(online): preencher a partir da autenticação real. Pontos que serão restritos a
  // master no futuro devem checar state.isMaster.
  isMaster: true,
};

window.telaShowHandlers = {};

// Nunca permitir que o scroll do mouse altere um campo numérico focado sem o usuário perceber
// (mesmo sem as setinhas visíveis, o navegador ainda incrementa/decrementa no wheel por padrão).
document.addEventListener('wheel', () => {
  if (document.activeElement && document.activeElement.type === 'number') document.activeElement.blur();
}, { passive: true });

// parseFloat não entende vírgula decimal ("0,9" vira 0) — usuários brasileiros digitam vírgula.
// Usar sempre esta função em vez de parseFloat direto em valor vindo de input do usuário.
function parseNumBR(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '') return null;
  const n = parseFloat(s.replace(',', '.'));
  return isNaN(n) ? null : n;
}

// Para campos exibidos com separador de milhar (ex.: "1.234,56") — remove os pontos de milhar
// antes de interpretar a vírgula decimal.
function parseNumBRMilhar(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '') return null;
  return parseNumBR(s.replace(/\./g, ''));
}

async function escolherPastaEExportar(url) {
  let pasta = null;
  if (window.vektorium?.escolherPasta) {
    pasta = await window.vektorium.escolherPasta({ titulo: 'Escolher pasta para exportação' });
  } else {
    try {
      const r = await api.post('/api/projetos/escolher-pasta', {});
      pasta = r.pasta || null;
    } catch (_) {}
  }
  if (!pasta) return;
  const sep = url.includes('?') ? '&' : '?';
  api.baixarOuSalvar(url + sep + 'pasta=' + encodeURIComponent(pasta));
}

// Aplica formatação "1.234,56" (milhar + 2 decimais) num campo ao perder o foco.
function formatarCampoMilhar(id) {
  const el = document.getElementById(id);
  el.addEventListener('blur', () => {
    const n = parseNumBRMilhar(el.value);
    el.value = n != null ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '';
  });
}

async function showTab(n, skipHandler) {
  document.querySelectorAll('.screen').forEach(el => el.classList.toggle('active', el.id === 'tela' + n));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', Number(b.dataset.tab) === n));
  if (!skipHandler && window.telaShowHandlers[n]) {
    mostrarLoading('Carregando...');
    try { await window.telaShowHandlers[n](); } catch (_) {}
    finally { esconderLoading(); }
  }
  if (window.onShowTab) window.onShowTab(n);
}

function fmtNum(n, dec = 0) {
  if (n === null || n === undefined || n === '') return '—';
  return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function fmtKcal(n) {
  if (n === null || n === undefined) return '—';
  return fmtNum(n, 0) + ' kcal/h';
}

// Resumo do forçador considerado + temperaturas do sistema, ao lado das dimensões nos cards de
// lista das Telas 2 e 3. Formato: " · 1x <modelo comercial> · Cap. unit. N kcal/h · Evap. X°C ·
// Cond. Y°C · ΔEvap. Z°C". Sem forçador considerado: retorna '' (mostra só carga + dimensões).
function _resumoForcadorCamara(calculo) {
  if (!calculo) return '';
  const f = (calculo.forcadores || []).find(x => x.considerado && x.modelo_resultante);
  const partes = [];
  if (f) {
    const modelo = f.modelo_comercial || f.modelo_resultante;
    partes.push(`${f.quantidade || 1}x ${modelo}`);
    if (f.capacidade_corrigida_unitaria != null) partes.push(`Cap. unit. ${fmtKcal(f.capacidade_corrigida_unitaria)}`);
  }
  if (calculo.temp_evaporacao_sistema != null) partes.push(`Evap. ${fmtNum(calculo.temp_evaporacao_sistema, 0)}°C`);
  if (calculo.temp_condensacao != null) partes.push(`Cond. ${fmtNum(calculo.temp_condensacao, 1)}°C`);
  if (calculo.dt_camara != null) partes.push(`ΔEvap. ${fmtNum(calculo.dt_camara, 0)}°C`);
  return partes.length ? ' · ' + partes.join(' · ') : '';
}

function populateSelect(select, items, valueKey, labelKey, placeholder) {
  const atual = select.value;
  select.innerHTML = (placeholder ? `<option value="">${placeholder}</option>` : '') +
    items.map(it => `<option value="${it[valueKey]}">${it[labelKey]}</option>`).join('');
  if (atual) select.value = atual;
}

async function carregarSistemasDoProjeto() {
  if (!state.projetoId) { state.sistemas = []; return; }
  const pid = state.projetoId;
  const gen = state.projetoGen;
  const sistemas = await api.get(`/api/projetos/${pid}/sistemas`);
  if (gen !== state.projetoGen) return;
  state.sistemas = sistemas;
}

function popularSelectsSistema(selects) {
  selects.forEach(sel => populateSelect(sel, state.sistemas, 'id', 'nome', '—'));
}

async function definirProjetoAtivo(projetoId) {
  aplicarModoProjetoFechado(false);
  state.projetoId = projetoId;
  state.projetoGen++;
  await carregarSistemasDoProjeto();
  document.dispatchEvent(new CustomEvent('projeto-changed', { detail: { projetoId } }));
}

// Fecha o projeto ativo — nenhuma tela (2 em diante) mostra dados até o usuário escolher
// explicitamente um projeto de novo. Nunca reabre sozinho ao abrir o app (sem localStorage).
async function fecharProjetoAtivo() {
  await definirProjetoAtivo(null);
  const form = document.getElementById('formProjetoWrap');
  if (form) form.style.display = 'none';
}

// Projeto fechado (Tela 1) = as telas DESSE projeto ficam só para visualização. Esta função liga/
// desliga a classe .projeto-bloqueado no <body>; o congelamento visual em si (quais telas, quais
// campos) está no CSS (ver style.css). Só o projeto ativo, quando fechado, congela — catálogos
// globais, a lista de projetos e os demais projetos nunca bloqueiam (aprovado 2026-08-12).
function aplicarModoProjetoFechado(fechado) {
  document.body.classList.toggle('projeto-bloqueado', !!fechado);
}

// Verificação de licença ativa — consulta /api/licenca/status (backend local, que cacheia do Fly.io).
// Se licença inativa, congela a UI com a classe .licenca-inativa (mesma mecânica do projeto-bloqueado).
let _licencaAtiva = true;
let _licencaTimer = null;

async function verificarLicenca() {
  if (!AUTH.logado()) { _aplicarLicenca(true); return; }
  try {
    await AUTH.garantirToken();
    if (!AUTH.token()) { _aplicarLicenca(true); return; }
    const r = await fetch('/api/licenca/status', { headers: { 'Authorization': 'Bearer ' + AUTH.token() } });
    if (r.ok) {
      const d = await r.json();
      _aplicarLicenca(!!d.ativa);
    }
  } catch (e) { _aplicarLicenca(true); }
}

function pararVerificacaoLicenca() {
  if (_licencaTimer) { clearInterval(_licencaTimer); _licencaTimer = null; }
  _aplicarLicenca(true);
}

function _aplicarLicenca(ativa) {
  _licencaAtiva = ativa;
  document.body.classList.toggle('licenca-inativa', !ativa);
  const aviso = document.getElementById('avisoLicencaInativa');
  if (aviso) aviso.style.display = ativa ? 'none' : 'flex';
}

function iniciarVerificacaoPeriodicaLicenca() {
  // SE-074: verificação periódica desativada — apenas aplica licença ativa uma vez
  if (_licencaTimer) clearInterval(_licencaTimer);
  _aplicarLicenca(true);
}

window.verificarLicenca = verificarLicenca;
window.iniciarVerificacaoPeriodicaLicenca = iniciarVerificacaoPeriodicaLicenca;
window.pararVerificacaoLicenca = pararVerificacaoLicenca;

function _mostrarPopupSair() {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9999;display:flex;align-items:center;justify-content:center;';
    const box = document.createElement('div');
    box.style.cssText = 'background:#fff;border-radius:8px;padding:24px;min-width:360px;max-width:480px;box-shadow:0 8px 32px rgba(0,0,0,.25);';
    box.innerHTML = `
      <h3 style="margin:0 0 16px;font-size:15px;">Deseja salvar as alterações antes de sair?</h3>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:20px;">
        <button class="vk-sair-cancelar" style="padding:8px 16px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;">Cancelar</button>
        <button class="vk-sair-sem" style="padding:8px 16px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;color:#b91c1c;">Sair sem Salvar</button>
        <button class="vk-sair-salvar" style="padding:8px 16px;border:none;border-radius:4px;background:#1668c7;color:#fff;cursor:pointer;font-weight:bold;">Salvar e Sair</button>
      </div>`;
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    function fechar(r) { overlay.remove(); resolve(r); }
    box.querySelector('.vk-sair-cancelar').addEventListener('click', () => fechar('cancelar'));
    box.querySelector('.vk-sair-sem').addEventListener('click', () => fechar('sem-salvar'));
    box.querySelector('.vk-sair-salvar').addEventListener('click', () => fechar('salvar'));
    box.addEventListener('keydown', (e) => { if (e.key === 'Escape') fechar('cancelar'); });
    box.querySelector('.vk-sair-salvar').focus();
  });
}

function _mostrarPopupUsuario(email) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9999;display:flex;align-items:center;justify-content:center;';
    const box = document.createElement('div');
    box.style.cssText = 'background:#fff;border-radius:8px;padding:24px;min-width:360px;max-width:480px;box-shadow:0 8px 32px rgba(0,0,0,.25);';
    box.innerHTML = `
      <h3 style="margin:0 0 6px;font-size:15px;">Conta conectada</h3>
      <p style="margin:0 0 20px;font-size:13px;color:#6b7280;">${email || '—'}</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="vk-usr-cancelar" style="padding:8px 16px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;">Cancelar</button>
        <button class="vk-usr-logout" style="padding:8px 16px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;color:#1668c7;">Voltar ao Login</button>
        <button class="vk-usr-fechar" style="padding:8px 16px;border:none;border-radius:4px;background:#b91c1c;color:#fff;cursor:pointer;font-weight:bold;">Fechar Aplicativo</button>
      </div>`;
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    function fechar(r) { overlay.remove(); resolve(r); }
    box.querySelector('.vk-usr-cancelar').addEventListener('click', () => fechar('cancelar'));
    box.querySelector('.vk-usr-logout').addEventListener('click', () => fechar('logout'));
    box.querySelector('.vk-usr-fechar').addEventListener('click', () => fechar('fechar'));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) fechar('cancelar'); });
    box.addEventListener('keydown', (e) => { if (e.key === 'Escape') fechar('cancelar'); });
    box.querySelector('.vk-usr-cancelar').focus();
  });
}

async function logoutDoApp() {
  let querSalvar = true;
  if (state.projetoId) {
    try {
      const escolha = await _mostrarPopupSair();
      if (escolha === 'cancelar') return false;
      querSalvar = (escolha === 'salvar');
    } catch (_) {
      querSalvar = true;
    }
  }

  if (typeof window._pararHeartbeat === 'function') window._pararHeartbeat();

  mostrarLoading('Realizando logout...');
  try {
    if (querSalvar && state.projetoId) {
      for (let t = 0; t < 3; t++) {
        try {
          const r = await api.post('/api/workspace/salvar-todos');
          if (r.ok) break;
        } catch (_) {}
      }
    }
    if (typeof AUTH !== 'undefined') {
      try { await AUTH.garantirToken(); } catch (_) {}
      const _uid = AUTH._sessao && AUTH._sessao.user ? AUTH._sessao.user.id : null;
      const _jwt = AUTH.token();
      if (_uid && _jwt) {
        for (let tentativa = 0; tentativa < 10; tentativa++) {
          try {
            const r = await api.post('/api/cloud/delete-lock', { user_id: _uid, token: _jwt });
            if (r && r.ok) break;
          } catch (_) {}
          await new Promise(ok => setTimeout(ok, 1500));
        }
      }
      try { await AUTH.logout(); } catch (_) {}
    }
    try { await api.post('/api/workspace/fechar-todos'); } catch (_) {}
  } finally {
    esconderLoading();
    if (typeof _atualizarBotaoLogin === 'function') _atualizarBotaoLogin();
    if (typeof _mostrarTelaLogin === 'function') _mostrarTelaLogin();
  }
  return true;
}
window.logoutDoApp = logoutDoApp;

async function sairDoApp() {
  if (!state.projetoId) {
    if (typeof window._pararHeartbeat === 'function') window._pararHeartbeat();
    if (typeof window.electronAPI !== 'undefined') window.electronAPI.fecharApp();
    return true;
  }
  let querSalvar = true;
  try {
    const escolha = await _mostrarPopupSair();
    if (escolha === 'cancelar') return false;
    querSalvar = (escolha === 'salvar');
  } catch (_) {
    querSalvar = true;
  }

  if (typeof window._pararHeartbeat === 'function') window._pararHeartbeat();

  if (typeof state !== 'undefined' && state.isMaster === true) {
    mostrarLoading('Realizando backup pré-logout...');
    try {
      const ctrl = new AbortController();
      setTimeout(() => ctrl.abort(), 30000);
      await fetch('/api/sistema/backup-pre-logout', { method: 'POST', signal: ctrl.signal });
    } catch (_) {
      console.warn('[sairDoApp] backup pré-logout falhou (best-effort)');
    }
  }

  try {
    if (querSalvar) {
      for (let t = 0; t < 3; t++) {
        try {
          const r = await api.post('/api/workspace/salvar-todos');
          if (r.ok) break;
        } catch (_) {}
      }
    }
    if (typeof AUTH !== 'undefined') {
      try { await AUTH.garantirToken(); } catch (_) {}
      const _uid = AUTH._sessao && AUTH._sessao.user ? AUTH._sessao.user.id : null;
      const _jwt = AUTH.token();
      if (_uid && _jwt) {
        mostrarLoading('Removendo sessão do servidor...');
        for (let tentativa = 0; tentativa < 10; tentativa++) {
          try {
            const r = await api.post('/api/cloud/delete-lock', { user_id: _uid, token: _jwt });
            if (r && r.ok) break;
          } catch (_) {}
          await new Promise(ok => setTimeout(ok, 1500));
        }
      }
      try { await AUTH.logout(); } catch (_) {}
    }

    try { await api.post('/api/workspace/fechar-todos'); } catch (_) {}

  } finally {
    esconderLoading();
    const overlay = document.getElementById('overlaySaida');
    if (overlay) overlay.style.display = 'flex';

    if (window.vektorium && typeof window.vektorium.sair === 'function') {
      await window.vektorium.sair();
    } else {
      location.reload();
    }
  }
  return true;
}


// SE-074: auto-save configurável via Configurações Globais (default 5 min)
(async function _iniciarAutoSave() {
  let minutos = 5;
  try {
    const cfgs = await api.get('/api/catalogos/configuracao-global');
    const cfg = cfgs.find(c => c.chave === 'intervalo_auto_salvamento_min');
    if (cfg && cfg.valor > 0) minutos = cfg.valor;
  } catch (_) {}
  setInterval(async () => {
    const ov = document.getElementById('overlayCarregamento');
    const jaAtivo = ov && ov.classList.contains('ativo');
    if (!jaAtivo) mostrarLoading('Salvando...');
    try { await api.post('/api/workspace/salvar-todos'); } catch (_) {}
    if (!jaAtivo) esconderLoading();
  }, minutos * 60 * 1000);
})();

async function _carregarPerfilRemoto() {
  // SE-074: chamada remota desativada — perfil sempre master (mono-usuário local)
}

async function atualizarCamposPorArvore() {
  const arvore = await api.get('/api/catalogos/ids-comerciais');
  const porCampo = {};
  for (const no of arvore) {
    if (!no.campo_id) continue;
    if (!porCampo[no.campo_id]) porCampo[no.campo_id] = [];
    porCampo[no.campo_id].push(no);
  }
  let atualizados = 0;
  for (const [campoId, nodes] of Object.entries(porCampo)) {
    const sel = document.querySelector(`select[data-id-campo="${campoId}"]`);
    if (!sel) continue;
    const valorAtual = sel.value;
    const primeiraOpcao = sel.options.length ? sel.options[0].outerHTML : '<option value="">—</option>';
    nodes.sort((a, b) => a.codigo.localeCompare(b.codigo, undefined, { numeric: true }));
    sel.innerHTML = primeiraOpcao + nodes.map(n => `<option value="${n.codigo}">${n.nome}</option>`).join('');
    sel.value = valorAtual;
    atualizados++;
  }
  return atualizados;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => showTab(Number(btn.dataset.tab))));
  document.getElementById('btnSair').addEventListener('click', sairDoApp);
  if (window.initTela1) window.initTela1();
  _carregarPerfilRemoto();
  const m = location.hash.match(/^#tela(\d)$/);
  if (m) showTab(Number(m[1]));
});
