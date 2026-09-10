const state = {
  projetoId: null,
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

// Aplica formatação "1.234,56" (milhar + 2 decimais) num campo ao perder o foco.
function formatarCampoMilhar(id) {
  const el = document.getElementById(id);
  el.addEventListener('blur', () => {
    const n = parseNumBRMilhar(el.value);
    el.value = n != null ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '';
  });
}

function showTab(n) {
  document.querySelectorAll('.screen').forEach(el => el.classList.toggle('active', el.id === 'tela' + n));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', Number(b.dataset.tab) === n));
  if (window.telaShowHandlers[n]) window.telaShowHandlers[n]();
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
  state.sistemas = await api.get(`/api/projetos/${state.projetoId}/sistemas`);
}

function popularSelectsSistema(selects) {
  selects.forEach(sel => populateSelect(sel, state.sistemas, 'id', 'nome', '—'));
}

async function definirProjetoAtivo(projetoId) {
  state.projetoId = projetoId;
  await carregarSistemasDoProjeto();
  document.dispatchEvent(new CustomEvent('projeto-changed', { detail: { projetoId } }));
}

// Fecha o projeto ativo — nenhuma tela (2 em diante) mostra dados até o usuário escolher
// explicitamente um projeto de novo. Nunca reabre sozinho ao abrir o app (sem localStorage).
async function fecharProjetoAtivo() {
  await definirProjetoAtivo(null);
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
  } catch (e) { /* sem rede — mantém último estado */ }
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
  if (_licencaTimer) clearInterval(_licencaTimer);
  verificarLicenca();
  _licencaTimer = setInterval(verificarLicenca, 30 * 60 * 1000);
}

window.verificarLicenca = verificarLicenca;
window.iniciarVerificacaoPeriodicaLicenca = iniciarVerificacaoPeriodicaLicenca;
window.pararVerificacaoLicenca = pararVerificacaoLicenca;

async function sairDoApp() {
  if (typeof AUTH !== 'undefined' && AUTH.token()) {
    await AUTH.logout();
  }
  if (window.vektorium && window.vektorium.sair) {
    document.getElementById('overlaySaida').style.display = 'flex';
    window.vektorium.sair();
  } else {
    location.reload();
  }
}

async function _carregarPerfilRemoto() {
  if (typeof AUTH === 'undefined' || !AUTH.logado()) return;
  try {
    const dados = await api.get('/api/admin/meu-perfil');
    state.isMaster = dados.usuario.papel === 'master';
  } catch (_) {}
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => showTab(Number(btn.dataset.tab))));
  document.getElementById('btnSair').addEventListener('click', sairDoApp);
  if (window.initTela1) window.initTela1();
  _carregarPerfilRemoto();
  const m = location.hash.match(/^#tela(\d)$/);
  if (m) showTab(Number(m[1]));
});
