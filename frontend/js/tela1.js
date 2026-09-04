let t1_editandoProjetoId = null;
let t1_editandoSistemaId = null;
let t1_estacaoSelecionadaId = null;
let t1_estacoesPorLabel = {}; // "CIDADE (UF)" -> {id, ...}
let t1_estacoesLista = [];    // mesma lista, em array — usada pra filtrar o autocomplete
let t1_classificacoesSistema = []; // Tela 6 - Classificação de Sistemas e Envelope Compressores (Configurações)

const T1_ACORDEOES = ['accDadosCliente', 'accDadosProjeto', 'accSistemas', 'accSelecaoUC'];
function t1_retrairTudo() {
  T1_ACORDEOES.forEach(id => { const el = document.getElementById(id); if (el) el.open = false; });
}

// Barra de ações do projeto ATIVO (+Revisão/Exportar Tudo/Fechar/Excluir), dentro de
// "1. Dados do Cliente" — chamada depois de abrir/salvar/fechar um projeto.
async function t1_renderAcoesProjetoAtivo() {
  const el = document.getElementById('acoesProjetoAtivo');
  if (!el) return;
  if (!state.projetoId) { el.style.display = 'none'; el.innerHTML = ''; return; }
  const id = state.projetoId;
  let p;
  try { p = await api.get(`/api/projetos/${id}`); } catch (e) { el.style.display = 'none'; return; }
  const rev = 'R' + String(p.revisao ?? 0).padStart(2, '0');
  el.style.display = 'flex';
  el.innerHTML =
    `<span class="info"><b>${p.codigo_projeto || '(sem código)'}</b> ${rev}${p.fechado ? ' · FECHADO' : ''}</span>` +
    `<span class="btn-text" id="apaRevisar">+ Revisão</span>` +
    `<span class="btn-text" id="apaExportar">Exportar Tudo</span>` +
    `<span class="btn-text" id="apaFechar">${p.fechado ? 'Reabrir Projeto' : 'Fechar Projeto'}</span>` +
    `<span class="btn-text danger" id="apaExcluir">Excluir</span>`;
  document.getElementById('apaRevisar').addEventListener('click', async () => {
    if (!confirm('Gerar uma nova revisão (cópia editável) deste projeto? A revisão anterior é preservada e continua editável.')) return;
    const novo = await api.post(`/api/projetos/${id}/revisao`, {});
    if (window.refreshArvoreProjetos) window.refreshArvoreProjetos();
    await t1_abrirProjeto(novo.id, [novo]);
  });
  document.getElementById('apaExportar').addEventListener('click', async (ev) => {
    const b = ev.currentTarget, original = b.textContent;
    b.textContent = 'Exportando...';
    try {
      const r = await api.post(`/api/projetos/${id}/exportar-tudo`, {});
      alert(`Exportado com sucesso em:\n${r.salvo_em}`);
    } catch (e) {
      alert(`Erro ao exportar: ${e.message}`);
    } finally {
      b.textContent = original;
    }
  });
  document.getElementById('apaFechar').addEventListener('click', async () => {
    const acao = p.fechado ? 'reabrir' : 'fechar';
    if (acao === 'fechar' && !confirm('Fechar este projeto? Ele ficará somente para visualização até ser reaberto — a ação é reversível a qualquer momento.')) return;
    try {
      await api.post(`/api/projetos/${id}/${acao}`, {});
      aplicarModoProjetoFechado(acao === 'fechar');
      if (window.refreshArvoreProjetos) window.refreshArvoreProjetos();
      t1_renderAcoesProjetoAtivo();
    } catch (e) {
      alert(`Erro ao ${acao === 'fechar' ? 'fechar' : 'reabrir'} o projeto: ${e.message}`);
    }
  });
  document.getElementById('apaExcluir').addEventListener('click', async () => {
    if (!confirm('EXCLUIR este projeto/revisão em definitivo? Todos os dados dele (sistemas, câmaras, seleções) serão apagados. Esta ação não pode ser desfeita.')) return;
    await api.del(`/api/projetos/${id}`);
    await t1_fecharProjetoAtivo();
  });
}

async function initTela1() {
  document.getElementById('btnNovoProjeto').addEventListener('click', t1_novoProjeto);
  document.getElementById('btnRetrairTudo').addEventListener('click', t1_retrairTudo);
  document.getElementById('btnCancelarProjeto').addEventListener('click', t1_cancelarProjeto);
  document.getElementById('btnSalvarProjeto').addEventListener('click', t1_salvarProjeto);
  document.getElementById('btnEscolherPastaSalvamento').addEventListener('click', t1_escolherPastaSalvamento);
  document.getElementById('p_estacao_busca').addEventListener('focus', () => t1_estacaoRenderLista(document.getElementById('p_estacao_busca').value));
  document.getElementById('p_estacao_busca').addEventListener('input', () => t1_estacaoRenderLista(document.getElementById('p_estacao_busca').value));
  document.addEventListener('click', (ev) => {
    const wrap = document.getElementById('p_estacao_busca').parentElement;
    if (!wrap.contains(ev.target)) document.getElementById('p_estacao_lista').style.display = 'none';
  });
  document.getElementById('p_estado_uf').addEventListener('change', t1_estadoAlterado);
  document.getElementById('p_telefone').addEventListener('input', t1_mascararTelefone);
  document.getElementById('p_cnpj_faturamento').addEventListener('input', t1_mascararCnpj);
  document.getElementById('p_cep_faturamento').addEventListener('input', () => t1_mascararCep('p_cep_faturamento'));
  document.getElementById('p_cep_obra').addEventListener('input', () => t1_mascararCep('p_cep_obra'));
  document.getElementById('p_temp_ambiente').addEventListener('input', t1_atualizarTempAposCondensador);
  document.getElementById('sTempEvap').addEventListener('input', t1_atualizarClassificacaoSistema);
  document.getElementById('sExp').addEventListener('change', () =>   // An.04: tipo muda → recarrega fabricantes de válvula
    t1_carregarFabricantesValvula(document.getElementById('sExp').value, document.getElementById('sFabricanteValvula').value, false));
  t1_carregarClassificacoesSistema();
  document.getElementById('btnAddSistema').addEventListener('click', t1_salvarSistema);
  document.getElementById('btnRevelarFormSistema').addEventListener('click', () => {
    t1_limparFormSistema();
    t1_mostrarFormSistema(true);
    const btnFechar = document.getElementById('btnCancelarEdicaoSistema');
    btnFechar.textContent = 'Fechar';
    btnFechar.style.display = 'inline-block';
  });
  document.getElementById('btnCancelarEdicaoSistema').addEventListener('click', t1_cancelarEdicaoSistema);
  document.getElementById('btnFecharProjetoAtivo').addEventListener('click', t1_fecharProjetoAtivo);
  T1_FAB_TIPOS.forEach(t => document.getElementById(t.btn).addEventListener('click', () => t1_aplicarFabGlobal(t)));
  document.getElementById('sTipoCompressao').addEventListener('change', t1_atualizarVisibilidadeCamposSistema);
  document.getElementById('sAutomacao').addEventListener('change', t1_atualizarVisibilidadeCamposSistema);
  document.getElementById('sTipoAutomacaoLinhas').addEventListener('change', () => {
    t1_popularFornecedorAutomacaoLinhas(document.getElementById('sTipoAutomacaoLinhas').value, '');
    t1_popularModeloControladorLinhas(document.getElementById('sTipoAutomacaoLinhas').value, '', '');
  });
  document.getElementById('sAutomacaoLinhasFabricante').addEventListener('change', () =>
    t1_popularModeloControladorLinhas(document.getElementById('sTipoAutomacaoLinhas').value,
      document.getElementById('sAutomacaoLinhasFabricante').value, ''));
  document.getElementById('sAutomacao').addEventListener('change', () => {
    t1_popularFornecedorAutomacaoEquipamentos(document.getElementById('sAutomacao').value, '');
    t1_popularModeloControladorEquipamentos(document.getElementById('sAutomacao').value, '', '');
  });
  document.getElementById('sAutomacaoFabricante').addEventListener('change', () =>
    t1_popularModeloControladorEquipamentos(document.getElementById('sAutomacao').value,
      document.getElementById('sAutomacaoFabricante').value, ''));
  document.addEventListener('projeto-changed', t1_atualizarStatusProjeto);
  t1_carregarEstados();
  t1_carregarProjetos();
  await t1_carregarArvoreIds();
  t1_popularCamposArvoreFixos('');
  t1_atualizarVisibilidadeCamposSistema();
}

// ---- Campos da Seção 3 (Sistemas) que passam a ler as opções direto da árvore de Ids Comerciais
// (Configurações), em vez de lista fixa no código — qualquer nó novo cadastrado lá aparece aqui
// automaticamente (aprovado 2026-08-08). ----
let t1_arvoreIds = [];

async function t1_carregarArvoreIds() {
  t1_arvoreIds = await api.get('/api/catalogos/ids-comerciais');
}

function t1_filhosArvore(prefixo) {
  return t1_arvoreIds
    .filter(i => i.codigo.startsWith(prefixo + '.') && i.codigo.slice(prefixo.length + 1).indexOf('.') === -1)
    .sort((a, b) => a.codigo.localeCompare(b.codigo, undefined, { numeric: true }));
}

// Nome ATUAL do nó pra um código salvo — usado só pra exibição (resumo de sistemas), nunca pra
// decidir nada. Espelha id_comercial.nome_por_codigo do backend (aprovado 2026-08-08).
function t1_nomePorCodigo(codigo) {
  if (!codigo) return null;
  const no = t1_arvoreIds.find(i => i.codigo === codigo);
  return no ? no.nome : null;
}

function t1_codigoFilhoPorNome(prefixo, nome) {
  if (!nome) return null;
  const alvo = nome.trim().toLowerCase();
  const f = t1_filhosArvore(prefixo).find(i => (i.nome || '').trim().toLowerCase() === alvo);
  return f ? f.codigo : null;
}

// Popula um <select> com os filhos diretos de `prefixo`, preservando a 1ª opção já existente no
// HTML (ex.: "—" ou "Liga/Desliga (padrão)"). Se o valor salvo não bater com nenhum filho atual da
// árvore, o campo fica sem seleção visível — não inventa opção nenhuma (aprovado 2026-08-08). O
// dado em si continua salvo no banco, intocado; só não aparece marcado no dropdown.
// `codigosPermitidos` (opcional, array de códigos): restringe aos filhos citados — usado quando o
// nó-pai tem OUTROS filhos que não são opções deste campo (ex.: "4.1" tem "4.1.1"/"4.1.2" =
// Tipo Equip. Compressão, mas também "4.1.3"/"4.1.4" = campos próprios de Partida/Modo Operação).
function t1_popularSelectArvore(id, prefixo, valorAtual, codigosPermitidos) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const primeiraOpcao = sel.options.length ? sel.options[0].outerHTML : '<option value="">—</option>';
  let filhos = t1_filhosArvore(prefixo);
  if (codigosPermitidos) filhos = filhos.filter(f => codigosPermitidos.includes(f.codigo));
  sel.innerHTML = primeiraOpcao + filhos.map(f => `<option value="${f.codigo}">${f.nome}</option>`).join('');
  sel.value = valorAtual || '';
}

function t1_popularGases(valorAtual) {
  const sel = document.getElementById('sGas');
  if (!sel) return;
  const categorias = t1_filhosArvore('2.1');
  let html = '<option value="">—</option>';
  categorias.forEach(cat => {
    const gases = t1_filhosArvore(cat.codigo);
    if (!gases.length) return;
    html += `<optgroup label="${cat.nome}">` + gases.map(g => `<option>${g.nome}</option>`).join('') + '</optgroup>';
  });
  sel.innerHTML = html;
  sel.value = valorAtual || '';
}

// `tipo`/`fornecedor` já chegam como CÓDIGO (o próprio value do select-pai, não mais o nome) —
// aprovado 2026-08-08: nada de tradução por nome, o código já qualifica a posição na árvore.
function t1_popularFornecedorAutomacaoLinhas(tipo, valor) {
  if (!tipo) { const sel = document.getElementById('sAutomacaoLinhasFabricante'); sel.innerHTML = '<option value="">—</option>'; sel.value = ''; return; }
  t1_popularSelectArvore('sAutomacaoLinhasFabricante', tipo, valor);
}
function t1_popularModeloControladorLinhas(tipo, fornecedor, valor) {
  if (!fornecedor) { const sel = document.getElementById('sModeloControladorLinhas'); sel.innerHTML = '<option value="">—</option>'; sel.value = ''; return; }
  t1_popularSelectArvore('sModeloControladorLinhas', fornecedor, valor);
}
function t1_popularFornecedorAutomacaoEquipamentos(tipo, valor) {
  if (!tipo) { const sel = document.getElementById('sAutomacaoFabricante'); sel.innerHTML = '<option value="">—</option>'; sel.value = ''; return; }
  t1_popularSelectArvore('sAutomacaoFabricante', tipo, valor);
}
function t1_popularModeloControladorEquipamentos(tipo, fornecedor, valor) {
  if (!fornecedor) { const sel = document.getElementById('sModeloControladorEquipamentos'); sel.innerHTML = '<option value="">—</option>'; sel.value = ''; return; }
  t1_popularSelectArvore('sModeloControladorEquipamentos', fornecedor, valor);
}

// Campos com opções fixas (sem cascata) — recarregados toda vez que um sistema é aberto/limpo, pra
// sempre refletir a árvore atual e preservar o valor salvo (ou marcá-lo como legado).
function t1_popularCamposArvoreFixos(s) {
  s = s || {};
  t1_popularGases(s.gas_refrigerante);
  t1_popularSelectArvore('sExp', '3', s.tipo_expansao);
  t1_popularSelectArvore('sTipoCompressao', '4.1', s.tipo_compressao, ['4.1.1', '4.1.2']);
  t1_popularSelectArvore('sEstruturaCompressao', '4.1.2.1', s.estrutura_compressao);
  t1_popularSelectArvore('sPartida', '4.1.3', s.partida);
  t1_popularSelectArvore('sModoOperacao', '4.1.4', s.modo_operacao);
  // selecao_condensador_ar agora é editável na Tela 6 — display readonly aqui
  const condDisplay = document.getElementById('sSelecaoCondensadorAr_display');
  if (condDisplay) condDisplay.value = (s.selecao_condensador_ar && t1_nomePorCodigo(s.selecao_condensador_ar)) || '—';
  t1_popularSelectArvore('sTipoAutomacaoLinhas', '1.2', s.tipo_automacao_linhas);
  t1_popularFornecedorAutomacaoLinhas(s.tipo_automacao_linhas, s.automacao_linhas_fabricante);
  t1_popularModeloControladorLinhas(s.tipo_automacao_linhas, s.automacao_linhas_fabricante, s.modelo_controlador_linhas);
  t1_popularSelectArvore('sAutomacao', '1.3', s.automacao);
  t1_popularFornecedorAutomacaoEquipamentos(s.automacao, s.automacao_fabricante);
  t1_popularModeloControladorEquipamentos(s.automacao, s.automacao_fabricante, s.modelo_controlador_equipamentos);
}

function t1_mascararTelefone() {
  const el = document.getElementById('p_telefone');
  let d = el.value.replace(/\D/g, '').slice(0, 11);
  let out = d;
  if (d.length > 10) out = d.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3');
  else if (d.length > 6) out = d.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
  else if (d.length > 2) out = d.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
  else if (d.length > 0) out = d.replace(/^(\d{0,2}).*/, '($1');
  el.value = out;
}

function t1_mascararCnpj() {
  const el = document.getElementById('p_cnpj_faturamento');
  const d = el.value.replace(/\D/g, '').slice(0, 14);
  let out = d;
  if (d.length > 12) out = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2}).*/, '$1.$2.$3/$4-$5');
  else if (d.length > 8) out = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{0,4}).*/, '$1.$2.$3/$4');
  else if (d.length > 5) out = d.replace(/^(\d{2})(\d{3})(\d{0,3}).*/, '$1.$2.$3');
  else if (d.length > 2) out = d.replace(/^(\d{2})(\d{0,3}).*/, '$1.$2');
  el.value = out;
}

function t1_mascararCep(id) {
  const el = document.getElementById(id);
  const d = el.value.replace(/\D/g, '').slice(0, 8);
  el.value = d.length > 5 ? d.replace(/^(\d{5})(\d{0,3}).*/, '$1-$2') : d;
}

async function t1_carregarEstados() {
  const estados = await api.get('/api/catalogos/estados-brasileiros');
  const sel = document.getElementById('p_estado_uf');
  sel.innerHTML = '<option value="">—</option>' +
    estados.slice().sort((a, b) => a.estado.localeCompare(b.estado, 'pt-BR'))
      .map(e => `<option value="${e.sigla}">${e.estado} (${e.sigla})</option>`).join('');
}

// Tela 1 - Dados Climatológicos INMET 1990-2020 (Configurações) — lista de estações filtrada pelo
// Estado selecionado (ver discussão real 2026-07-18: elimina o antigo Critério de Projeto, fonte
// única agora é a Temp. Máxima Histórica dessa tabela).
async function t1_carregarEstacoes(uf) {
  const estacoes = uf ? await api.get(`/api/catalogos/clima-inmet/estacoes?uf=${encodeURIComponent(uf)}`) : [];
  t1_estacoesPorLabel = {};
  t1_estacoesLista = estacoes.map(e => {
    const label = `${e.nome_estacao} (${e.uf || '—'})`;
    const comLabel = { ...e, label };
    t1_estacoesPorLabel[label] = comLabel;
    return comLabel;
  });
}

async function t1_estadoAlterado() {
  const uf = document.getElementById('p_estado_uf').value;
  document.getElementById('p_estacao_busca').value = '';
  t1_estacaoSelecionadaId = null;
  await t1_carregarEstacoes(uf);
}

// Autocomplete próprio (substitui <datalist>, que em muitos navegadores só sugere depois de
// digitar e não abre com um simples clique) — abre a lista ao focar (mostra tudo, até um limite)
// e filtra conforme digita.
function t1_estacaoRenderLista(filtro) {
  const box = document.getElementById('p_estacao_lista');
  const termo = (filtro || '').trim().toLowerCase();
  const encontrados = (termo ? t1_estacoesLista.filter(e => e.label.toLowerCase().includes(termo)) : t1_estacoesLista).slice(0, 50);
  if (!encontrados.length) {
    box.innerHTML = '<div style="padding:8px;font-size:12px;color:#9ca3af;">nenhuma estação encontrada</div>';
  } else {
    box.innerHTML = encontrados.map(e => `<div data-estacao-label="${e.label}" style="padding:6px 8px;font-size:13px;cursor:pointer;border-bottom:1px solid var(--line-light);">${e.label}</div>`).join('');
    box.querySelectorAll('[data-estacao-label]').forEach(el => {
      el.addEventListener('mouseenter', () => el.style.background = '#eff6ff');
      el.addEventListener('mouseleave', () => el.style.background = '');
      el.addEventListener('click', () => {
        document.getElementById('p_estacao_busca').value = el.dataset.estacaoLabel;
        box.style.display = 'none';
        t1_estacaoAlterada();
      });
    });
  }
  box.style.display = 'block';
}

async function t1_atualizarStatusProjeto() {
  const status = document.getElementById('projetoStatus');
  const btnFechar = document.getElementById('btnFecharProjetoAtivo');
  if (state.projetoId) {
    const p = await api.get(`/api/projetos/${state.projetoId}`);
    status.textContent = `projeto ativo: ${p.codigo_projeto || '#' + p.id}${p.cliente ? ' — ' + p.cliente : ''}`;
    btnFechar.style.display = 'inline';
    aplicarModoProjetoFechado(p.fechado);   // projeto fechado = telas dele só para visualização
  } else {
    status.textContent = 'nenhum projeto ativo';
    btnFechar.style.display = 'none';
    aplicarModoProjetoFechado(false);
  }
}

async function t1_fecharProjetoAtivo() {
  await fecharProjetoAtivo();
  document.getElementById('formProjetoWrap').style.display = 'none';
  t1_editandoProjetoId = null;
  t1_carregarProjetos();
  t1_renderAcoesProjetoAtivo();
  if (window.refreshArvoreProjetos) window.refreshArvoreProjetos();
}

let t1_revisoesRetraidas = new Set();   // codigo_base cujos filhos (revisões) estão recolhidos

async function t1_carregarProjetos() {
  if (state.projetoId) { await carregarSistemasDoProjeto(); t1_renderSistemas(); }
  const projetos = await api.get('/api/projetos');
  const el = document.getElementById('listaProjetos');
  const formWrap = document.getElementById('formProjetoWrap');
  // o formulário é uma única instância reaproveitada, que pode estar posicionada dentro da lista
  // (embaixo do card do projeto em edição) — tira antes de recriar os cards, senão o innerHTML
  // abaixo apaga o formulário junto com os cards antigos.
  if (formWrap.parentElement === el) el.parentElement.insertBefore(formWrap, el.nextSibling);
  if (projetos.length === 0) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhum projeto cadastrado ainda.</div>';
    return;
  }
  // agrupa por codigo_base — cada grupo é uma "pasta": R00 é o pai, R01/R02… ficam aninhadas.
  // NUNCA cair pro texto livre codigo_projeto: dois projetos sem relação nenhuma podem ter o
  // mesmo código digitado por coincidência (ex.: projeto em branco abandonado) — sem codigo_base
  // de verdade (que só existe numa revisão real), cada projeto deve ficar isolado, chave = id.
  const grupos = {};
  projetos.forEach(p => {
    const k = p.codigo_base || `__id:${p.id}`;
    (grupos[k] = grupos[k] || []).push(p);
  });
  const card = (p, filho) => `
    <div class="lista-card" data-projeto="${p.id}" style="${filho ? 'margin-left:26px;' : ''}">
      <div class="nome" style="display:flex;align-items:center;gap:8px;">
        <span style="flex:1;">${p.codigo_projeto || '(sem código)'} ${p.cliente ? '— ' + p.cliente : ''}
          <span class="badge" style="background:#eef2ff;color:#3730a3;">R${String(p.revisao ?? 0).padStart(2, '0')}</span>
          ${p.id === state.projetoId ? '<span class="badge" style="background:var(--green-bg);color:var(--green);">ativo</span>' : ''}
          ${p.fechado ? '<span class="badge" style="background:#fee2e2;color:#991b1b;">FECHADO</span>' : ''}</span>
        <span class="btn-text" data-revisar="${p.id}">+ Revisão</span>
        <span class="btn-text" data-exportar-tudo="${p.id}">Exportar Tudo</span>
        <span class="btn-text" data-toggle-fechado="${p.id}" data-fechado="${p.fechado ? '1' : '0'}">${p.fechado ? 'Reabrir Projeto' : 'Fechar Projeto'}</span>
        <span class="btn-text danger" data-excluir-proj="${p.id}">Excluir</span>
      </div>
      <div class="meta">${p.cidade_instalacao || '—'} · ${p.condicao_salao}</div>
    </div>`;
  let html = '';
  Object.keys(grupos).sort().forEach(k => {
    const lista = grupos[k].sort((a, b) => (b.revisao ?? 0) - (a.revisao ?? 0));
    const pai = lista[0], filhos = lista.slice(1);
    const retraido = t1_revisoesRetraidas.has(k);
    const toggle = filhos.length
      ? `<span class="btn-text" data-toggle-grupo="${k}" style="width:18px;flex:none;text-align:center;">${retraido ? '▸' : '▾'}</span>`
      : `<span style="width:18px;flex:none;"></span>`;
    html += `<div style="display:flex;align-items:flex-start;gap:2px;"><div style="padding-top:9px;">${toggle}</div><div style="flex:1;">${card(pai, false)}</div></div>`;
    if (filhos.length && !retraido) html += filhos.map(f => card(f, true)).join('');
  });
  el.innerHTML = html;
  el.querySelectorAll('[data-projeto]').forEach(c =>
    c.addEventListener('click', () => t1_abrirProjeto(Number(c.dataset.projeto), projetos)));
  el.querySelectorAll('[data-toggle-grupo]').forEach(b => b.addEventListener('click', (ev) => {
    ev.stopPropagation();
    const k = b.dataset.toggleGrupo;
    if (t1_revisoesRetraidas.has(k)) t1_revisoesRetraidas.delete(k); else t1_revisoesRetraidas.add(k);
    t1_carregarProjetos();
  }));
  el.querySelectorAll('[data-revisar]').forEach(b => b.addEventListener('click', async (ev) => {
    ev.stopPropagation();   // não abrir o projeto ao clicar no botão dentro do card
    if (!confirm('Gerar uma nova revisão (cópia editável) deste projeto? A revisão anterior é preservada e continua editável.')) return;
    const novo = await api.post(`/api/projetos/${b.dataset.revisar}/revisao`, {});
    await t1_carregarProjetos();
    await t1_abrirProjeto(novo.id, [novo]);
  }));
  el.querySelectorAll('[data-exportar-tudo]').forEach(b => b.addEventListener('click', async (ev) => {
    ev.stopPropagation();
    const original = b.textContent;
    b.textContent = 'Exportando...';
    try {
      const r = await api.post(`/api/projetos/${b.dataset.exportarTudo}/exportar-tudo`, {});
      alert(`Exportado com sucesso em:\n${r.salvo_em}`);
    } catch (e) {
      alert(`Erro ao exportar: ${e.message}`);
    } finally {
      b.textContent = original;
    }
  }));
  el.querySelectorAll('[data-toggle-fechado]').forEach(b => b.addEventListener('click', async (ev) => {
    ev.stopPropagation();
    const id = b.dataset.toggleFechado;
    const estaFechado = b.dataset.fechado === '1';
    const acao = estaFechado ? 'reabrir' : 'fechar';
    if (!estaFechado && !confirm('Fechar este projeto? Ele ficará somente para visualização até ser reaberto — a ação é reversível a qualquer momento.')) return;
    try {
      await api.post(`/api/projetos/${id}/${acao}`, {});
      // se o projeto fechado/reaberto é o que está ativo na tela, liga/desliga o modo só-visualização na hora
      if (Number(id) === state.projetoId) aplicarModoProjetoFechado(acao === 'fechar');
      await t1_carregarProjetos();
    } catch (e) {
      alert(`Erro ao ${acao === 'fechar' ? 'fechar' : 'reabrir'} o projeto: ${e.message}`);
    }
  }));
  el.querySelectorAll('[data-excluir-proj]').forEach(b => b.addEventListener('click', async (ev) => {
    ev.stopPropagation();
    if (!confirm('EXCLUIR este projeto/revisão em definitivo? Todos os dados dele (sistemas, câmaras, seleções) serão apagados. Esta ação não pode ser desfeita.')) return;
    const id = Number(b.dataset.excluirProj);
    await api.del(`/api/projetos/${id}`);
    if (state.projetoId === id) await t1_fecharProjetoAtivo();
    if (t1_editandoProjetoId === id) t1_editandoProjetoId = null;
    await t1_carregarProjetos();
  }));
  // Nota: a lista antiga (#listaProjetos) está sempre oculta agora — a navegação é pela árvore
  // lateral e o formulário do projeto ativo fica dentro de "1. Dados do Cliente". Por isso o form
  // NÃO é mais reposicionado pra dentro do card da lista (comportamento antigo, agora obsoleto —
  // deixava o form invisível junto com a lista escondida).
}

async function t1_novoProjeto() {
  await fecharProjetoAtivo();  // limpa state.projetoId/sistemas — senão as outras telas continuam
  // mostrando dados do projeto anterior até o novo ser salvo e aberto de verdade (bug real).
  t1_editandoProjetoId = null;
  t1_estacaoSelecionadaId = null;
  ['p_codigo_projeto', 'p_data', 'p_cliente', 'p_cidade_instalacao', 'p_altitude_m', 'p_estacao_busca',
   'p_temp_ambiente', 'p_ur_externa', 'p_contato', 'p_telefone',
   'p_custo_energia', 'p_pasta_salvamento',
   'p_razao_social_faturamento', 'p_cnpj_faturamento', 'p_cep_faturamento',
   'p_endereco_faturamento', 'p_endereco_obra', 'p_cep_obra'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('p_estado_uf').value = '';
  t1_carregarEstacoes(null);
  document.getElementById('p_tipo_comando').value = '';
  document.getElementById('p_tensao_equipamentos').value = '';
  document.getElementById('p_tensao_comando').value = '';
  document.getElementById('p_condicao_salao').value = '25°C - 60% UR (com ar condicionado)';
  document.getElementById('p_considerar_iluminacao_ambiente').value = '1';
  document.getElementById('formProjetoWrap').style.display = 'block';
  document.getElementById('blocoSistemas').style.display = 'none';
  t1_retrairTudo();
  t1_renderAcoesProjetoAtivo();
}

async function t1_escolherPastaSalvamento() {
  const campo = document.getElementById('p_pasta_salvamento');
  if (window.vektorium?.escolherPasta) {
    const pasta = await window.vektorium.escolherPasta({ titulo: 'Escolher pasta de salvamento do projeto', inicial: campo.value || null });
    if (pasta) campo.value = pasta;
  } else {
    const r = await api.post('/api/projetos/escolher-pasta', { inicial: campo.value || null });
    if (r.pasta) campo.value = r.pasta;
  }
}

function t1_cancelarProjeto() {
  document.getElementById('formProjetoWrap').style.display = 'none';
}

async function t1_abrirProjeto(id, projetosCache) {
  const p = projetosCache.find(x => x.id === id) || await api.get(`/api/projetos/${id}`);
  t1_editandoProjetoId = id;
  document.getElementById('p_codigo_projeto').value = p.codigo_projeto || '';
  document.getElementById('p_data').value = p.data || '';
  document.getElementById('p_cliente').value = p.cliente || '';
  document.getElementById('p_cidade_instalacao').value = p.cidade_instalacao || '';
  document.getElementById('p_razao_social_faturamento').value = p.razao_social_faturamento || '';
  document.getElementById('p_cnpj_faturamento').value = p.cnpj_faturamento || '';
  document.getElementById('p_cep_faturamento').value = p.cep_faturamento || '';
  document.getElementById('p_endereco_faturamento').value = p.endereco_faturamento || '';
  document.getElementById('p_endereco_obra').value = p.endereco_obra || '';
  document.getElementById('p_cep_obra').value = p.cep_obra || '';
  document.getElementById('p_altitude_m').value = p.altitude_m ?? '';
  document.getElementById('p_temp_ambiente').value = p.temp_ambiente ?? '';
  document.getElementById('p_ur_externa').value = p.ur_externa ?? '';
  document.getElementById('p_estado_uf').value = p.estado_uf || '';
  t1_estacaoSelecionadaId = p.estacao_inmet_id || null;
  document.getElementById('p_estacao_busca').value = '';
  await t1_carregarEstacoes(p.estado_uf);
  if (t1_estacaoSelecionadaId) {
    const est = Object.values(t1_estacoesPorLabel).find(e => e.id === t1_estacaoSelecionadaId);
    document.getElementById('p_estacao_busca').value = est ? est.label : '';
  }
  document.getElementById('p_contato').value = p.contato || '';
  document.getElementById('p_telefone').value = p.telefone || '';
  t1_mascararTelefone();
  document.getElementById('p_tipo_comando').value = p.tipo_comando || '';
  document.getElementById('p_tensao_equipamentos').value = p.tensao_equipamentos || '';
  document.getElementById('p_tensao_comando').value = p.tensao_comando || '';
  document.getElementById('p_custo_energia').value = p.custo_energia ?? '';
  document.getElementById('p_pasta_salvamento').value = p.pasta_salvamento || '';
  document.getElementById('p_condicao_salao').value = p.condicao_salao;
  document.getElementById('p_considerar_iluminacao_ambiente').value = p.considerar_iluminacao_ambiente === false ? '0' : '1';
  document.getElementById('formProjetoWrap').style.display = 'block';
  document.getElementById('blocoSistemas').style.display = 'block';
  t1_retrairTudo();
  await definirProjetoAtivo(id);
  t1_renderSistemas();
  t1_carregarFiltroFabGlobal();
  t1_carregarProjetos();
  t1_renderAcoesProjetoAtivo();
}

// Filtro Global de Fabricante — UM por tipo (forçador, UC, condensador). Lista só os fabricantes
// que cobrem TODO o escopo daquele tipo. Aplicar move o "Considerar" daquele tipo; não altera dados.
const T1_FAB_TIPOS = [
  { tipo: 'forcador', sel: 'p_fab_global_forcador', btn: 'btnFabGlobal_forcador', msg: 'msg_fab_forcador', nome: 'forçadores' },
  { tipo: 'uc', sel: 'p_fab_global_uc', btn: 'btnFabGlobal_uc', msg: 'msg_fab_uc', nome: 'unidades condensadoras' },
  { tipo: 'condensador', sel: 'p_fab_global_condensador', btn: 'btnFabGlobal_condensador', msg: 'msg_fab_condensador', nome: 'condensadores' },
];

async function t1_carregarFiltroFabGlobal() {
  if (!state.projetoId || !document.getElementById('p_fab_global_forcador')) return;
  const r = await api.get(`/api/projetos/${state.projetoId}/fabricante-global`);
  T1_FAB_TIPOS.forEach(t => {
    const eleg = r[t.tipo] || [];
    const sel = document.getElementById(t.sel);
    const btn = document.getElementById(t.btn);
    const msg = document.getElementById(t.msg);
    sel.innerHTML = '<option value="">—</option>' + eleg.map(f => `<option value="${f}">${f}</option>`).join('');
    const vazio = eleg.length === 0;
    sel.disabled = vazio;
    btn.disabled = vazio;
    msg.style.color = '#6b7280';
    msg.textContent = vazio ? 'Nenhum fabricante cobre todo o escopo deste tipo.' : '';
  });
}

async function t1_aplicarFabGlobal(t) {
  const fab = document.getElementById(t.sel).value;
  if (!fab) { alert('Selecione um fabricante elegível.'); return; }
  if (!confirm(`Aplicar "${fab}" como fabricante considerado em todos os ${t.nome} do projeto?`)) return;
  await api.post(`/api/projetos/${state.projetoId}/fabricante-global/aplicar`, { tipo: t.tipo, fabricante: fab });
  const msg = document.getElementById(t.msg);
  msg.style.color = 'var(--green)';
  msg.textContent = `Aplicado: ${fab}.`;
}

function t1_estacaoAlterada() {
  const label = document.getElementById('p_estacao_busca').value.trim();
  const est = t1_estacoesPorLabel[label];
  const tag = document.getElementById('climaTag');
  if (!est) {
    t1_estacaoSelecionadaId = null;
    tag.textContent = 'estação não encontrada na lista — escolha uma opção sugerida';
    tag.style.color = '#b45309';
    return;
  }
  t1_estacaoSelecionadaId = est.id;
  t1_resolverClima();
}

async function t1_resolverClima() {
  const tag = document.getElementById('climaTag');
  if (!t1_estacaoSelecionadaId) return;
  const r = await api.get(`/api/catalogos/clima-inmet/resolver?estacao_id=${t1_estacaoSelecionadaId}`);
  if (r.encontrado) {
    document.getElementById('p_temp_ambiente').value = r.temp_bulbo_seco ?? '';
    document.getElementById('p_ur_externa').value = r.umidade_relativa ?? '';
    tag.textContent = 'estação climatológica — Temp. Máxima Histórica — editável';
    tag.style.color = '#9ca3af';
    t1_atualizarTempAposCondensador();
  }
}

async function t1_salvarProjeto() {
  const payload = {
    codigo_projeto: document.getElementById('p_codigo_projeto').value,
    data: document.getElementById('p_data').value || null,
    cliente: document.getElementById('p_cliente').value,
    cidade_instalacao: document.getElementById('p_cidade_instalacao').value,
    razao_social_faturamento: document.getElementById('p_razao_social_faturamento').value || null,
    cnpj_faturamento: document.getElementById('p_cnpj_faturamento').value || null,
    cep_faturamento: document.getElementById('p_cep_faturamento').value || null,
    endereco_faturamento: document.getElementById('p_endereco_faturamento').value || null,
    endereco_obra: document.getElementById('p_endereco_obra').value || null,
    cep_obra: document.getElementById('p_cep_obra').value || null,
    altitude_m: parseNumBR(document.getElementById('p_altitude_m').value),
    estado_uf: document.getElementById('p_estado_uf').value || null,
    estacao_inmet_id: t1_estacaoSelecionadaId,
    temp_ambiente: parseNumBR(document.getElementById('p_temp_ambiente').value) || null,
    ur_externa: parseNumBR(document.getElementById('p_ur_externa').value),
    contato: document.getElementById('p_contato').value,
    telefone: document.getElementById('p_telefone').value,
    tipo_comando: document.getElementById('p_tipo_comando').value,
    tensao_equipamentos: document.getElementById('p_tensao_equipamentos').value,
    tensao_comando: document.getElementById('p_tensao_comando').value,
    custo_energia: parseNumBR(document.getElementById('p_custo_energia').value) || null,
    pasta_salvamento: document.getElementById('p_pasta_salvamento').value || null,
    condicao_salao: document.getElementById('p_condicao_salao').value,
    considerar_iluminacao_ambiente: document.getElementById('p_considerar_iluminacao_ambiente').value === '1',
  };
  let p;
  if (t1_editandoProjetoId) {
    p = await api.put(`/api/projetos/${t1_editandoProjetoId}`, payload);
  } else {
    p = await api.post('/api/projetos', payload);
  }
  t1_editandoProjetoId = p.id;
  document.getElementById('blocoSistemas').style.display = 'block';
  await definirProjetoAtivo(p.id);
  t1_renderSistemas();
  t1_carregarProjetos();
  t1_renderAcoesProjetoAtivo();
  if (window.refreshArvoreProjetos) window.refreshArvoreProjetos();
}

// ---- Sistemas ----
const T1_CAMPOS_SISTEMA = ['sNome', 'sNivel', 'sGas', 'sExp', 'sFabricanteValvula', 'sTempEvap', 'sTipoCompressao', 'sEstruturaCompressao',
  'sPartida', 'sAutomacao', 'sAutomacaoFabricante', 'sTipoAutomacaoLinhas', 'sAutomacaoLinhasFabricante',
  'sModeloControladorLinhas', 'sModeloControladorEquipamentos',
  'sTempAposCondensador', 'sTempAposSubresfriamento', 'sModoOperacao',
  'sQuantidadeDegeloDia', 'sTempoDegeloMin', 'sCustoSistemaSimples', 'sCustoSistemaProjeto'];

function t1_atualizarVisibilidadeCamposSistema() {
  // Partida/Automação valem pros dois tipos de compressão (Rack Paralelo e Unidade Condensadora
  // Comercial) — só ficam ocultos se nenhum tipo de compressão foi escolhido ainda.
  const temTipo = !!document.getElementById('sTipoCompressao').value;
  document.getElementById('sCampoPartidaWrap').style.display = temTipo ? 'block' : 'none';
  document.getElementById('sCampoAutomacaoWrap').style.display = temTipo ? 'block' : 'none';
  if (!temTipo) {
    document.getElementById('sPartida').value = '';
    document.getElementById('sAutomacao').value = '';
  }
  const gerenciamento = temTipo && document.getElementById('sAutomacao').value === '1.3.2';  // Gerenciamento Eletrônico
  document.getElementById('sCampoFabricanteWrap').style.display = gerenciamento ? 'block' : 'none';
  if (!gerenciamento) {
    document.getElementById('sAutomacaoFabricante').value = '';
  }

  t1_atualizarTempAposCondensador();
}

// Linha de Líquido — Temp. após Condensador = Temp. Ambiente (Tela 1, Seção 1) + Delta de
// Condensação (Sistema) − 3 — fórmula fixa definida pelo usuário (ver discussão real 2026-07-18).
// Campo travado (disabled), recalculado a cada mudança de Delta de Condensação ou de Temp. Ambiente.
async function t1_carregarClassificacoesSistema() {
  t1_classificacoesSistema = await api.get('/api/catalogos/classificacao-sistema-compressor');
}

// Classificação do Sistema — automática, conforme a tabela "Tela 6 - Classificação de Sistemas e
// Envelope Compressores" (Configurações): casa a Temp. Evaporação do sistema com o range
// temp_evap_sistema_min/max de cada tipo (Sistema de Alta/Média/Baixa) e extrai o rótulo curto
// (Alta/Média/Baixa) do campo "tipo" ("Sistema de Alta" -> "Alta"). Campo travado — deixou de ser
// seleção manual (ver discussão real 2026-07-18).
function t1_atualizarClassificacaoSistema() {
  const el = document.getElementById('sNivel');
  const tempStr = document.getElementById('sTempEvap').value;
  const temp = tempStr !== '' ? parseNumBR(tempStr) : null;
  if (temp == null || !t1_classificacoesSistema.length) { el.value = ''; return; }
  const match = t1_classificacoesSistema.find(c =>
    c.temp_evap_sistema_min != null && c.temp_evap_sistema_max != null &&
    temp >= c.temp_evap_sistema_min && temp <= c.temp_evap_sistema_max);
  el.value = match ? match.tipo.replace(/^Sistema de /, '') : 'Fora de faixa';
}

function t1_atualizarTempAposCondensador() {
  const tempAmbienteStr = document.getElementById('p_temp_ambiente').value;
  const tempAmbiente = tempAmbienteStr !== '' ? parseNumBR(tempAmbienteStr) : null;
  // Delta de Condensação agora vem do state.sistemas (editável na Tela 6), exibido readonly na Tela 1
  const sistemaAtual = t1_editandoSistemaId && state.sistemas ? state.sistemas.find(s => s.id === t1_editandoSistemaId) : null;
  const deltaDisplay = document.getElementById('sDeltaCondensacao');
  const delta = sistemaAtual?.delta_condensacao != null ? sistemaAtual.delta_condensacao : (deltaDisplay ? parseNumBR(deltaDisplay.value) : null);
  if (deltaDisplay && sistemaAtual) deltaDisplay.value = sistemaAtual.delta_condensacao ?? '';
  const el = document.getElementById('sTempAposCondensador');
  el.value = (tempAmbiente != null && delta != null) ? (tempAmbiente + delta - 3).toFixed(1) : '';
  const elCond = document.getElementById('sTempCondensacao');
  elCond.value = (tempAmbiente != null && delta != null) ? (tempAmbiente + delta).toFixed(1) : '';
}

// Mostra/oculta o formulário de sistema. Oculto por padrão (tela enxuta): o botão
// "+ Adicionar Sistema" revela; salvar/cancelar oculta de novo.
function t1_mostrarFormSistema(mostrar) {
  const wrap = document.getElementById('formSistemaWrap');
  const btn = document.getElementById('btnRevelarFormSistema');
  if (wrap) wrap.style.display = mostrar ? 'block' : 'none';
  if (btn) btn.style.display = mostrar ? 'none' : 'inline-block';
}

function t1_limparFormSistema() {
  T1_CAMPOS_SISTEMA.forEach(id => document.getElementById(id).value = '');
  t1_carregarFabricantesValvula('', '', false);   // sem tipo → lista de fabricante-válvula vazia
  t1_popularCamposArvoreFixos(null);
  t1_editandoSistemaId = null;
  document.getElementById('btnAddSistema').textContent = '+';
  document.getElementById('btnCancelarEdicaoSistema').style.display = 'none';
  t1_atualizarVisibilidadeCamposSistema();
  t1_mostrarFormSistema(false);
}

function t1_tempCondensacao(s) {
  if (s.delta_condensacao == null) return null;
  const tempAmbiente = document.getElementById('p_temp_ambiente').value;
  const base = tempAmbiente !== '' ? parseNumBR(tempAmbiente) : null;
  return base != null ? base + s.delta_condensacao : null;
}

function t1_tempLiquido(s) {
  const valores = [s.temp_apos_condensador, s.temp_apos_subresfriamento].filter(v => v != null);
  return valores.length ? Math.min(...valores) : null;
}

function t1_renderSistemas() {
  const el = document.getElementById('sistemasList');
  if (state.sistemas.length === 0) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhum sistema cadastrado ainda.</div>';
    return;
  }
  let html = '<div style="overflow-x:auto;"><table class="list"><tbody>';
  html += '<tr><th>Nome</th><th>Classificação</th><th>Gás</th><th>Expansão</th><th>Temp. Evap.</th>'
    + '<th>Compressão</th><th>Condensação</th><th>Temp. Condensação</th><th>Temp. Líquido</th><th>Vínculos</th><th>Ações</th></tr>';
  state.sistemas.forEach(s => {
    const revisarTag = s.precisa_revisar ? ' <span style="color:#b45309;font-size:10px;">⚠ revisar lançamentos</span>' : '';
    const compressaoResumo = [s.tipo_compressao, s.estrutura_compressao, s.partida, s.automacao, s.automacao_fabricante]
      .map(t1_nomePorCodigo).filter(Boolean).join(' · ') || '—';
    const expansaoResumo = [t1_nomePorCodigo(s.tipo_expansao), s.fabricante_valvula,
      t1_nomePorCodigo(s.tipo_automacao_linhas), t1_nomePorCodigo(s.automacao_linhas_fabricante)]
      .filter(Boolean).join(' · ') || '—';
    const condensacaoResumo = t1_nomePorCodigo(s.selecao_condensador_ar) || '—';
    const tCond = t1_tempCondensacao(s);
    const tLiq = t1_tempLiquido(s);
    html += `<tr>
      <td style="font-weight:bold;">${s.nome}${revisarTag}</td><td>${s.classificacao || '—'}</td><td>${s.gas_refrigerante || '—'}</td>
      <td>${expansaoResumo}</td><td>${s.temp_evaporacao ?? '—'}°C</td>
      <td>${compressaoResumo}</td><td>${condensacaoResumo}</td>
      <td>${tCond != null ? tCond.toFixed(1) + '°C' : '—'}</td><td>${tLiq != null ? tLiq.toFixed(1) + '°C' : '—'}</td>
      <td>${s.vinculos} lançamento(s)</td>
      <td><span class="btn-text" data-editar="${s.id}" style="margin-right:4px;">Editar</span><span class="btn-text danger" data-excluir="${s.id}">Excluir</span></td>
    </tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
  el.querySelectorAll('[data-editar]').forEach(b => b.addEventListener('click', () => t1_editarSistema(Number(b.dataset.editar))));
  el.querySelectorAll('[data-excluir]').forEach(b => b.addEventListener('click', () => t1_excluirSistema(Number(b.dataset.excluir))));
  if (window.t1uc_render) window.t1uc_render();
}

// An.04 — "Fabricante Válvula" data-driven: opções vêm da Tabela de Válvulas (Tela A) filtradas pelo
// tipo (Termostática/Eletrônica), não mais fixas no HTML. `preservarLegado`=true (ao carregar um
// sistema salvo) injeta o valor salvo como "(legado)" se ele não estiver mais na tabela — nunca
// perde o dado. `false` (troca manual de tipo) reseta o fabricante que não vale para o novo tipo.
async function t1_carregarFabricantesValvula(tipo, selecionado, preservarLegado) {
  const sel = document.getElementById('sFabricanteValvula');
  if (!sel) return;
  const t = (tipo || '').trim();
  let fabs = [];
  if (t) {
    try { const r = await api.get(`/api/valvulas-expansao/fabricantes?tipo=${encodeURIComponent(t)}`); fabs = r.fabricantes || []; }
    catch (e) { fabs = []; }
  }
  sel.innerHTML = '<option value="">—</option>' + fabs.map(f => `<option>${f}</option>`).join('');
  const v = selecionado || '';
  if (v && !fabs.includes(v)) {
    if (preservarLegado) {
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v + ' (legado)';
      sel.appendChild(opt);
      sel.value = v;
    } else {
      sel.value = '';
    }
  } else {
    sel.value = v;
  }
}

async function t1_editarSistema(id) {
  const s = state.sistemas.find(x => x.id === id);
  document.getElementById('sNome').value = s.nome || '';
  t1_carregarFabricantesValvula(s.tipo_expansao, s.fabricante_valvula, true);   // An.04: lista vem da Tabela de Válvulas
  document.getElementById('sTempEvap').value = s.temp_evaporacao ?? '';
  t1_atualizarClassificacaoSistema();
  await t1_carregarArvoreIds();   // busca a árvore de novo — pega nós cadastrados na mesma sessão, sem precisar recarregar o app
  t1_popularCamposArvoreFixos(s);
  document.getElementById('sTempAposCondensador').value = s.temp_apos_condensador ?? '';
  document.getElementById('sTempAposSubresfriamento').value = s.temp_apos_subresfriamento ?? '';
  document.getElementById('sDeltaCondensacao').value = s.delta_condensacao ?? '';
  const condDisplay2 = document.getElementById('sSelecaoCondensadorAr_display');
  if (condDisplay2) condDisplay2.value = (s.selecao_condensador_ar && t1_nomePorCodigo(s.selecao_condensador_ar)) || '—';
  t1_atualizarTempAposCondensador();
  document.getElementById('sQuantidadeDegeloDia').value = s.quantidade_degelo_dia ?? '';
  document.getElementById('sTempoDegeloMin').value = s.tempo_degelo_min ?? '';
  document.getElementById('sCustoSistemaSimples').value = s.custo_sistema_simples ?? '';
  document.getElementById('sCustoSistemaProjeto').value = s.custo_sistema_projeto ?? '';
  t1_editandoSistemaId = id;
  document.getElementById('btnAddSistema').textContent = '✓';
  const btnFechar = document.getElementById('btnCancelarEdicaoSistema');
  btnFechar.textContent = 'Cancelar edição';
  btnFechar.style.display = 'inline-block';
  t1_atualizarVisibilidadeCamposSistema();
  t1_mostrarFormSistema(true);
}

function t1_cancelarEdicaoSistema() { t1_limparFormSistema(); }

async function t1_salvarSistema() {
  const nome = document.getElementById('sNome').value;
  if (!nome) return;
  const payload = {
    nome, classificacao: document.getElementById('sNivel').value, gas_refrigerante: document.getElementById('sGas').value,
    tipo_expansao: document.getElementById('sExp').value,
    fabricante_valvula: document.getElementById('sFabricanteValvula').value || null,
    temp_evaporacao: parseNumBR(document.getElementById('sTempEvap').value),
    tipo_compressao: document.getElementById('sTipoCompressao').value || null,
    estrutura_compressao: document.getElementById('sEstruturaCompressao').value || null,
    partida: document.getElementById('sPartida').value || null,
    automacao: document.getElementById('sAutomacao').value || null,
    automacao_fabricante: document.getElementById('sAutomacaoFabricante').value || null,
    tipo_automacao_linhas: document.getElementById('sTipoAutomacaoLinhas').value || null,
    automacao_linhas_fabricante: document.getElementById('sAutomacaoLinhasFabricante').value || null,
    modelo_controlador_linhas: document.getElementById('sModeloControladorLinhas').value || null,
    modelo_controlador_equipamentos: document.getElementById('sModeloControladorEquipamentos').value || null,
    temp_apos_condensador: parseNumBR(document.getElementById('sTempAposCondensador').value),
    temp_apos_subresfriamento: parseNumBR(document.getElementById('sTempAposSubresfriamento').value),
    modo_operacao: document.getElementById('sModoOperacao').value || null,
    quantidade_degelo_dia: parseNumBR(document.getElementById('sQuantidadeDegeloDia').value),
    tempo_degelo_min: parseNumBR(document.getElementById('sTempoDegeloMin').value),
    custo_sistema_simples: parseNumBR(document.getElementById('sCustoSistemaSimples').value),
    custo_sistema_projeto: parseNumBR(document.getElementById('sCustoSistemaProjeto').value),
  };
  if (t1_editandoSistemaId) {
    const r = await api.put(`/api/sistemas/${t1_editandoSistemaId}`, payload);
    if (r.vinculos > 0 && r.precisa_revisar) {
      alert(`Este sistema tem ${r.vinculos} lançamento(s) vinculado(s). Os parâmetros foram alterados — eles ficarão marcados como "revisar" até serem confirmados manualmente.`);
    }
  } else {
    await api.post(`/api/projetos/${state.projetoId}/sistemas`, payload);
  }
  t1_limparFormSistema();
  await carregarSistemasDoProjeto();
  t1_renderSistemas();
}

async function t1_excluirSistema(id) {
  const { vinculos } = await api.get(`/api/sistemas/${id}/vinculos`);
  const msg = vinculos > 0
    ? `Este sistema tem ${vinculos} lançamento(s) vinculado(s) (câmaras/expositores), que serão excluídos junto. Excluir mesmo assim?`
    : 'Excluir este sistema?';
  if (!confirm(msg)) return;
  await api.del(`/api/sistemas/${id}`);
  if (t1_editandoSistemaId === id) t1_limparFormSistema();
  await carregarSistemasDoProjeto();
  t1_renderSistemas();
}

window.initTela1 = initTela1;
window.telaShowHandlers[1] = t1_carregarProjetos;

