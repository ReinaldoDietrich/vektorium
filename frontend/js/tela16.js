// Tela 12 — Comparativo de Revisões / Projetos (id interno 16, livre — não confundir com
// tela12.js, que é a Tela 8 internamente). Só leitura: reaproveita os endpoints já existentes de
// Projeto, Compilação Geral (Tela 8), Compilação de Linhas (Tela 5), Consumo (Tela 9) e
// Composição de Preço (Tela 10), chamados 1x pra cada revisão escolhida — nenhum cálculo próprio
// além de forcadores_total (compilacao_geral.py, aprovado 2026-08-10). Baseado no documento
// "TELA COMPARATIVA DE REVISÕES DO PROJETO.docx". Suporta 2 ou 3 projetos (C é opcional).

let t16_arvoreIds = [];
let t16_nRevs = 2;

function initTela16() {
  window.telaShowHandlers[16] = t16_carregar;
  document.getElementById('t16_btnComparar').addEventListener('click', t16_comparar);
  document.getElementById('t16_btnImprimir').addEventListener('click', () => {
    abrirImpressao(['t16_resultado']);
  });
  document.getElementById('t16_btnExportarExcel').addEventListener('click', () => {
    const idA = document.getElementById('t16_revA').value;
    const idB = document.getElementById('t16_revB').value;
    const idC = document.getElementById('t16_revC').value;
    if (!idA || !idB) { alert('Escolha pelo menos 2 projetos antes de exportar.'); return; }
    let url = `/api/comparativo-revisoes/exportar/excel?projeto_a_id=${idA}&projeto_b_id=${idB}`;
    if (idC) url += `&projeto_c_id=${idC}`;
    api.baixarOuSalvar(url);
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
  document.getElementById('t16_revC').innerHTML = '<option value="">— (nenhum)</option>' + opts;
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
  const idC = document.getElementById('t16_revC').value;
  if (!idA || !idB) { alert('Escolha pelo menos 2 projetos antes de comparar.'); return; }
  document.getElementById('t16_aviso').textContent = 'Carregando…';
  const ids = [idA, idB];
  if (idC) ids.push(idC);
  const dados = await Promise.all(ids.map(id => t16_carregarDadosRevisao(id)));
  t16_nRevs = dados.length;
  document.getElementById('t16_aviso').textContent = '';
  document.getElementById('t16_resultado').style.display = 'block';
  t16_render(dados);
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

function t16_linha(label, valores, fmt = t16_fmt) {
  const formatados = valores.map(v => fmt(v));
  const temDiff = formatados.some(t => t !== formatados[0]);
  return '<tr><td class="label">' + label + '</td>' +
    formatados.map(t => '<td class="val' + (temDiff ? ' diff' : '') + '">' + t + '</td>').join('') +
    '</tr>';
}
function t16_subheader(nome) {
  return `<tr class="grupo-sep"><td colspan="${t16_nRevs + 1}" class="sistema-nome">${nome}</td></tr>`;
}
function t16_stripQtd(v) {
  if (!v) return v;
  return v.replace(/\d+x\s*/g, '').replace(/\s*\+\s*/g, ' + ');
}
function t16_bloco(titulo, subtitulo, corpoHtml) {
  const letras = ['A', 'B', 'C'];
  const ths = letras.slice(0, t16_nRevs).map(l => `<th>Projeto ${l}</th>`).join('');
  return `<div class="t16-bloco">
    <div class="t16-bloco-titulo">${titulo}${subtitulo ? ` <span class="t16-sub">${subtitulo}</span>` : ''}</div>
    <div style="overflow-x:auto;"><table class="list t16-tabela">
      <thead><tr><th></th>${ths}</tr></thead>
      <tbody>${corpoHtml}</tbody>
    </table></div>
  </div>`;
}

function t16_paresSistemas(listas, chave = 'sistema_nome') {
  const nomes = [...new Set(listas.flatMap(l => l.map(s => s[chave])))].sort();
  return nomes.map(nome => ({
    nome,
    items: listas.map(l => l.find(s => s[chave] === nome) || null),
  }));
}

function t16_render(dados) {
  const el = document.getElementById('t16_blocos');
  let html = '';

  // ---- Dados do Projeto ----
  html += t16_bloco('Dados do Projeto', null,
    t16_linha('Tipo de comando', dados.map(d => t16_nomePorCodigo(d.projeto.tipo_comando))) +
    t16_linha('Tensão de comando', dados.map(d => d.projeto.tensao_comando)) +
    t16_linha('Tensão de equipamento', dados.map(d => d.projeto.tensao_equipamentos)) +
    t16_linha('Custo de energia', dados.map(d => d.projeto.custo_energia), v => v == null ? '—' : t16_fmtR$(v) + '/kWh'));

  // ---- Sistemas ----
  const paresSist = t16_paresSistemas(dados.map(d => d.sistemas), 'nome');
  let corpoSist = '';
  paresSist.forEach(p => {
    corpoSist += t16_subheader(p.nome);
    const ss = p.items;
    corpoSist += t16_linha('Classificação', ss.map(s => s && s.classificacao));
    corpoSist += t16_linha('Gás refrigerante', ss.map(s => s && s.gas_refrigerante));
    corpoSist += t16_linha('Tipo de expansão', ss.map(s => s && t16_nomePorCodigo(s.tipo_expansao)));
    corpoSist += t16_linha('Temp. evaporação', ss.map(s => s && s.temp_evaporacao), v => v == null ? '—' : t16_fmt(v, ' °C'));
    corpoSist += t16_linha('Compressão', ss.map(s => s && t16_nomePorCodigo(s.tipo_compressao)));
    corpoSist += t16_linha('Condensação', ss.map(s => s && t16_nomePorCodigo(s.selecao_condensador_ar)));
    const conds = dados.map(d => (d.compilacaoGeral.sistemas.find(x => x.sistema_nome === p.nome) || {}).condensador || {});
    corpoSist += t16_linha('Temp. condensação', conds.map(c => c.temp_condensacao), v => v == null ? '—' : t16_fmt(v, ' °C'));
    const cargas = dados.map(d => (d.compilacaoGeral.totais.carga_termica_por_sistema.find(x => x.sistema_nome === p.nome) || {}).carga_termica_kcal_h);
    corpoSist += t16_linha('Carga térmica', cargas, v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
  });
  html += t16_bloco('Sistemas', 'Tabela Seção 3', corpoSist);

  // ---- Forçadores de ar (total por sistema) ----
  let corpoForc = '';
  paresSist.forEach(p => {
    const fs = dados.map(d => (d.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).forcadores_total || {});
    corpoForc += t16_subheader(p.nome);
    corpoForc += t16_linha('Capacidade fornecida', fs.map(f => f.capacidade_fornecida_kcal_h), v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoForc += t16_linha('Folga técnica total', fs.map(f => f.folga_tecnica_pct), v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Forçadores de Ar', null, corpoForc);

  // ---- Unidade Compressora (UC ou Rack) ----
  let corpoUc = '';
  paresSist.forEach(p => {
    const rs = dados.map(d => (d.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).rack_uc || {});
    corpoUc += t16_subheader(p.nome);
    corpoUc += t16_linha('Modelo equipamento', rs.map(r => r.modelo_comercial || r.modelo_tecnico));
    corpoUc += t16_linha('Modelo compressores', rs.map(r => t16_stripQtd(r.modelo_compressor)));
    corpoUc += t16_linha('Quantidade compressores', rs.map(r => r.quantidade_compressores));
    corpoUc += t16_linha('Linha compressores', rs.map(r => r.linha_compressor));
    corpoUc += t16_linha('Fabricante compressores', rs.map(r => r.fabricante_compressor));
    corpoUc += t16_linha('Capacidade total fornecida', rs.map(r => r.carga_total_fornecida_kcal_h), v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoUc += t16_linha('Calor total rejeitado', rs.map(r => r.calor_total_rejeitado_kcal_h), v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoUc += t16_linha('Corrente nominal', rs.map(r => r.corrente_nominal_a), v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoUc += t16_linha('Corrente máxima', rs.map(r => r.corrente_maxima_trabalho_a), v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoUc += t16_linha('Folga técnica', rs.map(r => r.folga_tecnica_pct), v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Unidade Compressora', 'UC ou Rack', corpoUc);

  // ---- Condensadores ----
  let corpoCond = '';
  paresSist.forEach(p => {
    const ss = p.items;
    const cs = dados.map(d => (d.compilacaoGeral.sistemas.find(s => s.sistema_nome === p.nome) || {}).condensador || {});
    corpoCond += t16_subheader(p.nome);
    corpoCond += t16_linha('Tipo', ss.map(s => s && t16_nomePorCodigo(s.selecao_condensador_ar)));
    corpoCond += t16_linha('Modelo', cs.map(c => c.modelo_condensador));
    corpoCond += t16_linha('Quantidade condensadores', cs.map(c => c.quantidade_condensadores));
    corpoCond += t16_linha('Diâmetro ventiladores', cs.map(c => c.diametro_ventilador_mm), v => v == null ? '—' : t16_fmt(v, ' mm'));
    corpoCond += t16_linha('Corrente nominal', cs.map(c => c.corrente_nominal_ventiladores_a), v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoCond += t16_linha('Capacidade condensador', cs.map(c => c.capacidade_condensador_kcal_h), v => v == null ? '—' : t16_fmt(v, ' kcal/h'));
    corpoCond += t16_linha('Folga técnica', cs.map(c => c.folga_tecnica_pct), v => v == null ? '—' : t16_fmt(v, '%'));
  });
  html += t16_bloco('Condensadores', null, corpoCond);

  // ---- Resumo de Potências (quadros + unidades compressoras) ----
  const paresQuadro = t16_paresSistemas(dados.map(d => d.compilacao.resumo_sistemas));
  let corpoPotQuadro = '';
  paresQuadro.forEach(p => {
    corpoPotQuadro += t16_subheader(p.nome);
    corpoPotQuadro += t16_linha('Potência operação', p.items.map(s => s && s.potencia_total_w), v => v == null ? '—' : t16_fmt(v, ' W'));
    corpoPotQuadro += t16_linha('Corrente total', p.items.map(s => s && s.corrente_total_a), v => v == null ? '—' : t16_fmt(v, ' A'));
    corpoPotQuadro += t16_linha('Potência operação', p.items.map(s => s && s.potencia_total_kva), v => v == null ? '—' : t16_fmt(v, ' kVA'));
    corpoPotQuadro += t16_linha('Disjuntor sugerido', p.items.map(s => s && s.disjuntor));
  });
  const paresComp = t16_paresSistemas(dados.map(d => d.compilacao.resumo_compressao));
  let corpoPotComp = '';
  paresComp.forEach(p => {
    corpoPotComp += t16_subheader(p.nome);
    corpoPotComp += t16_linha('Potência operação (máx.)', p.items.map(s => s && s.potencia_maxima_w), v => v == null ? '—' : t16_fmt(v, ' W'));
    corpoPotComp += t16_linha('Potência operação (máx.)', p.items.map(s => s && s.potencia_maxima_kva), v => v == null ? '—' : t16_fmt(v, ' kVA'));
    corpoPotComp += t16_linha('Disjuntor sugerido', p.items.map(s => s && s.disjuntor));
  });
  html += t16_bloco('Resumo de Potências — Quadros', 'por sistema', corpoPotQuadro);
  html += t16_bloco('Resumo de Potências — Unidades Compressoras', 'por sistema · sem dado de corrente total (Tela 5 não calcula esse campo hoje)', corpoPotComp);

  // ---- Totais da instalação ----
  html += t16_bloco('Totais da Instalação', null,
    t16_linha('Potência total da instalação', dados.map(d => d.compilacao.potencia_geral_maxima_kva), v => v == null ? '—' : t16_fmt(v, ' kVA')) +
    t16_linha('Consumo elétrico total', dados.map(d => d.consumo.total.kwh_projeto_mes), v => v == null ? '—' : t16_fmt(v, ' kWh/mês')) +
    t16_linha('Custo consumo elétrico', dados.map(d => d.consumo.total.custo_projeto_mes), t16_fmtR$));

  // ---- Custo financeiro por bloco ----
  const blocosNomes = [...new Set(dados.flatMap(d => Object.keys(d.composicao.blocos)))];
  let corpoCusto = '';
  const totais = dados.map(() => 0);
  blocosNomes.forEach(bloco => {
    const somas = dados.map(d => (d.composicao.blocos[bloco] || []).filter(it => it.incluir_orcamento !== false).reduce((acc, it) => acc + (it.valor_venda_negociacao || 0), 0));
    somas.forEach((s, i) => totais[i] += s);
    corpoCusto += t16_linha(bloco, somas, t16_fmtR$);
  });
  corpoCusto += '<tr><td class="label" style="font-weight:500;">Total</td>' +
    totais.map(t => `<td class="val" style="font-weight:700;">${t16_fmtR$(t)}</td>`).join('') + '</tr>';
  html += t16_bloco('Custo Financeiro', 'resumo por bloco — Composição de Preço', corpoCusto);

  el.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', initTela16);
