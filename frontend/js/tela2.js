let t2_editandoId = null;
let t2_catalogos = null;
let t2_fechada = false;
let t2_debounceTimer = null;

const T2_CAMPOS = ['nome', 'sistema_id', 'linha_succao', 'linha_eletrica', 'temp_interna', 'largura', 'comprimento',
  'pedireito', 'utilizar_valv_reg_pressao', 'dt_evaporacao_desejado',
  'produto_id', 'qtd_estocada', 'mov_diaria', 'tempo_processo', 'temp_entrada', 'temp_saida',
  'tipo_embalagem_id', 'massa_embalagem', 'isolamento_parede_id', 'isolamento_teto_id', 'isolamento_piso_id',
  'fonte_ar', 'temp_adjacente', 'umidade_adjacente', 'num_pessoas',
  'tempo_pessoas', 'qtd_luminarias', 'tipo_ambiente_lumino_id', 'potencia_luminaria_texto',
  'modelo_luminaria_texto', 'horas_iluminacao_carga',
  'fator_seguranca', 'tempo_func_compressores'];

// ---- Potência/Modelo Luminária: cascata em cima da árvore de Ids Comerciais ("1.4" = Iluminação
// Câmaras), mesmo mecanismo já usado na Tela 1 (t1_filhosArvore/t1_popularSelectArvore) — aprovado
// 2026-08-08. NÃO é FK pra tabela própria: o valor salvo é o texto exato do nó escolhido. ----
const T2_ANCORA_ILUMINACAO = '1.4';
let t2_arvoreIds = [];

function t2_filhosArvore(prefixo) {
  return t2_arvoreIds
    .filter(i => i.codigo.startsWith(prefixo + '.') && i.codigo.slice(prefixo.length + 1).indexOf('.') === -1)
    .sort((a, b) => a.codigo.localeCompare(b.codigo, undefined, { numeric: true }));
}

function t2_codigoFilhoPorNome(prefixo, nome) {
  if (!nome) return null;
  const alvo = nome.trim().toLowerCase();
  const f = t2_filhosArvore(prefixo).find(i => (i.nome || '').trim().toLowerCase() === alvo);
  return f ? f.codigo : null;
}

// Desce recursivamente a partir de `codigo` e devolve só os nós-FOLHA (sem filho nenhum) —
// usado onde a tela não tem campo pra escolher os níveis intermediários (ex.: Fabricante), então
// precisa pular direto pro nível final, não importa quantos níveis existam no meio (aprovado
// 2026-08-10: "o código vai direto para todos os modelos válidos dentro do id anterior").
function t2_folhasArvore(codigo) {
  const diretos = t2_filhosArvore(codigo);
  if (!diretos.length) return [];
  let folhas = [];
  diretos.forEach(f => {
    const netos = t2_filhosArvore(f.codigo);
    folhas = folhas.concat(netos.length ? t2_folhasArvore(f.codigo) : [f]);
  });
  return folhas;
}

function t2_popularPotenciaLuminaria() {
  const sel = document.getElementById('c2_potencia_luminaria_texto');
  const filhos = t2_filhosArvore(T2_ANCORA_ILUMINACAO);
  sel.innerHTML = '<option value="">—</option>' + filhos.map(f => `<option>${f.nome}</option>`).join('');
}

// Popula Modelo Luminária com os nós-FOLHA abaixo do nó de Potência escolhido (pula qualquer
// nível intermediário tipo Fabricante, já que não há campo próprio pra ele nesta tela — aprovado
// 2026-08-10). `valorAtual` (opcional) tenta manter o Modelo já salvo se ainda existir como folha.
function t2_popularModeloLuminaria(valorAtual) {
  const selPot = document.getElementById('c2_potencia_luminaria_texto');
  const selMod = document.getElementById('c2_modelo_luminaria_texto');
  const codPot = t2_codigoFilhoPorNome(T2_ANCORA_ILUMINACAO, selPot.value);
  const folhas = codPot ? t2_folhasArvore(codPot) : [];
  selMod.innerHTML = '<option value="">—</option>' + folhas.map(f => `<option>${f.nome}</option>`).join('');
  selMod.value = valorAtual || '';
}

function initTela2() {
  document.getElementById('c2_btnNova').addEventListener('click', t2_novaCamara);
  document.getElementById('c2_btnNovaTopo').addEventListener('click', () => { t2_novaCamara(); t2_abrirForm(); });
  document.getElementById('c2_btnFecharForm').addEventListener('click', t2_fecharForm);
  document.getElementById('c2_btnSalvar').addEventListener('click', t2_salvarCamara);
  document.getElementById('c2_btnEditar').addEventListener('click', t2_editarEntidade);
  document.getElementById('c2_btnExcluir').addEventListener('click', t2_excluirCamara);
  document.getElementById('c2_btnDuplicar').addEventListener('click', t2_duplicarCamara);
  document.getElementById('c2_btnAddEquip').addEventListener('click', t2_addEquipamento);
  document.getElementById('c2_btnAddPorta').addEventListener('click', t2_addPorta);
  document.getElementById('c2_pt_fonte').addEventListener('change', t2_togglePortaAdj);
  document.getElementById('c2_btnAddEvap').addEventListener('click', t2_addForcador);
  document.getElementById('c2_btnAtualizarCalculo').addEventListener('click', () => { if (t2_editandoId) t2_salvarCamara(); });
  ['c2_linha_succao', 'c2_linha_eletrica', 'c2_sistema_id'].forEach(id =>
    document.getElementById(id).addEventListener('input', t2_atualizarCodigo));
  ['c2_qtd_estocada', 'c2_mov_diaria'].forEach(formatarCampoMilhar);
  // Cascata Potência -> Modelo Luminária precisa repopular o select de Modelo ANTES do autoSalvar
  // genérico (abaixo) ler o formulário — senão salva um Modelo desatualizado da Potência anterior.
  document.getElementById('c2_potencia_luminaria_texto').addEventListener('change', () => t2_popularModeloLuminaria());
  // Auto-recalcular a carga a cada mudança de QUALQUER campo de cálculo (change = ao sair do
  // campo). Cria a câmara no primeiro campo alterado (se já houver Sistema), o que também elimina
  // a exigência de "salvar antes" ao chegar nos equipamentos.
  T2_CAMPOS.forEach(c => {
    const el = document.getElementById('c2_' + c);
    if (el) el.addEventListener('change', t2_autoSalvar);
  });
  document.getElementById('c2_fonte_ar').addEventListener('change', t2_toggleAdjacente);
  document.getElementById('c2_utilizar_valv_reg_pressao').addEventListener('change', t2_onValvRegChange);
  document.getElementById('vi_arquivo').addEventListener('change', t2_previewValvulas);
  document.getElementById('vi_btnCancelar').addEventListener('click', t2_cancelarPreviewValvulas);
  document.getElementById('vi_btnConfirmar').addEventListener('click', t2_confirmarImportacaoValvulas);
  document.addEventListener('projeto-changed', t2_onProjetoChanged);
}

async function t2_carregarCatalogos() {
  if (t2_catalogos) return t2_catalogos;
  const [produtos, embalagens, paredeTeto, piso, equipamentos, fabricantes, ambientesLumino, arvoreIds] = await Promise.all([
    api.get('/api/catalogos/produtos'), api.get('/api/catalogos/tipos-embalagem'),
    api.get('/api/catalogos/isolamento-parede-teto'), api.get('/api/catalogos/isolamento-piso'),
    api.get('/api/catalogos/tipos-equipamento'), carregarFabricantes(),
    api.get('/api/catalogos/ambientes-luminotecnico'), api.get('/api/catalogos/ids-comerciais'),
  ]);
  t2_arvoreIds = arvoreIds;
  t2_catalogos = { produtos, embalagens, paredeTeto, piso, equipamentos, fabricantes, ambientesLumino };
  return t2_catalogos;
}

async function t2_onProjetoChanged() {
  const semProjeto = !state.projetoId;
  document.getElementById('t2_aviso_sem_projeto').style.display = semProjeto ? 'block' : 'none';
  document.getElementById('t2_conteudo').style.display = semProjeto ? 'none' : 'block';
  if (semProjeto) return;
  const cat = await t2_carregarCatalogos();
  popularSelectsSistema([document.getElementById('c2_sistema_id')]);
  populateSelect(document.getElementById('c2_produto_id'), cat.produtos, 'id', 'nome', '—');
  populateSelect(document.getElementById('c2_tipo_embalagem_id'), cat.embalagens, 'id', 'nome', null);
  populateSelect(document.getElementById('c2_isolamento_parede_id'), cat.paredeTeto, 'id', 'material', '—');
  populateSelect(document.getElementById('c2_isolamento_teto_id'), cat.paredeTeto, 'id', 'material', '—');
  populateSelect(document.getElementById('c2_isolamento_piso_id'), cat.piso, 'id', 'material', '—');
  populateSelect(document.getElementById('c2_eqTipo'), cat.equipamentos, 'id', 'nome', '—');
  populateSelect(document.getElementById('c2_tipo_ambiente_lumino_id'), cat.ambientesLumino, 'id', 'nome', '—');
  t2_popularPotenciaLuminaria();
  t2_popularModeloLuminaria();
  wireFabricanteLinhaSelects(document.getElementById('c2_evFab'), document.getElementById('c2_evLinha'), cat.fabricantes);
  t2_novaCamara();
  t2_fecharForm();
  t2_carregarLista();
}

function t2_abrirForm() { document.getElementById('c2_formWrap').style.display = 'block'; }
function t2_fecharForm() { document.getElementById('c2_formWrap').style.display = 'none'; }

// Válvula Reguladora de Pressão (Temperatura de Saturação controlada) — os 2 campos só aparecem
// quando o Δt de evaporação REAL da câmara (temp_interna - sistema.temp_evaporacao) é > 10°C.
// Usa dt_camara_real (não dt_camara) de propósito: dt_camara vira o Δt virtual assim que a
// válvula é ativada, e normalmente é <10°C — se o gatilho usasse dt_camara, os campos sumiriam
// assim que o usuário marcasse "Sim", sem deixar ele desligar de novo.
function t2_toggleValvReg(dtCamaraReal) {
  const mostrar = dtCamaraReal != null && Math.abs(dtCamaraReal) > 10;
  document.getElementById('c2_valvRegWrap').style.display = mostrar ? 'block' : 'none';
  const ativo = mostrar && document.getElementById('c2_utilizar_valv_reg_pressao').value === 'Sim';
  document.getElementById('c2_dtDesejadoWrap').style.display = ativo ? 'block' : 'none';
  if (!mostrar) document.getElementById('c2_utilizar_valv_reg_pressao').value = '';
}

function t2_onValvRegChange() {
  const dtWrap = document.getElementById('c2_dtDesejadoWrap');
  if (document.getElementById('c2_utilizar_valv_reg_pressao').value === 'Sim') {
    dtWrap.style.display = 'block';
  } else {
    dtWrap.style.display = 'none';
    document.getElementById('c2_dt_evaporacao_desejado').value = '';
  }
}

// Mostra os campos de temperatura/umidade adjacentes só quando a Fonte do ar = "Adjacente".
function t2_toggleAdjacente() {
  const adj = document.getElementById('c2_fonte_ar').value === 'Adjacente';
  document.getElementById('c2_adjWrapTemp').style.display = adj ? 'block' : 'none';
  document.getElementById('c2_adjWrapUr').style.display = adj ? 'block' : 'none';
}

function t2_atualizarCodigo() {
  const sel = document.getElementById('c2_sistema_id');
  const nomeSistema = sel.options[sel.selectedIndex]?.text || '';
  const prefixo = nomeSistema.substring(0, 3).toUpperCase() || '???';
  const suc = document.getElementById('c2_linha_succao').value || '?';
  const ele = document.getElementById('c2_linha_eletrica').value || '?';
  document.getElementById('c2_codigo').textContent = prefixo + suc + ele;
}

function t2_novaCamara() {
  t2_editandoId = null;
  t2_fechada = false;
  t2_aplicarEstadoFechada(null);
  T2_CAMPOS.forEach(c => { const el = document.getElementById('c2_' + c); if (el) el.value = ''; });
  t2_popularModeloLuminaria();
  ['c2_evFab', 'c2_evLinha'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('c2_fator_seguranca').value = '10';
  document.getElementById('c2_tempo_func_compressores').value = '18';
  document.getElementById('c2_horas_iluminacao_carga').value = '24';
  document.getElementById('c2_fonte_ar').value = 'Externo';
  document.getElementById('c2_temp_adjacente').value = '25';
  document.getElementById('c2_umidade_adjacente').value = '60';
  t2_toggleAdjacente();
  document.getElementById('c2_btnExcluir').style.display = 'none';
  document.getElementById('c2_btnDuplicar').style.display = 'none';
  document.getElementById('c2_equipList').innerHTML = '';
  document.getElementById('c2_portasList').innerHTML = '';
  document.getElementById('c2_pt_fonte').value = 'Externo';
  t2_togglePortaAdj();
  document.getElementById('c2_evapList').innerHTML = '';
  document.getElementById('c2_alertas').innerHTML = '';
  document.getElementById('c2_dtCamara').value = '—';
  document.getElementById('c2_valvRegWrap').style.display = 'none';
  document.getElementById('c2_dtDesejadoWrap').style.display = 'none';
  t2_limparPainel();
  t2_atualizarCodigo();
}

function t2_limparPainel() {
  ['c2_sideQ1','c2_sideQ2','c2_sideQ3','c2_sideQ4','c2_sideQ5','c2_sideQ6','c2_sideQ7','c2_sideFator','c2_sideTempo','c2_sideCap']
    .forEach(id => document.getElementById(id).textContent = '—');
  document.getElementById('c2_capRequerida').value = '—';
}

function t2_coletarPayload() {
  const p = {};
  T2_CAMPOS.forEach(c => {
    const el = document.getElementById('c2_' + c);
    if (!el) return;
    if (el.tagName === 'SELECT') p[c] = el.value ? (isNaN(el.value) ? el.value : Number(el.value)) : null;
    else if (['nome', 'linha_succao', 'linha_eletrica', 'protecao_porta'].includes(c)) p[c] = el.value;
    else if (['qtd_estocada', 'mov_diaria'].includes(c)) p[c] = parseNumBRMilhar(el.value);
    else p[c] = el.value === '' ? null : parseNumBR(el.value);
  });
  return p;
}

function t2_autoSalvar() {
  if (!document.getElementById('c2_sistema_id').value) return;
  if (t2_fechada) return;
  clearTimeout(t2_debounceTimer);
  t2_debounceTimer = setTimeout(() => t2_salvarCamara(), 300);
}

async function t2_salvarCamara() {
  const payload = t2_coletarPayload();
  if (!payload.sistema_id) { alert('Selecione o Sistema.'); return; }
  if (payload.utilizar_valv_reg_pressao === 'Sim') {
    const dt = payload.dt_evaporacao_desejado;
    if (dt == null || !(dt > 4 && dt < 10)) {
      alert('Dt. Evaporação Desejado deve ser maior que 4 e menor que 10.');
      return;
    }
  }
  const editando = t2_editandoId;
  let resultado;
  if (editando) resultado = await api.put(`/api/camaras-completo/${editando}`, payload);
  else resultado = await api.post('/api/camaras-completo', payload);
  await t2_carregarLista();
  // Mantém a câmara aberta (nova ou existente) pra permitir adicionar forçador/equipamento em
  // seguida sem perder o contexto — fechar/zerar aqui era o que causava a sensação de "salvar
  // fecha a janela" quando o usuário tentava incluir algo na seção 7 logo depois de salvar.
  await t2_abrirCamara(editando || resultado.id);
}

function t2_aplicarEstadoFechada(c) {
  const wrap = document.getElementById('c2_formWrap');
  const btnSalvar = document.getElementById('c2_btnSalvar');
  const barraDesatualizada = document.getElementById('c2_barraDesatualizada');
  if (t2_fechada) {
    wrap.classList.add('entidade-fechada');
    btnSalvar.style.display = 'none';
    barraDesatualizada.style.display = c && c.calculo_desatualizado ? 'flex' : 'none';
  } else {
    wrap.classList.remove('entidade-fechada');
    btnSalvar.style.display = '';
    barraDesatualizada.style.display = 'none';
  }
}

async function t2_editarEntidade() {
  if (!t2_editandoId) return;
  const c = await api.post(`/api/camaras-completo/${t2_editandoId}/editar`, {});
  t2_fechada = false;
  t2_aplicarEstadoFechada(c);
  await t2_carregarLista();
}

async function t2_excluirCamara() {
  if (!t2_editandoId) return;
  if (!confirm('Excluir esta câmara?')) return;
  await api.del(`/api/camaras-completo/${t2_editandoId}`);
  t2_novaCamara();
  t2_carregarLista();
}

// Copia só dimensionamento (campos básicos + equipamentos + portas) — Forçadores/Válvulas NÃO
// vêm junto, a câmara nova nasce sem forçador selecionado. Abre já pronta pra renomear.
async function t2_duplicarCamara() {
  if (!t2_editandoId) return;
  const nova = await api.post(`/api/camaras-completo/${t2_editandoId}/duplicar`, {});
  await t2_carregarLista();
  await t2_abrirCamara(nova.id);
  const campoNome = document.getElementById('c2_nome');
  campoNome.focus();
  campoNome.select();
}

async function t2_abrirCamara(id) {
  const c = await api.get(`/api/camaras-completo/${id}`);
  t2_editandoId = id;
  T2_CAMPOS.forEach(campo => {
    const el = document.getElementById('c2_' + campo);
    if (!el) return;
    if (['qtd_estocada', 'mov_diaria'].includes(campo)) {
      el.value = c[campo] != null ? Number(c[campo]).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '';
    } else {
      el.value = c[campo] ?? '';
    }
  });
  // Modelo Luminária é cascata da Potência escolhida — o select só tem os filhos daquele nó, então
  // precisa ser repopulado (com o valor salvo) DEPOIS do loop genérico acima ter setado a Potência.
  t2_popularModeloLuminaria(c.modelo_luminaria_texto);
  if (!c.fonte_ar) document.getElementById('c2_fonte_ar').value = 'Externo';
  t2_toggleAdjacente();
  document.getElementById('c2_btnExcluir').style.display = 'inline-block';
  document.getElementById('c2_btnDuplicar').style.display = 'inline-block';
  document.getElementById('c2_codigo').textContent = c.codigo;
  t2_renderEquipamentos(c.equipamentos);
  t2_renderPortas(c.portas);
  await carregarOpcoesValvulas(c.sistema_id);
  t2_renderCalculo(c.calculo);
  t2_fechada = !!c.fechada;
  t2_aplicarEstadoFechada(c);
  t2_abrirForm();
}

// Atualiza só o painel calculado (equipamentos, cálculo, forçadores, alertas, código) sem tocar
// nos campos básicos do formulário (T2_CAMPOS) — usado depois de ações que não alteram esses
// campos (add/editar/excluir forçador ou equipamento). Recarregar o formulário inteiro nesses
// casos (como t2_abrirCamara faz) sobrescrevia qualquer edição ainda não salva com o "Salvar".
async function t2_atualizarPainel(id) {
  const c = await api.get(`/api/camaras-completo/${id}`);
  document.getElementById('c2_codigo').textContent = c.codigo;
  t2_renderEquipamentos(c.equipamentos);
  await carregarOpcoesValvulas(c.sistema_id);
  t2_renderCalculo(c.calculo);
}

function t2_renderCalculo(calc) {
  t2_toggleValvReg(calc.dt_camara_real);
  const valvAtiva = document.getElementById('c2_utilizar_valv_reg_pressao').value === 'Sim'
    && document.getElementById('c2_dt_evaporacao_desejado').value !== '';
  document.getElementById('c2_dtCamara').value = valvAtiva ? 'Delta virtual'
    : (calc.dt_camara != null ? fmtNum(calc.dt_camara, 1) : '—');
  document.getElementById('c2_sideQ1').textContent = fmtKcal(calc.q1_produto);
  document.getElementById('c2_sideQ2').textContent = fmtKcal(calc.q2_embalagem);
  document.getElementById('c2_sideQ3').textContent = fmtKcal(calc.q3_penetracao);
  document.getElementById('c2_sideQ4').textContent = fmtKcal(calc.q4_infiltracao);
  document.getElementById('c2_sideQ5').textContent = fmtKcal(calc.q5_pessoas);
  document.getElementById('c2_sideQ6').textContent = fmtKcal(calc.q6_iluminacao);
  document.getElementById('c2_sideQ7').textContent = fmtKcal(calc.q7_equipamentos);
  document.getElementById('c2_sideQ8').textContent = fmtKcal(calc.q8_forcadores);
  document.getElementById('c2_sideFator').textContent = (document.getElementById('c2_fator_seguranca').value || '—') + '%';
  document.getElementById('c2_sideTempo').textContent = (document.getElementById('c2_tempo_func_compressores').value || '—') + 'h/24h';
  document.getElementById('c2_sideCap').textContent = fmtKcal(calc.capacidade_requerida);
  document.getElementById('c2_capRequerida').value = fmtKcal(calc.capacidade_requerida);
  const lum = calc.luminotecnico || {};
  document.getElementById('c2_lumFluxo').value = lum.fluxo_total ?? '—';
  document.getElementById('c2_lumLuxCalc').value = lum.lux_calculado ?? '—';
  document.getElementById('c2_lumDiferenca').value = lum.diferenca_lux ?? '—';
  document.getElementById('c2_lumAtende').value = lum.atende ?? '—';
  renderizarForcadores(document.getElementById('c2_evapList'), calc.forcadores, {
    onFolgaChange: (id, val) => t2_upd_forcador(id, { folga_desejada: parseNumBR(val) }),
    onQuantidadeChange: (id, val) => t2_upd_forcador(id, { quantidade: parseInt(val, 10) || 1 }),
    onTipoDegeloChange: (id, val) => t2_upd_forcador(id, { tipo_degelo: val || null }),
    onConsiderar: (id) => t2_upd_forcador(id, { considerado: true }),
    onExcluir: (id) => t2_del_forcador(id),
    onNomenclaturaChange: (id, valores) => t2_upd_forcador(id, { nomenclatura_selecionada: valores }),
    onValvulaPayload: (id, payload) => t2_upd_valvula(id, payload),
  }, T2_DYNAMIC_IDS);
  renderizarAlertas(document.getElementById('c2_alertas'), calc.alertas);
}

function t2_renderEquipamentos(itens) {
  const el = document.getElementById('c2_equipList');
  if (!itens || itens.length === 0) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhum equipamento adicionado ainda.</div>'; return; }
  const cat = t2_catalogos ? t2_catalogos.equipamentos : [];
  el.innerHTML = '<table class="list"><tbody>' + itens.map(e =>
    `<tr>
      <td style="width:40%;"><select data-equip-tipo="${e.id}">${cat.map(t => `<option value="${t.id}" ${t.id === e.tipo_equipamento_id ? 'selected' : ''}>${t.nome}</option>`).join('')}</select></td>
      <td style="width:15%;">Qtd.: <input type="text" value="${e.qtd}" data-equip-qtd="${e.id}" style="width:50px;display:inline-block;"></td>
      <td style="width:20%;">Tempo: <input type="text" value="${e.tempo}" data-equip-tempo="${e.id}" style="width:50px;display:inline-block;">h/24h</td>
      <td style="width:15%;color:#6b7280;">${fmtNum(e.calor_unitario_kcal_h)}kcal/h × ${e.qtd}</td>
      <td style="text-align:right;"><span class="btn-text danger" data-excluir-equip="${e.id}">Excluir</span></td>
     </tr>`).join('') + '</tbody></table>';
  const salvarEquip = async (id) => {
    await api.put(`/api/camaras-completo/${t2_editandoId}/equipamentos/${id}`, {
      tipo_equipamento_id: Number(el.querySelector(`[data-equip-tipo="${id}"]`).value),
      qtd: Number(el.querySelector(`[data-equip-qtd="${id}"]`).value) || 1,
      tempo: parseNumBR(el.querySelector(`[data-equip-tempo="${id}"]`).value) || 0,
    });
    await t2_atualizarPainel(t2_editandoId);
    t2_carregarLista();
  };
  el.querySelectorAll('[data-equip-tipo]').forEach(s => s.addEventListener('change', () => salvarEquip(s.dataset.equipTipo)));
  el.querySelectorAll('[data-equip-qtd]').forEach(i => i.addEventListener('change', () => salvarEquip(i.dataset.equipQtd)));
  el.querySelectorAll('[data-equip-tempo]').forEach(i => i.addEventListener('change', () => salvarEquip(i.dataset.equipTempo)));
  el.querySelectorAll('[data-excluir-equip]').forEach(b => b.addEventListener('click', async () => {
    await api.del(`/api/camaras-completo/${t2_editandoId}/equipamentos/${b.dataset.excluirEquip}`);
    t2_atualizarPainel(t2_editandoId);
    t2_carregarLista();
  }));
}

async function t2_addEquipamento() {
  if (!t2_editandoId) { alert('Salve a câmara primeiro.'); return; }
  if (document.querySelectorAll('#c2_equipList tbody tr').length >= 5) { alert('Máximo de 5 equipamentos por câmara.'); return; }
  const tipo_equipamento_id = document.getElementById('c2_eqTipo').value;
  if (!tipo_equipamento_id) return;
  await api.post(`/api/camaras-completo/${t2_editandoId}/equipamentos`, {
    tipo_equipamento_id: Number(tipo_equipamento_id), qtd: Number(document.getElementById('c2_eqQtd').value) || 1,
    tempo: parseNumBR(document.getElementById('c2_eqTempo').value) || 0,
  });
  document.getElementById('c2_eqTipo').value = '';
  document.getElementById('c2_eqQtd').value = '1';
  document.getElementById('c2_eqTempo').value = '';
  await t2_atualizarPainel(t2_editandoId);
  t2_carregarLista();
}

// ---- Portas (Seção 4 — infiltração; várias por câmara, cada uma com sua fonte de ar) ----
function t2_togglePortaAdj() {
  const adj = document.getElementById('c2_pt_fonte').value === 'Adjacente';
  document.getElementById('c2_pt_adjWrap').style.display = adj ? 'grid' : 'none';
}

async function t2_addPorta() {
  if (!t2_editandoId) {
    if (!document.getElementById('c2_sistema_id').value) { alert('Selecione o Sistema primeiro.'); return; }
    await t2_salvarCamara();
  }
  const larg = parseNumBR(document.getElementById('c2_pt_larg').value);
  const alt = parseNumBR(document.getElementById('c2_pt_alt').value);
  if (!larg || !alt) { alert('Informe largura e altura da porta.'); return; }
  const fonte = document.getElementById('c2_pt_fonte').value;
  await api.post(`/api/camaras-completo/${t2_editandoId}/portas`, {
    quantidade: parseInt(document.getElementById('c2_pt_qtd').value, 10) || 1,
    largura: larg, altura: alt,
    freq_abertura_min_h: parseNumBR(document.getElementById('c2_pt_freq').value),
    protecao: document.getElementById('c2_pt_protecao').value,
    fonte_ar: fonte,
    temp_adjacente: fonte === 'Adjacente' ? parseNumBR(document.getElementById('c2_pt_temp').value) : null,
    umidade_adjacente: fonte === 'Adjacente' ? parseNumBR(document.getElementById('c2_pt_ur').value) : null,
  });
  document.getElementById('c2_pt_qtd').value = '1';
  document.getElementById('c2_pt_larg').value = '';
  document.getElementById('c2_pt_alt').value = '';
  document.getElementById('c2_pt_freq').value = '';
  document.getElementById('c2_pt_protecao').value = 'Nenhuma';
  document.getElementById('c2_pt_fonte').value = 'Externo';
  t2_togglePortaAdj();
  await t2_atualizarPainelPortas();
}

async function t2_atualizarPainelPortas() {
  const c = await api.get(`/api/camaras-completo/${t2_editandoId}`);
  t2_renderPortas(c.portas);
  t2_renderCalculo(c.calculo);
  t2_carregarLista();
}

function t2_renderPortas(portas) {
  const el = document.getElementById('c2_portasList');
  if (!portas || portas.length === 0) { el.innerHTML = '<div style="padding:8px;text-align:center;color:#9ca3af;font-size:12px;">Nenhuma porta adicionada.</div>'; return; }
  const opcoesProtecao = ['Nenhuma', 'Cortina de tiras', 'Cortina de ar', 'Antecâmara'];
  el.innerHTML = '<table class="list"><thead><tr><th>Qtd</th><th>Largura (m)</th><th>Altura (m)</th><th>Abertura (min/h)</th><th>Proteção</th><th>Fonte do ar</th><th>Temp./UR Adjacente</th><th></th></tr></thead><tbody>' +
    portas.map(p => `<tr>
      <td><input type="text" value="${p.quantidade}" data-porta-campo="quantidade" data-porta-id="${p.id}" data-id-campo="T244" style="width:44px;"></td>
      <td><input type="text" value="${p.largura ?? ''}" data-porta-campo="largura" data-porta-id="${p.id}" data-id-campo="T245" style="width:56px;"></td>
      <td><input type="text" value="${p.altura ?? ''}" data-porta-campo="altura" data-porta-id="${p.id}" data-id-campo="T246" style="width:56px;"></td>
      <td><input type="text" value="${p.freq_abertura_min_h ?? ''}" data-porta-campo="freq_abertura_min_h" data-porta-id="${p.id}" data-id-campo="T247" style="width:56px;"></td>
      <td><select data-porta-campo="protecao" data-porta-id="${p.id}" data-id-campo="T248">${opcoesProtecao.map(o => `<option ${o === p.protecao ? 'selected' : ''}>${o}</option>`).join('')}</select></td>
      <td><select data-porta-campo="fonte_ar" data-porta-id="${p.id}" data-id-campo="T249"><option value="Externo" ${p.fonte_ar !== 'Adjacente' ? 'selected' : ''}>Externo</option><option value="Adjacente" ${p.fonte_ar === 'Adjacente' ? 'selected' : ''}>Adjacente</option></select></td>
      <td>${p.fonte_ar === 'Adjacente'
        ? `<input type="text" value="${p.temp_adjacente ?? 25}" data-porta-campo="temp_adjacente" data-porta-id="${p.id}" data-id-campo="T250" style="width:44px;">°C / <input type="text" value="${p.umidade_adjacente ?? 60}" data-porta-campo="umidade_adjacente" data-porta-id="${p.id}" data-id-campo="T251" style="width:44px;">%`
        : '<span style="color:#9ca3af;">—</span>'}</td>
      <td style="text-align:right;"><span class="btn-text danger" data-del-porta="${p.id}">Excluir</span></td>
    </tr>`).join('') + '</tbody></table>';
  el.querySelectorAll('[data-porta-campo]').forEach(campo => campo.addEventListener('change', async () => {
    const id = campo.dataset.portaId;
    const nomeCampo = campo.dataset.portaCampo;
    let valor = campo.value;
    if (['quantidade'].includes(nomeCampo)) valor = parseInt(valor, 10) || 1;
    else if (['largura', 'altura', 'freq_abertura_min_h', 'temp_adjacente', 'umidade_adjacente'].includes(nomeCampo)) valor = parseNumBR(valor);
    await api.put(`/api/camaras-completo/portas/${id}`, { [nomeCampo]: valor });
    await t2_atualizarPainelPortas();
  }));
  el.querySelectorAll('[data-del-porta]').forEach(b => b.addEventListener('click', () => t2_delPorta(Number(b.dataset.delPorta))));
}

async function t2_delPorta(id) {
  await api.del(`/api/camaras-completo/portas/${id}`);
  await t2_atualizarPainelPortas();
}

async function t2_addForcador() {
  if (!t2_editandoId) { alert('Salve a câmara primeiro.'); return; }
  const fabricante_id = document.getElementById('c2_evFab').value, linha_id = document.getElementById('c2_evLinha').value;
  if (!fabricante_id || !linha_id) return;
  await api.post(`/api/camaras-completo/${t2_editandoId}/forcadores`, { fabricante_id: Number(fabricante_id), linha_id: Number(linha_id), folga_desejada: 10 });
  document.getElementById('c2_evFab').value = '';
  document.getElementById('c2_evLinha').innerHTML = '';
  await t2_atualizarPainel(t2_editandoId);
  t2_carregarLista();
}
async function t2_upd_forcador(id, payload) {
  await api.put(`/api/camaras-completo/${t2_editandoId}/forcadores/${id}`, payload);
  await t2_atualizarPainel(t2_editandoId);
  t2_carregarLista();
}
async function t2_del_forcador(id) {
  if (!confirm('Excluir esta linha de forçador?')) return;
  await api.del(`/api/camaras-completo/${t2_editandoId}/forcadores/${id}`);
  await t2_atualizarPainel(t2_editandoId);
  t2_carregarLista();
}

// Campos da válvula (Modelo/Carga%/Conexões) não entram em nenhum cálculo — só grava, sem
// recarregar a câmara (recarregar destruía e recriava os <input>, quebrando o Tab no meio da digitação).
async function t2_upd_valvula(id, payload) {
  await api.put(`/api/camaras-completo/valvulas/${id}`, payload);
  if (t2_editandoId) await t2_atualizarPainel(t2_editandoId);  // Abert. Válv. recalculada no backend
}

async function t2_carregarLista() {
  const el = document.getElementById('c2_lista');
  if (!state.projetoId) { el.innerHTML = ''; return; }
  const todas = await api.get(`/api/camaras-completo?projeto_id=${state.projetoId}`);
  if (todas.length === 0) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma câmara cadastrada ainda.</div>'; return; }
  el.innerHTML = todas.map(c => {
    const badge = c.fechada
      ? (c.calculo_desatualizado
        ? '<span class="badge-fechada desatualizada">desatualizado</span>'
        : '<span class="badge-fechada ok">fechada</span>')
      : '';
    return `<div class="lista-card" data-camara="${c.id}">
      <div class="nome">${c.codigo} — ${c.nome}${badge}</div>
      <div class="meta">Carga: ${fmtKcal(c.calculo.capacidade_requerida)} · ${c.largura}x${c.comprimento}x${c.pedireito}m${_resumoForcadorCamara(c.calculo)}</div>
    </div>`;
  }).join('');
  el.querySelectorAll('[data-camara]').forEach(card => card.addEventListener('click', () => t2_abrirCamara(Number(card.dataset.camara))));
}

// ---- Importação de Válvulas de Expansão (Excel) — cobre Câmara Completo e Simples do projeto ----

let t2_previewValvulasItens = null;

async function t2_previewValvulas() {
  const input = document.getElementById('vi_arquivo');
  const file = input.files[0];
  if (!file) return;
  if (!state.projetoId) { alert('Selecione um projeto primeiro.'); return; }
  const resultado = await api.upload(`/api/valvulas-import/preview?projeto_id=${state.projetoId}`, file);
  input.value = '';
  if (resultado.erro) { alert(resultado.erro); return; }
  t2_previewValvulasItens = resultado.itens;
  t2_renderPreviewValvulas();
  document.getElementById('vi_previewWrap').style.display = 'block';
}

function t2_renderPreviewValvulas() {
  const el = document.getElementById('vi_preview');
  el.innerHTML = '<table class="list"><tbody>' +
    '<tr><th>Identificador</th><th>Câmara / Forçador</th><th>Fabricante</th><th>Tipo</th><th>Modelo</th><th>Capacidade (kcal/h)</th><th>Orifício</th><th>Carga %</th><th>Ø Entrada</th><th>Ø Saída</th><th>Já preenchida?</th></tr>' +
    t2_previewValvulasItens.map((it, i) => `<tr style="${it.encontrado ? '' : 'background:#fef2f2;'}">
      <td style="font-weight:bold;">${it.identificador || '—'}</td>
      <td>${it.encontrado ? `${it.camara_nome} — ${it.forcador_fabricante}/${it.forcador_linha}` : '<span style="color:#b91c1c;">⚠ não encontrado neste projeto</span>'}</td>
      <td><input type="text" value="${it.fabricante ?? ''}" data-vi-campo="fabricante" data-vi-i="${i}" style="width:80px;"></td>
      <td><input type="text" value="${it.tipo_expansao ?? ''}" data-vi-campo="tipo_expansao" data-vi-i="${i}" style="width:80px;"></td>
      <td><input type="text" value="${it.modelo_selecao ?? ''}" data-vi-campo="modelo_selecao" data-vi-i="${i}" style="width:90px;">${it.modelo_nao_cadastrado ? '<div style="color:#b45309;font-size:10px;max-width:140px;">⚠ Válvula não cadastrada no sistema. Inserir valores manuais ou selecionar outro modelo.</div>' : ''}</td>
      <td><input type="text" value="${it.capacidade_unit_kcal_h ?? ''}" data-vi-campo="capacidade_unit_kcal_h" data-vi-i="${i}" style="width:80px;"></td>
      <td><input type="text" value="${it.orificio ?? ''}" data-vi-campo="orificio" data-vi-i="${i}" style="width:55px;"></td>
      <td><input type="text" value="${it.carga_abertura_pct ?? ''}" data-vi-campo="carga_abertura_pct" data-vi-i="${i}" style="width:55px;"></td>
      <td><input type="text" value="${it.conexao_entrada ?? ''}" data-vi-campo="conexao_entrada" data-vi-i="${i}" style="width:55px;"></td>
      <td><input type="text" value="${it.conexao_saida ?? ''}" data-vi-campo="conexao_saida" data-vi-i="${i}" style="width:55px;"></td>
      <td style="text-align:center;">${it.ja_preenchida ? '<span style="color:#b45309;font-weight:bold;">⚠ Sim</span>' : '—'}</td>
    </tr>`).join('') + '</tbody></table>';
  el.querySelectorAll('[data-vi-campo]').forEach(inp => inp.addEventListener('change', () => {
    t2_previewValvulasItens[Number(inp.dataset.viI)][inp.dataset.viCampo] = inp.value;
  }));
}

function t2_cancelarPreviewValvulas() {
  t2_previewValvulasItens = null;
  document.getElementById('vi_previewWrap').style.display = 'none';
}

async function t2_confirmarImportacaoValvulas() {
  // Reimportação: se alguma válvula do projeto já tem seleção gravada, pergunta ao usuário se
  // quer sobrepor — OK sobrepõe com os dados da planilha; Cancelar mantém as existentes e
  // importa só as vazias.
  const jaPreenchidas = (t2_previewValvulasItens || []).filter(it => it.encontrado && it.ja_preenchida).length;
  let sobrepor = true;
  if (jaPreenchidas > 0) {
    sobrepor = confirm(`${jaPreenchidas} válvula(s) deste projeto JÁ possuem seleção gravada.\n\n`
      + `OK = SOBREPOR os dados existentes com os da planilha.\n`
      + `Cancelar = MANTER os existentes e importar apenas as válvulas ainda vazias.`);
  }
  const resultado = await api.post('/api/valvulas-import/confirmar', { itens: t2_previewValvulasItens, sobrepor });
  alert(`Importação concluída: ${resultado.criadas} criada(s), ${resultado.atualizadas} atualizada(s)`
    + (resultado.mantidas ? `, ${resultado.mantidas} mantida(s) (já preenchidas — sem sobrepor)` : '')
    + (resultado.ignoradas ? `, ${resultado.ignoradas} ignorada(s) (identificador não encontrado no projeto)` : '') + '.');
  t2_cancelarPreviewValvulas();
  if (t2_editandoId) t2_abrirCamara(t2_editandoId);
}

window.initTela2 = initTela2;
window.telaShowHandlers[2] = async () => {
  if (!state.projetoId) return;
  await carregarSistemasDoProjeto();
  popularSelectsSistema([document.getElementById('c2_sistema_id')]);
  t2_carregarLista();
};
document.addEventListener('DOMContentLoaded', initTela2);
