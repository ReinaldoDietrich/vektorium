// Tela 6 — Rack Paralelo (Informações Rack + Lista de Materiais Rack).

const T11_CAMPOS_TEXTO = ['linha_compressor', 'fabricante_compressor'];
const T11_CAMPOS_NUM = ['quantidade_compressores', 'folga_tecnica_pct', 'quantidade_paralelo'];
// Modelo Compressor/COP/Capacidade unitária/Carga Total Fornecida/Calor Rejeitado/Potência Total/
// Corrente Nominal/Vazão Mássica/Corrente Máxima/Carga de Óleo/Conexão Descarga/Conexão Sucção/
// Tanque de Líquido/Carga de Gás Estimada saíram desses arrays: TUDO no painel "Resumo do Rack" é
// exibição automática (ver t11_renderResumoCampos), nunca campo de texto. Carga de Gás Estimada é
// calculada (soma dos forçadores do sistema + tanque, ou x1,5 sem tanque — ver
// _carga_gas_estimada_sistema, rack_paralelo.py); os demais ficam em branco sem fonte de dado.
// HP Total foi removido do resumo (aprovado 2026-08-11, sem fonte de dado confiável).

let t11_rackAtual = null;
let t11_racks = [];              // todos os racks (opções) do sistema atual
let t11_rackEditandoId = null;   // rack atualmente aberto no formulário
let t11_fechada = false;

function initTela11() {
  document.getElementById('t11_sistema_id').addEventListener('change', t11_trocarSistema);
  document.getElementById('t11_btnSalvar').addEventListener('click', t11_salvar);
  document.getElementById('t11_quantidade_compressores').addEventListener('change', t11_atualizarImediato);
  document.getElementById('t11_folga_tecnica_pct').addEventListener('change', t11_atualizarImediato);
  document.getElementById('t11_quantidade_paralelo').addEventListener('change', t11_atualizarImediato);
  document.getElementById('t11_filtro_motor_compressor').addEventListener('change', t11_atualizarImediato);
  document.getElementById('t11_ri_arquivo').addEventListener('change', t11_previewImportacao);
  document.getElementById('t11_ri_btnCancelar').addEventListener('click', t11_cancelarPreviewImportacao);
  document.getElementById('t11_ri_btnConfirmar').addEventListener('click', t11_confirmarImportacao);
  document.getElementById('t11_cond_fabricante').addEventListener('change', async () => { t11_cond_repopularLinhas(); await t11_salvarCondensador(); });
  document.getElementById('t11_cond_linha').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_fpi').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_polos').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_folga').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_qtdCondensadores').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_protecaoAletas').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_notas').addEventListener('change', t11_salvarCondensador);
  document.getElementById('t11_cond_btnAdd').addEventListener('click', t11_addOpcaoCondensador);
  document.getElementById('t11_btnAddRack').addEventListener('click', t11_addRack);
  document.getElementById('t11_btnEditar').addEventListener('click', t11_editarEntidade);
  document.addEventListener('projeto-changed', t11_onProjetoChanged);
}

// Quantidade de Compressores e Folga Técnica recalculam a Seleção de Compressores inteira (número
// de posições, capacidade mínima por posição, modelo automático) — salva e atualiza na hora, sem
// esperar o botão "Salvar Informações Rack" (mesmo padrão já usado no % Sistema do master).
async function t11_atualizarImediato() {
  if (!t11_rackAtual) return;
  if (t11_fechada) return;
  const filtroMotor = document.getElementById('t11_filtro_motor_compressor').value;
  const payload = {
    quantidade_compressores: parseNumBR(document.getElementById('t11_quantidade_compressores').value),
    folga_tecnica_pct: parseNumBR(document.getElementById('t11_folga_tecnica_pct').value),
    quantidade_paralelo: Math.max(parseInt(document.getElementById('t11_quantidade_paralelo').value, 10) || 1, 1),
    filtro_motor_compressor: filtroMotor ? Number(filtroMotor) : null,
  };
  t11_rackAtual = await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, payload);
  document.getElementById('t11_cargaRequerida').value = fmtNum(t11_rackAtual.carga_sistema_total_kcal_h ?? t11_rackAtual.carga_requerida_kcal_h);
  document.getElementById('t11_modelo_comercial').value = t11_rackAtual.modelo_comercial ?? '—';
  await t11_carregarCompressores();
}

function t11_onProjetoChanged() {
  const semProjeto = document.getElementById('t11_semProjeto');
  const importacao = document.getElementById('t11_importacao');
  const semSistema = document.getElementById('t11_semSistema');
  const conteudo = document.getElementById('t11_conteudo');
  if (!state.projetoId) {
    semProjeto.style.display = 'block'; importacao.style.display = 'none';
    semSistema.style.display = 'none'; conteudo.style.display = 'none';
    return;
  }
  semProjeto.style.display = 'none'; importacao.style.display = 'block';
  const racks = state.sistemas;  // seleção de Rack liberada para TODOS os sistemas (aprovado 2026-08-13) — o tipo_compressao do sistema é quem decide o que entra no cálculo (Tela 5/8/9/10), não esta tela
  if (racks.length === 0) {
    semSistema.style.display = 'block'; conteudo.style.display = 'none';
    return;
  }
  semSistema.style.display = 'none'; conteudo.style.display = 'block';
  populateSelect(document.getElementById('t11_sistema_id'), racks, 'id', 'nome', null);
  t11_trocarSistema();
}

async function t11_trocarSistema() {
  const sistemaId = document.getElementById('t11_sistema_id').value;
  if (!sistemaId) return;
  const sistema = state.sistemas.find(s => String(s.id) === String(sistemaId));
  document.getElementById('t11_tipoEquipamento').value = t1_nomePorCodigo(sistema.tipo_compressao) || '—';
  document.getElementById('t11_estrutura').value = t1_nomePorCodigo(sistema.estrutura_compressao) || '—';
  document.getElementById('t11_gasRefrigerante').value = sistema.gas_refrigerante || '—';
  document.getElementById('t11_tempLinhaLiquido').value = sistema.temp_apos_subresfriamento ?? sistema.temp_apos_condensador ?? '—';
  document.getElementById('t11_tipoPartida').value = t1_nomePorCodigo(sistema.partida) || '—';
  document.getElementById('t11_tipoOperacao').value = t1_nomePorCodigo(sistema.modo_operacao) || '—';

  t11_rackEditandoId = null;              // troca de sistema → volta pro rack considerado
  await t11_recarregarRacks(false);
}

// Recarrega a lista de racks do sistema e abre um deles no formulário. manterEdicao=true mantém o
// rack que já estava aberto (se ainda existir); senão abre o considerado (ou o 1º).
async function t11_recarregarRacks(manterEdicao = false) {
  const sistemaId = document.getElementById('t11_sistema_id').value;
  if (!sistemaId) return;
  const resp = await api.get(`/api/rack-paralelo?sistema_id=${sistemaId}`);
  t11_racks = resp.racks || [];
  let alvo = null;
  if (manterEdicao && t11_rackEditandoId) alvo = t11_racks.find(x => x.id === t11_rackEditandoId);
  if (!alvo) alvo = t11_racks.find(x => x.considerado) || t11_racks[0] || null;
  t11_rackEditandoId = alvo ? alvo.id : null;
  t11_renderRacks();
  if (alvo) await t11_carregarRackNoForm(alvo);
}

async function t11_carregarRackNoForm(r) {
  t11_rackAtual = r;
  t11_fechada = !!r.fechada;
  await t11_popularFabricantesLinhas(r.fabricante_compressor, r.linha_compressor);
  T11_CAMPOS_TEXTO.forEach(c => { document.getElementById('t11_' + c).value = r[c] ?? ''; });
  T11_CAMPOS_NUM.forEach(c => { document.getElementById('t11_' + c).value = r[c] ?? ''; });
  document.getElementById('t11_filtro_motor_compressor').value = r.filtro_motor_compressor ?? '';
  document.getElementById('t11_tensao').value = r.tensao ?? '—';
  document.getElementById('t11_modelo_comercial').value = r.modelo_comercial ?? '—';
  document.getElementById('t11_cargaRequerida').value = fmtNum(r.carga_sistema_total_kcal_h ?? r.carga_requerida_kcal_h);
  t11_renderMateriais(r.materiais);
  await t11_carregarOpcoesCondensador();
  await t11_carregarCompressores();
  t11_aplicarEstadoFechada(r);
}

// Lista de racks (opções), padrão simples do forçador: rádio = considerado (entra no cálculo);
// clicar no nome abre a opção no formulário abaixo. "+ Adicionar rack" cria e já abre o novo.
function t11_renderRacks() {
  const el = document.getElementById('t11_racksLista');
  if (!el) return;
  el.innerHTML = t11_racks.map((r, i) => {
    const resumo = (r.modelo_comercial && r.modelo_comercial !== '—') ? r.modelo_comercial
      : ([r.fabricante_compressor, r.linha_compressor].filter(Boolean).join(' / ') || `Rack ${i + 1}`);
    const editando = r.id === t11_rackEditandoId;   // barra azul à esquerda = rack aberto no formulário
    let badge = '';
    if (r.fechada) {
      badge = r.calculo_desatualizado
        ? '<span class="badge-fechada desatualizada">desatualizado</span>'
        : '<span class="badge-fechada ok">fechada</span>';
    }
    return `<div style="display:flex;align-items:center;gap:10px;padding:5px 10px;border:1px solid var(--line);border-radius:6px;margin-bottom:4px;${r.considerado ? 'background:#eff6ff;' : ''}${editando ? 'box-shadow:inset 3px 0 0 0 #2563eb;' : ''}">
      <input type="radio" name="t11_rack_considerado" ${r.considerado ? 'checked' : ''} data-considerar-rack="${r.id}" style="cursor:pointer;">
      <span data-editar-rack="${r.id}" style="cursor:pointer;white-space:nowrap;font-weight:${r.considerado ? 'bold' : 'normal'};">${resumo}${badge}</span>
      ${t11_racks.length > 1 ? `<span class="btn-text danger" data-excluir-rack="${r.id}" style="margin-left:auto;">Excluir</span>` : ''}
    </div>`;
  }).join('');
  el.querySelectorAll('[data-considerar-rack]').forEach(rd => rd.addEventListener('change', async () => {
    await api.put(`/api/rack-paralelo/${rd.dataset.considerarRack}/considerar`, {});
    await t11_recarregarRacks(true);
  }));
  el.querySelectorAll('[data-editar-rack]').forEach(b => b.addEventListener('click', async () => {
    t11_rackEditandoId = Number(b.dataset.editarRack);
    await t11_recarregarRacks(true);
  }));
  el.querySelectorAll('[data-excluir-rack]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir este rack?')) return;
    await api.del(`/api/rack-paralelo/${b.dataset.excluirRack}`);
    t11_rackEditandoId = null;
    await t11_recarregarRacks(false);
  }));
}

async function t11_addRack() {
  const sistemaId = document.getElementById('t11_sistema_id').value;
  if (!sistemaId) return;
  const novo = await api.post(`/api/rack-paralelo?sistema_id=${sistemaId}`, {});
  t11_rackEditandoId = novo.id;           // abre o novo pra configurar (os outros ficam na lista)
  await t11_recarregarRacks(true);
}

let t11_fabricantesCache = null;

async function t11_popularFabricantesLinhas(fabricanteAtual, linhaAtual) {
  const fab = document.getElementById('t11_fabricante_compressor');
  const linha = document.getElementById('t11_linha_compressor');
  if (!t11_fabricantesCache) t11_fabricantesCache = await api.get('/api/polinomios/fabricantes');
  populateSelect(fab, t11_fabricantesCache.map(f => ({ v: f, l: f })), 'v', 'l', '—');
  fab.value = fabricanteAtual || '';
  fab.onchange = async () => { await t11_recarregarLinhasCabecalho(); await t11_salvarCabecalhoCompressor(); };
  linha.onchange = () => t11_salvarCabecalhoCompressor();
  await t11_recarregarLinhasCabecalho(linhaAtual);
}

async function t11_recarregarLinhasCabecalho(linhaAtual) {
  const fab = document.getElementById('t11_fabricante_compressor').value;
  const linha = document.getElementById('t11_linha_compressor');
  if (!fab) { linha.innerHTML = '<option value="">—</option>'; return; }
  const linhas = await api.get(`/api/polinomios/linhas?fabricante=${encodeURIComponent(fab)}`);
  linha.innerHTML = '<option value="">—</option>' + linhas.map(l => `<option ${l === linhaAtual ? 'selected' : ''}>${l}</option>`).join('');
}

// Fabricante/Linha Compressor recalculam a Seleção de Compressores inteira — salva e atualiza na
// hora, sem esperar "Salvar Informações Rack" (mesmo padrão de Quantidade/Folga, ver
// t11_atualizarImediato). Bug real corrigido 2026-07-18: trocar a Linha Compressor não fazia nada
// até o usuário clicar Salvar — parecia que o filtro de envelope não respeitava a troca.
async function t11_salvarCabecalhoCompressor() {
  if (!t11_rackAtual) return;
  if (t11_fechada) return;
  const payload = {
    fabricante_compressor: document.getElementById('t11_fabricante_compressor').value || null,
    linha_compressor: document.getElementById('t11_linha_compressor').value || null,
  };
  t11_rackAtual = await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, payload);
  document.getElementById('t11_modelo_comercial').value = t11_rackAtual.modelo_comercial ?? '—';
  await t11_carregarCompressores();
}

async function t11_salvar() {
  if (!t11_rackAtual) return;
  const payload = {};
  T11_CAMPOS_TEXTO.forEach(c => { payload[c] = document.getElementById('t11_' + c).value || null; });
  T11_CAMPOS_NUM.forEach(c => { payload[c] = parseNumBR(document.getElementById('t11_' + c).value); });
  const filtroMotorSalvar = document.getElementById('t11_filtro_motor_compressor').value;
  payload.filtro_motor_compressor = filtroMotorSalvar ? Number(filtroMotorSalvar) : null;
  await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, payload);
  await t11_recarregarRacks(true);
  alert('Informações do Rack salvas.');
}

function t11_renderMateriais(materiais) {
  const el = document.getElementById('t11_materiais');
  let html = '<table class="list"><thead><tr><th>Categoria</th><th>Descrição</th><th>Modelo</th><th style="width:100px;">Quantidade</th></tr></thead><tbody>';
  materiais.forEach(item => {
    html += `<tr>
      <td style="color:#6b7280;">${item.categoria || '—'}</td>
      <td>${item.descricao}</td>
      <td><input type="text" value="${item.modelo ?? ''}" data-mat-modelo="${item.id}" data-id-campo="T616" style="width:100%;"></td>
      <td><input type="text" value="${item.quantidade ?? 0}" data-mat-qtd="${item.id}" data-id-campo="T617" style="width:100%;"></td>
    </tr>`;
  });
  html += '</tbody></table>';
  el.innerHTML = html;
  el.querySelectorAll('[data-mat-modelo]').forEach(inp => inp.addEventListener('change', () =>
    api.put(`/api/rack-paralelo/materiais/${inp.dataset.matModelo}`, { modelo: inp.value || null })));
  el.querySelectorAll('[data-mat-qtd]').forEach(inp => inp.addEventListener('change', () =>
    api.put(`/api/rack-paralelo/materiais/${inp.dataset.matQtd}`, { quantidade: parseNumBR(inp.value) || 0 })));
}

// ---- Importação de Rack (Excel a partir do relatório do fabricante) ----

let t11_previewItens = null;

async function t11_previewImportacao() {
  const input = document.getElementById('t11_ri_arquivo');
  const file = input.files[0];
  if (!file) return;
  if (!state.projetoId) { alert('Selecione um projeto primeiro.'); return; }
  const resultado = await api.upload(`/api/rack-import/preview?projeto_id=${state.projetoId}`, file);
  input.value = '';
  if (resultado.erro) { alert(resultado.erro); return; }
  t11_previewItens = resultado.itens;
  t11_renderPreviewImportacao();
  document.getElementById('t11_ri_previewWrap').style.display = 'block';
}

function t11_renderPreviewImportacao() {
  const el = document.getElementById('t11_ri_preview');
  el.innerHTML = '<table class="list"><tbody>' +
    '<tr><th>Sistema</th><th>Fabricante</th><th>Modelo Compressor</th><th>Qtd. Compressores</th><th>Carga Total (kcal/h)</th></tr>' +
    t11_previewItens.map(it => `<tr style="${it.encontrado ? '' : 'background:#fef2f2;'}">
      <td style="font-weight:bold;">${it.sistema_nome || '—'}</td>
      <td>${it.encontrado ? (it.fabricante_compressor ?? '—') : '<span style="color:#b91c1c;">⚠ sistema não encontrado neste projeto</span>'}</td>
      <td>${it.modelo_compressor ?? '—'}</td>
      <td>${it.quantidade_compressores ?? '—'}</td>
      <td>${it.carga_total_fornecida_kcal_h ?? '—'}</td>
    </tr>`).join('') + '</tbody></table>';
}

function t11_cancelarPreviewImportacao() {
  t11_previewItens = null;
  document.getElementById('t11_ri_previewWrap').style.display = 'none';
}

async function t11_confirmarImportacao() {
  const resultado = await api.post('/api/rack-import/confirmar', { itens: t11_previewItens });
  alert(`Importação concluída: ${resultado.criadas} criada(s), ${resultado.atualizadas} atualizada(s)`
    + (resultado.ignoradas ? `, ${resultado.ignoradas} ignorada(s) (sistema não encontrado no projeto)` : '') + '.');
  t11_cancelarPreviewImportacao();
  const sistemaAtual = document.getElementById('t11_sistema_id').value;
  if (sistemaAtual) t11_trocarSistema();
}

// ---- Seleção de Compressores por polinômio (1 a 5 posições) ----

async function t11_carregarCompressores() {
  const semDados = document.getElementById('t11_comp_semDados');
  const conteudo = document.getElementById('t11_comp_conteudo');
  if (!t11_rackAtual || !t11_rackAtual.quantidade_compressores) {
    semDados.style.display = 'block';
    conteudo.style.display = 'none';
    return;
  }
  semDados.style.display = 'none';
  conteudo.style.display = 'block';

  const dados = await api.get(`/api/rack-paralelo/${t11_rackAtual.id}/resumo-compressores`);
  document.getElementById('t11_comp_cargaRequerida').textContent = fmtNum(dados.carga_requerida_kcal_h) + ' kcal/h';
  document.getElementById('t11_comp_demandaTotal').textContent = fmtNum(dados.demanda_total_kcal_h) + ' kcal/h';
  document.getElementById('t11_comp_te').textContent = dados.temp_evaporacao ?? '—';
  document.getElementById('t11_comp_tc').textContent = dados.temp_condensacao ?? '—';

  const el = document.getElementById('t11_comp_posicoes');
  el.innerHTML = dados.posicoes.map(p => t11_htmlPosicaoCompressor(p)).join('');

  const pctInput = document.getElementById('t11_comp_pct_1');
  if (pctInput) pctInput.addEventListener('change', () => t11_comp_salvarPercentual(parseNumBR(pctInput.value)));

  document.getElementById('t11_comp_nota').textContent = dados.nota;
  t11_renderResumoCampos(dados.resumo);
  // O condensador depende do calor rejeitado (que muda com os compressores) — recalcula junto.
  await t11_carregarCondensador();
}

function t11_renderResumoCampos(r) {
  const grupos = r.grupos_modelo || [];
  const linhasModelo = grupos.map((g, i) => [`Modelo ${i + 1}`, `${g.quantidade}x ${g.modelo}`]);
  const linhasCapacidade = grupos.map((g, i) => [`Capacidade Unit. — Modelo ${i + 1}`,
    g.capacidade_unitaria_kcal_h != null ? fmtNum(g.capacidade_unitaria_kcal_h) + ' kcal/h' : '—']);
  // Peso/Conexões/Carga de Óleo — só vêm preenchidos pra Bitzer (Tela 6 - Dados Físicos
  // Compressores Bitzer, Configurações); outros fabricantes ficam "—" (sem catálogo com esse dado).
  const linhasPeso = grupos.map((g, i) => [`Peso — Modelo ${i + 1} (kg)`, g.peso || '—']);
  const linhasConexaoSuccao = grupos.map((g, i) => [`Conexão Sucção — Modelo ${i + 1}`, g.conexao_succao || '—']);
  const linhasConexaoDescarga = grupos.map((g, i) => [`Conexão Descarga — Modelo ${i + 1}`, g.conexao_descarga || '—']);
  const linhasCargaOleo = grupos.map((g, i) => [`Carga de Óleo — Modelo ${i + 1}`, g.carga_oleo || '—']);
  const linhas = [
    ...linhasModelo,
    ...linhasCapacidade,
    ['COP Compressor', r.cop != null ? fmtNum(r.cop, 2) : '—'],
    ['Carga Total Fornecida (kcal/h)', fmtNum(r.capacidade_total_kcal_h)],
    ['Calor Total Rejeitado Rack (kcal/h)', r.calor_rejeitado_total_kcal_h != null ? fmtNum(r.calor_rejeitado_total_kcal_h) : '—'],
    ['Potência Total Rack (W)', fmtNum(r.potencia_total_w)],
    ['Corrente Nominal (A)', fmtNum(r.corrente_total_a, 2)],
    ['Corrente Máxima de Trabalho (A)', r.corrente_maxima_total_a != null ? fmtNum(r.corrente_maxima_total_a, 2) : '—'],
    ['Vazão Mássica (kg/h)', fmtNum(r.vazao_total_kg_h)],
    ...linhasPeso,
    ...linhasConexaoSuccao,
    ...linhasConexaoDescarga,
    ...linhasCargaOleo,
    ['Tanque de Líquido (L)', '—'],
    ['Carga de Gás Estimada Sistema (kg)', r.carga_gas_estimada_kg != null ? fmtNum(r.carga_gas_estimada_kg, 1) : '—'],
    ['Folga Real (%)', r.folga_real_pct != null ? fmtNum(r.folga_real_pct, 1) + '%' : '—'],
    ['Atende a demanda?', r.atende_demanda
      ? '<span style="color:#15803d;font-weight:bold;">Sim ✓</span>'
      : '<span style="color:#b91c1c;font-weight:bold;">Não — complete a seleção</span>'],
  ];
  document.getElementById('t11_resumoCampos').innerHTML = linhas.map(([label, valor]) =>
    `<tr><td style="color:#6b7280;">${label}</td><td style="text-align:right;">${valor}</td></tr>`).join('');
}

function t11_htmlPosicaoCompressor(p) {
  const badge = p.resultado
    ? `<span style="color:#15803d;">✓ ${p.modelo} — ${p.tensao} (${fmtNum(p.resultado.capacidade_kcal_h)} kcal/h${p.resultado.corrente_fonte === 'nominal' ? ' · corrente = valor nominal de placa' : ''})</span>`
    : p.nota
      ? `<span style="color:#b91c1c;">✗ ${p.nota}</span>`
      : '<span style="color:#b91c1c;">✗ nenhum modelo do catálogo (Fabricante/Linha do cabeçalho + Gás do sistema) atende essa capacidade mínima na condição Te/Tc do projeto</span>';
  return `<div style="border:1px solid var(--line);border-radius:6px;padding:10px;margin-bottom:8px;">
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
      <div style="min-width:70px;"><label class="lbl">Posição</label><input type="text" value="${p.posicao}${p.posicao === 1 ? ' (master)' : ''}" disabled style="width:100%;"></div>
      <div style="min-width:90px;"><label class="lbl">% Sistema</label>
        ${p.editavel_percentual
          ? `<input type="text" id="t11_comp_pct_${p.posicao}" value="${p.percentual_sistema}" style="width:100%;">`
          : `<input type="text" value="${p.percentual_sistema}" disabled style="width:100%;">`}
      </div>
      <div style="min-width:110px;"><label class="lbl">Mín. (kcal/h)</label><input type="text" value="${fmtNum(p.capacidade_minima_kcal_h)}" disabled style="width:100%;"></div>
      <div style="min-width:220px;flex:1;"><label class="lbl">Modelo <span class="readonly-tag">automático</span></label><input type="text" value="${p.modelo ? p.modelo + ' — ' + p.tensao : '—'}" disabled style="width:100%;"></div>
    </div>
    <p class="small" style="margin-top:6px;">${badge}${p.resultado ? ` · Potência: ${fmtNum(p.resultado.potencia_w)} W · Corrente: ${fmtNum(p.resultado.corrente_a, 2)} A · Vazão: ${fmtNum(p.resultado.vazao_kg_h)} kg/h` : ''}</p>
  </div>`;
}

async function t11_comp_salvarPercentual(pct) {
  await api.put(`/api/rack-paralelo/${t11_rackAtual.id}/compressores/1`, { percentual_sistema: pct });
  await t11_carregarCompressores();
}

// ---- Seleção de Condensador Remoto (catálogo da Tela C) ----

let t11_condOpcoes = null;

// Campos da "Seleção de Condensadores" que só fazem sentido quando o Tipo de Condensador (Tela 1)
// não é "-" nem "Plano Onboard" (Onboard não usa catálogo de condensador remoto) — aprovado 2026-08-08.
const T11_CAMPOS_CONDENSADOR_SELECAO = ['t11_cond_fabricante', 't11_cond_linha', 't11_cond_polos', 't11_cond_fpi',
  't11_cond_protecaoAletas', 't11_cond_folga', 't11_cond_qtdCondensadores', 't11_cond_notas'];

function t11_atualizarDisponibilidadeCondensador(tipoCondensador) {
  const habilitado = !!tipoCondensador && tipoCondensador !== 'Plano Onboard';
  T11_CAMPOS_CONDENSADOR_SELECAO.forEach(id => { const el = document.getElementById(id); if (el) el.disabled = !habilitado; });
  const btnAdd = document.getElementById('t11_cond_btnAdd');
  if (btnAdd) btnAdd.disabled = !habilitado;
}

// Tipo Condensador agora é editável aqui (master) — popula o select com opções da árvore 4.4.1,
// salva no sistema.selecao_condensador_ar e no rack.tipo_condensador.
async function t11_carregarOpcoesCondensador() {
  if (!t11_rackAtual) return;
  const sistemaId = document.getElementById('t11_sistema_id').value;
  const sistema = state.sistemas.find(s => String(s.id) === String(sistemaId));
  const tipoSel = document.getElementById('t11_cond_tipoCondensador');
  const isUC = sistema?.tipo_compressao === '4.1.1';
  if (isUC && !sistema.selecao_condensador_ar) {
    sistema.selecao_condensador_ar = '4.4.1.2';
    await api.put(`/api/sistemas/${sistemaId}`, { selecao_condensador_ar: '4.4.1.2' });
  }
  t1_popularSelectArvore('t11_cond_tipoCondensador', '4.4.1', sistema?.selecao_condensador_ar);
  const tipoCondensador = (sistema && t1_nomePorCodigo(sistema.selecao_condensador_ar)) || '';
  if ((t11_rackAtual.tipo_condensador || '') !== tipoCondensador) {
    t11_rackAtual = await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, { tipo_condensador: tipoCondensador || null });
  }
  const deltaEl = document.getElementById('t11_cond_deltaCondensacao');
  if (deltaEl) {
    deltaEl.value = sistema?.delta_condensacao ?? '';
    deltaEl.disabled = isUC;
    if (isUC && !sistema?.delta_condensacao) deltaEl.value = '10';
  }
  t11_atualizarDisponibilidadeCondensador(tipoCondensador);
  t11_condOpcoes = await api.get(`/api/rack-paralelo/${t11_rackAtual.id}/condensador-opcoes`);
  const fab = document.getElementById('t11_cond_fabricante');
  fab.innerHTML = '<option value="">—</option>' + t11_condOpcoes.fabricantes.map(f => `<option>${f}</option>`).join('');
  fab.value = t11_rackAtual.fabricante_condensador || '';
  t11_cond_repopularLinhas(t11_rackAtual.linha_condensador);
  document.getElementById('t11_cond_folga').value = t11_rackAtual.folga_condensador_pct ?? '';
  document.getElementById('t11_cond_qtdCondensadores').value = t11_rackAtual.quantidade_condensadores ?? 1;
  document.getElementById('t11_cond_protecaoAletas').value = t11_rackAtual.protecao_aletas_condensador ? 'true' : '';
  t11_renderOpcoesCondensador();
}

// Lista de opções de condensador do rack. A marcada (rádio) é a considerada — espelhada nas colunas
// do rack, é ela que o formulário abaixo e o resumo/compilação usam. "+ Adicionar" cria retraída.
function t11_renderOpcoesCondensador() {
  const el = document.getElementById('t11_cond_opcoesLista');
  if (!el || !t11_rackAtual) return;
  const ops = t11_rackAtual.condensadores || [];
  el.innerHTML = ops.map(o => {
    const resumo = [o.fabricante_condensador, o.linha_condensador].filter(Boolean).join(' / ') || '(sem seleção)';
    return `<div style="display:flex;align-items:center;gap:10px;padding:5px 10px;border:1px solid var(--line);border-radius:6px;margin-bottom:4px;${o.considerado ? 'background:#eff6ff;' : ''}">
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
        <input type="radio" name="t11_cond_considerado" ${o.considerado ? 'checked' : ''} data-considerar="${o.id}">
        <span style="font-weight:${o.considerado ? 'bold' : 'normal'};white-space:nowrap;">${resumo}</span>
      </label>
      ${ops.length > 1 ? `<span class="btn-text danger" data-excluir-cond="${o.id}" style="margin-left:auto;">Excluir</span>` : ''}
    </div>`;
  }).join('');
  el.querySelectorAll('[data-considerar]').forEach(r => r.addEventListener('change', async () => {
    await api.put(`/api/rack-paralelo/condensadores/${r.dataset.considerar}/considerar`, {});
    await t11_recarregarRacks(true);
  }));
  el.querySelectorAll('[data-excluir-cond]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir esta opção de condensador?')) return;
    await api.del(`/api/rack-paralelo/condensadores/${b.dataset.excluirCond}`);
    await t11_recarregarRacks(true);
  }));
}

async function t11_addOpcaoCondensador() {
  if (!t11_rackAtual) return;
  await api.post(`/api/rack-paralelo/${t11_rackAtual.id}/condensadores`, {});
  await t11_recarregarRacks(true);
}

function t11_cond_repopularLinhas(linhaAtual) {
  const fab = document.getElementById('t11_cond_fabricante').value;
  const linha = document.getElementById('t11_cond_linha');
  const opcoes = (t11_condOpcoes && t11_condOpcoes.linhas_por_fabricante[fab]) || [];
  linha.innerHTML = '<option value="">—</option>' + opcoes.map(l => `<option ${l === linhaAtual ? 'selected' : ''}>${l}</option>`).join('');
}

async function t11_salvarCondensador() {
  if (!t11_rackAtual) return;
  if (t11_fechada) return;
  // Salvar selecao_condensador_ar e delta_condensacao no SISTEMA (campo master agora é a Tela 6)
  const sistemaId = document.getElementById('t11_sistema_id').value;
  const selCond = document.getElementById('t11_cond_tipoCondensador').value || null;
  const deltaCond = parseNumBR(document.getElementById('t11_cond_deltaCondensacao').value);
  const tipoCondensadorNome = (selCond && t1_nomePorCodigo(selCond)) || '';
  await api.put(`/api/sistemas/${sistemaId}`, { selecao_condensador_ar: selCond, delta_condensacao: deltaCond });
  // Atualizar state local
  const sist = state.sistemas.find(s => String(s.id) === String(sistemaId));
  if (sist) { sist.selecao_condensador_ar = selCond; sist.delta_condensacao = deltaCond; }
  t11_rackAtual = await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, {
    tipo_condensador: tipoCondensadorNome || null,
    fabricante_condensador: document.getElementById('t11_cond_fabricante').value || null,
    linha_condensador: document.getElementById('t11_cond_linha').value || null,
    filtro_fpi_condensador: document.getElementById('t11_cond_fpi').value ? Number(document.getElementById('t11_cond_fpi').value) : null,
    filtro_polos_rpm_condensador: document.getElementById('t11_cond_polos').value || null,
    folga_condensador_pct: parseNumBR(document.getElementById('t11_cond_folga').value),
    quantidade_condensadores: parseNumBR(document.getElementById('t11_cond_qtdCondensadores').value) || 1,
    protecao_aletas_condensador: document.getElementById('t11_cond_protecaoAletas').value === 'true',
    notas_condensador: document.getElementById('t11_cond_notas').value || null,
  });
  await t11_carregarCondensador();
}

async function t11_carregarCondensador() {
  if (!t11_rackAtual) return;
  const d = await api.get(`/api/rack-paralelo/${t11_rackAtual.id}/condensador`);
  document.getElementById('t11_cond_tempAposCondensador').value = d.temp_apos_condensador != null ? fmtNum(d.temp_apos_condensador, 1) : '—';
  document.getElementById('t11_cond_tempCondensacao').value = d.temp_condensacao != null ? fmtNum(d.temp_condensacao, 1) : '—';
  document.getElementById('t11_cond_notas').value = d.notas_condensador || '';
  // repopula filtros FPI / Polos-RPM preservando a seleção salva
  const fpiSel = document.getElementById('t11_cond_fpi');
  fpiSel.innerHTML = '<option value="">Qualquer</option>' + d.filtros_disponiveis.fpis.map(v =>
    `<option ${String(v) === String(d.filtro_fpi_condensador) ? 'selected' : ''}>${v}</option>`).join('');
  const polSel = document.getElementById('t11_cond_polos');
  const rotuloPolosOpcao = { AC: 'Qualquer AC', EC: 'EC' };
  polSel.innerHTML = '<option value="">Qualquer</option>' + d.filtros_disponiveis.polos_rpm.map(v =>
    `<option value="${v}" ${v === d.filtro_polos_rpm_condensador ? 'selected' : ''}>${rotuloPolosOpcao[v] || v}</option>`).join('');

  const el = document.getElementById('t11_cond_resultado');
  const nomencEl = document.getElementById('t11_cond_nomenclatura');
  if (d.aviso) { el.innerHTML = `<p class="small" style="color:#6b7280;">${d.aviso}</p>`; nomencEl.querySelector('[data-nomenc-cond-wrap]').innerHTML = ''; return; }
  const sel = d.selecao;
  const calor = d.calor_rejeitado_kcal_h;
  const ctx = d.contexto;
  // Delta de condensação é razão (projeto / DT de Catálogo), igual ao ΔT do forçador — não é fator de tabela.
  const razao = (ctx.delta_condensacao != null && d.dt_catalogo_c)
    ? ` (×${fmtNum(ctx.delta_condensacao / d.dt_catalogo_c, 3)})` : '';
  const linhaCtx = `Calor rejeitado do rack: <strong>${calor != null ? fmtNum(calor) + ' kcal/h' : '—'}</strong>`
    + ` · Demanda (c/ folga): <strong>${sel && sel.demanda_kcal_h != null ? fmtNum(sel.demanda_kcal_h) + ' kcal/h' : '—'}</strong>`
    + `<br><span class="small" style="color:#6b7280;">ΔCond projeto ${ctx.delta_condensacao ?? '—'} / catálogo ${d.dt_catalogo_c ?? '—'}${razao}`
    + ` · Fatores: Gás ${ctx.gas ?? '—'} · Aleta ${ctx.aleta} · Altitude ${ctx.altitude ?? '—'}m · Temp. Ar ${ctx.temp_entrada_ar ?? '—'}°C</span>`;
  if (!calor) {
    el.innerHTML = `<p class="small">${linhaCtx}</p><p class="small" style="color:#b45309;">Complete a Seleção de Compressores para calcular o calor rejeitado.</p>`;
    nomencEl.querySelector('[data-nomenc-cond-wrap]').innerHTML = '';
    return;
  }
  let corpo;
  if (!sel || !sel.escolhido) {
    corpo = '<p class="small" style="color:#b91c1c;">Nenhum modelo do catálogo atende — confira Fabricante/Linha, filtros e os fatores de correção da Tela C.</p>';
    nomencEl.querySelector('[data-nomenc-cond-wrap]').innerHTML = '';
  } else {
    const e = sel.escolhido;
    const faltantes = sel.fatores_faltantes.length
      ? `<p class="small" style="color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:6px;">Fatores não cadastrados na Tela C (usados como 1,0): ${sel.fatores_faltantes.join(', ')}</p>` : '';
    const badge = sel.atende
      ? '<span style="color:#15803d;font-weight:bold;">Atende ✓</span>'
      : '<span style="color:#b91c1c;font-weight:bold;">Nenhum atende — mostrando o maior</span>';
    const rotuloPolos = (e.tipo_motor || '').toUpperCase().startsWith('EC') ? 'Rotação (RPM)' : 'Nº de Polos';
    // mesmo padrão de "Informações Condensadores" do memorial (PDF) e mesmo layout de tabela do Resumo do Rack
    const qtdCond = sel.quantidade_condensadores || 1;
    const linhas = [
      ['Tipo de Equipamento', 'Condensador Remoto'],
      ['Modelo Condensador', `<strong>${qtdCond}x ${e.codigo_comercial || e.modelo}</strong>`],
      ['Fabricante / Linha', `${t11_rackAtual.fabricante_condensador || '—'} / ${t11_rackAtual.linha_condensador || '—'}`],
      ['Temperatura Ambiente (°C)', ctx.temp_entrada_ar != null ? fmtNum(ctx.temp_entrada_ar, 1) : '—'],
      ['ΔT Condensação', ctx.delta_condensacao != null ? fmtNum(ctx.delta_condensacao, 1) : '—'],
      ['Temperatura de Condensação (°C)', d.temp_condensacao != null ? fmtNum(d.temp_condensacao, 1) : '—'],
      ['Aletas por Polegada (FPI)', e.fpi ?? '—'],
      [rotuloPolos, e.polos_ou_rpm ?? '—'],
      ['Ventiladores', (e.qtd_ventiladores && e.diametro_ventilador_mm) ? `${e.qtd_ventiladores}x Ø${e.diametro_ventilador_mm}mm` : '—'],
      ['Tensão', d.tensao_equipamentos || '—'],
      ['Corrente Nominal Ventiladores (A)', e.corrente_ventiladores_a != null ? fmtNum(e.corrente_ventiladores_a, 2) : '—'],
      ['Capacidade de Catálogo (kcal/h)', fmtNum(e.capacidade_catalogo_kcal_h)],
      ['Capacidade Unit. — corrigida (kcal/h)', fmtNum(e.capacidade_corrigida_kcal_h)],
      ['Capacidade Total Fornecida (kcal/h)', `<strong>${fmtNum(e.capacidade_corrigida_total_kcal_h ?? e.capacidade_corrigida_kcal_h)}</strong>`],
      ['Folga Técnica (%)', sel.folga_real_pct != null ? fmtNum(sel.folga_real_pct, 1) + '%' : '—'],
      ['Resultado', badge],
    ];
    corpo = `<table class="list"><tbody>${linhas.map(([label, valor]) =>
      `<tr><td style="color:#6b7280;">${label}</td><td style="text-align:right;">${valor}</td></tr>`).join('')}</tbody></table>${faltantes}`;
  }
  el.innerHTML = `<p class="small">${linhaCtx}</p>${corpo}`;
  await _carregarPainelNomenclaturaCondensador(nomencEl, d, t11_salvarNomenclaturaCondensador);
}

async function t11_salvarNomenclaturaCondensador(valores) {
  await api.put(`/api/rack-paralelo/${t11_rackAtual.id}`, { nomenclatura_condensador_selecionada: valores });
  await t11_carregarCondensador();
}

function t11_aplicarEstadoFechada(r) {
  const conteudo = document.getElementById('t11_conteudo');
  const btnSalvar = document.getElementById('t11_btnSalvar');
  const btnEditar = document.getElementById('t11_btnEditar');
  const barraFechada = document.getElementById('t11_barraFechada');
  const barraDesatualizada = document.getElementById('t11_barraDesatualizada');
  if (t11_fechada) {
    conteudo.classList.add('entidade-fechada');
    btnSalvar.style.display = 'none';
    btnEditar.style.display = 'inline-block';
    barraFechada.style.display = 'flex';
    barraDesatualizada.style.display = r && r.calculo_desatualizado ? 'flex' : 'none';
  } else {
    conteudo.classList.remove('entidade-fechada');
    btnSalvar.style.display = '';
    btnEditar.style.display = 'none';
    barraFechada.style.display = 'none';
    barraDesatualizada.style.display = 'none';
  }
}

async function t11_editarEntidade() {
  if (!t11_rackEditandoId) return;
  await api.post(`/api/rack-paralelo/${t11_rackEditandoId}/editar`, {});
  t11_fechada = false;
  t11_aplicarEstadoFechada(null);
  await t11_recarregarRacks(true);
}

window.initTela11 = initTela11;
window.telaShowHandlers[11] = async () => {
  if (!state.projetoId) return;
  await carregarSistemasDoProjeto();
  t11_onProjetoChanged();
};
document.addEventListener('DOMContentLoaded', initTela11);
