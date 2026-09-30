// Tela 12 — Comparativo de Revisões do Projeto (id interno 16, livre — não confundir com
// tela12.js, que é a Tela 8 internamente). Só leitura: reaproveita os endpoints já existentes de
// Projeto, Compilação Geral (Tela 8), Compilação de Linhas (Tela 5), Consumo (Tela 9) e
// Composição de Preço (Tela 10), chamados 1x pra cada revisão escolhida — nenhum cálculo próprio
// além de forcadores_total (compilacao_geral.py, aprovado 2026-08-10). Baseado no documento
// "TELA COMPARATIVA DE REVISÕES DO PROJETO.docx".

let t16_arvoreIds = [];

function initTela16() {
  window.telaShowHandlers[16] = t16_carregar;
  document.getElementById('t16_btnComparar').addEventListener('click', t16_comparar);
  document.getElementById('t16_btnImprimir').addEventListener('click', () => {
    abrirImpressao(['t16_resultado']);
  });
  document.getElementById('t16_btnExportarExcel').addEventListener('click', () => {
    const idA = document.getElementById('t16_revA').value;
    const idB = document.getElementById('t16_revB').value;
    if (!idA || !idB) { alert('Escolha as 2 revisões antes de exportar.'); return; }
    api.baixarOuSalvar(`/api/comparativo-revisoes/exportar/excel?projeto_a_id=${idA}&projeto_b_id=${idB}`);
  });
}

function t16_nomePorCodigo(codigo) {
  if (!codigo) return null;
  const no = t16_arvoreIds.find(i => i.codigo === codigo);
  return no ? no.nome : codigo;
}

async function t16_carregar() {
  const [projetos, arvoreIds] = await Promise.all([
    api.get('/api/projetos'), api.get('/api/catalogos/ids-comerciais'),
  ]);
  t16_arvoreIds = arvoreIds;
  const opts = projetos
    .slice()
    .sort((a, b) => (a.codigo_projeto || '').localeCompare(b.codigo_projeto || '') || (a.revisao || 0) - (b.revisao || 0))
    .map(p => `<option value="${p.id}">${p.codigo_projeto} — R${String(p.revisao || 0).padStart(2, '0')} (${p.cliente || ''})</option>`)
    .join('');
  document.getElementById('t16_revA').innerHTML = '<option value="">—</option>' + opts;
  document.getElementById('t16_revB').innerHTML = '<option value="">—</option>' + opts;
}

async function t16_carregarDadosRevisao(projetoId) {
  const [projeto, compilacaoGeral, compilacao, consumo, composicao] = await Promise.all([
    api.get(`/api/projetos/${projetoId}`),
    api.get(`/api/compilacao-geral?projeto_id=${projetoId}`),
    api.get(`/api/compilacao?projeto_id=${projetoId}`),
    api.get(`/api/consumo/projetos/${projetoId}`),
    api.get(`/api/composicao-preco?projeto_id=${projetoId}`),
  ]);
  const sistemas = await api.get(`/api/projetos/${projetoId}/sistemas`);
  return { projeto, compilacaoGeral, compilacao, consumo, composicao, sistemas };
}

async function t16_comparar() {
  const idA = document.getElementById('t16_revA').value;
  const idB = document.getElementById('t16_revB').value;
  if (!idA || !idB) { alert('Escolha as 2 revisões antes de comparar.'); return; }
  document.getElementById('t16_aviso').textContent = 'Carregando…';
  const [a, b] = await Promise.all([t16_carregarDadosRevisao(idA), t16_carregarDadosRevisao(idB)]);
  document.getElementById('t16_aviso').textContent = '';
  document.getElementById('t16_resultado').style.display = 'block';
  t16_render(a, b);
}

// ---- formatação e diff ----
function t16_fmt(v, sufixo = '') {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'number') return v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + sufixo;
  return v + sufixo;
}
function t16_fmtR$(v) {
  if (v === null || v === undefined) return '—';
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Uma linha da tabela: rótulo | valor A | valor B, com a célula B marcada se o texto formatado
// divergir do A (comparação por valor já formatado, evita falso positivo por ruído de float).
function t16_linha(label, va, vb, fmt = t16_fmt) {
  const ta = fmt(va), tb = fmt(vb);
  const diff = ta !== tb;
  return `<tr><td class="label">${label}</td><td class="val${diff ? ' diff' : ''}">${ta}</td><td class="val${diff ? ' diff' : ''}">${tb}</td></tr>`;
}
function t16_subheader(nome) {
  return `<tr class="grupo-sep"><td colspan="3" class="sistema-nome">${nome}</td></tr>`;
}
function t16_bloco(titulo, subtitulo, corpoHtml) {
  return `<div class="t16-bloco">
    <div class="t16-bloco-titulo">${titulo}${subtitulo ? ` <span class="t16-sub">${subtitulo}</span>` : ''}</div>
    <div style="overflow-x:auto;"><table class="list t16-tabela">
      <thead><tr><th></th><th>Revisão A</th><th>Revisão B</th></tr></thead>
      <tbody>${corpoHtml}</tbody>
    </table></div>
  </div>`;
}

// Pareia sistemas de A e B pelo NOME (podem existir em quantidades/nomes diferentes entre
// revisões — o que não existir do outro lado aparece como "—", contando como diferença).
function t16_paresSistemas(listaA, listaB, chave = 'sistema_nome') {
  const nomes = [...new Set([...listaA.map(s => s[chave]), ...listaB.map(s => s[chave])])].sort();
  return nomes.map(nome => ({
    nome,
    a: listaA.find(s => s[chave] === nome) || null,
    b: listaB.find(s => s[chave] === nome) || null,
  }));
}

function t16_render(a, b) {
  const el = document.getElementById('t16_blocos');
  let html = '';

  // ---- Dados do Projeto ----
  html += t16_bloco('Dados do Projeto', null,
    t16_linha('Tipo de comando', t16_nomePorCodigo(a.projeto.tipo_comando), t16_nomePorCodigo(b.projeto.tipo_comando)) +
    t16_linha('Tensão de comando', a.projeto.tensao_comando, b.projeto.tensao_comando) +
    t16_linha('Tensão de equipamento', a.projeto.tensao_equipamentos, b.projeto.tensao_equipamentos) +
    t16_linha('Custo de energia', a.projeto.custo_energia, b.projeto.custo_energia, v => v == null ? '—' : t16_fmtR$(v) + '/kWh'));

  // ---- Sistemas ----
  const paresSist = t16_paresSistemas(a.sistemas, b.sistemas, 'nome');
  let corpoSist = '';
  paresSist.forEach(p => {
    corpoSist += t16_subheader(p.nome);
    const sa = p.a, sb = p.b;
    corpoSist += t16_linha('Classificação', sa && sa.classificacao, sb && sb.classificacao);
    corpoSist += t16_linha('Gás refrigerante', sa && sa.gas_refrigerante, sb && sb.gas_refrigerante);
    corpoSist += t16_linha('Tipo de expansão', sa && t16_nomePorCodigo(sa.tipo_expansao), sb && t16_nomePorCodigo(sb.tipo_expansao));
    corpoSist += t16_linha('Temp. evaporação', sa && sa.temp_evaporacao, sb && sb.temp_evaporacao, v => v == null ? '—' : t16_fmt(v, ' °C'));
    corpoSist += t16_linha('Compressão', sa && t16_nomePorCodigo(sa.tipo_compressao), sb && t16_nomePorCodigo(sb.tipo_compressao));
    corpoSist += t16_linha('Condensação', sa && t16_nomePorCodigo(sa.selecao_condensador_ar), sb && t16_nomePorCodigo(sb.selecao_condensador_ar));
    corpoSist += t16_linha('Temp. condensação', sa && sa.temp_apos_condensador, sb && sb.temp_apos_condensador, v => v == null ? '—' : t16_fmt(v, ' °C'));
    const cargaA = (a.compilacaoGeral.totais.carga_termica_por_sistema.find(x => x.sistema_nome === p.nome) || {}).carga_termica_kcal_h;
    const cargaB = (b.compilacaoGeral.totais.carga_termica_por_sistema.find(x => x.sistema_nome === p.nome) || {}).carga_termica_kcal_h;
    corpoSist += t16_linha('Carga térmica', cargaA, cargaB, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
  });
  html += t16_bloco('Sistemas', 'Tabela Seção 3', corpoSist);

  // ---- Forçadores de ar (total por sistema) ----
  let corpoForc = '';
  paresSist.forEach(p => {
    const fa = (a.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).forcadores_total || {};
    const fb = (b.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).forcadores_total || {};
    corpoForc += t16_subheader(p.nome);
    corpoForc += t16_linha('Capacidade fornecida', fa.capacidade_fornecida_kcal_h, fb.capacidade_fornecida_kcal_h, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoForc += t16_linha('Folga técnica total', fa.folga_tecnica_pct, fb.folga_tecnica_pct, v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Forçadores de Ar', null, corpoForc);

  // ---- Unidade Compressora (UC ou Rack) ----
  let corpoUc = '';
  paresSist.forEach(p => {
    const ra = (a.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).rack_uc || {};
    const rb = (b.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).rack_uc || {};
    corpoUc += t16_subheader(p.nome);
    corpoUc += t16_linha('Modelo equipamento', ra.modelo_comercial, rb.modelo_comercial);
    corpoUc += t16_linha('Modelo compressores', ra.modelo_compressor, rb.modelo_compressor);
    corpoUc += t16_linha('Quantidade compressores', ra.quantidade_compressores, rb.quantidade_compressores);
    corpoUc += t16_linha('Linha compressores', ra.linha_compressor, rb.linha_compressor);
    corpoUc += t16_linha('Fabricante compressores', ra.fabricante_compressor, rb.fabricante_compressor);
    corpoUc += t16_linha('Capacidade total fornecida', ra.carga_total_fornecida_kcal_h, rb.carga_total_fornecida_kcal_h, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoUc += t16_linha('Calor total rejeitado', ra.calor_total_rejeitado_kcal_h, rb.calor_total_rejeitado_kcal_h, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoUc += t16_linha('Corrente nominal', ra.corrente_nominal_a, rb.corrente_nominal_a, v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoUc += t16_linha('Corrente máxima', ra.corrente_maxima_trabalho_a, rb.corrente_maxima_trabalho_a, v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoUc += t16_linha('Folga técnica', ra.folga_tecnica_pct, rb.folga_tecnica_pct, v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Unidade Compressora', 'UC ou Rack', corpoUc);

  // ---- Condensadores ----
  let corpoCond = '';
  paresSist.forEach(p => {
    const sa = p.a, sb = p.b;
    const ca = (a.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).condensador || {};
    const cb = (b.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).condensador || {};
    corpoCond += t16_subheader(p.nome);
    corpoCond += t16_linha('Tipo', sa && t16_nomePorCodigo(sa.selecao_condensador_ar), sb && t16_nomePorCodigo(sb.selecao_condensador_ar));
    corpoCond += t16_linha('Modelo', ca.modelo_condensador, cb.modelo_condensador);
    corpoCond += t16_linha('Quantidade forçadores', ca.qtd_ventiladores, cb.qtd_ventiladores);
    corpoCond += t16_linha('Diâmetro ventiladores', ca.diametro_ventilador_mm, cb.diametro_ventilador_mm, v => v == null ? '—' : t16_fmt(v, ' mm'));
    corpoCond += t16_linha('Corrente nominal', ca.corrente_nominal_ventiladores_a, cb.corrente_nominal_ventiladores_a, v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoCond += t16_linha('Capacidade condensador', ca.capacidade_condensador_kcal_h, cb.capacidade_condensador_kcal_h, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoCond += t16_linha('Folga técnica', ca.folga_tecnica_pct, cb.folga_tecnica_pct, v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Condensadores', null, corpoCond);

  // ---- Resumo de Potências (quadros + unidades compressoras) ----
  const paresQuadro = t16_paresSistemas(a.compilacao.resumo_sistemas, b.compilacao.resumo_sistemas);
  let corpoPotQuadro = '';
  paresQuadro.forEach(p => {
    corpoPotQuadro += t16_subheader(p.nome);
    corpoPotQuadro += t16_linha('Potência operação', p.a && p.a.potencia_total_w, p.b && p.b.potencia_total_w, v => v == null ? '—' : t16_fmt(v, ' W'));
    corpoPotQuadro += t16_linha('Corrente total', p.a && p.a.corrente_total_a, p.b && p.b.corrente_total_a, v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoPotQuadro += t16_linha('Potência operação', p.a && p.a.potencia_total_kva, p.b && p.b.potencia_total_kva, v => v == null ? '—' : t16_fmt(v, ' kVA'));
    corpoPotQuadro += t16_linha('Disjuntor sugerido', p.a && p.a.disjuntor, p.b && p.b.disjuntor);
  });
  const paresComp = t16_paresSistemas(a.compilacao.resumo_compressao, b.compilacao.resumo_compressao);
  let corpoPotComp = '';
  paresComp.forEach(p => {
    corpoPotComp += t16_subheader(p.nome);
    corpoPotComp += t16_linha('Potência operação (máx.)', p.a && p.a.potencia_maxima_w, p.b && p.b.potencia_maxima_w, v => v == null ? '—' : t16_fmt(v, ' W'));
    corpoPotComp += t16_linha('Potência operação (máx.)', p.a && p.a.potencia_maxima_kva, p.b && p.b.potencia_maxima_kva, v => v == null ? '—' : t16_fmt(v, ' kVA'));
    corpoPotComp += t16_linha('Disjuntor sugerido', p.a && p.a.disjuntor, p.b && p.b.disjuntor);
  });
  html += t16_bloco('Resumo de Potências — Quadros', 'por sistema', corpoPotQuadro);
  html += t16_bloco('Resumo de Potências — Unidades Compressoras', 'por sistema · sem dado de corrente total (Tela 5 não calcula esse campo hoje)', corpoPotComp);

  // ---- Totais da instalação ----
  html += t16_bloco('Totais da Instalação', null,
    t16_linha('Potência total da instalação', a.compilacao.potencia_geral_maxima_kva, b.compilacao.potencia_geral_maxima_kva, v => v == null ? '—' : t16_fmt(v, ' kVA')) +
    t16_linha('Consumo elétrico total', a.consumo.total.kwh_projeto_mes, b.consumo.total.kwh_projeto_mes, v => v == null ? '—' : t16_fmt(v, ' kWh/mês')) +
    t16_linha('Custo consumo elétrico', a.consumo.total.custo_projeto_mes, b.consumo.total.custo_projeto_mes, t16_fmtR$));

  // ---- Custo financeiro por bloco ----
  const blocosNomes = [...new Set([...Object.keys(a.composicao.blocos), ...Object.keys(b.composicao.blocos)])];
  let corpoCusto = '';
  let totalA = 0, totalB = 0;
  blocosNomes.forEach(bloco => {
    const somaA = (a.composicao.blocos[bloco] || []).reduce((acc, it) => acc + (it.valor_venda_negociacao || 0), 0);
    const somaB = (b.composicao.blocos[bloco] || []).reduce((acc, it) => acc + (it.valor_venda_negociacao || 0), 0);
    totalA += somaA; totalB += somaB;
    corpoCusto += t16_linha(bloco, somaA, somaB, t16_fmtR$);
  });
  corpoCusto += `<tr><td class="label" style="font-weight:500;">Total</td><td class="val" style="font-weight:700;">${t16_fmtR$(totalA)}</td><td class="val" style="font-weight:700;">${t16_fmtR$(totalB)}</td></tr>`;
  html += t16_bloco('Custo Financeiro', 'resumo por bloco — Composição de Preço', corpoCusto);

  el.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', initTela16);
