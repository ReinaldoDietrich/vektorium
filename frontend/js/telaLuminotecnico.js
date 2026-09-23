// Tela 11 — Estudo Luminotécnico. Somente leitura: reflete automaticamente as câmaras (Completo/
// Simples) já lançadas nas Telas 2/3 com Tipo Ambiente + Modelo Luminária preenchidos — mesmo
// padrão do Resumo de Painéis/Portas (nunca editado/excluído aqui).

function initTelaLuminotecnico() {
  window.telaShowHandlers[18] = t18_carregar;
  document.getElementById('t18_btnImprimir').addEventListener('click', () => {
    document.body.classList.add('t18-imprimindo');
    window.print();
    document.body.classList.remove('t18-imprimindo');
  });
  document.getElementById('t18_btnExportarExcel').addEventListener('click', () => {
    if (state.projetoId) api.baixarOuSalvar(`/api/luminotecnico/exportar/excel?projeto_id=${state.projetoId}`);
  });
}

async function t18_carregar() {
  const semProjeto = document.getElementById('t18_semProjeto');
  const conteudo = document.getElementById('t18_conteudo');
  if (!state.projetoId) {
    semProjeto.style.display = 'block';
    conteudo.style.display = 'none';
    return;
  }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';
  const d = await api.get(`/api/luminotecnico/estudo?projeto_id=${state.projetoId}`);
  t18_renderTabela(d.linhas);
  t18_renderResumo(d.resumo_por_modelo);
  t18_renderNotas(d.notas);
}

const T18_COLUNAS = [
  { key: 'seq', label: 'Seq.' },
  { key: 'linha_succao', label: 'Linha de Sucção' },
  { key: 'ambiente', label: 'Ambiente' },
  { key: 'comprimento', label: 'Comprimento (m)' },
  { key: 'largura', label: 'Largura (m)' },
  { key: 'area', label: 'Área (m²)' },
  { key: 'altura', label: 'Altura (m)' },
  { key: 'plano_calculo', label: 'Plano de Cálculo (m)' },
  { key: 'altura_util', label: 'Altura Útil (m)' },
  { key: 'indice_ambiente_k', label: 'Índice do Ambiente (K)' },
  { key: 'refletancia_teto', label: 'Refletância Teto' },
  { key: 'refletancia_parede', label: 'Refletância Parede' },
  { key: 'refletancia_piso', label: 'Refletância Piso' },
  { key: 'fator_manutencao', label: 'Fator de Manutenção (MF)' },
  { key: 'coeficiente_utilizacao', label: 'Coeficiente de Utilização (CU)' },
  { key: 'tipo_ambiente', label: 'Tipo Ambiente' },
  { key: 'lux_requerido', label: 'Lux Requerido' },
  { key: 'qtd_luminarias', label: 'Qtd Luminárias' },
  { key: 'potencia_w', label: 'Potência (W)' },
  { key: 'fluxo_lumens', label: 'Fluxo (Lumens)' },
  { key: 'ip', label: 'IP' },
  { key: 'fluxo_total', label: 'Fluxo Total' },
  { key: 'eficiencia_lmxw', label: 'Eficiência Luminosa (LmxW)' },
  { key: 'temperatura_cor_k', label: 'Temperatura Cor (K)' },
  { key: 'tensao', label: 'Tensão' },
  { key: 'potencia_total_w', label: 'Potência Total (W)' },
  { key: 'densidade_w_m2', label: 'Densidade (Wxm²)' },
  { key: 'lux_calculado', label: 'Lux Calculado' },
  { key: 'diferenca_lux', label: 'Diferença (lux Calc.-Lux Req.)' },
  { key: 'atende', label: 'Atende' },
];

function t18_fmt(v) {
  if (v == null) return '—';
  if (typeof v === 'number') return v.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
  return v;
}

function t18_renderTabela(linhas) {
  const el = document.getElementById('t18_tabela');
  if (!linhas.length) {
    el.innerHTML = '<p class="small" style="color:#9ca3af;">Nenhuma câmara com Tipo Ambiente + Modelo Luminária preenchidos ainda.</p>';
    return;
  }
  let html = '<table class="list" style="width:auto;"><thead><tr>' +
    T18_COLUNAS.map(c => `<th style="white-space:normal;text-align:center;">${c.label}</th>`).join('') + '</tr></thead><tbody>';
  linhas.forEach(l => {
    html += '<tr>' + T18_COLUNAS.map(c => {
      let v = l[c.key];
      if (c.key === 'atende' && v === 'Não') return `<td style="color:#b91c1c;font-weight:bold;">${v}</td>`;
      return `<td>${t18_fmt(v)}</td>`;
    }).join('') + '</tr>';
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

function t18_renderResumo(resumo) {
  const el = document.getElementById('t18_resumo');
  if (!resumo.length) { el.innerHTML = '<p class="small" style="color:#9ca3af;">—</p>'; return; }
  el.innerHTML = '<table class="list" style="width:fit-content;"><thead><tr><th>Modelo Luminária</th><th>Qtd. Total</th></tr></thead><tbody>' +
    resumo.map(r => `<tr><td>${t18_fmt(r.modelo_luminaria)}</td><td>${r.qtd_total}</td></tr>`).join('') + '</tbody></table>';
}

function t18_renderNotas(notas) {
  document.getElementById('t18_notas').innerHTML = notas.map((n, i) => `<p>${i + 1}) ${n}</p>`).join('');
}

document.addEventListener('projeto-changed', () => { if (document.getElementById('tela18').classList.contains('active')) t18_carregar(); });
window.initTelaLuminotecnico = initTelaLuminotecnico;
document.addEventListener('DOMContentLoaded', initTelaLuminotecnico);
