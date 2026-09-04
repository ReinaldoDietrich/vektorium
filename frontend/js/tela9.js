// Tela D — Cálculo de Consumo Elétrico e Payback.

function initTela9() {
  document.getElementById('t9_btnSalvarObs').addEventListener('click', t9_salvarObservacao);
  document.getElementById('t9_btnRestaurarObs').addEventListener('click', t9_restaurarObservacao);
  document.getElementById('t9_btnImprimir').addEventListener('click', () => window.print());
  document.getElementById('t9_btnExportarExcel').addEventListener('click', () => {
    if (state.projetoId) api.baixarOuSalvar(`/api/consumo/exportar/excel?projeto_id=${state.projetoId}`);
  });
  window.telaShowHandlers[9] = t9_carregar;
}

async function t9_salvarObservacao() {
  if (!state.projetoId) return;
  await api.put(`/api/consumo/observacao?projeto_id=${state.projetoId}`, { texto: document.getElementById('t9_observacao').value });
  alert('Observação salva.');
}

async function t9_restaurarObservacao() {
  if (!state.projetoId) return;
  if (!confirm('Restaurar o texto padrão? A observação customizada atual será perdida.')) return;
  await api.del(`/api/consumo/observacao?projeto_id=${state.projetoId}`);
  t9_carregar();
}

async function t9_carregar() {
  const semProjeto = document.getElementById('t9_semProjeto');
  const conteudo = document.getElementById('t9_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';

  const r = await api.get(`/api/consumo/projetos/${state.projetoId}`);
  const el = document.getElementById('t9_sistemas');
  el.innerHTML = r.sistemas.map(t9_renderSistema).join('');
  document.getElementById('t9_total').innerHTML = t9_renderTotal(r.total);
  document.getElementById('t9_observacao').value = r.observacao;
  el.querySelectorAll('[data-horas-ilum]').forEach(inp => inp.addEventListener('change', async () => {
    await api.put(`/api/sistemas/${inp.dataset.horasIlum}`, { horas_iluminacao_dia: parseNumBR(inp.value) || 10 });
    t9_carregar();
  }));
  t9_ativarRedimensionamento();
}

// Larguras por coluna, iguais em TODAS as tabelas de bloco (colgroup + table-layout:fixed) — são 8
// colunas. Padrão abaixo + o que estiver salvo no navegador (por índice de coluna).
const T9_LARGURAS_COL_PADRAO = [200, 120, 120, 110, 120, 110, 110, 90];
function t9_larguraColAtual() {
  const salvo = JSON.parse(localStorage.getItem('ct_t9_larguras') || '{}');
  return T9_LARGURAS_COL_PADRAO.map((w, i) => salvo[i] || w);
}
function t9_colgroup() {
  return '<colgroup>' + t9_larguraColAtual().map(w => `<col style="width:${w}px;">`).join('') + '</colgroup>';
}

// Colunas redimensionáveis: arrastar a borda de uma coluna ajusta SÓ aquela coluna (as da esquerda
// nunca se movem, graças ao table-layout:fixed) e aplica a MESMA largura à mesma coluna em TODOS os
// blocos ao vivo — as colunas são idênticas entre os blocos (aprovado 2026-08-13). A largura é salva
// por índice de coluna (localStorage) e restaurada em todos os blocos ao recarregar a tela.
function t9_ativarRedimensionamento() {
  const tabelas = Array.from(document.querySelectorAll('#t9_sistemas table.list'));
  if (!tabelas.length) return;
  const aplicarEmTodos = (idx, largura) => {
    tabelas.forEach(t => { const c = t.querySelectorAll('colgroup col')[idx]; if (c) c.style.width = largura + 'px'; });
  };
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
        const onMove = ev => aplicarEmTodos(idx, Math.max(30, startW + (ev.pageX - startX)));
        const onUp = () => {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          const larguras = JSON.parse(localStorage.getItem('ct_t9_larguras') || '{}');
          larguras[idx] = Math.round(col.getBoundingClientRect().width);
          localStorage.setItem('ct_t9_larguras', JSON.stringify(larguras));
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
      });
    });
  });
}

function t9_renderSistema(s) {
  const cab = `<div style="background:#111827;color:#fff;padding:6px 10px;font-size:12px;font-weight:bold;">SISTEMA ${s.sistema_nome}</div>`;
  if (!s.disponivel) {
    return `<div style="border:1px solid var(--line);border-radius:6px;margin-bottom:12px;overflow:hidden;">${cab}
      <div class="small" style="padding:10px;color:#9ca3af;">${s.motivo}</div></div>`;
  }
  const linha = (rotulo, cenario) => `<tr><td>${rotulo}</td>
    <td style="text-align:right;">${fmtNum(cenario.kwh_compressor)}</td>
    <td style="text-align:right;">${fmtNum(cenario.kwh_ventiladores)}</td>
    <td style="text-align:right;">${fmtNum(cenario.kwh_degelo)}${cenario.degelo_sem_dado ? ' <span title="catálogo sem potência de degelo publicada">⚠</span>' : ''}</td>
    <td style="text-align:right;">${fmtNum(cenario.kwh_portas_drenos)}</td>
    <td style="text-align:right;">${fmtNum(cenario.kwh_iluminacao)}</td>
    <td style="text-align:right;font-weight:bold;">${fmtNum(cenario.kwh_total_mes)}</td>
    <td style="text-align:right;font-weight:bold;">R$ ${fmtNum(cenario.custo_mes)}</td></tr>`;

  const payback = s.payback_meses != null
    ? `${fmtNum(s.payback_meses)} mes(es) <span class="small" style="color:#6b7280;">(${fmtNum(s.payback_meses / 12)} anos)</span>`
    : (s.custo_sistema_simples == null || s.custo_sistema_projeto == null
        ? 'preencha Custo Sistema Simples/Projeto no cadastro do sistema (Tela 1)'
        : '— sem economia mensal, payback não se aplica');

  return `<div style="border:1px solid var(--line);border-radius:6px;margin-bottom:12px;overflow:hidden;">${cab}
    <div style="padding:10px;">
      <div class="small" style="margin-bottom:8px;color:#374151;">
        ${s.rotulo_equipamento || 'UC considerada'}: <strong>${s.modelo_uc}</strong> (${fmtNum(s.hp_uc)} HP) ·
        Carga: ${fmtNum(s.carga_total_kcal_h)} kcal/h · Capacidade: ${fmtNum(s.capacidade_uc_kcal_h)} kcal/h ·
        Fator de carga: ${fmtNum(s.fator_carga_pct)}% · Horas/dia: ${fmtNum(s.horas_funcionamento)}
        ${s.eev_ativo ? ` · Redução EEV: ${fmtNum(s.reducao_eev_pct)}%` : ''}
        ${s.modo_operacao ? ` · Redução ${s.modo_operacao}: ${fmtNum(s.reducao_operacao_pct)}%` : ''}
        ${s.ec_condensador_ativo ? ` · Redução Ventilador EC (Condensador): ${fmtNum(s.reducao_ec_condensador_pct)}%` : ''}
      </div>
      <div class="small" style="margin-bottom:8px;color:#374151;">
        <label class="lbl" style="display:inline;margin:0;">Horas de Iluminação/Dia <span class="sub">— usada pra estimar kWh de iluminação (todas as câmaras do sistema)</span></label>
        <input type="text" value="${fmtNum(s.horas_iluminacao_dia)}" data-horas-ilum="${s.sistema_id}" style="width:50px;display:inline-block;margin-left:4px;">
      </div>
      <div style="overflow-x:auto;">
      <table class="list" style="table-layout:fixed;width:auto;">
      ${t9_colgroup()}
      <thead><tr><th>Cenário</th><th style="text-align:right;">Compressor (kWh/mês)</th>
        <th style="text-align:right;">Ventiladores (kWh/mês)</th><th style="text-align:right;">Degelo (kWh/mês)</th>
        <th style="text-align:right;">Portas/Drenos (kWh/mês)</th><th style="text-align:right;">Iluminação (kWh/mês)</th>
        <th style="text-align:right;">Total (kWh/mês)</th><th style="text-align:right;">Custo/mês</th></tr></thead>
      <tbody>
        ${linha('Projeto (conforme configurado)', s.projeto)}
        ${linha('Simples (sem otimizações)', s.simples)}
      </tbody></table>
      </div>
      <div class="small" style="margin-top:8px;">
        Economia mensal: <strong>R$ ${fmtNum(s.economia_mes)}</strong> ·
        Payback: <strong>${payback}</strong>
      </div>
    </div>
  </div>`;
}

function t9_renderTotal(t) {
  return `<div style="overflow-x:auto;">
    <table class="list" style="table-layout:fixed;width:auto;">
    ${t9_colgroup()}
    <thead><tr><th>Cenário</th><th></th><th></th><th></th><th></th><th></th>
      <th style="text-align:right;">Total (kWh/mês)</th><th style="text-align:right;">Custo/mês</th></tr></thead>
    <tbody>
      <tr><td>Projeto</td><td></td><td></td><td></td><td></td><td></td>
        <td style="text-align:right;font-weight:bold;">${fmtNum(t.kwh_projeto_mes)}</td>
        <td style="text-align:right;font-weight:bold;">R$ ${fmtNum(t.custo_projeto_mes)}</td></tr>
      <tr><td>Simples</td><td></td><td></td><td></td><td></td><td></td>
        <td style="text-align:right;font-weight:bold;">${fmtNum(t.kwh_simples_mes)}</td>
        <td style="text-align:right;font-weight:bold;">R$ ${fmtNum(t.custo_simples_mes)}</td></tr>
    </tbody></table>
    </div>
    <div class="small" style="margin-top:8px;">
      Economia mensal total: <strong>R$ ${fmtNum(t.economia_mes)}</strong> ·
      Payback total do projeto: <strong>${t.payback_meses != null ? fmtNum(t.payback_meses) + ' mes(es) (' + fmtNum(t.payback_meses / 12) + ' anos)' : '—'}</strong>
    </div>`;
}

window.initTela9 = initTela9;
document.addEventListener('DOMContentLoaded', initTela9);
