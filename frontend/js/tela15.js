// Tela C — Catálogo de Condensadores Remotos a Ar. Espelho da Tela A (tela6.js), adaptado ao
// modelo achatado do condensador (tabela de modelos plana, sem matriz por temperatura) e aos 5
// tipos de fator de correção.
async function c15_carregarSubtreeIdPai() {
  const sel = document.getElementById('c15_idPai');
  sel.innerHTML = '<option value="">(automático)</option>';
  try {
    const nos = await api.get('/api/catalogos/ids-comerciais/subtree?raiz=4.4.1');
    for (const n of nos) {
      const indent = '  '.repeat(n.codigo.split('.').length - 3);
      sel.innerHTML += `<option value="${n.codigo}">${indent}${n.codigo} — ${n.nome}</option>`;
    }
  } catch (e) { /* mantém só a opção automático */ }
}

let c15_linhaAtualId = null;
let c15_previewLinhas = null;
let c15_previewNomeArquivo = null;

// Colunas da tabela de modelos (n:true = numérico, parseNumBR ao salvar).
const C15_MODELO_COLS = [
  { k: 'modelo', l: 'Modelo', w: 110 },
  { k: 'fpi', l: 'FPI', w: 50, n: true }, { k: 'qtd_ventiladores', l: 'Qtd Vent', w: 60, n: true },
  { k: 'diametro_ventilador_mm', l: 'Diâm. Vent. (mm)', w: 80, n: true },
  { k: 'vazao_ar_m3h', l: 'Vazão Ar (m³/h)', w: 90, n: true }, { k: 'polos_ou_rpm', l: 'Polos/RPM', w: 80 },
  { k: 'tipo_motor', l: 'Motor', w: 60 }, { k: 'num_fileiras', l: 'Fileiras', w: 60, n: true },
  { k: 'capacidade_kcal_h', l: 'Capac. (kcal/h)', w: 100, n: true }, { k: 'potencia_kw', l: 'Pot. (kW)', w: 70, n: true },
  { k: 'corrente_220v', l: '220V (A)', w: 65, n: true }, { k: 'corrente_380v', l: '380V (A)', w: 65, n: true },
  { k: 'corrente_460v', l: '460V (A)', w: 65, n: true }, { k: 'ruido_db', l: 'Ruído (dBa)', w: 70, n: true },
  { k: 'carga_refrigerante_kg', l: 'Carga Ref. (kg)', w: 90, n: true },
  { k: 'coletor_entrada_pol', l: 'Colet. Ent.', w: 80 }, { k: 'coletor_saida_pol', l: 'Colet. Saída', w: 80 },
  { k: 'peso_liquido_kg', l: 'Peso Líq. (kg)', w: 85, n: true }, { k: 'peso_bruto_kg', l: 'Peso Bruto (kg)', w: 85, n: true },
  { k: 'comprimento_mm', l: 'Comp. (mm)', w: 80, n: true }, { k: 'largura_mm', l: 'Larg. (mm)', w: 80, n: true },
  { k: 'altura_mm', l: 'Alt. (mm)', w: 80, n: true }, { k: 'num_fixacoes', l: 'Nº Fix.', w: 55, n: true },
];

// Delta de condensação NÃO tem tabela de fator — é razão (delta do projeto / DT de Catálogo da
// linha), igual ao ΔT do forçador de ar. O DT de Catálogo é campo da própria linha do catálogo.
const C15_FATORES_TIPOS = [
  ['gas', 'Gás Refrigerante'], ['aleta', 'Material de Aletas'],
  ['altitude', 'Altitude (Até, m)'], ['temp_entrada_ar', 'Temp. Entrada Ar (Até, °C)'],
];

const C15_CAMPO_BUSCA_SISTEMA_OPCOES = [
  ['gas', 'Gás Refrigerante'], ['tensao_comando', 'Tensão Comando'], ['tensao_equipamentos', 'Tensão Equipamentos'],
  ['fpi', 'FPI / Aletas por Polegada (catálogo)'], ['tipo_motor', 'Tipo Motor (catálogo)'],
  ['num_fileiras', 'Nº Fileiras (catálogo)'], ['qtd_ventiladores', 'Nº de Ventiladores (catálogo)'],
  ['polos_ou_rpm', 'Nº de Pólos / RPM (catálogo)'],
];

function initTela15() {
  document.getElementById('c15_btnBaixarTemplate').addEventListener('click', c15_baixarTemplate);
  document.getElementById('c15_arquivoExcel').addEventListener('change', c15_previewExcel);
  document.getElementById('c15_btnBaixarDocumento').addEventListener('click', c15_baixarDocumento);
  document.getElementById('c15_btnExportar').addEventListener('click', c15_abrirFiltroExportacao);
  document.getElementById('c15exp_cancelar').addEventListener('click', () => { document.getElementById('c15_exportFiltro').style.display = 'none'; });
  document.getElementById('c15exp_gerar').addEventListener('click', c15_gerarExportacao);
  document.getElementById('c15_btnConfirmarImportacao').addEventListener('click', c15_confirmarImportacao);
  document.getElementById('c15_btnCancelarPreview').addEventListener('click', c15_cancelarPreview);
  document.getElementById('c15_btnFecharLinha').addEventListener('click', c15_fecharLinha);
  document.getElementById('c15_btnSalvarLinha').addEventListener('click', c15_salvarLinha);
  document.getElementById('c15_btnExcluirLinha').addEventListener('click', c15_excluirLinhaAtual);
  document.getElementById('c15_btnAddModelo').addEventListener('click', c15_addModelo);
  document.getElementById('c15_linhaFotoInput').addEventListener('change', c15_enviarFoto);
  window.telaShowHandlers[15] = c15_carregarTudo;
}

async function c15_carregarTudo() {
  await c15_carregarLinhas();
}

// ---------- Exportação ----------
async function c15_abrirFiltroExportacao() {
  const painel = document.getElementById('c15_exportFiltro');
  if (painel.style.display !== 'none') { painel.style.display = 'none'; return; }
  const o = await api.get('/api/condensadores/exportar-bd/opcoes');
  const fill = (id, vals) => { document.getElementById(id).innerHTML = '<option value="">Todos</option>' + vals.map(v => `<option value="${v}">${v}</option>`).join(''); };
  fill('c15exp_fabricante', o.fabricantes); fill('c15exp_linha', o.linhas);
  fill('c15exp_estrutura', o.tipos_estrutura); fill('c15exp_fpi', o.fpis); fill('c15exp_motor', o.tipos_motor);
  painel.style.display = 'block';
}

function c15_gerarExportacao() {
  const p = new URLSearchParams();
  const g = (id, key) => { const v = document.getElementById(id).value; if (v) p.set(key, v); };
  g('c15exp_fabricante', 'fabricante'); g('c15exp_linha', 'linha'); g('c15exp_estrutura', 'tipo_estrutura');
  g('c15exp_fpi', 'fpi'); g('c15exp_motor', 'tipo_motor');
  api.baixarOuSalvar('/api/condensadores/exportar-bd' + (p.toString() ? '?' + p.toString() : ''));
  document.getElementById('c15_exportFiltro').style.display = 'none';
}

function c15_baixarTemplate(e) { e.preventDefault(); api.baixarOuSalvar('/api/condensadores/template'); }
function c15_baixarDocumento(e) { e.preventDefault(); api.baixarOuSalvar('/api/condensadores/documento'); }

// ---------- Tabela de modelos (achatada, reutilizada no preview e no detalhe) ----------
function c15_htmlTabelaModelos(modelos, { comExcluir }) {
  return `<table class="list" style="white-space:nowrap;"><thead><tr>
    ${C15_MODELO_COLS.map(c => `<th style="white-space:normal;">${c.l}</th>`).join('')}${comExcluir ? '<th></th>' : ''}
    </tr></thead><tbody>${modelos.map(md => `<tr data-modelo-id="${md.id ?? ''}">
    ${C15_MODELO_COLS.map(c => `<td><input type="text" data-campo="${c.k}" value="${md[c.k] ?? ''}" style="width:${c.w}px;"></td>`).join('')}
    ${comExcluir ? `<td><span class="btn-text danger" data-excluir-modelo="${md.id}">Excluir</span></td>` : ''}</tr>`).join('')}
    </tbody></table>`;
}

function c15_coletarModelos(container, modelosOriginais) {
  return Array.from(container.querySelectorAll('tbody tr')).map((tr, i) => {
    const item = { id: tr.dataset.modeloId ? Number(tr.dataset.modeloId) : null };
    C15_MODELO_COLS.forEach(c => {
      const v = tr.querySelector(`[data-campo="${c.k}"]`).value;
      item[c.k] = c.n ? parseNumBR(v) : (v || null);
    });
    // descricao_comercial é campo da LINHA (não aparece na grade por modelo) — sem isso, todo
    // reconstrução a partir da grade (confirmação de importação) descartava o texto lido do Excel.
    if (modelosOriginais && modelosOriginais[i]) item.descricao_comercial = modelosOriginais[i].descricao_comercial;
    return item;
  }).filter(md => md.modelo);
}

// ---------- Importação por Excel ----------
async function c15_previewExcel() {
  const input = document.getElementById('c15_arquivoExcel');
  const file = input.files[0];
  if (!file) return;
  const el = document.getElementById('c15_resultadoExcel');
  el.textContent = 'Lendo planilha...';
  try {
    const r = await api.upload('/api/condensadores/excel-preview', file);
    input.value = '';
    if (r.erro) { el.innerHTML = `<span style="color:#b91c1c;">${r.erro}</span>`; return; }
    el.textContent = '';
    c15_previewLinhas = r.linhas;
    c15_previewNomeArquivo = file.name;
    c15_renderPreview();
  } catch (err) {
    el.innerHTML = `<span style="color:#b91c1c;">Falha ao ler planilha: ${err.message}</span>`;
    input.value = '';
  }
}

const C15_STATUS_LABEL = {
  nova_linha: '<span style="color:#15803d;font-weight:bold;">Linha nova</span>',
  nova_versao: '<span style="color:#b45309;font-weight:bold;">Nova versão (substitui a anterior)</span>',
  atualizar_versao_existente: '<span style="color:#b45309;font-weight:bold;">Atualiza versão já existente</span>',
  sem_alteracoes: '<span style="color:#6b7280;">Sem alterações em relação à versão anterior</span>',
};

function c15_renderPreview() {
  const wrap = document.getElementById('c15_previewWrap');
  const cont = document.getElementById('c15_previewLinhas');
  if (!c15_previewLinhas || !c15_previewLinhas.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'block';
  c15_carregarSubtreeIdPai();
  cont.innerHTML = c15_previewLinhas.map((item, i) => {
    if (item.erro) return `<div style="color:#b91c1c;padding:8px 0;">• ${item.linha || '?'}: ${item.erro}</div>`;
    return `<div style="margin-bottom:20px;border:1px solid #e5e7eb;border-radius:6px;padding:10px;">
      <div style="margin-bottom:6px;"><strong>${item.fabricante} / ${item.linha}</strong> — ${item.tipo_estrutura || '—'} · versão ${item.versao_catalogo || '—'}
        &nbsp;·&nbsp; ${C15_STATUS_LABEL[item.status] || item.status}
        ${item.observacao ? `<div class="small" style="color:#6b7280;">${item.observacao}</div>` : ''}
        <div class="small" style="color:#6b7280;">${item.fatores.length} fator(es) · ${item.campos.length} campo(s) de nomenclatura</div>
      </div>
      <div style="overflow-x:auto;" class="c15-preview-tabela" data-idx="${i}">${c15_htmlTabelaModelos(item.modelos, { comExcluir: false })}</div>
    </div>`;
  }).join('');
}

async function c15_confirmarImportacao() {
  if (!c15_previewLinhas) return;
  const idPai = document.getElementById('c15_idPai').value || undefined;
  const linhas = c15_previewLinhas.filter(item => !item.erro).map((item, i) => {
    const el = document.querySelector(`.c15-preview-tabela[data-idx="${i}"]`);
    const modelos = el ? c15_coletarModelos(el, item.modelos) : item.modelos;
    return { fabricante: item.fabricante, linha: item.linha, versao_catalogo: item.versao_catalogo,
             tipo_estrutura: item.tipo_estrutura, dt_catalogo_c: item.dt_catalogo_c,
             modelos, fatores: item.fatores, campos: item.campos, id_pai: idPai };
  });
  const btn = document.getElementById('c15_btnConfirmarImportacao');
  btn.disabled = true; btn.textContent = 'Gravando...';
  try {
    const r = await api.post('/api/condensadores/excel-confirmar', { nome_arquivo: c15_previewNomeArquivo, linhas });
    document.getElementById('c15_resultadoExcel').innerHTML = r.resultados.map(l =>
      l.erro ? `<div style="color:#b91c1c;">• ${l.linha || '?'}: ${l.erro}</div>`
             : `<div style="color:#15803d;">• ${l.fabricante} / ${l.linha} (${l.tipo_estrutura || '—'}): importado (${l.qtd_modelos} modelo(s))</div>`).join('');
    nomenc_invalidarCache();  // importação pode ter trazido Campos novos/atualizados pras linhas gravadas
    c15_cancelarPreview();
    c15_carregarTudo();
  } catch (err) {
    alert('Falha ao gravar: ' + err.message);
  }
  btn.disabled = false; btn.textContent = 'Confirmar Importação';
}

function c15_cancelarPreview() {
  c15_previewLinhas = null;
  document.getElementById('c15_previewWrap').style.display = 'none';
  document.getElementById('c15_previewLinhas').innerHTML = '';
}

// ---------- Linhas (catálogos) ----------
async function c15_carregarLinhas() {
  const linhas = await api.get('/api/condensadores/linhas');
  const el = document.getElementById('c15_linhasList');
  if (!linhas.length) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma linha cadastrada ainda — importe uma planilha acima.</div>'; return; }
  const grupos = {};
  linhas.forEach(l => { (grupos[l.fabricante_nome] = grupos[l.fabricante_nome] || []).push(l); });
  let html = '';
  Object.keys(grupos).forEach(fab => {
    html += `<div class="group-head">${fab}</div><table class="list"><tbody>`;
    grupos[fab].forEach(l => {
      html += `<tr class="clickable" data-linha="${l.id}">
        <td style="font-weight:bold;">${l.nome}</td><td>${l.tipo_estrutura || '—'}</td><td>versão ${l.versao_catalogo || '—'}</td>
        <td>${l.qtd_modelos} modelo(s)</td><td>${l.ativo_comercial ? '' : '<span class="badge badge-pendente">Obsoleto</span>'}</td>
        <td style="text-align:right;"><span class="btn-text danger" data-excluir-linha="${l.id}">Excluir</span></td></tr>`;
    });
    html += '</tbody></table>';
  });
  el.innerHTML = html;
  el.querySelectorAll('[data-linha]').forEach(tr => tr.addEventListener('click', (e) => {
    if (e.target.closest('[data-excluir-linha]')) return;
    c15_abrirLinha(Number(tr.dataset.linha), linhas);
  }));
  el.querySelectorAll('[data-excluir-linha]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!confirm('Excluir esta linha e todos os seus modelos?')) return;
    try {
      await api.del(`/api/condensadores/linhas/${b.dataset.excluirLinha}`);
      if (c15_linhaAtualId === Number(b.dataset.excluirLinha)) c15_fecharLinha();
      c15_carregarLinhas();
    } catch (err) { alert('Erro ao excluir linha: ' + err.message); }
  }));
}

async function c15_abrirLinha(id, linhasCache) {
  c15_linhaAtualId = id;
  const linha = linhasCache.find(l => l.id === id);
  document.getElementById('c15_linhaDetalheWrap').style.display = 'block';
  document.querySelector('#c15_linhaDetalheTitulo').childNodes[0].textContent = `Modelos — ${linha.fabricante_nome} / ${linha.nome} (${linha.tipo_estrutura || '—'}) `;
  document.getElementById('c15_linhaNome').value = linha.nome || '';
  document.getElementById('c15_linhaEstrutura').value = linha.tipo_estrutura || '';
  document.getElementById('c15_linhaDtCatalogo').value = linha.dt_catalogo_c ?? '';
  document.getElementById('c15_linhaIdComercial').value = linha.id_comercial || '—';
  document.getElementById('c15_linhaDescricao').value = linha.descricao_comercial || '';
  document.getElementById('c15_linhaObsoleto').checked = linha.ativo_comercial === false;
  c15_renderFoto(linha.imagem_path);
  const idAbertura = id;
  await Promise.all([c15_carregarModelos(idAbertura), c15_carregarFatores(idAbertura), c15_carregarNomenclatura(idAbertura)]);
  document.getElementById('c15_linhaDetalheWrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function c15_renderFoto(caminho) {
  document.getElementById('c15_linhaFotoPreview').innerHTML = caminho
    ? `<img src="${caminho}" style="max-width:220px;max-height:160px;border:1px solid var(--line);border-radius:4px;">`
    : '<span class="small" style="color:#9ca3af;">Nenhuma foto enviada ainda.</span>';
}

async function c15_enviarFoto(ev) {
  const file = ev.target.files[0];
  if (!file || !c15_linhaAtualId) return;
  const r = await api.upload(`/api/condensadores/linhas/${c15_linhaAtualId}/foto`, file);
  c15_renderFoto(r.imagem_path);
  ev.target.value = '';
}

// ---------- Modelos (tabela plana editável inline) ----------
async function c15_carregarModelos(idAbertura = c15_linhaAtualId) {
  const modelos = await api.get(`/api/condensadores/linhas/${idAbertura}/modelos`);
  if (c15_linhaAtualId !== idAbertura) return; // resposta desatualizada
  const el = document.getElementById('c15_modelosView');
  el.innerHTML = modelos.length ? c15_htmlTabelaModelos(modelos, { comExcluir: true })
    : '<div class="small" style="padding:8px;color:#9ca3af;">Nenhum modelo — adicione um abaixo.</div>';
  el.querySelectorAll('tbody tr[data-modelo-id]').forEach(tr => {
    const id = tr.dataset.modeloId;
    tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async () => {
      const c = C15_MODELO_COLS.find(x => x.k === inp.dataset.campo);
      const v = c.n ? parseNumBR(inp.value) : (inp.value || null);
      await api.put(`/api/condensadores/modelos/${id}`, { [inp.dataset.campo]: v });
    }));
    tr.querySelector('[data-excluir-modelo]').addEventListener('click', async () => {
      if (!confirm('Excluir este modelo?')) return;
      try {
        await api.del(`/api/condensadores/modelos/${id}`);
        c15_carregarModelos();
      } catch (err) { alert('Erro ao excluir modelo: ' + err.message); }
    });
  });
}

async function c15_addModelo() {
  if (!c15_linhaAtualId) return;
  await api.post(`/api/condensadores/linhas/${c15_linhaAtualId}/modelos`, { modelo: 'Novo modelo' });
  c15_carregarModelos();
}

// ---------- Fatores de correção (5 tipos) ----------
function c15_htmlLinhaFator(chave, fator) {
  return `<tr>
    <td><input type="text" data-fator-chave value="${chave ?? ''}" placeholder="chave" style="width:120px;"></td>
    <td><input type="text" data-fator-valor value="${fator ?? ''}" placeholder="—" style="width:80px;"></td>
    <td style="text-align:right;"><span class="btn-text danger" data-excluir-fator>Excluir</span></td></tr>`;
}

async function c15_carregarFatores(idAbertura = c15_linhaAtualId) {
  const fatores = await api.get(`/api/condensadores/linhas/${idAbertura}/fatores`);
  if (c15_linhaAtualId !== idAbertura) return;
  const porTipo = {};
  fatores.forEach(f => { (porTipo[f.tipo] = porTipo[f.tipo] || []).push(f); });
  const el = document.getElementById('c15_fatores');
  el.innerHTML = C15_FATORES_TIPOS.map(([tipo, rotulo]) => `
    <div style="display:inline-block;vertical-align:top;margin:0 16px 12px 0;" data-fator-tipo="${tipo}">
      <div class="small" style="font-weight:bold;margin-bottom:4px;">${rotulo}</div>
      <table class="list"><tbody>${(porTipo[tipo] || []).map(f => c15_htmlLinhaFator(f.chave, f.fator)).join('')}</tbody></table>
      <p style="margin-top:4px;"><span class="btn-text" data-add-fator>+ adicionar</span></p>
    </div>`).join('');
  el.querySelectorAll('[data-fator-tipo]').forEach(bloco => {
    bloco.querySelectorAll('[data-excluir-fator]').forEach(b => b.addEventListener('click', () => b.closest('tr').remove()));
    bloco.querySelector('[data-add-fator]').addEventListener('click', () => {
      const tbody = bloco.querySelector('tbody');
      tbody.insertAdjacentHTML('beforeend', c15_htmlLinhaFator('', ''));
      const tr = tbody.lastElementChild;
      tr.querySelector('[data-excluir-fator]').addEventListener('click', () => tr.remove());
      tr.querySelector('[data-fator-chave]').focus();
    });
  });
}

function c15_coletarFatores() {
  const fatores = [];
  document.querySelectorAll('#c15_fatores [data-fator-tipo]').forEach(bloco => {
    const tipo = bloco.dataset.fatorTipo;
    bloco.querySelectorAll('tbody tr').forEach(tr => {
      const chave = tr.querySelector('[data-fator-chave]').value.trim();
      const fatorTxt = tr.querySelector('[data-fator-valor]').value;
      if (chave) fatores.push({ tipo, chave, fator: fatorTxt === '' ? null : parseNumBR(fatorTxt) });
    });
  });
  return fatores;
}

// ---------- Nomenclatura ----------
let c15_editorNomenclatura = null;
function c15_obterEditorNomenclatura() {
  if (!c15_editorNomenclatura) c15_editorNomenclatura = nomenc_criarEditorCampos('c15_nomenclatura', C15_CAMPO_BUSCA_SISTEMA_OPCOES);
  return c15_editorNomenclatura;
}
async function c15_carregarNomenclatura(idAbertura = c15_linhaAtualId) {
  await c15_obterEditorNomenclatura().carregar(`/api/condensadores/linhas/${idAbertura}/campos`);
}

// ---------- Salvar / fechar / excluir ----------
async function c15_salvarLinha() {
  const btn = document.getElementById('c15_btnSalvarLinha');
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    const fatores = c15_coletarFatores();
    const tarefas = [
      { nome: 'Cabeçalho', fn: () => api.put(`/api/condensadores/linhas/${c15_linhaAtualId}`, {
          nome: document.getElementById('c15_linhaNome').value,
          tipo_estrutura: document.getElementById('c15_linhaEstrutura').value || null,
          dt_catalogo_c: parseNumBR(document.getElementById('c15_linhaDtCatalogo').value),
          descricao_comercial: document.getElementById('c15_linhaDescricao').value || null,
          ativo_comercial: !document.getElementById('c15_linhaObsoleto').checked,
        }) },
      { nome: 'Fatores de Correção', fn: () => api.put(`/api/condensadores/linhas/${c15_linhaAtualId}/fatores`, { fatores }) },
      { nome: 'Nomenclatura de Compra', fn: () => c15_obterEditorNomenclatura().salvar() },
    ];
    const erros = [];
    for (const t of tarefas) {
      try { await t.fn(); } catch (err) { erros.push(`${t.nome}: ${err.message}`); }
    }
    nomenc_invalidarCache();
    await c15_carregarFatores();
    await c15_carregarNomenclatura();
    c15_carregarLinhas();
    if (erros.length) alert('Algumas partes NÃO foram salvas:\n' + erros.join('\n'));
  } finally {
    btn.disabled = false;
  }
}

function c15_fecharLinha() {
  c15_linhaAtualId = null;
  document.getElementById('c15_linhaDetalheWrap').style.display = 'none';
  document.getElementById('c15_modelosView').innerHTML = '';
  document.getElementById('c15_fatores').innerHTML = '';
  const nomEl = document.getElementById('c15_nomenclatura');
  nomEl.innerHTML = '';
  nomEl.dataset.campos = '[]';
}

async function c15_excluirLinhaAtual() {
  if (!c15_linhaAtualId) return;
  if (!confirm('Excluir este catálogo (linha) inteiro e todos os seus modelos?')) return;
  try {
    await api.del(`/api/condensadores/linhas/${c15_linhaAtualId}`);
    c15_fecharLinha();
    c15_carregarLinhas();
  } catch (err) { alert('Erro ao excluir catálogo: ' + err.message); }
}

window.initTela15 = initTela15;
document.addEventListener('DOMContentLoaded', initTela15);
