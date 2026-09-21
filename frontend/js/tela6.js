let t6_linhaAtualId = null;
let t6_previewLinhas = null; // resultado bruto de /excel-preview, um item por linha detectada
let t6_previewNomeArquivo = null;
let t6_matrizAtual = null; // matriz da linha atualmente aberta (view/edit)

async function t6_carregarSubtreeIdPai() {
  const sel = document.getElementById('f6_idPai');
  sel.innerHTML = '<option value="">(automático)</option>';
  try {
    const nos = await api.get('/api/catalogos/ids-comerciais/subtree?raiz=4.2');
    for (const n of nos) {
      const indent = '  '.repeat(n.codigo.split('.').length - 2);
      sel.innerHTML += `<option value="${n.codigo}">${indent}${n.codigo} — ${n.nome}</option>`;
    }
  } catch (e) { /* mantém só a opção automático */ }
}

function initTela6() {
  document.getElementById('f6_btnBaixarTemplate').addEventListener('click', t6_baixarTemplate);
  document.getElementById('f6_arquivoExcel').addEventListener('change', t6_previewExcel);
  document.getElementById('f6_btnBaixarDocumento').addEventListener('click', t6_baixarDocumento);
  document.getElementById('f6_btnExportar').addEventListener('click', t6_abrirFiltroExportacao);
  document.getElementById('f6exp_cancelar').addEventListener('click', () => { document.getElementById('f6_exportFiltro').style.display = 'none'; });
  document.getElementById('f6exp_gerar').addEventListener('click', t6_gerarExportacao);
  document.getElementById('f6_btnConfirmarImportacao').addEventListener('click', t6_confirmarImportacao);
  document.getElementById('f6_btnCancelarPreview').addEventListener('click', t6_cancelarPreview);
  document.getElementById('f6_btnFecharLinha').addEventListener('click', t6_fecharLinha);
  document.getElementById('f6_btnSalvarLinha').addEventListener('click', t6_salvarLinha);
  document.getElementById('f6_btnExcluirLinha').addEventListener('click', t6_excluirLinhaAtual);
  document.getElementById('f6_linhaFotoInput').addEventListener('change', t6_enviarFotoLinha);
  window.telaShowHandlers[6] = t6_carregarTudo;
}

async function t6_carregarTudo() {
  await t6_carregarLinhas();
}

async function t6_abrirFiltroExportacao() {
  const painel = document.getElementById('f6_exportFiltro');
  if (painel.style.display !== 'none') { painel.style.display = 'none'; return; }
  const opcoes = await api.get('/api/forcadores/exportar-bd/opcoes');
  const fill = (id, valores) => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">Todos</option>' + valores.map(v => `<option value="${v}">${v}</option>`).join('');
  };
  fill('f6exp_fabricante', opcoes.fabricantes);
  fill('f6exp_linha', opcoes.linhas);
  fill('f6exp_fpi', opcoes.fpis);
  fill('f6exp_pdl', opcoes.pdls);
  painel.style.display = 'block';
}

function t6_gerarExportacao() {
  const params = new URLSearchParams();
  const fab = document.getElementById('f6exp_fabricante').value;
  const lin = document.getElementById('f6exp_linha').value;
  const fpi = document.getElementById('f6exp_fpi').value;
  const pdl = document.getElementById('f6exp_pdl').value;
  if (fab) params.set('fabricante', fab);
  if (lin) params.set('linha', lin);
  if (fpi) params.set('fpi', fpi);
  if (pdl) params.set('pdl', pdl);
  api.downloadRemoto('/api/forcadores/exportar-bd' + (params.toString() ? '?' + params.toString() : ''));
  document.getElementById('f6_exportFiltro').style.display = 'none';
}

function t6_baixarTemplate(e) {
  e.preventDefault();
  api.downloadRemoto('/api/importacao/template');
}

function t6_baixarDocumento(e) {
  e.preventDefault();
  api.downloadRemoto('/api/importacao/documento');
}

// ---------- Importação por Excel, com revisão antes de gravar ----------

async function t6_previewExcel() {
  const input = document.getElementById('f6_arquivoExcel');
  const file = input.files[0];
  if (!file) return;
  const el = document.getElementById('f6_resultadoExcel');
  el.textContent = 'Lendo planilha...';
  try {
    const r = await api.upload('/api/importacao/excel-preview', file);
    input.value = '';
    if (r.erro) {
      el.innerHTML = `<span style="color:#b91c1c;">${r.erro}</span>`;
      return;
    }
    el.textContent = '';
    t6_previewLinhas = r.linhas;
    t6_previewNomeArquivo = r.nome_arquivo;
    t6_renderPreview();
  } catch (err) {
    el.innerHTML = `<span style="color:#b91c1c;">Falha ao ler planilha: ${err.message}</span>`;
    input.value = '';
  }
}

const T6_STATUS_LABEL = {
  nova_linha: '<span style="color:#15803d;font-weight:bold;">Linha nova</span>',
  nova_versao: '<span style="color:#b45309;font-weight:bold;">Nova versão (substitui a anterior)</span>',
  atualizar_versao_existente: '<span style="color:#b45309;font-weight:bold;">Atualiza versão já existente</span>',
  sem_alteracoes: '<span style="color:#6b7280;">Sem alterações em relação à versão anterior</span>',
};

function t6_renderPreview() {
  const wrap = document.getElementById('f6_previewWrap');
  const cont = document.getElementById('f6_previewLinhas');
  if (!t6_previewLinhas || t6_previewLinhas.length === 0) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'block';
  t6_carregarSubtreeIdPai();
  cont.innerHTML = t6_previewLinhas.map((item, i) => {
    if (item.erro) return `<div style="color:#b91c1c;padding:8px 0;">• ${item.linha || '?'}: ${item.erro}</div>`;
    const m = item.matriz;
    return `<div style="margin-bottom:20px;border:1px solid #e5e7eb;border-radius:6px;padding:10px;">
      <div style="margin-bottom:6px;"><strong>${m.fabricante} / ${m.linha}</strong> — versão ${m.versao_catalogo || '—'}
        &nbsp;·&nbsp; ${T6_STATUS_LABEL[item.status] || item.status}
        ${item.observacao ? `<div class="small" style="color:#6b7280;">${item.observacao}</div>` : ''}
      </div>
      <div class="f6-preview-tabela" data-idx="${i}"></div>
    </div>`;
  }).join('');
  t6_previewLinhas.forEach((item, i) => {
    if (item.erro) return;
    const el = cont.querySelector(`.f6-preview-tabela[data-idx="${i}"]`);
    mf_renderMatriz(el, item.matriz, { readOnly: false });
  });
}

async function t6_confirmarImportacao() {
  if (!t6_previewLinhas) return;
  const idPai = document.getElementById('f6_idPai').value || undefined;
  const linhas = t6_previewLinhas.filter(item => !item.erro).map((item, i) => {
    const el = document.querySelector(`.f6-preview-tabela[data-idx="${i}"]`);
    const matrizEditada = el ? mf_coletarMatriz(el, item.matriz) : item.matriz;
    return { status: item.status, observacao: item.observacao, matriz: matrizEditada,
             campos: item.campos, fatores_gas: item.fatores_gas, linha_anterior_id: item.linha_anterior_id,
             id_pai: idPai };
  });
  const btn = document.getElementById('f6_btnConfirmarImportacao');
  btn.disabled = true;
  btn.textContent = 'Gravando...';
  try {
    const r = await api.post('/api/importacao/excel-confirmar', { nome_arquivo: t6_previewNomeArquivo, linhas });
    const el = document.getElementById('f6_resultadoExcel');
    el.innerHTML = r.linhas.map(l => {
      if (l.erro) return `<div style="color:#b91c1c;">• ${l.linha || '?'}: ${l.erro}</div>`;
      if (l.acao === 'sem_alteracoes') return `<div style="color:#6b7280;">• ${l.fabricante} / ${l.linha}: sem alterações</div>`;
      return `<div style="color:#15803d;">• ${l.fabricante} / ${l.linha}: importado (${l.qtd_modelos} modelo(s))</div>`;
    }).join('');
    nomenc_invalidarCache();  // importação pode ter trazido Campos novos/atualizados pras linhas gravadas
    t6_cancelarPreview();
    t6_carregarTudo();
    catalogoSincronizar();  // push imediato para Fly.io/Supabase
  } catch (err) {
    alert('Falha ao gravar: ' + err.message);
  }
  btn.disabled = false;
  btn.textContent = 'Confirmar Importação';
}

function t6_cancelarPreview() {
  t6_previewLinhas = null;
  document.getElementById('f6_previewWrap').style.display = 'none';
  document.getElementById('f6_previewLinhas').innerHTML = '';
}

// ---------- Linhas ----------

async function t6_carregarLinhas() {
  const linhas = await api.get('/api/forcadores/linhas');
  const el = document.getElementById('f6_linhasList');
  if (linhas.length === 0) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma linha cadastrada ainda — importe uma planilha acima.</div>'; return; }
  const grupos = {};
  linhas.forEach(l => { (grupos[l.fabricante_nome] = grupos[l.fabricante_nome] || []).push(l); });
  let html = '';
  Object.keys(grupos).forEach(fab => {
    const fabId = grupos[fab][0].fabricante_id;
    html += `<div class="group-head">${fab} <span class="btn-text" data-renomear-fab-id="${fabId}" data-renomear-fab-nome="${fab}" style="font-size:11px;cursor:pointer;">Renomear</span></div><table class="list"><tbody>`;
    grupos[fab].forEach(l => {
      html += `<tr class="clickable" data-linha="${l.id}">
        <td style="font-weight:bold;">${l.nome}</td><td>versão ${l.versao_catalogo || '—'}</td>
        <td>${l.qtd_modelos} modelo(s)</td><td>${l.ativo_comercial ? '' : '<span class="badge badge-pendente">Obsoleto</span>'}</td>
        <td style="color:#6b7280;font-size:11px;">${l.observacao_versao || ''}</td>
        <td style="text-align:right;"><span class="btn-text danger" data-excluir-linha="${l.id}">Excluir</span></td></tr>`;
    });
    html += '</tbody></table>';
  });
  el.innerHTML = html;
  el.querySelectorAll('[data-linha]').forEach(tr => tr.addEventListener('click', (e) => {
    if (e.target.closest('[data-excluir-linha]')) return;
    t6_abrirLinha(Number(tr.dataset.linha), linhas);
  }));
  el.querySelectorAll('[data-excluir-linha]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!confirm('Excluir esta linha e todos os seus modelos?')) return;
    try {
      await api.del(`/api/forcadores/linhas/${b.dataset.excluirLinha}`);
      if (t6_linhaAtualId === Number(b.dataset.excluirLinha)) t6_fecharLinha();
      t6_carregarLinhas();
      try { localStorage.setItem('catalogosDirty', 'true'); } catch (_) {}
    } catch (err) { alert('Erro ao excluir linha: ' + err.message); }
  }));
  el.querySelectorAll('[data-renomear-fab-id]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    const id = b.dataset.renomearFabId;
    const nomeAtual = b.dataset.renomearFabNome;
    vkPrompt('Renomear Fabricante', [{ chave: 'nome', rotulo: 'Novo nome', valor: nomeAtual }], async (vals) => {
      const nomeNovo = (vals.nome || '').trim();
      if (!nomeNovo || nomeNovo === nomeAtual) return;
      try {
        await api.put(`/api/forcadores/fabricantes/${id}`, { nome: nomeNovo });
        t6_carregarLinhas();
        try { localStorage.setItem('catalogosDirty', 'true'); } catch (_) {}
      } catch (err) { alert('Erro ao renomear: ' + err.message); }
    });
  }));
}

async function t6_abrirLinha(id, linhasCache) {
  t6_linhaAtualId = id;
  const linha = linhasCache.find(l => l.id === id);
  document.getElementById('f6_linhaDetalheWrap').style.display = 'block';
  document.querySelector('#f6_linhaDetalheTitulo').childNodes[0].textContent = `Modelos — ${linha.fabricante_nome} / ${linha.nome} `;
  document.getElementById('f6_linhaNome').value = linha.nome || '';
  document.getElementById('f6_linhaIdComercial').value = linha.id_comercial || '—';
  document.getElementById('f6_linhaDescricao').value = linha.descricao_comercial || '';
  document.getElementById('f6_linhaObsoleto').checked = linha.ativo_comercial === false;
  t6_renderFotoPreview(linha.imagem_path);
  // Guarda o id no momento da abertura: se o usuário trocar de linha antes das respostas
  // chegarem, as respostas desta chamada (agora desatualizada) são descartadas em vez de
  // "vazar" pra tela da linha nova (bug real: catálogos diferentes pareciam interligados
  // porque uma resposta atrasada da linha antiga sobrescrevia os dados da linha nova).
  const idAbertura = id;
  await Promise.all([t6_carregarMatriz(idAbertura), t6_carregarFatoresGas(idAbertura), t6_carregarNomenclatura(idAbertura)]);
  document.getElementById('f6_linhaDetalheWrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function t6_renderFotoPreview(caminho) {
  const el = document.getElementById('f6_linhaFotoPreview');
  el.innerHTML = caminho ? `<img src="${caminho}" style="max-width:220px;max-height:160px;border:1px solid var(--line);border-radius:4px;">` : '<span class="small" style="color:#9ca3af;">Nenhuma foto enviada ainda.</span>';
}

async function t6_enviarFotoLinha(ev) {
  const file = ev.target.files[0];
  if (!file || !t6_linhaAtualId) return;
  try {
    const r = await api.upload(`/api/forcadores/linhas/${t6_linhaAtualId}/foto`, file);
    t6_renderFotoPreview(r.imagem_path);
    catalogoSincronizar();  // push imediato para Fly.io/Supabase
  } catch (err) { alert('Erro ao enviar foto: ' + err.message); }
  ev.target.value = '';
}

function t6_fecharLinha() {
  t6_linhaAtualId = null;
  t6_matrizAtual = null;
  document.getElementById('f6_linhaDetalheWrap').style.display = 'none';
  document.getElementById('f6_linhaMatrizView').innerHTML = '';
  document.getElementById('f6_fatoresGas').innerHTML = '';
  const nomEl = document.getElementById('f6_nomenclatura');
  nomEl.innerHTML = '';
  nomEl.dataset.campos = '[]';
}

// A tabela já vem sempre editável — sem alternância entre "ver" e "editar" (item 1: edição
// direto na mesma tabela, sem abrir outra).
async function t6_carregarMatriz(idAbertura = t6_linhaAtualId) {
  const matriz = await api.get(`/api/forcadores/linhas/${idAbertura}/matriz`);
  if (t6_linhaAtualId !== idAbertura) return; // resposta desatualizada, linha trocou nesse meio-tempo
  t6_matrizAtual = matriz;
  mf_renderMatriz(document.getElementById('f6_linhaMatrizView'), matriz, { readOnly: false });
}

async function t6_salvarLinha() {
  // Trava o botão durante o salvamento — clicar várias vezes seguidas disparava chamadas
  // simultâneas de PUT .../campos, que podiam se sobrepor (delete + insert de cada chamada
  // intercalados) e duplicar os Campos salvos (bug real reportado).
  const btn = document.getElementById('f6_btnSalvarLinha');
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    // Cada seção grava independente — uma falhar não pode impedir as outras de salvar.
    const el = document.getElementById('f6_linhaMatrizView');
    const matrizEditada = mf_coletarMatriz(el, t6_matrizAtual);
    const fatores = Array.from(document.querySelectorAll('#f6_fatoresGas tbody tr')).map(tr => ({
      gas: tr.querySelector('[data-gas-nome]').value.trim(),
      fator: tr.querySelector('[data-gas-fator]').value === '' ? null : parseNumBR(tr.querySelector('[data-gas-fator]').value),
    })).filter(f => f.gas);
    const tarefas = [
      { nome: 'Cabeçalho (nome/descrição)', fn: () => api.put(`/api/forcadores/linhas/${t6_linhaAtualId}`, {
          nome: document.getElementById('f6_linhaNome').value,
          descricao_comercial: document.getElementById('f6_linhaDescricao').value || null,
          ativo_comercial: !document.getElementById('f6_linhaObsoleto').checked,
        }) },
      { nome: 'Matriz de Modelos', fn: () => api.put(`/api/forcadores/linhas/${t6_linhaAtualId}/matriz`, matrizEditada) },
      { nome: 'Fatores de Gás', fn: () => api.put(`/api/forcadores/linhas/${t6_linhaAtualId}/fatores-gas`, { fatores }) },
      { nome: 'Nomenclatura de Compra', fn: () => t6_obterEditorNomenclatura().salvar() },
    ];
    const erros = [];
    for (const t of tarefas) {
      try { await t.fn(); } catch (err) { erros.push(`${t.nome}: ${err.message}`); }
    }
    nomenc_invalidarCache();

    await t6_carregarMatriz();
    await t6_carregarFatoresGas();
    await t6_carregarNomenclatura();
    const tituloEl = document.querySelector('#f6_linhaDetalheTitulo').childNodes[0];
    tituloEl.textContent = tituloEl.textContent.replace(/\/ .+$/, `/ ${document.getElementById('f6_linhaNome').value} `);
    t6_carregarLinhas();

    try { localStorage.setItem('catalogosDirty', 'true'); } catch (_) {}
    if (erros.length) {
      alert('Algumas partes NÃO foram salvas:\n' + erros.join('\n') + '\n\nAs demais partes foram salvas normalmente.');
    }
  } finally {
    btn.disabled = false;
  }
}

// Lista fixa (mesma do Documento de Importação) — sempre mostrada e editável, mesmo sem nenhum
// fator salvo ainda, senão a seção fica vazia sem nenhum jeito de adicionar (bug real encontrado).
const T6_GASES_FATOR_CORRECAO = ["R-404A", "R-134a", "R-452A", "R-448A", "R-449A", "R-407C", "R-22", "R-410A"];

function t6_linhaFatorGas(gas, fator) {
  return `<tr>
    <td style="width:160px;"><input type="text" data-gas-nome value="${gas ?? ''}" placeholder="ex.: R-404A" style="font-weight:bold;"></td>
    <td><input type="text" data-gas-fator value="${fator ?? ''}" style="width:80px;" placeholder="—"></td>
    <td style="width:60px;text-align:right;"><span class="btn-text danger" data-excluir-gas>Excluir</span></td>
  </tr>`;
}

async function t6_carregarFatoresGas(idAbertura = t6_linhaAtualId) {
  const fatores = await api.get(`/api/forcadores/linhas/${idAbertura}/fatores-gas`);
  if (t6_linhaAtualId !== idAbertura) return; // resposta desatualizada, linha trocou nesse meio-tempo
  const porGas = {};
  fatores.forEach(f => { porGas[f.gas] = f.fator; });
  const gases = [...new Set([...T6_GASES_FATOR_CORRECAO, ...Object.keys(porGas)])];
  const el = document.getElementById('f6_fatoresGas');
  el.innerHTML = `<table class="list"><tbody>${gases.map(gas => t6_linhaFatorGas(gas, porGas[gas])).join('')}</tbody></table>
    <p style="margin-top:6px;"><span class="btn-text" id="f6_btnAddGas">+ adicionar gás</span></p>`;
  el.querySelectorAll('[data-excluir-gas]').forEach(b => b.addEventListener('click', () => b.closest('tr').remove()));
  document.getElementById('f6_btnAddGas').addEventListener('click', () => {
    el.querySelector('tbody').insertAdjacentHTML('beforeend', t6_linhaFatorGas('', ''));
    const linhas = el.querySelectorAll('tbody tr');
    const novaLinha = linhas[linhas.length - 1];
    novaLinha.querySelector('[data-excluir-gas]').addEventListener('click', () => novaLinha.remove());
    novaLinha.querySelector('[data-gas-nome]').focus();
  });
}

// Editor horizontal de Campos do código comercial (Automático/Fixo/Manual) — mesmo motor e layout
// das Unidades Condensadoras (ver tela8.js). Cada linha de forçador tem sua própria estrutura.
// Duas fontes: seleção do Sistema/Projeto (Tipo de Degelo, Tensão Comando/Equipamentos, Gás) e
// dado que já existe no próprio catálogo por modelo (Qtd. Ventiladores, Diâmetro Ventilador) —
// só resolve depois que um modelo é escolhido pelo dimensionamento.
const T6_CAMPO_BUSCA_SISTEMA_OPCOES = [
  ['tipo_degelo', 'Tipo de Degelo'], ['tensao_comando', 'Tensão Comando'], ['tensao_equipamentos', 'Tensão Equipamentos'],
  ['gas', 'Gás Refrigerante'],
  ['num_ventiladores', 'Qtd. Ventiladores (catálogo)'], ['diametro_ventilador_mm', 'Diâmetro Ventilador (catálogo)'],
  ['fpi', 'FPI / Aletas por Polegada (catálogo)'],
];

let t6_editorNomenclatura = null;
function t6_obterEditorNomenclatura() {
  if (!t6_editorNomenclatura) t6_editorNomenclatura = nomenc_criarEditorCampos('f6_nomenclatura', T6_CAMPO_BUSCA_SISTEMA_OPCOES);
  return t6_editorNomenclatura;
}

async function t6_carregarNomenclatura(idAbertura = t6_linhaAtualId) {
  await t6_obterEditorNomenclatura().carregar(`/api/forcadores/linhas/${idAbertura}/campos`);
}

async function t6_excluirLinhaAtual() {
  if (!t6_linhaAtualId) return;
  if (!confirm('Excluir este catálogo (linha) inteiro e todos os seus modelos?')) return;
  try {
    await api.del(`/api/forcadores/linhas/${t6_linhaAtualId}`);
    t6_fecharLinha();
    t6_carregarLinhas();
    try { localStorage.setItem('catalogosDirty', 'true'); } catch (_) {}
  } catch (err) { alert('Erro ao excluir: ' + err.message); }
}

window.initTela6 = initTela6;
document.addEventListener('DOMContentLoaded', initTela6);
