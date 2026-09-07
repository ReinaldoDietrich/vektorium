let t3_editandoId = null;
let t3_catalogos = null;
let t3_fechada = false;
let t3_debounceTimer = null;

const T3_CAMPOS = ['nome', 'sistema_id', 'linha_succao', 'linha_eletrica', 'tabela02_id', 'largura', 'comprimento', 'area', 'pedireito',
  'temp_interna', 'utilizar_valv_reg_pressao', 'dt_evaporacao_desejado',
  'fator_seguranca', 'num_portas', 'porta_largura', 'porta_altura',
  'qtd_luminarias', 'tipo_ambiente_lumino_id', 'potencia_luminaria_texto', 'modelo_luminaria_texto',
  'horas_iluminacao_carga'];

// ---- Potência/Modelo Luminária: cascata em cima da árvore de Ids Comerciais ("1.4" = Iluminação
// Câmaras), mesmo mecanismo da Tela 1/Tela 2 — aprovado 2026-08-08. ----
const T3_ANCORA_ILUMINACAO = '1.4';
let t3_arvoreIds = [];

function t3_filhosArvore(prefixo) {
  return t3_arvoreIds
    .filter(i => i.codigo.startsWith(prefixo + '.') && i.codigo.slice(prefixo.length + 1).indexOf('.') === -1)
    .sort((a, b) => a.codigo.localeCompare(b.codigo, undefined, { numeric: true }));
}

function t3_codigoFilhoPorNome(prefixo, nome) {
  if (!nome) return null;
  const alvo = nome.trim().toLowerCase();
  const f = t3_filhosArvore(prefixo).find(i => (i.nome || '').trim().toLowerCase() === alvo);
  return f ? f.codigo : null;
}

function t3_popularPotenciaLuminaria() {
  const sel = document.getElementById('c3_potencia_luminaria_texto');
  const filhos = t3_filhosArvore(T3_ANCORA_ILUMINACAO);
  sel.innerHTML = '<option value="">—</option>' + filhos.map(f => `<option>${f.nome}</option>`).join('');
}

// Desce recursivamente a partir de `codigo` e devolve só os nós-FOLHA (sem filho nenhum) — mesmo
// mecanismo da Tela 2 (aprovado 2026-08-10).
function t3_folhasArvore(codigo) {
  const diretos = t3_filhosArvore(codigo);
  if (!diretos.length) return [];
  let folhas = [];
  diretos.forEach(f => {
    const netos = t3_filhosArvore(f.codigo);
    folhas = folhas.concat(netos.length ? t3_folhasArvore(f.codigo) : [f]);
  });
  return folhas;
}

function t3_popularModeloLuminaria(valorAtual) {
  const selPot = document.getElementById('c3_potencia_luminaria_texto');
  const selMod = document.getElementById('c3_modelo_luminaria_texto');
  const codPot = t3_codigoFilhoPorNome(T3_ANCORA_ILUMINACAO, selPot.value);
  const folhas = codPot ? t3_folhasArvore(codPot) : [];
  selMod.innerHTML = '<option value="">—</option>' + folhas.map(f => `<option>${f.nome}</option>`).join('');
  selMod.value = valorAtual || '';
}

function initTela3() {
  document.getElementById('c3_btnNova').addEventListener('click', t3_novaCamara);
  document.getElementById('c3_btnNovaTopo').addEventListener('click', () => { t3_novaCamara(); t3_abrirForm(); });
  document.getElementById('c3_btnFecharForm').addEventListener('click', t3_fecharForm);
  document.getElementById('c3_btnSalvar').addEventListener('click', t3_salvarCamara);
  document.getElementById('c3_btnFechar').addEventListener('click', t3_fecharEntidade);
  document.getElementById('c3_btnEditar').addEventListener('click', t3_editarEntidade);
  document.getElementById('c3_btnExcluir').addEventListener('click', t3_excluirCamara);
  document.getElementById('c3_btnDuplicar').addEventListener('click', t3_duplicarCamara);
  document.getElementById('c3_btnAddEvap').addEventListener('click', t3_addForcador);
  document.getElementById('c3_btnAtualizarCalculo').addEventListener('click', () => { if (t3_editandoId) t3_salvarCamara(); });
  ['c3_linha_succao', 'c3_linha_eletrica', 'c3_sistema_id'].forEach(id =>
    document.getElementById(id).addEventListener('input', t3_atualizarCodigo));
  document.getElementById('c3_tabela02_id').addEventListener('change', t3_aplicarDefaultTipo);
  document.getElementById('c3_utilizar_valv_reg_pressao').addEventListener('change', t3_onValvRegChange);
  // Cascata Potência -> Modelo Luminária precisa repopular o select de Modelo ANTES do autoSalvar
  // genérico (abaixo) ler o formulário.
  document.getElementById('c3_potencia_luminaria_texto').addEventListener('change', () => t3_popularModeloLuminaria());
  // Auto-recalcular a carga a cada mudança de qualquer campo de cálculo (change = ao sair do campo).
  T3_CAMPOS.forEach(c => {
    const el = document.getElementById('c3_' + c);
    if (el) el.addEventListener('change', t3_autoSalvar);
  });
  document.addEventListener('projeto-changed', t3_onProjetoChanged);
}

async function t3_carregarCatalogos() {
  if (t3_catalogos) return t3_catalogos;
  const [tabela02, fabricantes, fatorAltura, ambientesLumino, arvoreIds] = await Promise.all([
    api.get('/api/catalogos/tabela-tipo02'), carregarFabricantes(), api.get('/api/catalogos/fator-altura'),
    api.get('/api/catalogos/ambientes-luminotecnico'), api.get('/api/catalogos/ids-comerciais'),
  ]);
  t3_arvoreIds = arvoreIds;
  t3_catalogos = { tabela02, fabricantes, fatorAltura, ambientesLumino };
  return t3_catalogos;
}

async function t3_onProjetoChanged() {
  const semProjeto = !state.projetoId;
  document.getElementById('t3_aviso_sem_projeto').style.display = semProjeto ? 'block' : 'none';
  document.getElementById('t3_conteudo').style.display = semProjeto ? 'none' : 'block';
  if (semProjeto) return;
  const cat = await t3_carregarCatalogos();
  popularSelectsSistema([document.getElementById('c3_sistema_id')]);
  populateSelect(document.getElementById('c3_tabela02_id'), cat.tabela02, 'id', 'tipo', '—');
  populateSelect(document.getElementById('c3_tipo_ambiente_lumino_id'), cat.ambientesLumino, 'id', 'nome', '—');
  t3_popularPotenciaLuminaria();
  t3_popularModeloLuminaria();
  const faixasOrdenadas = [...cat.fatorAltura].sort((a, b) => a.pe_direito_ate_m - b.pe_direito_ate_m);
  const opcoesAltura = faixasOrdenadas.map((f, i) => ({
    id: f.pe_direito_ate_m,
    label: `${i === 0 ? '0,00' : faixasOrdenadas[i - 1].pe_direito_ate_m.toFixed(2)} a ${f.pe_direito_ate_m.toFixed(2)}m`,
  }));
  populateSelect(document.getElementById('c3_pedireito'), opcoesAltura, 'id', 'label', '—');
  wireFabricanteLinhaSelects(document.getElementById('c3_evFab'), document.getElementById('c3_evLinha'), cat.fabricantes);
  t3_novaCamara();
  t3_fecharForm();
  t3_carregarLista();
}

function t3_abrirForm() { document.getElementById('c3_formWrap').style.display = 'block'; }
function t3_fecharForm() { document.getElementById('c3_formWrap').style.display = 'none'; }

function t3_atualizarCodigo() {
  const sel = document.getElementById('c3_sistema_id');
  const nomeSistema = sel.options[sel.selectedIndex]?.text || '';
  const prefixo = nomeSistema.substring(0, 3).toUpperCase() || '???';
  const suc = document.getElementById('c3_linha_succao').value || '?';
  const ele = document.getElementById('c3_linha_eletrica').value || '?';
  document.getElementById('c3_codigo').textContent = prefixo + suc + ele;
}

function t3_aplicarDefaultTipo() {
  const sel = document.getElementById('c3_tabela02_id');
  const tipo = t3_catalogos.tabela02.find(t => String(t.id) === sel.value);
  if (tipo) document.getElementById('c3_temp_interna').value = tipo.temp_interna_default ?? '';
}

function t3_novaCamara() {
  t3_editandoId = null;
  t3_fechada = false;
  t3_aplicarEstadoFechada(null);
  T3_CAMPOS.forEach(c => { const el = document.getElementById('c3_' + c); if (el) el.value = ''; });
  t3_popularModeloLuminaria();
  ['c3_evFab', 'c3_evLinha'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('c3_fator_seguranca').value = '10';
  document.getElementById('c3_btnExcluir').style.display = 'none';
  document.getElementById('c3_btnDuplicar').style.display = 'none';
  document.getElementById('c3_evapList').innerHTML = '';
  document.getElementById('c3_alertas').innerHTML = '';
  document.getElementById('c3_cargaCalc').value = '—';
  document.getElementById('c3_potenciaIlum').value = '—';
  ['c3_sideCarga', 'c3_sideFator', 'c3_sideCap'].forEach(id => document.getElementById(id).textContent = '—');
  document.getElementById('c3_valvRegWrap').style.display = 'none';
  document.getElementById('c3_dtDesejadoWrap').style.display = 'none';
  t3_atualizarCodigo();
}

// Mesma regra da Tela 2 (ver t2_toggleValvReg): usa dt_camara_real (não dt_camara) pro gatilho,
// senão os campos sumiriam assim que a válvula fosse ativada.
function t3_toggleValvReg(dtCamaraReal) {
  const mostrar = dtCamaraReal != null && Math.abs(dtCamaraReal) > 10;
  document.getElementById('c3_valvRegWrap').style.display = mostrar ? 'block' : 'none';
  const ativo = mostrar && document.getElementById('c3_utilizar_valv_reg_pressao').value === 'Sim';
  document.getElementById('c3_dtDesejadoWrap').style.display = ativo ? 'block' : 'none';
  if (!mostrar) document.getElementById('c3_utilizar_valv_reg_pressao').value = '';
}

function t3_onValvRegChange() {
  const dtWrap = document.getElementById('c3_dtDesejadoWrap');
  if (document.getElementById('c3_utilizar_valv_reg_pressao').value === 'Sim') {
    dtWrap.style.display = 'block';
  } else {
    dtWrap.style.display = 'none';
    document.getElementById('c3_dt_evaporacao_desejado').value = '';
  }
}

function t3_coletarPayload() {
  const p = {};
  T3_CAMPOS.forEach(c => {
    const el = document.getElementById('c3_' + c);
    if (el.tagName === 'SELECT') p[c] = el.value ? (isNaN(el.value) ? el.value : Number(el.value)) : null;
    else if (['nome', 'linha_succao', 'linha_eletrica'].includes(c)) p[c] = el.value;
    else p[c] = el.value === '' ? null : parseNumBR(el.value);
  });
  return p;
}

function t3_autoSalvar() {
  if (!document.getElementById('c3_sistema_id').value) return;
  if (t3_fechada) return;
  clearTimeout(t3_debounceTimer);
  t3_debounceTimer = setTimeout(() => t3_salvarCamara(), 300);
}

async function t3_salvarCamara() {
  const payload = t3_coletarPayload();
  if (!payload.sistema_id) { alert('Selecione o Sistema.'); return; }
  if (payload.utilizar_valv_reg_pressao === 'Sim') {
    const dt = payload.dt_evaporacao_desejado;
    if (dt == null || !(dt > 4 && dt < 10)) {
      alert('Dt. Evaporação Desejado deve ser maior que 4 e menor que 10.');
      return;
    }
  }
  const editando = t3_editandoId;
  let resultado;
  if (editando) resultado = await api.put(`/api/camaras-simples/${editando}`, payload);
  else resultado = await api.post('/api/camaras-simples', payload);
  await t3_carregarLista();
  // Mantém a câmara aberta (nova ou existente) — zerar aqui fazia o usuário perder o contexto
  // logo depois de salvar, bem quando ia adicionar um forçador em seguida.
  await t3_abrirCamara(editando || resultado.id);
}

function t3_aplicarEstadoFechada(c) {
  const wrap = document.getElementById('c3_formWrap');
  const btnSalvar = document.getElementById('c3_btnSalvar');
  const btnFechar = document.getElementById('c3_btnFechar');
  const barraFechada = document.getElementById('c3_barraFechada');
  const barraDesatualizada = document.getElementById('c3_barraDesatualizada');
  if (t3_fechada) {
    wrap.classList.add('entidade-fechada');
    btnSalvar.style.display = 'none';
    btnFechar.style.display = 'none';
    barraDesatualizada.style.display = c && c.calculo_desatualizado ? 'flex' : 'none';
  } else {
    wrap.classList.remove('entidade-fechada');
    btnSalvar.style.display = '';
    btnFechar.style.display = t3_editandoId ? 'inline-block' : 'none';
    barraDesatualizada.style.display = 'none';
  }
}

async function t3_editarEntidade() {
  if (!t3_editandoId) return;
  const c = await api.post(`/api/camaras-simples/${t3_editandoId}/editar`, {});
  t3_fechada = false;
  t3_aplicarEstadoFechada(c);
  await t3_carregarLista();
}

async function t3_fecharEntidade() {
  if (!t3_editandoId) return;
  await t3_salvarCamara();
  const c = await api.post(`/api/camaras-simples/${t3_editandoId}/salvar`, {});
  t3_fechada = true;
  t3_aplicarEstadoFechada(c);
  await t3_carregarLista();
  await t3_abrirCamara(t3_editandoId);
}

async function t3_excluirCamara() {
  if (!t3_editandoId) return;
  if (!confirm('Excluir esta câmara?')) return;
  await api.del(`/api/camaras-simples/${t3_editandoId}`);
  t3_novaCamara();
  t3_carregarLista();
}

// Copia só dimensionamento (campos básicos) — Forçadores/Válvulas NÃO vêm junto, a câmara nova
// nasce sem forçador selecionado. Abre já pronta pra renomear.
async function t3_duplicarCamara() {
  if (!t3_editandoId) return;
  const nova = await api.post(`/api/camaras-simples/${t3_editandoId}/duplicar`, {});
  await t3_carregarLista();
  await t3_abrirCamara(nova.id);
  const campoNome = document.getElementById('c3_nome');
  campoNome.focus();
  campoNome.select();
}

async function t3_abrirCamara(id) {
  const c = await api.get(`/api/camaras-simples/${id}`);
  t3_editandoId = id;
  T3_CAMPOS.forEach(campo => { const el = document.getElementById('c3_' + campo); if (el) el.value = c[campo] ?? ''; });
  t3_popularModeloLuminaria(c.modelo_luminaria_texto);
  document.getElementById('c3_btnExcluir').style.display = 'inline-block';
  document.getElementById('c3_btnDuplicar').style.display = 'inline-block';
  document.getElementById('c3_codigo').textContent = c.codigo;
  await carregarOpcoesValvulas(c.sistema_id);
  t3_renderCalculo(c.calculo);
  t3_fechada = !!c.fechada;
  t3_aplicarEstadoFechada(c);
  t3_abrirForm();
}

// Atualiza só o painel calculado (cálculo, forçadores, alertas, código) sem tocar nos campos
// básicos do formulário (T3_CAMPOS) — evita sobrescrever edições ainda não salvas quando o
// usuário adiciona/edita/exclui uma linha de forçador.
async function t3_atualizarPainel(id) {
  const c = await api.get(`/api/camaras-simples/${id}`);
  document.getElementById('c3_codigo').textContent = c.codigo;
  await carregarOpcoesValvulas(c.sistema_id);
  t3_renderCalculo(c.calculo);
}

function t3_renderCalculo(calc) {
  t3_toggleValvReg(calc.dt_camara_real);
  document.getElementById('c3_cargaCalc').value = fmtKcal(calc.carga_termica_total_24h / 24);
  document.getElementById('c3_potenciaIlum').value = calc.potencia_ilum_w != null ? fmtNum(calc.potencia_ilum_w) : '—';
  const lum = calc.luminotecnico || {};
  document.getElementById('c3_area').value = lum.area ?? (document.getElementById('c3_area').value || '—');
  document.getElementById('c3_lumFluxo').value = lum.fluxo_total ?? '—';
  document.getElementById('c3_lumLuxCalc').value = lum.lux_calculado ?? '—';
  document.getElementById('c3_lumDiferenca').value = lum.diferenca_lux ?? '—';
  document.getElementById('c3_lumAtende').value = lum.atende ?? '—';
  document.getElementById('c3_sideCarga').textContent = fmtKcal(calc.carga_termica_total_24h / 24);
  document.getElementById('c3_sideFator').textContent = (document.getElementById('c3_fator_seguranca').value || '—') + '%';
  document.getElementById('c3_sideCap').textContent = fmtKcal(calc.capacidade_requerida);
  document.getElementById('c3_capRequerida').value = fmtKcal(calc.capacidade_requerida);
  renderizarForcadores(document.getElementById('c3_evapList'), calc.forcadores, {
    onFolgaChange: (id, val) => t3_upd_forcador(id, { folga_desejada: parseNumBR(val) }),
    onQuantidadeChange: (id, val) => t3_upd_forcador(id, { quantidade: parseInt(val, 10) || 1 }),
    onTipoDegeloChange: (id, val) => t3_upd_forcador(id, { tipo_degelo: val || null }),
    onConsiderar: (id) => t3_upd_forcador(id, { considerado: true }),
    onExcluir: (id) => t3_del_forcador(id),
    onNomenclaturaChange: (id, valores) => t3_upd_forcador(id, { nomenclatura_selecionada: valores }),
    onValvulaPayload: (id, payload) => t3_upd_valvula(id, payload),
  }, T3_DYNAMIC_IDS);
  renderizarAlertas(document.getElementById('c3_alertas'), calc.alertas);
}

async function t3_addForcador() {
  if (!t3_editandoId) { alert('Salve a câmara primeiro.'); return; }
  const fabricante_id = document.getElementById('c3_evFab').value, linha_id = document.getElementById('c3_evLinha').value;
  if (!fabricante_id || !linha_id) return;
  await api.post(`/api/camaras-simples/${t3_editandoId}/forcadores`, { fabricante_id: Number(fabricante_id), linha_id: Number(linha_id), folga_desejada: 10 });
  document.getElementById('c3_evFab').value = '';
  document.getElementById('c3_evLinha').innerHTML = '';
  await t3_atualizarPainel(t3_editandoId);
  t3_carregarLista();
}
async function t3_upd_forcador(id, payload) {
  await api.put(`/api/camaras-simples/${t3_editandoId}/forcadores/${id}`, payload);
  await t3_atualizarPainel(t3_editandoId);
  t3_carregarLista();
}
async function t3_del_forcador(id) {
  if (!confirm('Excluir esta linha de forçador?')) return;
  await api.del(`/api/camaras-simples/${t3_editandoId}/forcadores/${id}`);
  await t3_atualizarPainel(t3_editandoId);
  t3_carregarLista();
}

// Campos da válvula (Modelo/Carga%/Conexões) não entram em nenhum cálculo — só grava, sem
// recarregar a câmara (recarregar destruía e recriava os <input>, quebrando o Tab no meio da digitação).
async function t3_upd_valvula(id, payload) {
  await api.put(`/api/camaras-simples/valvulas/${id}`, payload);
  if (t3_editandoId) await t3_atualizarPainel(t3_editandoId);  // Abert. Válv. recalculada no backend
}

async function t3_carregarLista() {
  const el = document.getElementById('c3_lista');
  if (!state.projetoId) { el.innerHTML = ''; return; }
  const todas = await api.get(`/api/camaras-simples?projeto_id=${state.projetoId}`);
  if (todas.length === 0) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma câmara cadastrada ainda.</div>'; return; }
  el.innerHTML = todas.map(c => {
    const badge = c.fechada
      ? (c.calculo_desatualizado
        ? '<span class="badge-fechada desatualizada">desatualizado</span>'
        : '<span class="badge-fechada ok">fechada</span>')
      : '';
    return `<div class="lista-card" data-camara="${c.id}">
      <div class="nome">${c.codigo} — ${c.nome}${badge}</div>
      <div class="meta">Carga: ${fmtKcal(c.calculo.capacidade_requerida)} · Área ${c.area}m²${_resumoForcadorCamara(c.calculo)}</div>
    </div>`;
  }).join('');
  el.querySelectorAll('[data-camara]').forEach(card => card.addEventListener('click', () => t3_abrirCamara(Number(card.dataset.camara))));
}

window.initTela3 = initTela3;
window.telaShowHandlers[3] = async () => {
  if (!state.projetoId) return;
  await carregarSistemasDoProjeto();
  popularSelectsSistema([document.getElementById('c3_sistema_id')]);
  t3_carregarLista();
};
document.addEventListener('DOMContentLoaded', initTela3);
