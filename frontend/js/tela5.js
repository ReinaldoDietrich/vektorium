// 4º elemento = chave do disjuntor (Tela 5 - Tabela de Disjuntores), todas as 5 cargas. Cada
// bloco tem uma borda esquerda mais grossa (separação visual, não misturar os dados de cada carga).
const ELET_LABELS = [['Ventilação', 'vent_w', 'vent_a', 'disjuntor_ventilacao'],
  ['Res. Portas', 'portas_w', 'portas_a', 'disjuntor_res_porta'],
  ['Res. Drenos', 'drenos_w', 'drenos_a', 'disjuntor_res_dreno'],
  ['Degelo', 'degelo_w', 'degelo_a', 'disjuntor_degelo'],
  ['Ilum. Expositores/ Ilum. Ambiente Câm.', 'ilum_w', 'ilum_a', 'disjuntor_iluminacao']];
const COMPIL_BASE_COLS = ['Sistema', 'Gabinete/Câmara', 'Modulação/Área', 'Carga Térmica', 'Forçadores', 'Folga Real Forçador', 'Nº Trocas de Ar', 'Válvulas de Expansão'];
function t5_eletColsPorBloco() { return ELET_LABELS.map(([, , , d]) => d ? 3 : 2); }
function t5_compilNcols(ehQd) {
  const eletCols = t5_eletColsPorBloco().reduce((a, b) => a + b, 0);
  return COMPIL_BASE_COLS.length + eletCols + (ehQd ? 2 : 0);
}
const TIPO_ORDER = { expositor: 0, simplificado: 1, completo: 2 };

let t5_colunasResumoTodas = [];
let t5_colunasResumoCompressaoTodas = [];

function initTela5() {
  document.getElementById('btnAtualizarCompilacao').addEventListener('click', t5_carregar);
  document.getElementById('t5_fatorPotencia').addEventListener('change', t5_carregar);
  document.getElementById('btnExportarExcel').addEventListener('click', () => {
    if (state.projetoId) api.baixarOuSalvar(`/api/compilacao/exportar/excel?projeto_id=${state.projetoId}&fator_potencia=${t5_fator()}&colunas=${t5_colunasSelecionadas().join(',')}&colunas_compressao=${t5_colunasCompressaoSelecionadas().join(',')}`);
  });
  document.getElementById('btnExportarPdf').addEventListener('click', () => {
    document.body.classList.add('t5-imprimindo');
    window.print();
    document.body.classList.remove('t5-imprimindo');
  });
  document.getElementById('t5_btnSalvarObs').addEventListener('click', t5_salvarObservacao);
  document.getElementById('t5_btnRestaurarObs').addEventListener('click', t5_restaurarObservacao);
  document.getElementById('t5_quadroTensaoFonte').addEventListener('change', t5_salvarQuadroTensaoFonte);
  document.addEventListener('projeto-changed', t5_onProjetoChanged);
}

function t5_fator() {
  return parseNumBR(document.getElementById('t5_fatorPotencia').value) || 0.92;
}

// Seleção de colunas dos "Resumo de Potência por Sistema" (Quadro de Linhas e Compressão/
// Condensação, cada um com seu próprio filtro independente) — persiste no navegador (não no
// projeto) e vale tanto pra tela quanto pro que é exportado (Excel/PDF), conforme pedido. Como as
// duas tabelas reaproveitam as mesmas chaves/rótulos/ordem (exceto "Pot. Total Instalada", que só
// existe em Linhas), as colunas ficam alinhadas verticalmente mesmo filtrando cada uma à parte.
function t5_colunasSelecionadasGenerico(todasCols, chaveStorage) {
  const todasChaves = todasCols.map(c => c.chave);
  const salvo = localStorage.getItem(chaveStorage);
  if (!salvo) return todasChaves;
  const validas = salvo.split(',').filter(k => todasChaves.includes(k));
  return validas.length ? validas : todasChaves;
}
function t5_colunasSelecionadas() {
  return t5_colunasSelecionadasGenerico(t5_colunasResumoTodas, 'ct_t5_colunas_resumo');
}
function t5_colunasCompressaoSelecionadas() {
  return t5_colunasSelecionadasGenerico(t5_colunasResumoCompressaoTodas, 'ct_t5_colunas_resumo_compressao');
}

function t5_renderColunasResumoBoxGenerico(elId, todasCols, selecionadasFn, chaveStorage, classe) {
  const selecionadas = new Set(selecionadasFn());
  document.getElementById(elId).innerHTML =
    '<span class="small" style="margin-right:4px;">Colunas do Resumo de Potência:</span>' +
    todasCols.map(c => `
      <label style="font-size:11px;white-space:nowrap;">
        <input type="checkbox" class="${classe}" value="${c.chave}" ${selecionadas.has(c.chave) ? 'checked' : ''}> ${c.rotulo}
      </label>`).join('');
  document.querySelectorAll('.' + classe).forEach(cb => cb.addEventListener('change', () => {
    const marcadas = Array.from(document.querySelectorAll('.' + classe + ':checked')).map(x => x.value);
    localStorage.setItem(chaveStorage, marcadas.join(','));
    t5_carregar();
  }));
}
function t5_renderColunasResumoBox() {
  t5_renderColunasResumoBoxGenerico('t5_colunasResumoBox', t5_colunasResumoTodas, t5_colunasSelecionadas, 'ct_t5_colunas_resumo', 't5_colResumoChk');
}
function t5_renderColunasResumoCompressaoBox() {
  t5_renderColunasResumoBoxGenerico('t5_colunasResumoCompressaoBox', t5_colunasResumoCompressaoTodas, t5_colunasCompressaoSelecionadas, 'ct_t5_colunas_resumo_compressao', 't5_colResumoCompChk');
}

function t5_fmtColResumo(chave, valor) {
  if (valor === null || valor === undefined) return '—';
  if (chave.endsWith('_kva')) return fmtNum(valor, 2);
  if (chave.endsWith('_w')) return fmtNum(valor);
  return valor;
}

function t5_onProjetoChanged() {
  const semProjeto = !state.projetoId;
  document.getElementById('t5_aviso_sem_projeto').style.display = semProjeto ? 'block' : 'none';
  document.getElementById('t5_conteudo').style.display = semProjeto ? 'none' : 'block';
  if (!semProjeto) t5_carregar();
}

function t5_buildHeaderRows(ehQd) {
  const row1 = COMPIL_BASE_COLS.map(h => `<th>${h}</th>`).join('')
    + ELET_LABELS.map(([lbl, , , d]) => `<th colspan="${d ? 3 : 2}" style="text-align:center;white-space:normal;border-left:2px solid #d1d5db;">${lbl}</th>`).join('')
    + (ehQd ? '<th colspan="2" style="text-align:center;white-space:normal;border-left:2px solid #d1d5db;">Alimentações Quadros (QD)</th>' : '');
  const row2 = COMPIL_BASE_COLS.map(() => '<th></th>').join('')
    + ELET_LABELS.map(([, , , d]) => `<th style="text-align:center;border-left:2px solid #d1d5db;">W</th><th style="text-align:center;">A</th>` + (d ? '<th style="text-align:center;">Disjuntor</th>' : '')).join('')
    + (ehQd ? '<th style="text-align:center;border-left:2px solid #d1d5db;">A</th><th style="text-align:center;">Disjuntor</th>' : '');
  return `<tr>${row1}</tr><tr>${row2}</tr>`;
}
function t5_eletCells(c, ehQd) {
  let out = ELET_LABELS.map(([, w, a, d]) => `<td style="text-align:center;white-space:nowrap;border-left:2px solid #d1d5db;">${c[w] != null ? fmtNum(c[w]) : '—'}</td><td style="text-align:center;white-space:nowrap;">${c[a] != null ? fmtNum(c[a], 1) : '—'}</td>`
    + (d ? `<td style="text-align:center;white-space:nowrap;">${c[d] || '—'}</td>` : '')).join('');
  if (ehQd) {
    out += `<td style="text-align:center;white-space:nowrap;border-left:2px solid #d1d5db;">${c.alimentacao_quadro_a != null ? fmtNum(c.alimentacao_quadro_a, 1) : '—'}</td>`
      + `<td style="text-align:center;white-space:nowrap;">${c.disjuntor_alimentacao_quadro || '—'}</td>`;
  }
  return out;
}
function t5_rowCompilacao(c, ehQd) {
  const isCam = c.metodo !== 'expositor';
  return `<tr>
    <td style="font-weight:bold;white-space:nowrap;">${c.codigo}</td>
    <td style="white-space:nowrap;">${isCam ? c.nome : (c.nome + (c.setor ? ' - ' + c.setor : ''))}</td>
    <td style="white-space:nowrap;">${c.modulacao_area}</td>
    <td style="text-align:right;white-space:nowrap;">${fmtKcal(c.carga_termica)}</td>
    <td style="white-space:nowrap;">${c.forcadores}</td><td style="white-space:nowrap;">${c.folga_real}</td><td style="white-space:nowrap;">${c.trocas_ar}</td><td style="white-space:nowrap;">${c.valvulas}</td>
    ${t5_eletCells(c, ehQd)}</tr>`;
}

function t5_tabelaAgrupada(itens, resumoSistemas, potenciaTotalW, potenciaDemandadaW, ehQd) {
  if (itens.length === 0) return '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhum item lançado ainda.</div>';
  const ncols = t5_compilNcols(ehQd);
  const resumoPorSistema = {};
  resumoSistemas.forEach(r => { resumoPorSistema[r.sistema_nome] = r; });
  const porSistema = {};
  itens.forEach(c => { (porSistema[c.sistema_nome] = porSistema[c.sistema_nome] || []).push(c); });
  let body = '';
  let granT = 0;
  Object.keys(porSistema).sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).forEach(sistema => {
    const its = porSistema[sistema];
    const ref = its[0];
    body += `<tr><td colspan="${ncols}" style="background:#f3f4f6;font-size:11.5px;font-weight:bold;color:#374151;padding:6px 8px;">SISTEMA ${sistema}
      <span style="color:#9ca3af;font-weight:normal;">— Temp. Evaporação: ${ref.temp_evaporacao}°C — Gás: ${ref.gas_refrigerante}</span></td></tr>`;
    const porRamal = {};
    its.forEach(c => { (porRamal[c.linha_succao] = porRamal[c.linha_succao] || []).push(c); });
    let totT = 0;
    Object.keys(porRamal).sort().forEach(ramal => {
      body += `<tr><td colspan="${ncols}" style="background:#f7f9fc;font-size:10.5px;color:#6b7280;padding:3px 8px;">Linha de Sucção ${ramal}</td></tr>`;
      const lista = porRamal[ramal].slice().sort((a, b) => (a.codigo || '').localeCompare(b.codigo || '', undefined, { numeric: true }));
      let subT = 0, subE = 0;
      lista.forEach(c => {
        subT += c.carga_termica || 0; totT += c.carga_termica || 0;
        subE += ELET_LABELS.reduce((s, [, w]) => s + (c[w] || 0), 0);
        body += t5_rowCompilacao(c, ehQd);
      });
      body += `<tr><td colspan="${ncols}" style="text-align:right;font-size:11px;color:#374151;padding:4px 8px;background:#fafafa;">Subtotal Linha ${ramal}: <strong>${fmtKcal(subT)} · ${fmtNum(subE)} W</strong></td></tr>`;
    });
    const rs = resumoPorSistema[sistema] || {};
    body += `<tr><td colspan="${ncols}" style="text-align:right;font-size:12px;color:#fff;background:#111827;padding:6px 8px;font-weight:bold;">
      TOTAL SISTEMA ${sistema}: ${fmtKcal(totT)} · Potência Máxima Instalada ${fmtNum(rs.potencia_total_w)} W · Potência em Operação ${fmtNum(rs.potencia_demandada_w)} W</td></tr>`;
    granT += totT;
  });
  body += `<tr><td colspan="${ncols}" style="text-align:right;font-size:13px;color:#fff;background:#000;padding:8px 10px;font-weight:bold;">
    TOTAL GERAL DO PROJETO: ${fmtKcal(granT)} · Potência Máxima Instalada ${fmtNum(potenciaTotalW)} W · Potência em Operação ${fmtNum(potenciaDemandadaW)} W</td></tr>`;
  return `<div style="overflow:auto;width:100%;max-height:70vh;"><table class="list"><thead>${t5_buildHeaderRows(ehQd)}</thead><tbody>${body}</tbody></table></div>`;
}

function t5_tabelaResumoPotencia(resumoSistemas, colunasSelecionadas, disjuntorGeral) {
  if (!resumoSistemas || resumoSistemas.length === 0) return '';
  const cols = t5_colunasResumoTodas.filter(c => colunasSelecionadas.includes(c.chave));
  const totais = {};
  cols.forEach(c => {
    if (c.chave === 'disjuntor') { totais[c.chave] = disjuntorGeral; return; }
    if (c.chave.endsWith('_w') || c.chave.endsWith('_kva')) {
      totais[c.chave] = resumoSistemas.reduce((s, r) => s + (r[c.campo] || 0), 0);
    }
  });
  return `<div style="border:1px solid var(--line);border-radius:6px;padding:10px;margin-top:14px;margin-bottom:8px;width:fit-content;max-width:100%;">
    <div class="sec-title" style="margin:0 0 8px;border-bottom:none;">Resumo de Potência por Sistema — Quadros de Linhas</div>
    <div style="overflow-x:auto;"><table class="list" style="width:auto;">
      <tr><th style="white-space:nowrap;text-align:center;">Sistema</th>${cols.map(c => `<th style="white-space:nowrap;text-align:center;">${c.rotulo}</th>`).join('')}</tr>
      ${resumoSistemas.map(r => `<tr>
        <td style="font-weight:bold;white-space:nowrap;text-align:center;">Quadro de Linhas - ${r.sistema_nome}</td>
        ${cols.map(c => `<td style="white-space:nowrap;text-align:center;">${t5_fmtColResumo(c.chave, r[c.campo])}</td>`).join('')}
      </tr>`).join('')}
      <tr style="font-weight:bold;background:#f3f4f6;">
        <td style="white-space:nowrap;text-align:center;">Alimentação Geral - Quadro de Linhas</td>
        ${cols.map(c => `<td style="white-space:nowrap;text-align:center;">${c.chave in totais ? t5_fmtColResumo(c.chave, totais[c.chave]) : ''}</td>`).join('')}
      </tr>
    </table></div></div>`;
}

// Cabeçalho fixo: ao rolar a tabela verticalmente, as 2 linhas do thead continuam visíveis
// (sticky), sem alterar formatação/conteúdo do cabeçalho — largura das colunas é automática,
// ajustada ao conteúdo (table-layout padrão do navegador, sem sistema de largura fixa/arraste).
function t5_ativarCabecalhoFixo() {
  const tabela = document.querySelector('#compilacaoView table');
  if (!tabela) return;
  const linhas = Array.from(tabela.querySelectorAll('thead tr'));
  if (!linhas.length) return;
  let topAcumulado = 0;
  linhas.forEach(tr => {
    const altura = tr.getBoundingClientRect().height;
    Array.from(tr.children).forEach(th => {
      th.style.position = 'sticky';
      th.style.top = topAcumulado + 'px';
      th.style.zIndex = '3';
    });
    topAcumulado += altura;
  });
}

function t5_tabelaResumoCompressao(resumoCompressao, colunasSelecionadas, disjuntorGeral) {
  if (!resumoCompressao || resumoCompressao.length === 0) return '';
  const cols = t5_colunasResumoCompressaoTodas.filter(c => colunasSelecionadas.includes(c.chave));
  const totais = {};
  cols.forEach(c => {
    if (c.chave === 'disjuntor') { totais[c.chave] = disjuntorGeral; return; }
    if (c.chave.endsWith('_w') || c.chave.endsWith('_kva')) {
      totais[c.chave] = resumoCompressao.reduce((s, r) => s + (r[c.campo] || 0), 0);
    }
  });
  return `<div style="border:1px solid var(--line);border-radius:6px;padding:10px;margin-top:14px;margin-bottom:8px;width:fit-content;max-width:100%;">
    <div class="sec-title" style="margin:0 0 8px;border-bottom:none;">Resumo de Potência por Sistema — Compressão e Condensação</div>
    <div style="overflow-x:auto;"><table class="list" style="width:auto;"><thead><tr>
      <th style="white-space:nowrap;text-align:center;">Sistema / Equipamento</th>${cols.map(c => `<th style="white-space:nowrap;text-align:center;">${c.rotulo}</th>`).join('')}
    </tr></thead><tbody>
      ${resumoCompressao.map(r => `<tr>
        <td style="white-space:nowrap;text-align:center;">${r.sistema_nome} — ${r.equipamento}</td>
        ${cols.map(c => `<td style="white-space:nowrap;text-align:center;">${t5_fmtColResumo(c.chave, r[c.campo])}</td>`).join('')}
      </tr>`).join('')}
      <tr style="font-weight:bold;background:#f3f4f6;">
        <td style="white-space:nowrap;text-align:center;">Alimentação Geral - Compressão e Condensação</td>
        ${cols.map(c => `<td style="white-space:nowrap;text-align:center;">${c.chave in totais ? t5_fmtColResumo(c.chave, totais[c.chave]) : ''}</td>`).join('')}
      </tr>
    </tbody></table></div></div>`;
}

function t5_tabelaTotalGeral(r) {
  // Respeita o filtro de colunas (mesma lógica do Excel): cada métrica só aparece se sua coluna
  // estiver selecionada em algum dos 2 resumos (Quadros de Linhas ou Compressão/Condensação).
  const chavesSel = new Set([...t5_colunasSelecionadas(), ...t5_colunasCompressaoSelecionadas()]);
  const maxima = [];
  if (chavesSel.has('pot_maxima_w')) maxima.push(`${fmtNum(r.potencia_geral_maxima_w)} W`);
  if (chavesSel.has('pot_maxima_kva')) maxima.push(`(${fmtNum(r.potencia_geral_maxima_kva, 2)} kVA)`);
  const operacao = [];
  if (chavesSel.has('pot_demandada_w')) operacao.push(`${fmtNum(r.potencia_geral_demandada_w)} W`);
  if (chavesSel.has('pot_demandada_kva')) operacao.push(`(${fmtNum(r.potencia_geral_demandada_kva, 2)} kVA)`);
  const celMax = maxima.length ? `<td style="white-space:nowrap;text-align:center;">Pot. Máxima: ${maxima.join(' ')}</td>` : '';
  const celOp = operacao.length ? `<td style="white-space:nowrap;text-align:center;">Pot. em Operação: ${operacao.join(' ')}</td>` : '';
  return `<table class="list" style="margin-top:14px;width:auto;"><tbody>
    <tr style="font-weight:bold;background:#111827;color:#fff;">
      <td style="white-space:nowrap;text-align:center;">TOTAL GERAL — Quadro de Linhas + Compressão e Condensação</td>
      ${celMax}${celOp}
    </tr>
  </tbody></table>`;
}

async function t5_carregar() {
  if (!state.projetoId) return;
  const [r, sf] = await Promise.all([
    api.get(`/api/compilacao?projeto_id=${state.projetoId}&fator_potencia=${t5_fator()}`),
    api.get(`/api/compilacao/status-fechada?projeto_id=${state.projetoId}`).catch(() => ({ abertas: [], total_abertas: 0 })),
  ]);
  let bannerEl = document.getElementById('t5_bannerAbertas');
  if (!bannerEl) {
    bannerEl = document.createElement('div');
    bannerEl.id = 't5_bannerAbertas';
    document.getElementById('compilacaoView')?.parentElement?.prepend(bannerEl);
  }
  if (sf.total_abertas > 0) {
    const lista = sf.abertas.map(a => `${a.tipo}: ${a.nome}`).join(', ');
    bannerEl.style.cssText = 'background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#92400e;';
    bannerEl.innerHTML = `<strong>⚠ ${sf.total_abertas} entidade(s) aberta(s):</strong> ${lista}. Feche todas antes de compilar o projeto final.`;
  } else {
    bannerEl.style.display = 'none';
  }
  t5_colunasResumoTodas = r.colunas_resumo;
  t5_colunasResumoCompressaoTodas = r.colunas_resumo_compressao;
  document.getElementById('compilacaoView').innerHTML = t5_tabelaAgrupada(r.itens, r.resumo_sistemas, r.potencia_total_w, r.potencia_demandada_w, r.eh_qd);
  t5_ativarCabecalhoFixo();
  t5_renderColunasResumoBox();
  document.getElementById('t5_resumoPotenciaView').innerHTML = t5_tabelaResumoPotencia(r.resumo_sistemas, t5_colunasSelecionadas(), r.disjuntor_geral_quadro_linhas);
  t5_renderColunasResumoCompressaoBox();
  document.getElementById('t5_resumoCompressaoView').innerHTML = t5_tabelaResumoCompressao(r.resumo_compressao, t5_colunasCompressaoSelecionadas(), r.disjuntor_geral_compressao);
  document.getElementById('t5_totalGeralView').innerHTML = t5_tabelaTotalGeral(r);
  document.getElementById('t5_observacao').value = r.observacao;
  document.getElementById('t5_quadroTensaoFonte').value = r.quadro_linhas_tensao_fonte || 'equipamentos';
  const t5_notaEl = document.getElementById('t5_notaQuadroTensao');
  if ((r.quadro_linhas_tensao_fonte || 'equipamentos') === 'comando') {
    t5_notaEl.style.display = 'none';
    t5_notaEl.textContent = '';
  } else {
    t5_notaEl.style.display = 'block';
    t5_notaEl.textContent =
      `⚠ A tensão indicada define apenas a alimentação para os "Quadro de Linhas" (dimensionamento de cabos). ` +
      `A elétrica dos forçadores (Ventilação/Degelo) deve ser executada conforme tensão de comando ${r.tensao_comando || '—'}.`;
  }
}

// Fonte de tensão do "Quadro de Linhas" (Comando/Equipamentos) — decisão única do projetista
// elétrico pro projeto inteiro, não por sistema (ver discussão real: não faz sentido o projetista
// de refrigeração decidir detalhe elétrico linha a linha).
async function t5_salvarQuadroTensaoFonte() {
  if (!state.projetoId) return;
  await api.put(`/api/projetos/${state.projetoId}`, { quadro_linhas_tensao_fonte: document.getElementById('t5_quadroTensaoFonte').value });
  t5_carregar();
}

async function t5_salvarObservacao() {
  if (!state.projetoId) return;
  await api.put(`/api/compilacao/observacao?projeto_id=${state.projetoId}`, { texto: document.getElementById('t5_observacao').value });
  alert('Observação salva.');
}

async function t5_restaurarObservacao() {
  if (!state.projetoId) return;
  if (!confirm('Restaurar o texto padrão? A observação customizada atual será perdida.')) return;
  await api.del(`/api/compilacao/observacao?projeto_id=${state.projetoId}`);
  t5_carregar();
}

window.initTela5 = initTela5;
window.telaShowHandlers[5] = () => { if (state.projetoId) t5_carregar(); };
document.addEventListener('DOMContentLoaded', initTela5);
