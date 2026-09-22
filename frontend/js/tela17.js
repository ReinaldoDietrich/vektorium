// Tela 10 — Resumo Equip./Materiais e Composição de Preço (div id="tela17", data-tab="17";
// fusão com a antiga Tela 10, ver backend/scripts/migrar_fusao_tela10.py). 7 blocos fixos (ver
// backend/composicao_preco.py BLOCOS_COMPOSICAO), Resumo por bloco, Comissionamento, DRE.

const T17_BLOCOS = ['Equipamentos', 'Materiais Mecânicos', 'Materiais Elétricos',
  'Painéis Térmicos', 'Mão de Obra', 'Outros Serviços/ Materiais', 'Fretes e Transporte Vertical',
  'Comissões por Indicação de Negócio'];
const T17_BLOCOS_IMPORTAVEIS = { 'Materiais Mecânicos': 1, 'Materiais Elétricos': 1 };

let t17_fatores = [];
let t17_centrosCusto = [];
let t17_vendedores = [];
let t17_composicaoAtual = null;

function t17_brl(v) {
  return (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function t17_pct(v) {
  return v == null ? '—' : (v * 100).toFixed(1) + '%';
}

function initTela17() {
  window.telaShowHandlers[17] = t17_carregar;
  document.getElementById('t17_margemNegociacao').addEventListener('change', t17_salvarMargemNegociacao);
  document.getElementById('t17_btnRestaurarPadroes').addEventListener('click', async () => {
    const r = await api.post(`/api/composicao-preco/restaurar-padroes?projeto_id=${state.projetoId}`, {});
    alert(`${r.itens_criados} item(ns) restaurado(s).`);
    t17_carregar();
  });
  document.getElementById('t17_btnAddVendedor').addEventListener('click', t17_vincularVendedor);
  document.getElementById('t17_btnImprimir').addEventListener('click', t17_imprimirListaMateriais);
  document.getElementById('t17_btnExportarExcel').addEventListener('click', async () => {
    if (!state.projetoId) return;
    try { await api.baixarOuSalvar(`/api/composicao-preco/lista-materiais/exportar/excel?${t17_queryFiltrosAtivos()}`); }
    catch (e) { alert(`Erro ao exportar Excel:\n${e.message}`); }
  });
  document.getElementById('t17_filtroFab').addEventListener('change', t17_renderBlocosFiltrado);
  document.getElementById('t17_filtroCC').addEventListener('change', t17_renderBlocosFiltrado);
  document.getElementById('t17_filtroTipo').addEventListener('change', t17_renderBlocosFiltrado);
  document.getElementById('t17_orcAgrupar').addEventListener('change', () => {
    t17_atualizarVisibilidadeFiltrosOrcamento();
    if (t17_composicaoAtual) t17_renderTabelaOrcamento(t17_composicaoAtual);
  });
  document.getElementById('t17_orcExibir').addEventListener('change', () => {
    if (t17_composicaoAtual) t17_renderTabelaOrcamento(t17_composicaoAtual);
  });
  document.getElementById('t17_orcOcultarQtd').addEventListener('change', () => {
    if (t17_composicaoAtual) t17_renderTabelaOrcamento(t17_composicaoAtual);
  });
  t17_atualizarVisibilidadeFiltrosOrcamento();
  document.getElementById('t17_cpBtnGerar').addEventListener('click', t17_atualizarAgendaPagamento);
}

async function t17_carregar() {
  const semProjeto = document.getElementById('t17_semProjeto');
  const conteudo = document.getElementById('t17_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';

  const [, , , projeto] = await Promise.all([
    (async () => { t17_fatores = await api.get('/api/composicao-preco/fatores'); })(),
    (async () => { t17_centrosCusto = await api.get('/api/tela10/centro-custo'); })(),
    (async () => { t17_vendedores = await api.get('/api/composicao-preco/vendedores'); })(),
    api.get(`/api/projetos/${state.projetoId}`),
  ]);

  const margem = await api.get(`/api/composicao-preco/margem-negociacao?projeto_id=${state.projetoId}`);
  const margemInput = document.getElementById('t17_margemNegociacao');
  margemInput.value = (margem.percentual * 100).toFixed(1);

  t17_renderDadosProjeto(projeto);
  t17_popularFiltroCC();
  t17_popularFiltroTipo();
  const tudo = await t17_carregarTudo();
  t17_renderBlocos(tudo.composicao);
  t17_renderResumo(tudo.resumo);
  t17_renderTabelaOrcamento(tudo.composicao);
  t17_renderComissionamento(tudo.comissionamento);
  t17_renderDre(tudo.dre);
  await t17_carregarCondicaoPagamento();
}

// Composição + Resumo + Comissionamento + DRE numa passada só (ver backend obter_tudo) — antes
// cada um desses 4 era um GET separado, e cada GET rodava as 3 sincronizações pesadas
// (Equipamentos/Painéis/Comissões) do zero, travando a tela por segundos a cada campo editado
// (bug real reportado 2026-08-05: "a porra da tela leva uma eternidade pra atualizar").
async function t17_carregarTudo() {
  const tudo = await api.get(`/api/composicao-preco/tudo?projeto_id=${state.projetoId}`);
  t17_composicaoAtual = tudo.composicao;
  t17_popularFiltroFab();
  t17_itemPorId = new Map();
  Object.values(tudo.composicao.blocos).flat().forEach(it => t17_itemPorId.set(it.id, it));
  return tudo;
}

function t17_renderDadosProjeto(p) {
  const campo = (rot, val) => `<div><label class="lbl">${rot}</label><input type="text" value="${val ?? '—'}" disabled></div>`;
  document.getElementById('t17_dadosProjeto').innerHTML =
    campo('Código Projeto', p.codigo_projeto) +
    campo('Cidade da Instalação', p.cidade_instalacao) +
    campo('Tensão Elétrica de Comando', p.tensao_comando) +
    campo('Tensão Elétrica da Instalação', p.tensao_equipamentos);
}

function t17_popularFiltroCC() {
  const sel = document.getElementById('t17_filtroCC');
  const atual = sel.value;
  sel.innerHTML = '<option value="">— Todos —</option>' +
    t17_centrosCusto.map(c => `<option value="${c.id}">${c.codigo} — ${c.descricao || ''}</option>`).join('');
  sel.value = atual;
}

function t17_popularFiltroTipo() {
  const sel = document.getElementById('t17_filtroTipo');
  const atual = sel.value;
  sel.innerHTML = '<option value="">Todos</option>' +
    T17_BLOCOS.map(b => `<option value="${b}">${b}</option>`).join('');
  sel.value = atual;
}

function t17_popularFiltroFab() {
  const sel = document.getElementById('t17_filtroFab');
  const atual = sel.value;
  const fabs = new Set();
  Object.values(t17_composicaoAtual.blocos).forEach(itens =>
    itens.forEach(it => { if (it.fabricante) fabs.add(it.fabricante); }));
  sel.innerHTML = '<option value="">— Todos —</option>' +
    [...fabs].sort().map(f => `<option value="${f}">${f}</option>`).join('');
  sel.value = atual;
}

function t17_queryFiltrosAtivos() {
  const fab = document.getElementById('t17_filtroFab').value;
  const cc = document.getElementById('t17_filtroCC').value;
  const tipo = document.getElementById('t17_filtroTipo').value;
  const p = new URLSearchParams({ projeto_id: state.projetoId });
  if (fab) p.set('fabricante', fab);
  if (cc) p.set('centro_custo_id', cc);
  if (tipo) p.set('bloco', tipo);
  return p.toString();
}

async function t17_imprimirListaMateriais() {
  const linhas = await api.get(`/api/composicao-preco/lista-materiais?${t17_queryFiltrosAtivos()}`);
  const el = document.getElementById('t17_listaMateriaisPrint');
  el.innerHTML = `
    <h2 style="margin-bottom:12px;">LISTA DE MATERIAIS E EQUIPAMENTOS</h2>
    <table class="list" style="width:100%;">
      <thead><tr><th style="width:50px;">Nº/Item</th><th>Descrição</th><th style="width:120px;">Fabricante</th>
        <th style="width:120px;">Centro de Custo</th><th style="width:70px;">Unid.</th><th style="width:80px;">Quantidade</th></tr></thead>
      <tbody>${linhas.map(l => `<tr>
        <td>${l.numero}</td><td>${l.descricao}</td><td>${l.fabricante || '—'}</td>
        <td>${l.centro_custo || '—'}</td><td>${l.unidade || '—'}</td><td>${l.quantidade ?? '—'}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  document.body.classList.add('t17-imprimindo-lista');
  window.print();
  document.body.classList.remove('t17-imprimindo-lista');
}

function t17_passaFiltro(it) {
  const fab = document.getElementById('t17_filtroFab').value;
  const cc = document.getElementById('t17_filtroCC').value;
  if (fab && it.fabricante !== fab) return false;
  if (cc && String(it.centro_custo_id || '') !== cc) return false;
  return true;
}

function t17_renderBlocosFiltrado() {
  const tipo = document.getElementById('t17_filtroTipo').value;
  document.querySelectorAll('#t17_blocos [data-bloco-wrap]').forEach(el => {
    el.style.display = (!tipo || tipo === el.dataset.blocoWrap) ? '' : 'none';
  });
  document.querySelectorAll('#t17_blocos tr[data-item-id]').forEach(tr => {
    const it = t17_itemPorId.get(Number(tr.dataset.itemId));
    tr.style.display = (it && t17_passaFiltro(it)) ? '' : 'none';
  });
}

let t17_itemPorId = new Map();

async function t17_salvarMargemNegociacao() {
  const v = parseNumBR(document.getElementById('t17_margemNegociacao').value) / 100;
  await api.put(`/api/composicao-preco/margem-negociacao?projeto_id=${state.projetoId}`, { percentual: v });
  t17_carregar();
}

// ---------------- Blocos ----------------

function t17_htmlOpcoesFatores(selecionado) {
  return '<option value="">—</option>' + t17_fatores.map(f =>
    `<option value="${f.id}" ${f.id === selecionado ? 'selected' : ''}>${f.codigo} — ${f.descricao}</option>`).join('');
}
function t17_htmlOpcoesCC(selecionado, bloco) {
  const filtrados = t17_centrosCusto.filter(c => !c.bloco_composicao || c.bloco_composicao === bloco);
  return '<option value="">—</option>' + filtrados.map(c =>
    `<option value="${c.id}" ${c.id === selecionado ? 'selected' : ''}>${c.codigo} — ${c.descricao || ''}</option>`).join('');
}

// Bloco "Comissões por Indicação de Negócio": não faz sentido esse item ter Centro de Custo
// próprio (é uma linha agregada por fabricante, não pertence a bloco nenhum de material/serviço).
// Esse seletor vira "Agrupar valor em" — só pra Tabela de Orçamento (ver
// t17_calcularTabelaOrcamento): soma o valor da comissão, sem nunca expor a linha em si, dentro
// do Centro de Custo escolhido aqui. Só oferece Centro de Custo que já tem uso (item lançado) em
// algum bloco que não seja o próprio Comissões — o bloco de destino é descoberto automaticamente
// pelo backend a partir desse uso existente, não depende mais de um campo de cadastro separado
// (aprovado 2026-08-10 — antes dependia de CentroCusto.bloco_composicao, campo sem nenhuma tela
// de cadastro, então nunca tinha valor preenchido e o dropdown ficava sempre vazio).
function t17_centrosCustoComUso() {
  const usados = new Set();
  if (t17_composicaoAtual) {
    Object.entries(t17_composicaoAtual.blocos).forEach(([bloco, itens]) => {
      if (bloco === T17_BLOCO_COMISSOES) return;
      itens.forEach(it => { if (it.centro_custo_id) usados.add(it.centro_custo_id); });
    });
  }
  return usados;
}
function t17_htmlOpcoesCCAgrupar(selecionado) {
  const usados = t17_centrosCustoComUso();
  const filtrados = t17_centrosCusto.filter(c => usados.has(c.id));
  return '<option value="">— não expor no orçamento —</option>' + filtrados.map(c =>
    `<option value="${c.id}" ${c.id === selecionado ? 'selected' : ''}>${c.codigo} — ${c.descricao || ''}</option>`).join('');
}

// Larguras únicas, repetidas em TODAS as tabelas de bloco (colgroup + table-layout:fixed) — sem
// isso cada <table> recalcula a própria largura de coluna a partir do conteúdo e as colunas saem
// desalinhadas entre um bloco e outro (bug real reportado 2026-08-05).
// Colunas redimensionáveis (aprovado 2026-08-09, mesmo padrão de t9_ativarRedimensionamento):
// largura persiste em localStorage, caindo nos valores padrão abaixo se nada foi salvo ainda.
// A coluna Descrição (índice 1) recebe largura fixa (260) — com table-layout:fixed + width:auto uma
// coluna sem largura colapsaria (aprovado 2026-08-13).
const T17_LARGURAS_COL_PADRAO = [30, 260, 100, 200, 200, 80, 100, 100, 130, 90, 110, 150, 150, 170, 30];
function t17_larguraColAtual() {
  const salvo = JSON.parse(localStorage.getItem('ct_t17_larguras') || '{}');
  return T17_LARGURAS_COL_PADRAO.map((w, i) => salvo[i] || w);
}
function t17_colgroup() {
  return '<colgroup>' + t17_larguraColAtual().map(w => w ? `<col style="width:${w}px;">` : '<col>').join('') + '</colgroup>';
}

// Colunas redimensionáveis: arrastar a borda de uma coluna ajusta SÓ aquela coluna (as da esquerda
// nunca se movem, table-layout:fixed) e aplica a MESMA largura à mesma coluna em TODOS os blocos ao
// vivo — as colunas são idênticas entre os blocos (aprovado 2026-08-13). A largura é salva por
// índice de coluna (localStorage) e restaurada em todos os blocos ao recarregar a tela.
function t17_ativarRedimensionamento() {
  const tabelas = Array.from(document.querySelectorAll('#t17_blocos table.list'));
  if (!tabelas.length) return;
  tabelas.forEach(tabela => {
    const row1 = tabela.querySelector('thead tr');
    if (!row1) return;
    Array.from(row1.children).forEach((th, idx) => {
      th.style.position = 'relative';
      const handle = document.createElement('div');
      handle.style.cssText = 'position:absolute;top:0;right:0;width:6px;height:100%;cursor:col-resize;user-select:none;z-index:2;';
      th.appendChild(handle);
      handle.addEventListener('mousedown', e => {
        e.preventDefault(); e.stopPropagation();
        const startX = e.pageX;
        const col = tabela.querySelectorAll('colgroup col')[idx];
        const startW = col?.getBoundingClientRect().width || 0;
        const onMove = ev => {
          const largura = Math.max(30, startW + (ev.pageX - startX));
          // aplica a MESMA largura à mesma coluna em TODOS os blocos ao vivo (colunas idênticas)
          tabelas.forEach(t => { const c = t.querySelectorAll('colgroup col')[idx]; if (c) c.style.width = largura + 'px'; });
        };
        const onUp = () => {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          const larguras = JSON.parse(localStorage.getItem('ct_t17_larguras') || '{}');
          larguras[idx] = Math.round(col.getBoundingClientRect().width);
          localStorage.setItem('ct_t17_larguras', JSON.stringify(larguras));
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
      });
    });
  });
}

// Ordena os itens de um bloco por Centro de Custo (código, os sem Centro de Custo ficam no fim) e,
// dentro do mesmo Centro de Custo, por Descrição (aprovado 2026-08-09).
function t17_ordenarItens(itens) {
  return [...itens].sort((a, b) => {
    const ca = a.centro_custo_codigo || '';
    const cb = b.centro_custo_codigo || '';
    if (!ca && cb) return 1;
    if (ca && !cb) return -1;
    const cmp = ca.localeCompare(cb, undefined, { numeric: true });
    if (cmp !== 0) return cmp;
    return (a.descricao || '').localeCompare(b.descricao || '');
  });
}

// "Painéis Térmicos" tem ordem própria com significado (parede/teto -> isolamento de piso ->
// portas, igual ao resumo da Tela 7) já calculada pelo backend em cada sincronização (ver
// composicao_preco.sincronizar_paineis_portas, campo `ordem`) -- ordenar por Centro de
// Custo/Descrição aqui embaralharia essa sequência. Mesmo bloco único, mesma tabela, só muda o
// critério de ordenação das linhas dentro dele (aprovado 2026-08-09).
function t17_ordenarPorOrdemDoBackend(itens) {
  return [...itens].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
}

// Estado de retração dos blocos (só em memória, não persiste entre sessões) — sobrevive ao
// redesenho da tabela inteira a cada edição de campo (ver t17_renderBlocos), senão o bloco que o
// usuário retraiu voltava a expandir sozinho a cada salvamento.
const t17_blocosRetraidos = new Set();

function t17_renderBlocos(composicao) {
  t17_composicaoAtual = composicao;
  const el = document.getElementById('t17_blocos');
  el.innerHTML = T17_BLOCOS.map(bloco => {
    const itens = composicao.blocos[bloco] || [];
    const importavel = T17_BLOCOS_IMPORTAVEIS[bloco];
    const retraido = t17_blocosRetraidos.has(bloco);
    return `
    <div data-bloco-wrap="${bloco}" style="background:var(--surface-2,#fff);border:1px solid var(--line);border-radius:6px;padding:12px;margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-weight:bold;">${bloco.toUpperCase()}</span>
        <span class="no-print" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          <span class="btn-text" data-toggle-bloco="${bloco}">${retraido ? '▸ Expandir' : '▾ Retrair'}</span>
          ${importavel ? `<input type="file" id="t17_import_${t17_slug(bloco)}" accept=".xlsx,.xls" style="display:none;">
          <span class="btn-text" data-import-bloco="${bloco}">Importar arquivo</span>` : ''}
          <span class="btn-text" data-add-bloco="${bloco}">+ Item</span>
          <span style="border-left:1px solid var(--line);height:16px;margin:0 2px;"></span>
          <select data-bloco-cc-sel="${bloco}" style="font-size:10px;max-width:160px;padding:1px 3px;">${t17_htmlOpcoesCC(null, bloco)}</select>
          <span class="btn-text" data-aplicar-cc-bloco="${bloco}">Aplicar CC ao Bloco</span>
          <select data-bloco-fv-sel="${bloco}" style="font-size:10px;max-width:160px;padding:1px 3px;">${t17_htmlOpcoesFatores(null)}</select>
          <span class="btn-text" data-aplicar-fv-bloco="${bloco}">Aplicar FV ao Bloco</span>
        </span>
      </div>
      <div style="overflow-x:auto;${retraido ? 'display:none;' : ''}" data-bloco-corpo="${bloco}">
      <table class="list" style="min-width:1300px;font-size:11px;table-layout:fixed;width:auto;">
        ${t17_colgroup()}
        <thead><tr style="text-align:center;">
          <th style="text-align:center;" title="Considerar no orçamento">✓</th>
          <th style="text-align:center;">Descrição</th><th style="text-align:center;">Fabricante</th><th style="text-align:center;">${bloco === T17_BLOCO_COMISSOES ? 'Agrupar valor em' : 'Centro de Custo'}</th><th style="text-align:center;">Fator de venda</th>
          <th style="text-align:center;">Quantidade</th><th style="text-align:center;">Custo Unit. (R$)</th><th style="text-align:center;">Custo Total (R$)</th>
          <th style="text-align:center;">Margem Contribuição (R$)</th><th style="text-align:center;">Impostos (R$)</th><th style="text-align:center;">Comissões (R$)</th>
          <th style="text-align:center;">Valor unit. venda S/ Contribuição (R$)</th>
          <th style="text-align:center;">Valor total venda S/ Contribuição (R$)</th>
          <th style="text-align:center;">Valor Venda c/ Margem Contribuição e Negociação (R$)</th><th></th>
        </tr></thead>
        <tbody>
          ${(bloco === 'Painéis Térmicos' ? t17_ordenarPorOrdemDoBackend(itens) : t17_ordenarItens(itens)).map(it => t17_linhaItem(it, bloco)).join('')}
        </tbody>
      </table>
      </div>
    </div>`;
  }).join('');
  t17_ativarRedimensionamento();

  el.querySelectorAll('[data-toggle-bloco]').forEach(b => b.addEventListener('click', () => {
    const bloco = b.dataset.toggleBloco;
    const corpo = el.querySelector(`[data-bloco-corpo="${bloco}"]`);
    if (t17_blocosRetraidos.has(bloco)) {
      t17_blocosRetraidos.delete(bloco);
      corpo.style.display = '';
      b.textContent = '▾ Retrair';
    } else {
      t17_blocosRetraidos.add(bloco);
      corpo.style.display = 'none';
      b.textContent = '▸ Expandir';
    }
  }));
  el.querySelectorAll('[data-add-bloco]').forEach(b => b.addEventListener('click', () => t17_addItem(b.dataset.addBloco)));
  el.querySelectorAll('[data-import-bloco]').forEach(b => b.addEventListener('click', () => {
    document.getElementById(`t17_import_${t17_slug(b.dataset.importBloco)}`).click();
  }));
  el.querySelectorAll('input[type=file][id^=t17_import_]').forEach(inp => {
    const bloco = T17_BLOCOS.find(x => t17_slug(x) === inp.id.replace('t17_import_', ''));
    inp.addEventListener('change', () => t17_importarArquivo(inp, bloco));
  });
  el.querySelectorAll('[data-aplicar-cc-bloco]').forEach(b => b.addEventListener('click', () => t17_aplicarCCBloco(b.dataset.aplicarCcBloco)));
  el.querySelectorAll('[data-aplicar-fv-bloco]').forEach(b => b.addEventListener('click', () => t17_aplicarFVBloco(b.dataset.aplicarFvBloco)));
  el.querySelectorAll('[data-item-id]').forEach(tr => {
    tr.querySelectorAll('[data-campo]').forEach(inp =>
      inp.addEventListener('change', () => t17_salvarItem(tr.dataset.itemId, inp)));
    const btnDel = tr.querySelector('[data-del-item]');
    if (btnDel) btnDel.addEventListener('click', () => t17_excluirItem(tr.dataset.itemId));
  });
  t17_renderBlocosFiltrado();
}

async function t17_aplicarCCBloco(bloco) {
  const sel = document.querySelector(`[data-bloco-cc-sel="${bloco}"]`);
  const ccId = sel ? Number(sel.value) || null : null;
  if (!ccId) { alert('Selecione um Centro de Custo antes de aplicar.'); return; }
  const itens = (t17_composicaoAtual?.blocos[bloco] || []);
  if (!itens.length) return;
  for (const it of itens) await api.put(`/api/composicao-preco/item/${it.id}`, { centro_custo_id: ccId });
  const tudo = await t17_carregarTudo();
  t17_renderBlocos(tudo.composicao);
  t17_renderResumo(tudo.resumo);
  t17_renderTabelaOrcamento(tudo.composicao);
  t17_renderComissionamento(tudo.comissionamento);
  t17_renderDre(tudo.dre);
}

async function t17_aplicarFVBloco(bloco) {
  const sel = document.querySelector(`[data-bloco-fv-sel="${bloco}"]`);
  const fvId = sel ? Number(sel.value) || null : null;
  if (!fvId) { alert('Selecione um Fator de Venda antes de aplicar.'); return; }
  const itens = (t17_composicaoAtual?.blocos[bloco] || []);
  if (!itens.length) return;
  for (const it of itens) await api.put(`/api/composicao-preco/item/${it.id}`, { fator_id: fvId });
  const tudo = await t17_carregarTudo();
  t17_renderBlocos(tudo.composicao);
  t17_renderResumo(tudo.resumo);
  t17_renderTabelaOrcamento(tudo.composicao);
  t17_renderComissionamento(tudo.comissionamento);
  t17_renderDre(tudo.dre);
}

function t17_slug(s) { return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '-'); }

function t17_linhaItem(it, bloco) {
  // "sistema" (sincronizado da Tela 7/Compilação) e "default" (copiado do mestre) nunca têm
  // descrição digitável — só "manual" (criado pelo usuário nesse projeto).
  const readOnly = it.origem === 'sistema' || it.origem === 'default';
  // Quantidade: só "sistema" (auto-calculada, ex. nº de forçadores/portas) é travada — itens
  // "manual" e "default" (padrão) precisam ter a quantidade editável (aprovado 2026-08-10).
  const qtdReadOnly = it.origem === 'sistema';
  // Bloco Comissões por Indicação de Negócio: Custo Unit. é 100% resultado de um percentual
  // sobre o custo de outro item (ver backend sincronizar_comissoes_indicacao) — nunca digitável,
  // senão o usuário edita um valor que a próxima sincronização sobrescreve na hora (bug real
  // reportado 2026-08-05).
  const custoTravado = bloco === T17_BLOCO_COMISSOES;
  const custoUnitFmt = Number(it.custo_unitario || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // Checkbox "considerar no orçamento" (aprovado 2026-08-12): desmarcado tira o item do Resumo
  // por Bloco/Tabela de Orçamento/DRE/Comissionamento, mas o item continua aqui, calculado
  // normalmente — só esmaecido visualmente pra indicar que está fora do orçamento.
  const incluido = it.incluir_orcamento !== false;
  return `<tr data-item-id="${it.id}" style="${incluido ? '' : 'opacity:0.5;'}">
    <td style="text-align:center;"><input type="checkbox" data-campo="incluir_orcamento" ${incluido ? 'checked' : ''}></td>
    <td>${readOnly ? it.descricao : `<input data-campo="descricao" value="${it.descricao.replace(/"/g, '&quot;')}" style="width:100%;box-sizing:border-box;">`}</td>
    <td><input data-campo="fabricante" value="${(it.fabricante || '').replace(/"/g, '&quot;')}" style="width:100%;box-sizing:border-box;" ${it.origem === 'sistema' ? 'disabled' : ''}></td>
    <td><select data-campo="centro_custo_id" style="width:100%;box-sizing:border-box;">${bloco === T17_BLOCO_COMISSOES ? t17_htmlOpcoesCCAgrupar(it.centro_custo_id) : t17_htmlOpcoesCC(it.centro_custo_id, bloco)}</select></td>
    <td><select data-campo="fator_id" style="width:100%;box-sizing:border-box;">${t17_htmlOpcoesFatores(it.fator_id)}</select></td>
    <td>${qtdReadOnly ? it.quantidade : `<input data-campo="quantidade" value="${it.quantidade}" style="width:100%;box-sizing:border-box;">`}</td>
    <td>${custoTravado ? t17_brl(it.custo_unitario) : `<input data-campo="custo_unitario" value="${custoUnitFmt}" style="width:100%;box-sizing:border-box;">`}</td>
    <td data-calc="custo_total" style="text-align:right;">${t17_brl(it.custo_total)}</td>
    <td data-calc="margem_contribuicao" style="text-align:right;">${t17_brl(it.margem_contribuicao)}</td>
    <td data-calc="impostos" style="text-align:right;">${t17_brl(it.impostos)}</td>
    <td data-calc="comissoes" style="text-align:right;">${t17_brl(it.comissoes)}</td>
    <td data-calc="valor_unit_venda" style="text-align:right;">${t17_brl(it.valor_unit_venda)}</td>
    <td data-calc="valor_total_venda" style="text-align:right;">${t17_brl(it.valor_total_venda)}</td>
    <td data-calc="valor_venda_negociacao" style="text-align:right;font-weight:bold;">${t17_brl(it.valor_venda_negociacao)}</td>
    <td>${it.origem !== 'sistema' ? '<span class="btn-text danger" data-del-item>x</span>' : ''}</td>
  </tr>`;
}

async function t17_addItem(bloco) {
  await api.post(`/api/composicao-preco/item?projeto_id=${state.projetoId}`,
    { bloco, descricao: 'Novo item', quantidade: 1, custo_unitario: 0 });
  t17_carregar();
}

async function t17_salvarItem(itemId, inp) {
  const campo = inp.dataset.campo;
  let valor = campo === 'incluir_orcamento' ? inp.checked : inp.value;
  if (campo === 'custo_unitario') valor = parseNumBRMilhar(valor);
  else if (campo === 'quantidade') valor = parseNumBR(valor);
  if (campo === 'centro_custo_id' || campo === 'fator_id') valor = valor ? Number(valor) : null;
  await api.put(`/api/composicao-preco/item/${itemId}`, { [campo]: valor });
  if (campo === 'custo_unitario' && valor != null) {
    inp.value = valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  // 1 chamada só (composição + resumo + comissionamento + dre já calculados juntos no backend —
  // ver /tudo) em vez de 3-4 GETs separados, cada um recomputando tudo do zero (bug real de
  // lentidão reportado 2026-08-05: "a porra da tela leva uma eternidade pra atualizar").
  const tudo = await t17_carregarTudo();
  t17_atualizarLinhaCalculada(Number(itemId), tudo.composicao);
  // "Comissões por Indicação de Negócio" é 100% derivado (agregado por fabricante) — editar
  // custo/quantidade/fator de QUALQUER item com Fator tipo Comissão recalcula esse bloco inteiro,
  // não só a linha que foi editada (ficava estático até recarregar a página, bug real reportado
  // 2026-08-05).
  t17_atualizarBlocoDerivado(T17_BLOCO_COMISSOES, tudo.composicao);
  t17_renderResumo(tudo.resumo);
  t17_renderTabelaOrcamento(tudo.composicao);
  // Comissionamento (comissão REAL do vendedor) também ficava com o valor antigo até recarregar
  // a página inteira — esquecido nessa refatoração, bug real reportado 2026-08-05 ("como pode a
  // comissão estar errada" — Reinaldo mostrando 1% de um total de 5 dígitos atrás enquanto o
  // Total Geral já tinha mudado 30x).
  t17_renderComissionamento(tudo.comissionamento);
  t17_renderDre(tudo.dre);
}

// Atualiza só as células calculadas (custo total/margem/impostos/comissão/vlr. venda) da linha
// editada, sem redesenhar a tabela inteira — redesenhar tudo a cada campo destruía os inputs de
// outras linhas/campos que o usuário ainda estivesse preenchendo (perdia a digitação, bug real
// reportado 2026-08-05: "a partir do segundo lançamento não fez os cálculos").
const T17_BLOCO_COMISSOES = 'Comissões por Indicação de Negócio';

function t17_atualizarLinhaCalculada(itemId, composicao) {
  let item = null;
  for (const itens of Object.values(composicao.blocos)) {
    const achado = itens.find(i => i.id === itemId);
    if (achado) { item = achado; break; }
  }
  if (!item) return;
  const tr = document.querySelector(`#t17_blocos tr[data-item-id="${itemId}"]`);
  if (!tr) return;
  tr.style.opacity = item.incluir_orcamento === false ? '0.5' : '';
  ['custo_total', 'margem_contribuicao', 'impostos', 'comissoes',
   'valor_unit_venda', 'valor_total_venda', 'valor_venda_negociacao'].forEach(c => {
    const td = tr.querySelector(`[data-calc="${c}"]`);
    if (td) td.textContent = t17_brl(item[c]);
  });
}

function t17_atualizarBlocoDerivado(bloco, composicao) {
  const wrap = document.querySelector(`[data-bloco-wrap="${CSS.escape(bloco)}"]`);
  const tbody = wrap ? wrap.querySelector('tbody') : null;
  if (!tbody) return;
  const itens = composicao.blocos[bloco] || [];
  itens.forEach(it => t17_itemPorId.set(it.id, it));
  tbody.innerHTML = itens.map(it => t17_linhaItem(it, bloco)).join('');
  tbody.querySelectorAll('tr[data-item-id]').forEach(tr => {
    tr.querySelectorAll('[data-campo]').forEach(inp =>
      inp.addEventListener('change', () => t17_salvarItem(tr.dataset.itemId, inp)));
    const btnDel = tr.querySelector('[data-del-item]');
    if (btnDel) btnDel.addEventListener('click', () => t17_excluirItem(tr.dataset.itemId));
  });
  t17_renderBlocosFiltrado();
}

async function t17_excluirItem(itemId) {
  if (!confirm('Excluir este item?')) return;
  await api.del(`/api/composicao-preco/item/${itemId}`);
  t17_carregar();
}

async function t17_importarArquivo(inp, bloco) {
  const file = inp.files[0];
  if (!file) return;
  const preview = await api.upload('/api/materiais-import/preview', file);
  const comErro = preview.itens.filter(i => i.erros.length);
  if (comErro.length) {
    alert(`${comErro.length} linha(s) com erro não serão importadas:\n` +
      comErro.map(i => `- ${i.descricao || '(sem descrição)'}: ${i.erros.join('; ')}`).join('\n'));
  }
  const r = await api.post(`/api/materiais-import/confirmar?projeto_id=${state.projetoId}`, { itens: preview.itens });
  alert(`${r.itens_importados} item(ns) importado(s).`);
  inp.value = '';
  t17_carregar();
}

// ---------------- Resumo ----------------

function t17_renderResumo(resumo) {
  const el = document.getElementById('t17_resumo');
  let html = '<table class="list" style="max-width:900px;"><thead><tr><th>Centro de Custo</th><th style="width:110px;">Custo Total</th><th style="width:110px;">Impostos</th><th style="width:110px;">Comissões</th><th style="width:130px;">Vlr. c/ Negociação</th></tr></thead><tbody>';
  resumo.blocos.forEach(b => {
    if (!b.centros_custo.length) return;
    html += `<tr style="background:var(--surface-1,#f4f4f4);"><td colspan="5" style="font-weight:bold;">${b.bloco.toUpperCase()}</td></tr>`;
    b.centros_custo.forEach(cc => {
      const rotulo = cc.centro_custo ? `${cc.centro_custo} — ${cc.descricao || ''}` : cc.descricao;
      html += `<tr><td>${rotulo}</td><td style="text-align:right;">${t17_brl(cc.custo_total)}</td><td style="text-align:right;">${t17_brl(cc.impostos)}</td><td style="text-align:right;">${t17_brl(cc.comissoes)}</td><td style="text-align:right;">${t17_brl(cc.valor_venda_negociacao)}</td></tr>`;
    });
    html += `<tr><td style="font-weight:bold;">Subtotal ${b.bloco}</td><td style="text-align:right;font-weight:bold;">${t17_brl(b.subtotal.custo_total)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(b.subtotal.impostos)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(b.subtotal.comissoes)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(b.subtotal.valor_venda_negociacao)}</td></tr>`;
  });
  const tg = resumo.total_geral;
  html += `<tr style="border-top:2px solid var(--accent);"><td style="font-weight:bold;">TOTAL GERAL</td><td style="text-align:right;font-weight:bold;">${t17_brl(tg.custo_total)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(tg.impostos)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(tg.comissoes)}</td><td style="text-align:right;font-weight:bold;">${t17_brl(tg.valor_venda_negociacao)}</td></tr>`;
  html += '</tbody></table>';
  el.innerHTML = html;
}

// ---------------- Comissionamento ----------------

function t17_renderComissionamento(com) {
  const sel = document.getElementById('t17_selVendedor');
  const vinculadosIds = new Set(com.itens.map(i => i.vendedor_id));
  sel.innerHTML = t17_vendedores.filter(v => !vinculadosIds.has(v.id))
    .map(v => `<option value="${v.id}">${v.nome}</option>`).join('') || '<option value="">— nenhum vendedor cadastrado —</option>';

  const tbody = document.getElementById('t17_comissionamento');
  tbody.innerHTML = com.itens.map(i => {
    return `<tr data-vinc-id="${i.id}">
      <td>${i.vendedor_nome}</td>
      <td><input data-campo="percentual" value="${(i.percentual * 100).toFixed(1)}" style="width:60px;"> %</td>
      <td style="text-align:right;">${t17_brl(i.comissao_r)}</td>
      <td><span class="btn-text danger" data-del-vinc>x</span></td>
    </tr>`;
  }).join('');
  tbody.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async (e) => {
    const tr = e.target.closest('tr');
    await api.put(`/api/composicao-preco/comissionamento/${tr.dataset.vincId}`,
      { percentual: parseNumBR(inp.value) / 100 });
    const tudo = await t17_carregarTudo();
    t17_renderComissionamento(tudo.comissionamento);
    t17_renderDre(tudo.dre);
  }));
  tbody.querySelectorAll('[data-del-vinc]').forEach(b => b.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr');
    await api.del(`/api/composicao-preco/comissionamento/${tr.dataset.vincId}`);
    const tudo = await t17_carregarTudo();
    t17_renderComissionamento(tudo.comissionamento);
    t17_renderDre(tudo.dre);
  }));
}

async function t17_vincularVendedor() {
  const sel = document.getElementById('t17_selVendedor');
  if (!sel.value) return;
  await api.post(`/api/composicao-preco/comissionamento?projeto_id=${state.projetoId}`, { vendedor_id: Number(sel.value) });
  const tudo = await t17_carregarTudo();
  t17_renderComissionamento(tudo.comissionamento);
  t17_renderDre(tudo.dre);
}

// ---------------- DRE ----------------

function t17_renderDre(dre) {
  const linhas = [
    ['Receita de Vendas (produtos)', dre.receita_vendas, false],
    ['(+) Receita de Comissões de Indicação de Negócio', dre.receita_comissoes, false],
    ['Receita Bruta Total', dre.receita_bruta, true],
    ['(-) Impostos sobre Vendas', -dre.impostos_vendas, false],
    ['(-) Impostos sobre Comissões de Indicação', -dre.impostos_comissoes, false],
    ['Receita Líquida', dre.receita_liquida, true],
    ['(-) Custo dos Materiais/Serviços', -dre.custo, false],
    ['Lucro Bruto', dre.lucro_bruto, true],
    ['(-) Comissões', -dre.comissoes, false],
    ['Resultado do Projeto', dre.resultado, true],
  ];
  document.getElementById('t17_dre').innerHTML = linhas.map(([label, val, bold]) =>
    `<tr style="${bold ? 'border-top:1px solid var(--line);font-weight:bold;' : ''}"><td>${label}</td><td style="text-align:right;">${t17_brl(val)}</td></tr>`
  ).join('') + `<tr><td colspan="2" style="font-size:11px;color:var(--muted,#888);">Margem líquida: ${t17_pct(dre.margem_liquida_pct)}</td></tr>`;
}

// Tabela de Orçamento — visão só pra composição de preço, uso do próprio usuário na proposta
// comercial (não é impressão/exportação da Tela 10): Descrição, Unidade, Quantidade e Valor Venda
// c/ Margem Contribuição e Negociação, sem margem/imposto/comissão expostos.
// O bloco "Comissões por Indicação de Negócio" NUNCA aparece aqui como seção própria — cada item
// dele, se tiver um Centro de Custo escolhido em "Agrupar valor em", soma seu valor, por dentro,
// no total do Centro de Custo escolhido (dentro do bloco onde esse Centro de Custo já tem uso
// real). Sem CC escolhido, o valor não entra na Tabela de Orçamento (aprovado 2026-08-06; deixou
// de depender de CentroCusto.bloco_composicao em 2026-08-10 — campo sem tela de cadastro, nunca
// preenchido na prática; bug real corrigido: o valor da comissão sumia sempre, mesmo com Centro
// de Custo escolhido, mesma causa raiz do backend — ver resumo_por_bloco/valor_total_proposta em
// composicao_preco.py).
function t17_calcularTabelaOrcamento(composicao) {
  const resultado = {};
  const ordem = [];
  T17_BLOCOS.forEach(bloco => {
    if (bloco === T17_BLOCO_COMISSOES) return;
    // Checkbox "considerar no orçamento" (aprovado 2026-08-12): item desmarcado sai daqui, mas
    // continua no bloco acima normalmente.
    const brutos = (composicao.blocos[bloco] || []).filter(it => it.incluir_orcamento !== false);
    // Mesma ordenação dos blocos: por código de centro de custo (menor acima); "Painéis Térmicos"
    // mantém a ordem própria do backend (aprovado 2026-08-13).
    const ordenados = bloco === 'Painéis Térmicos' ? t17_ordenarPorOrdemDoBackend(brutos) : t17_ordenarItens(brutos);
    const itens = ordenados.map(it => ({
      descricao: it.descricao,
      unidade: it.unidade || '-',
      quantidade: it.quantidade,
      cc: it.centro_custo_descricao || null,
      valor: it.valor_venda_negociacao || 0,
    }));
    resultado[bloco] = { itens, total: itens.reduce((s, i) => s + i.valor, 0), extraPorCC: {} };
    ordem.push(bloco);
  });

  // Bloco onde cada Centro de Custo já tem uso real (primeiro bloco, na ordem de T17_BLOCOS, em
  // que aparece pelo menos 1 item com esse centro_custo_id) — mesmo critério do dropdown "Agrupar
  // valor em" (ver t17_centrosCustoComUso).
  const blocoPorCC = {};
  ordem.forEach(bloco => {
    (composicao.blocos[bloco] || []).forEach(it => {
      if (it.centro_custo_id && !(it.centro_custo_id in blocoPorCC)) blocoPorCC[it.centro_custo_id] = bloco;
    });
  });

  (composicao.blocos[T17_BLOCO_COMISSOES] || []).forEach(it => {
    if (!it.centro_custo_id || it.incluir_orcamento === false) return;
    const blocoAlvoNome = blocoPorCC[it.centro_custo_id];
    const blocoAlvo = blocoAlvoNome ? resultado[blocoAlvoNome] : null;
    if (!blocoAlvo) return;
    const ccInfo = t17_centrosCusto.find(c => c.id === it.centro_custo_id);
    const valor = it.valor_venda_negociacao || 0;
    blocoAlvo.totalComissao = (blocoAlvo.totalComissao || 0) + valor;
    const chave = (ccInfo && (ccInfo.descricao || ccInfo.codigo)) || 'Sem Centro de Custo';
    blocoAlvo.extraPorCC[chave] = (blocoAlvo.extraPorCC[chave] || 0) + valor;
  });

  return { ordem, blocos: resultado };
}

function t17_renderTabelaOrcamento(composicao) {
  const dados = t17_calcularTabelaOrcamento(composicao);
  const agrupar = document.getElementById('t17_orcAgrupar').value;
  const exibir = document.getElementById('t17_orcExibir').value;
  const isBlocoCC = agrupar === 'bloco_cc';
  const showQtd = isBlocoCC && !document.getElementById('t17_orcOcultarQtd').checked;

  const larguraQtd = showQtd
    ? '<div style="width:52px;flex-shrink:0;font-size:12px;color:var(--muted,#888);font-weight:bold;">Unid.</div>' +
      '<div style="width:64px;flex-shrink:0;font-size:12px;color:var(--muted,#888);font-weight:bold;text-align:right;">Qtd.</div>'
    : '';
  const head = '<div style="display:flex;align-items:baseline;gap:10px;padding:0 4px 8px;border-bottom:1px solid var(--line);">' +
    '<div style="flex:1;font-size:12px;color:var(--muted,#888);font-weight:bold;">Descrição</div>' +
    larguraQtd +
    '<div style="width:110px;flex-shrink:0;text-align:right;font-size:12px;color:var(--muted,#888);font-weight:bold;">Valor</div>' +
  '</div>';

  function linha(label, valor, opts) {
    opts = opts || {};
    const qtdCols = showQtd
      ? `<div style="width:52px;flex-shrink:0;font-size:${opts.fs || 13}px;color:var(--muted,#888);">${opts.u || ''}</div>` +
        `<div style="width:64px;flex-shrink:0;font-size:${opts.fs || 13}px;color:var(--muted,#888);text-align:right;">${opts.q !== undefined ? opts.q : ''}</div>`
      : '';
    return `<div style="display:flex;align-items:baseline;gap:10px;padding:${opts.pad || '4px 4px 4px 16px'};">` +
      `<div style="flex:1;min-width:0;font-size:${opts.fs || 13}px;font-weight:${opts.bold ? 'bold' : 'normal'};word-break:break-word;">${label}</div>` +
      qtdCols +
      `<div style="width:110px;flex-shrink:0;text-align:right;font-size:${opts.fs || 13}px;font-weight:${opts.bold ? 'bold' : 'normal'};color:${opts.muted ? 'var(--muted,#888)' : 'inherit'};white-space:nowrap;">${valor}</div>` +
    '</div>';
  }

  let totalProposta = 0;
  const blocosHtml = dados.ordem.map(bloco => {
    const info = dados.blocos[bloco];
    totalProposta += info.total + (info.totalComissao || 0);
    let body = '';

    if (isBlocoCC) {
      const porCC = {};
      const ordemCC = [];
      info.itens.forEach(it => {
        const cc = it.cc || 'Sem Centro de Custo';
        if (!porCC[cc]) { porCC[cc] = []; ordemCC.push(cc); }
        porCC[cc].push(it);
      });
      Object.keys(info.extraPorCC).forEach(cc => {
        if (!porCC[cc]) { porCC[cc] = []; ordemCC.push(cc); }
      });

      body = ordemCC.map(cc => {
        const subtotalItens = porCC[cc].reduce((s, it) => s + it.valor, 0);
        const comissaoCC = info.extraPorCC[cc] || 0;
        const subtotal = subtotalItens + comissaoCC;
        const itensHtml = porCC[cc].map(it =>
          linha(it.descricao, exibir === 'individual' ? t17_brl(it.valor) : '', { u: it.unidade, q: it.quantidade })
        ).join('');
        // Subtotal sempre visível quando há comissão no CC; em total_bloco mostra mesmo sem comissão
        const subtotalHtml = (exibir === 'total_bloco' || comissaoCC > 0)
          ? linha('Subtotal — ' + cc, t17_brl(subtotal), { fs: 12, muted: true })
          : '';
        return `<div style="padding:6px 4px 0;font-size:12px;color:var(--muted,#888);">${cc}</div>` + itensHtml + subtotalHtml;
      }).join('');
    }

    const header = '<div style="display:flex;align-items:baseline;gap:10px;padding:10px 4px 6px;border-top:1px solid var(--line);">' +
      `<div style="flex:1;min-width:0;font-size:14px;font-weight:bold;">${bloco}</div>` +
      (showQtd ? '<div style="width:52px;flex-shrink:0;"></div><div style="width:64px;flex-shrink:0;"></div>' : '') +
      `<div style="width:110px;flex-shrink:0;text-align:right;font-size:14px;font-weight:bold;white-space:nowrap;">${t17_brl(info.total + (info.totalComissao || 0))}</div>` +
    '</div>';

    return header + body;
  }).join('');

  const rodape = '<div style="display:flex;align-items:baseline;gap:10px;padding:14px 4px;margin-top:8px;border-top:2px solid var(--line);">' +
    '<div style="flex:1;min-width:0;font-size:15px;font-weight:bold;">Valor total da proposta</div>' +
    (showQtd ? '<div style="width:52px;flex-shrink:0;"></div><div style="width:64px;flex-shrink:0;"></div>' : '') +
    `<div style="width:110px;flex-shrink:0;text-align:right;font-size:15px;font-weight:bold;white-space:nowrap;">${t17_brl(totalProposta)}</div>` +
  '</div>';

  document.getElementById('t17_tabelaOrcamento').innerHTML = head + blocosHtml + rodape;
}

function t17_atualizarVisibilidadeFiltrosOrcamento() {
  const isBlocoCC = document.getElementById('t17_orcAgrupar').value === 'bloco_cc';
  document.getElementById('t17_orcWrapExibir').style.display = isBlocoCC ? '' : 'none';
  const chk = document.getElementById('t17_orcOcultarQtd');
  chk.disabled = !isBlocoCC;
  document.getElementById('t17_orcWrapOcultar').style.opacity = isBlocoCC ? '1' : '0.4';
}

// Condições de Pagamento — agenda de Sinal de Negócio + parcelas sobre o Valor Total da Proposta
// (ver backend composicao_preco.gerar_agenda_pagamento). Data/Valor de cada linha gerada ficam
// editáveis manualmente depois — editar uma linha não recalcula as outras (aprovado 2026-08-06).
async function t17_carregarCondicaoPagamento() {
  const agenda = await api.get(`/api/composicao-preco/condicao-pagamento?projeto_id=${state.projetoId}`);
  if (agenda.config) {
    document.getElementById('t17_cpSinalPct').value = (agenda.config.percentual_sinal * 100).toFixed(1);
    document.getElementById('t17_cpDataSinal').value = agenda.config.data_sinal || '';
    document.getElementById('t17_cpQtdParcelas').value = agenda.config.quantidade_parcelas;
    document.getElementById('t17_cpPeriodicidade').value = agenda.config.periodicidade_dias;
  }
  t17_renderCondicaoPagamento(agenda);
}

function t17_renderCondicaoPagamento(agenda) {
  const tbody = document.getElementById('t17_condicaoPagamento');
  tbody.innerHTML = agenda.parcelas.map(p => `
    <tr data-parcela-id="${p.id}">
      <td>${p.descricao}</td>
      <td><input type="date" data-campo="data" value="${p.data}" style="width:100%;box-sizing:border-box;"></td>
      <td><input data-campo="valor" value="${Number(p.valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}" style="width:100%;box-sizing:border-box;"></td>
    </tr>`).join('') +
    (agenda.parcelas.length ? `<tr style="font-weight:bold;"><td>Total</td><td></td><td>${t17_brl(agenda.total)}</td></tr>` : '');
  tbody.querySelectorAll('[data-campo]').forEach(inp =>
    inp.addEventListener('change', () => t17_salvarParcelaPagamento(inp.closest('tr').dataset.parcelaId, inp)));
}

async function t17_salvarParcelaPagamento(parcelaId, inp) {
  const campo = inp.dataset.campo;
  let valor = inp.value;
  if (campo === 'valor') {
    valor = parseNumBRMilhar(valor);
    inp.value = valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  await api.put(`/api/composicao-preco/condicao-pagamento/parcela/${parcelaId}`, { [campo]: valor });
  const agenda = await api.get(`/api/composicao-preco/condicao-pagamento?projeto_id=${state.projetoId}`);
  t17_renderCondicaoPagamento(agenda);
}

// "Atualizar": se o Valor Total da Proposta estiver zerado (usuário zerou os dados da
// composição), apaga a agenda existente — não faz sentido manter parcelas sobre um valor que não
// existe mais. Se tiver valor, gera/regera a agenda normalmente (aprovado 2026-08-06).
async function t17_atualizarAgendaPagamento() {
  const dadosOrc = t17_calcularTabelaOrcamento(t17_composicaoAtual);
  const totalProposta = dadosOrc.ordem.reduce((s, bloco) => s + dadosOrc.blocos[bloco].total + (dadosOrc.blocos[bloco].totalComissao || 0), 0);
  const existente = document.querySelectorAll('#t17_condicaoPagamento [data-parcela-id]').length;

  if (totalProposta === 0) {
    if (!existente) { alert('Valor Total da Proposta é zero — nada a atualizar.'); return; }
    if (!confirm('Valor Total da Proposta está zerado — a agenda de pagamento será apagada. Continuar?')) return;
    await api.del(`/api/composicao-preco/condicao-pagamento?projeto_id=${state.projetoId}`);
    t17_renderCondicaoPagamento({ parcelas: [], total: 0 });
    return;
  }

  const percentual_sinal = parseNumBR(document.getElementById('t17_cpSinalPct').value) / 100;
  const data_sinal = document.getElementById('t17_cpDataSinal').value;
  const quantidade_parcelas = parseInt(document.getElementById('t17_cpQtdParcelas').value, 10);
  const periodicidade_dias = parseInt(document.getElementById('t17_cpPeriodicidade').value, 10);
  if (!data_sinal || !quantidade_parcelas || !periodicidade_dias) {
    alert('Preencha Data do Sinal, Quantidade de Parcelas e Periodicidade.');
    return;
  }
  if (existente && !confirm('Já existe uma agenda gerada — atualizar substitui todas as linhas (inclusive as editadas manualmente). Continuar?')) return;
  const agenda = await api.post(`/api/composicao-preco/condicao-pagamento/gerar-agenda?projeto_id=${state.projetoId}`,
    { percentual_sinal, data_sinal, quantidade_parcelas, periodicidade_dias });
  t17_renderCondicaoPagamento(agenda);
}

window.initTela17 = initTela17;
document.addEventListener('DOMContentLoaded', initTela17);
