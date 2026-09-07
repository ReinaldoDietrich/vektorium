// Tela F — Compilação Geral. Layout invertido da Tela 5: campo = linha, câmara = coluna.
// Unidades/Rack e Condensadores são mesclados por sistema (uma célula larga cobrindo todas as
// câmaras daquele sistema) — não reaproveita o motor de tabela da Tela 5 (orientação diferente).

const T12_BLOCO_CARGA = [
  ['sistema', 'Sistema'], ['temp_ambiente', 'Temperatura Ambiente (°C)'],
  ['delta_condensacao', 'ΔT Condensação'], ['temp_condensacao', 'Temperatura de Condensação (°C)'],
  ['temp_evaporacao', 'Temperatura de Evaporação (°C)'], ['temp_interna', 'Temp. Interna (°C)'],
  ['dt_evaporacao', 'ΔT Evaporação'], ['largura', 'Largura (m)'], ['comprimento', 'Comprimento (m)'],
  ['pedireito', 'Pé-Direito (m)'], ['carga_termica_kcal_h', 'Carga Térmica (kcal/h)'],
];
const T12_BLOCO_DADOS_ENTRADA = [
  ['produto', 'Produto'], ['temp_entrada', 'Temp. Entrada Produto (°C)'],
  ['temp_saida', 'Temp. Saída Produto (°C)'], ['temp_interna', 'Temp. Interna (°C)'],
  ['mov_diaria', 'Movimentação Diária (kg/dia)'], ['qtd_estocada', 'Quantidade Estocada (kg)'],
  ['tempo_processo', 'Tempo de Processo (h)'], ['embalagem_tipo', 'Embalagem'],
  ['massa_embalagem', 'Massa Embalagem (kg/dia)'], ['num_pessoas', 'Nº de Pessoas', 0],
  ['tempo_pessoas', 'Tempo Pessoas (h/24h)'], ['qtd_luminarias', 'Qtd. Luminárias', 0],
  ['potencia_luminaria', 'Potência/Luminária (W)'],
  ['horas_iluminacao_carga', 'Horas Iluminação/Dia (carga)'], ['equipamentos', 'Equipamentos'],
  ['num_portas', 'Nº de Portas (total)', 0], ['portas', 'Portas (detalhe por porta)'],
  ['fonte_ar_paredes', 'Fonte do Ar das Paredes'], ['temp_adjacente', 'Temp. Adjacente Paredes (°C)'],
  ['umidade_adjacente', 'Umidade Adjacente Paredes (%)'],
];
const T12_BLOCO_MEMORIAL = [
  ['q1_produto', 'Q1 - Produto (kcal/h)'], ['q2_embalagem', 'Q2 - Embalagem (kcal/h)'],
  ['q3_penetracao', 'Q3 - Penetração (kcal/h)'], ['q4_infiltracao', 'Q4 - Infiltração (kcal/h)'],
  ['q5_pessoas', 'Q5 - Pessoas (kcal/h)'], ['q6_iluminacao', 'Q6 - Iluminação (kcal/h)'],
  ['q7_equipamentos', 'Q7 - Equipamentos (kcal/h)'], ['q8_forcadores', 'Q8 - Forçadores (kcal/h)'],
  ['total_24h', 'Total 24h (kcal/h)'],
];
const T12_BLOCO_FORCADORES = [
  ['quantidade', 'Quantidade de Evaporadores/Câmara', 0], ['fornecedor', 'Fornecedor'],
  ['modelo_evp', 'Modelo EVP'], ['modelo_comercial', 'Modelo Comercial'],
  ['fabricante_valvula', 'Fabricante Válvula de Expansão'], ['modelo_valvula', 'Modelo Válvula de Expansão'],
  ['gas_refrigerante', 'Gás Refrigerante'],
  ['capacidade_unit_kcal_h', 'Capacidade unit. (kcal/h)'], ['diametro_ventilador_mm', 'Tamanho Ventilador (mm)', 0],
  ['num_ventiladores', 'Qtd. Ventiladores', 0], ['vazao_ar_m3h', 'Vazão de Ar (m³/h)'], ['tensao', 'Tensão'],
  ['tipo_degelo', 'Tipo de Degelo'], ['corrente_ventiladores_a', 'Corrente Ventiladores (A)'],
  ['potencia_resist_degelo_w', 'Potências Resist. Degelo (W)', 0],
  ['corrente_resist_degelo_a', 'Corrente Resist. Degelo (A)'], ['flecha_ar_m', 'Flecha de Ar (m)'],
  ['trocas_de_ar', 'Trocas de Ar (h/24)'], ['quantidade_gas_kg', 'Quantidade de Gás (kg)'],
  ['folga_tecnica_pct', 'Folga Técnica (%)'],
];
const T12_BLOCO_RACK = [
  ['tipo_equipamento', 'Tipo de Equipamento'], ['quantidade_compressores', 'Quantidade de Compressores/Rack', 0],
  ['modelo_tecnico', 'Modelo técnico'], ['modelo_comercial', 'Modelo Comercial'], ['tensao', 'Tensão'],
  ['linha_compressor', 'Linha Compressor'], ['fabricante_compressor', 'Fabricante Compressor'],
  ['modelo_compressor', 'Modelo Compressor'], ['cop_compressor', 'COP Compressor', 2],
  ['capacidade_compressor_kcal_h', 'Capacidade Compressor (kcal/h)'],
  ['carga_total_fornecida_kcal_h', 'Carga Total Fornecida (kcal/h)'],
  ['calor_total_rejeitado_kcal_h', 'Calor Total Rejeitado Rack (kcal/h)'],
  ['potencia_total_w', 'Potência Total Rack (W)', 0], ['corrente_nominal_a', 'Corrente Nominal (A)'],
  ['corrente_maxima_trabalho_a', 'Corrente Máxima de Trabalho (A)'], ['vazao_massica_kg_h', 'Vazão Mássica (kg/h)'],
  ['carga_oleo_l', 'Carga de Óleo (L)'], ['conexao_descarga', 'Conexão Descarga (pol.)'],
  ['conexao_succao', 'Conexão Sucção (pol.)'],
  ['estrutura_equipamento', 'Estrutura Equipamento'], ['gas_refrigerante', 'Gás Refrigerante'],
  ['temp_linha_liquido', 'Temp. Linha de Líquido (°C)'], ['tanque_liquido_l', 'Tanque de Líquido (L)'],
  ['carga_gas_estimada_kg', 'Carga de Gás Estimada Sistema (kg)'], ['tipo_partida', 'Tipo de Partida'],
  ['folga_tecnica_pct', 'Folga Técnica (%)'],
];
const T12_BLOCO_CONDENSADOR = [
  ['tipo_equipamento', 'Tipo de Equipamento'], ['modelo_condensador', 'Modelo Condensador'],
  ['temp_ambiente', 'Temperatura Ambiente (°C)'], ['delta_condensacao', 'ΔT Condensação'],
  ['temp_condensacao', 'Temperatura de Condensação (°C)'], ['qtd_ventiladores', 'Qtd. Ventiladores/Condensador', 0],
  ['diametro_ventilador_mm', 'Diâmetro Ventilador (mm)', 0],
  ['tensao', 'Tensão'], ['corrente_nominal_ventiladores_a', 'Corrente Nominal Ventiladores (A)'],
  ['capacidade_condensador_kcal_h', 'Capacidade Condensador (kcal/h)'], ['folga_tecnica_pct', 'Folga Técnica (%)'],
];

function initTela12() {
  document.getElementById('t12_btnAtualizar').addEventListener('click', t12_carregar);
  document.getElementById('t12_btnImprimir').addEventListener('click', () => window.print());
  document.getElementById('t12_btnExportarExcel').addEventListener('click', () => {
    if (state.projetoId) api.baixarOuSalvar(`/api/compilacao-geral/exportar/excel?projeto_id=${state.projetoId}`);
  });
  document.addEventListener('projeto-changed', t12_onProjetoChanged);
}

function t12_onProjetoChanged() {
  const semProjeto = document.getElementById('t12_semProjeto');
  const conteudo = document.getElementById('t12_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none'; conteudo.style.display = 'block';
  t12_carregar();
}

async function t12_carregar() {
  if (!state.projetoId) return;
  const [dados, sf] = await Promise.all([
    api.get(`/api/compilacao-geral?projeto_id=${state.projetoId}`),
    api.get(`/api/compilacao/status-fechada?projeto_id=${state.projetoId}`).catch(() => ({ abertas: [], total_abertas: 0 })),
  ]);
  let bannerEl = document.getElementById('t12_bannerAbertas');
  if (!bannerEl) {
    bannerEl = document.createElement('div');
    bannerEl.id = 't12_bannerAbertas';
    document.getElementById('t12_tabela')?.parentElement?.prepend(bannerEl);
  }
  if (sf.total_abertas > 0) {
    const lista = sf.abertas.map(a => `${a.tipo}: ${a.nome}`).join(', ');
    bannerEl.style.cssText = 'background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px 14px;margin-bottom:10px;font-size:12px;color:#92400e;';
    bannerEl.innerHTML = `<strong>⚠ ${sf.total_abertas} entidade(s) aberta(s):</strong> ${lista}. Feche todas antes de compilar o projeto final.`;
  } else {
    bannerEl.style.display = 'none';
  }
  document.getElementById('t12_tabela').innerHTML = t12_render(dados);
}

function t12_fmtVal(v, dec) {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'number') return fmtNum(v, dec ?? 1);
  return v;
}

function t12_render(dados) {
  const sistemas = dados.sistemas.filter(s => s.camaras.length > 0);
  if (sistemas.length === 0) {
    return '<div class="small" style="padding:16px;text-align:center;color:#9ca3af;">Nenhuma câmara lançada ainda.</div>';
  }
  let html = '';
  if (dados.responsabilidade_dados_entrada) {
    html += `<p class="small no-print-keep" style="border:1px solid var(--line);background:#fafafa;padding:8px 10px;margin-bottom:14px;font-style:italic;">
      <b>Responsabilidade dos dados de entrada:</b> ${t12_escape(dados.responsabilidade_dados_entrada)}</p>`;
  }
  const cargaPorSistema = (dados.totais && dados.totais.carga_termica_por_sistema) || [];
  html += sistemas.map(s => t12_renderSistema(s, cargaPorSistema.find(cs => cs.sistema_nome === s.sistema_nome))).join('');
  return html;
}

function t12_escape(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Uma tabela por sistema, empilhadas (mesmo princípio da Tela 5) — evita uma tabela horizontal
// gigante com todas as câmaras do projeto juntas, e a mesclagem de Rack/Condensador nunca
// atravessa sistema (cada tabela só tem as câmaras do próprio sistema).
function t12_renderSistema(s, carga) {
  const camaras = s.camaras;
  const totalCols = camaras.length + 1;

  const secao = (titulo) => `<tr><td colspan="${totalCols}" style="background:#f3f4f6;font-weight:bold;color:#374151;padding:6px 8px;">${titulo}</td></tr>`;
  const linhaCamara = (label, blocoKey, campo, dec) => {
    let row = `<tr><td style="font-weight:bold;color:#374151;">${label}</td>`;
    camaras.forEach(c => {
      const bloco = c[blocoKey];
      row += `<td style="text-align:center;">${t12_fmtVal(bloco ? bloco[campo] : null, dec)}</td>`;
    });
    return row + '</tr>';
  };
  const linhaSistema = (label, blocoKey, campo, dec) => {
    const bloco = s[blocoKey];
    return `<tr><td style="font-weight:bold;color:#374151;">${label}</td>
      <td colspan="${camaras.length}" style="text-align:center;">${t12_fmtVal(bloco ? bloco[campo] : null, dec)}</td></tr>`;
  };

  let html = `<div style="margin-bottom:22px;">
    <div style="background:#111827;color:#fff;padding:6px 10px;font-size:12px;font-weight:bold;">SISTEMA ${s.sistema_nome}</div>
    <table class="list" style="table-layout:fixed;"><thead><tr><th style="width:220px;"></th>
      ${camaras.map(c => `<th style="text-align:center;">${c.nome}</th>`).join('')}</tr></thead><tbody>`;

  html += secao('Informações Carga');
  T12_BLOCO_CARGA.forEach(([campo, label, dec]) => { html += linhaCamara(label, 'bloco_carga', campo, dec); });

  html += secao('Dados de Entrada — Produto e Operação (fornecidos pelo cliente)');
  T12_BLOCO_DADOS_ENTRADA.forEach(([campo, label, dec]) => { html += linhaCamara(label, 'dados_entrada', campo, dec); });

  html += secao('Informações do Produto e Operação (Memorial)');
  T12_BLOCO_MEMORIAL.forEach(([campo, label, dec]) => { html += linhaCamara(label, 'memorial', campo, dec); });

  html += secao('Informações Forçadores de Ar');
  T12_BLOCO_FORCADORES.forEach(([campo, label, dec]) => { html += linhaCamara(label, 'forcador', campo, dec); });

  html += secao('Informações Unidades/Rack');
  T12_BLOCO_RACK.forEach(([campo, label, dec]) => { html += linhaSistema(label, 'rack_uc', campo, dec); });

  html += secao('Informações Condensadores');
  T12_BLOCO_CONDENSADOR.forEach(([campo, label, dec]) => { html += linhaSistema(label, 'condensador', campo, dec); });

  if (carga) {
    html += secao('Total do Sistema');
    html += `<tr><td style="font-weight:bold;color:#374151;">Carga Térmica Total Requerida (kcal/h)</td>
      <td colspan="${camaras.length}" style="text-align:center;font-weight:bold;">${t12_fmtVal(carga.carga_termica_kcal_h)}</td></tr>
      <tr><td style="font-weight:bold;color:#374151;">Qt (W)</td>
      <td colspan="${camaras.length}" style="text-align:center;font-weight:bold;">${t12_fmtVal(carga.qt_w)}</td></tr>`;
  }

  html += '</tbody></table></div>';
  return html;
}

window.initTela12 = initTela12;
window.telaShowHandlers[12] = () => { if (state.projetoId) t12_carregar(); };
document.addEventListener('DOMContentLoaded', initTela12);
