// Tela 1 — Seleção de Unidade Condensadora por Sistema (versão teste Tela B).
// Mostra o total de carga agrupado de cada sistema e permite selecionar até 5 UCs (regula por %
// de folga), no mesmo padrão do forçador. Reaproveita os endpoints /api/uc/*.
//
// Cadeia de filtros em cascata (cada campo só mostra opções compatíveis com os anteriores):
// Fabricante UC > Linha (Catálogo) > Tipo Compressor > Fabricante Compressor > Nº Compressores >
// Faixa de Operação > Folga. Trocar um campo invalida (limpa) os campos seguintes na cadeia.

let t1uc_addFiltros = {};   // filtros do add-row, por sistema_id — não persiste no servidor até o "+"

const T1UC_CASCATA = [
  ['fab', 'fabricante_uc'], ['linha', 'catalogo_id'], ['tipo', 'tipo_compressor'],
  ['fabcomp', 'fabricante_compressor'], ['numcomp', 'numero_compressores'], ['faixa', 'faixa_operacao'],
];

// Campos a limpar quando um campo anterior da cadeia muda.
const T1UC_CASCATA_LIMPAR = {
  fabricante_uc: ['catalogo_id', 'tipo_compressor', 'fabricante_compressor', 'numero_compressores', 'faixa_operacao'],
  catalogo_id: ['tipo_compressor', 'fabricante_compressor', 'numero_compressores', 'faixa_operacao'],
  tipo_compressor: ['fabricante_compressor', 'numero_compressores', 'faixa_operacao'],
  fabricante_compressor: ['numero_compressores', 'faixa_operacao'],
  numero_compressores: ['faixa_operacao'],
  faixa_operacao: [],
};

function t1uc_attrParaDataset(attr) {
  return attr.charAt(0).toUpperCase() + attr.slice(1);
}

async function t1uc_fetchOpcoes(filtros) {
  const params = new URLSearchParams();
  if (filtros.fabricante_uc) params.set('fabricante_uc', filtros.fabricante_uc);
  if (filtros.catalogo_id) params.set('catalogo_id', filtros.catalogo_id);
  if (filtros.tipo_compressor) params.set('tipo_compressor', filtros.tipo_compressor);
  if (filtros.fabricante_compressor) params.set('fabricante_compressor', filtros.fabricante_compressor);
  if (filtros.numero_compressores) params.set('numero_compressores', filtros.numero_compressores);
  return api.get(`/api/uc/opcoes?${params.toString()}`);
}

function t1uc_camposCascata(prefixo, id, filtros, opcoes) {
  const sel = (campo, valor) => filtros[campo] != null && String(filtros[campo]) === String(valor) ? 'selected' : '';
  return `
    <div><label class="lbl">Fabricante UC</label>
      <select data-${prefixo}-fab="${id}">
        <option value="">qualquer</option>
        ${opcoes.fabricantes_uc.map(v => `<option value="${v}" ${sel('fabricante_uc', v)}>${v}</option>`).join('')}
      </select></div>
    <div><label class="lbl">Linha (Catálogo)</label>
      <select data-${prefixo}-linha="${id}">
        <option value="">qualquer</option>
        ${opcoes.linhas.map(l => `<option value="${l.id}" ${sel('catalogo_id', l.id)}>${l.nome}</option>`).join('')}
      </select></div>
    <div><label class="lbl">Tipo Compressor</label>
      <select data-${prefixo}-tipo="${id}">
        <option value="">qualquer</option>
        ${opcoes.tipos_compressor.map(v => `<option value="${v}" ${sel('tipo_compressor', v)}>${v}</option>`).join('')}
      </select></div>
    <div><label class="lbl">Fab. Compressor</label>
      <select data-${prefixo}-fabcomp="${id}">
        <option value="">qualquer</option>
        ${opcoes.fabricantes_compressor.map(v => `<option value="${v}" ${sel('fabricante_compressor', v)}>${v}</option>`).join('')}
      </select></div>
    <div><label class="lbl">Nº Compressores</label>
      <select data-${prefixo}-numcomp="${id}">
        <option value="">qualquer</option>
        ${opcoes.numeros_compressores.map(v => `<option value="${v}" ${sel('numero_compressores', v)}>${v}</option>`).join('')}
      </select></div>
    <div><label class="lbl">Faixa de Operação</label>
      <select data-${prefixo}-faixa="${id}">
        <option value="">qualquer</option>
        ${opcoes.faixas_operacao.map(v => `<option value="${v}" ${sel('faixa_operacao', v)}>${v}</option>`).join('')}
      </select></div>`;
}

async function t1uc_render() {
  const el = document.getElementById('ucSelecaoSistemas');
  if (!el) return;
  if (!state.projetoId) { el.innerHTML = ''; return; }
  try {
  const totais = await api.get(`/api/uc/sistemas/${state.projetoId}/totais`);
  if (!totais.length) { el.innerHTML = '<div class="small" style="padding:10px;color:#9ca3af;">Cadastre sistemas acima primeiro.</div>'; return; }

  let html = '';
  const mapaSelecoes = {};   // id da selecao -> objeto (pra ler campos_selecionados atual antes de gravar)
  for (const s of totais) {
    const sel = await api.get(`/api/uc/sistemas/${s.sistema_id}/selecao`);
    sel.selecoes.forEach(o => { mapaSelecoes[o.id] = o; });
    html += `<div style="border:1px solid var(--line);border-radius:6px;margin-bottom:12px;">
      <div style="background:#111827;color:#fff;padding:6px 10px;font-size:12px;font-weight:bold;">
        SISTEMA ${s.sistema_nome} — Carga total: ${fmtNum(s.carga_total_kcal_h)} kcal/h
        <span style="font-weight:normal;color:#9ca3af;"> · T.Evap ${s.temp_evaporacao ?? '—'}°C · T.Amb ${sel.temp_ambiente ?? '—'}°C</span>
      </div>
      <div style="padding:8px 10px;">`;

    if (sel.selecoes.length === 0) {
      html += '<div class="small" style="color:#9ca3af;padding:4px;">Nenhuma opção adicionada.</div>';
    } else {
      for (const o of sel.selecoes) {
        const opcoesLinha = await t1uc_fetchOpcoes(o);
        let badge = '';
        if (o.fechada) {
          badge = o.calculo_desatualizado
            ? '<span class="badge-fechada desatualizada" style="margin-left:6px;">desatualizado</span>'
            : '<span class="badge-fechada ok" style="margin-left:6px;">fechada</span>';
        }
        html += `<div style="border:1px solid var(--line);border-radius:6px;padding:8px;margin-bottom:8px;" ${o.fechada ? 'class="entidade-fechada"' : ''}>
          ${o.fechada ? '<div class="c-barra-fechada" style="display:flex;">Seleção fechada — clique em <strong>Editar</strong> para reabrir.' + badge + '</div>' : ''}
          <div class="uc-cascata-fields" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
            ${t1uc_camposCascata('sel', o.id, o, opcoesLinha)}
            <div><label class="lbl">Folga %</label><input type="text" value="${o.folga_desejada ?? ''}" style="width:56px;" data-sel-folga="${o.id}"></div>
            <div><label class="lbl" title="Nº de unidades idênticas em paralelo dividindo a demanda do sistema">Qtd paralelo</label><input type="text" value="${o.quantidade_paralelo ?? 1}" style="width:56px;" data-sel-qtdpar="${o.id}"></div>
            <div><label style="font-size:11px;color:${o.considerado ? '#15803d' : '#6b7280'};font-weight:${o.considerado ? 'bold' : 'normal'};">
              <input type="radio" name="uc-consid-${s.sistema_id}" ${o.considerado ? 'checked' : ''} data-uc-consid="${o.id}"> Considerar</label></div>
            <div><span class="btn-text danger" data-uc-excluir="${o.id}">Excluir</span></div>
            ${o.fechada
              ? '<div><button class="btn c-btn-editar" data-uc-editar="' + o.id + '">Editar</button></div>'
              : ''}
          </div>
          <div class="small" style="color:#6b7280;margin-top:4px;">
            ${(o.quantidade_paralelo || 1) > 1 ? '<strong>' + o.quantidade_paralelo + '× em paralelo</strong> · carga/unid. ' + fmtNum(o.carga_por_unidade_kcal_h) + ' kcal/h · ' : ''}${o.modelo_resultante || '—'}
            ${o.capacidade_kcal_h != null ? ' · ' + fmtNum(o.capacidade_kcal_h) + ' kcal/h/unid.' : ''}
            ${o.folga_real != null ? ' · folga real ' + o.folga_real + '%' : ''}
          </div>`;
        if (o.unidade_id) {
          // Todas as colunas da nomenclatura aparecem (Fixo/Automático mostram o valor já resolvido
          // pelo backend, só leitura; Ignorar aparece cinza sem valor; Manual é a única editável
          // aqui) — estrutura (rótulo/opções/ordem/Modo) é editada dentro do próprio catálogo (Tela B).
          const campos = o.nomenclatura_campos || [];
          const selecionados = o.campos_selecionados || {};
          html += `<div style="background:#f9fafb;padding:8px 10px;margin-top:6px;">`;
          if (!campos.length) {
            html += `<div class="small" style="color:#9ca3af;">Nomenclatura ainda não disponível — cadastre em Tela B, dentro do catálogo desta unidade.</div>`;
          } else {
            html += `<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start;padding:4px 0;">
              ${campos.map(c => {
                const campoDiv = (conteudo) => `<div style="width:120px;flex:0 0 120px;">
                  <label class="lbl" style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${c.nome_campo ?? ''}">${c.nome_campo ?? ''}</label>
                  ${conteudo}
                </div>`;
                if (c.modo === 'ignorar') {
                  return campoDiv(`<div class="small" style="padding:6px 0;color:#9ca3af;">— (ignorado)</div>`);
                }
                if (c.modo === 'modelo_pesquisa') {
                  return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;" title="Modelo técnico do catálogo — não editável aqui">${c.valor_atual || '—'}</div>`);
                }
                if (c.modo === 'automatico') {
                  return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                      title="Automático, conforme dado já definido">
                      ${c.valor_atual ? c.valor_atual + ' (auto)' : '— sem dado'}
                    </div>`);
                }
                if (c.modo === 'fixo') {
                  return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;">${c.valor_atual || '—'} (fixo)</div>`);
                }
                return campoDiv(`<select data-uc-flut="${o.id}" data-uc-flut-campo="${c.nome_campo}" style="width:100%;">
                    <option value="">—</option>
                    ${c.opcoes.map(op => `<option value="${op.valor}" title="${op.valor}" ${selecionados[c.nome_campo] === op.valor ? 'selected' : ''}>${op.valor}</option>`).join('')}
                  </select>`);
              }).join('')}
            </div>
            <div class="small" style="color:#111827;margin-top:8px;">Código comercial (compra): <code style="font-weight:bold;">${o.codigo_comercial || '—'}</code></div>`;
          }
          html += `<div class="small" style="color:#6b7280;margin-top:6px;">
            Compressores: ${o.numero_compressores_uc ?? '—'}× ${o.modelo_compressor || '—'}
            · MCC: ${o.mcc_a != null ? fmtNum(o.mcc_a, 1) + ' A' : '—'}
            · RLA: ${o.rla_a != null ? fmtNum(o.rla_a, 1) + ' A' : '—'}
          </div>`;
          html += `</div>`;
        }
        html += `</div>`;
      }
    }

    // add-row — oculta por padrão (tela enxuta); botão "+" revela os campos
    if (!t1uc_addFiltros[s.sistema_id]) t1uc_addFiltros[s.sistema_id] = {};
    const opcoesAdd = await t1uc_fetchOpcoes(t1uc_addFiltros[s.sistema_id]);
    html += `<p style="margin:6px 0 0;"><button class="btn-wide" data-uc-revelar="${s.sistema_id}" type="button">+ Adicionar opção de UC</button></p>
      <div data-uc-addwrap="${s.sistema_id}" style="display:none;">
      <div class="uc-cascata-fields" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-top:6px;" data-uc-addfields="${s.sistema_id}">
        ${t1uc_camposCascata('add', s.sistema_id, t1uc_addFiltros[s.sistema_id], opcoesAdd)}
        <div><label class="lbl">Folga %</label><input type="text" value="10" data-add-folga="${s.sistema_id}"></div>
        <div><label class="lbl">&nbsp;</label><button class="btn" data-uc-add="${s.sistema_id}">+</button></div>
      </div>
      <p style="text-align:right;margin:4px 0 0;"><span class="btn-text" data-uc-fechar="${s.sistema_id}">Fechar</span></p>
      </div>`;
    html += '</div></div>';
  }
  el.innerHTML = html;

  // ---- linhas já existentes: cada campo da cadeia dispara PUT (limpando os campos seguintes) ----
  for (const [attr, campo] of T1UC_CASCATA) {
    el.querySelectorAll(`[data-sel-${attr}]`).forEach(sel2 => sel2.addEventListener('change', async () => {
      const id = sel2.dataset[`sel${t1uc_attrParaDataset(attr)}`];
      const payload = { [campo]: sel2.value || null };
      for (const limpar of (T1UC_CASCATA_LIMPAR[campo] || [])) payload[limpar] = null;
      await api.put(`/api/uc/selecao/${id}`, payload);
      t1uc_render();
    }));
  }
  el.querySelectorAll('[data-sel-folga]').forEach(inp => inp.addEventListener('change', async () => {
    await api.put(`/api/uc/selecao/${inp.dataset.selFolga}`, { folga_desejada: parseNumBR(inp.value) });
    t1uc_render();
  }));
  el.querySelectorAll('[data-sel-qtdpar]').forEach(inp => inp.addEventListener('change', async () => {
    // Nº de UCs idênticas em paralelo — a seleção passa a dividir a demanda do sistema por N.
    await api.put(`/api/uc/selecao/${inp.dataset.selQtdpar}`, { quantidade_paralelo: Math.max(parseInt(inp.value, 10) || 1, 1) });
    t1uc_render();
  }));
  el.querySelectorAll('[data-uc-consid]').forEach(inp => inp.addEventListener('change', async () => {
    await api.put(`/api/uc/selecao/${inp.dataset.ucConsid}`, { considerado: true });
    t1uc_render();
  }));
  el.querySelectorAll('[data-uc-excluir]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir esta seleção de UC?')) return;
    try {
      await api.del(`/api/uc/selecao/${b.dataset.ucExcluir}`);
      t1uc_render();
    } catch (err) { alert('Erro ao excluir seleção: ' + err.message); }
  }));
  el.querySelectorAll('[data-uc-editar]').forEach(b => b.addEventListener('click', async () => {
    await api.post(`/api/uc/selecao/${b.dataset.ucEditar}/editar`, {});
    t1uc_render();
  }));
  el.querySelectorAll('[data-uc-flut]').forEach(sel2 => sel2.addEventListener('change', async () => {
    const selId = sel2.dataset.ucFlut;
    const atual = { ...(mapaSelecoes[selId]?.campos_selecionados || {}) };
    if (sel2.value) atual[sel2.dataset.ucFlutCampo] = sel2.value;
    else delete atual[sel2.dataset.ucFlutCampo];
    await api.put(`/api/uc/selecao/${selId}`, { campos_selecionados: atual });
    // guarda no mapa local para não perder os já escolhidos entre um campo e outro
    if (mapaSelecoes[selId]) mapaSelecoes[selId].campos_selecionados = atual;
    // Só re-renderiza o painel quando TODOS os campos MANUAIS desta seleção estiverem preenchidos
    // (Automático/Fixo/Ignorar/Modelo Pesquisa não são <select>, então não contam) — evita o
    // re-render a cada campo, que causava reset/corrida (aprovado 2026-08-13).
    const manuais = el.querySelectorAll(`[data-uc-flut="${selId}"]`);
    if ([...manuais].every(s => s.value)) t1uc_render();
  }));
  el.querySelectorAll('[data-uc-revelar]').forEach(b => b.addEventListener('click', () => {
    const sid = b.dataset.ucRevelar;
    el.querySelector(`[data-uc-addwrap="${sid}"]`).style.display = 'block';
    b.style.display = 'none';
  }));
  el.querySelectorAll('[data-uc-fechar]').forEach(b => b.addEventListener('click', () => {
    const sid = b.dataset.ucFechar;
    el.querySelector(`[data-uc-addwrap="${sid}"]`).style.display = 'none';
    el.querySelector(`[data-uc-revelar="${sid}"]`).style.display = 'inline-block';
  }));

  // ---- add-row: cada campo da cadeia refaz o fetch de opções em cascata só pra essa linha,
  // sem persistir no servidor (fica em t1uc_addFiltros até o usuário clicar "+") ----
  el.querySelectorAll('[data-uc-addfields]').forEach(fields => t1uc_wireAddFields(el, fields.dataset.ucAddfields));
  el.querySelectorAll('[data-uc-add]').forEach(b => b.addEventListener('click', () => t1uc_confirmarAdd(el, b.dataset.ucAdd)));
  } catch (err) {
    el.innerHTML = `<div style="color:red;padding:10px;">Erro ao carregar seleção de UC: ${err.message}</div>`;
  }
}

function t1uc_wireAddFields(el, sid) {
  for (const [attr, campo] of T1UC_CASCATA) {
    const sel2 = el.querySelector(`[data-add-${attr}="${sid}"]`);
    if (!sel2) continue;
    sel2.addEventListener('change', async () => {
      t1uc_addFiltros[sid] = t1uc_addFiltros[sid] || {};
      t1uc_addFiltros[sid][campo] = sel2.value || null;
      for (const limpar of (T1UC_CASCATA_LIMPAR[campo] || [])) t1uc_addFiltros[sid][limpar] = null;
      const folgaAtual = el.querySelector(`[data-add-folga="${sid}"]`)?.value ?? '10';
      const opcoes = await t1uc_fetchOpcoes(t1uc_addFiltros[sid]);
      const container = el.querySelector(`[data-uc-addfields="${sid}"]`);
      container.innerHTML = t1uc_camposCascata('add', sid, t1uc_addFiltros[sid], opcoes) +
        `<div><label class="lbl">Folga %</label><input type="text" value="${folgaAtual}" data-add-folga="${sid}"></div>
        <div><label class="lbl">&nbsp;</label><button class="btn" data-uc-add="${sid}">+</button></div>`;
      t1uc_wireAddFields(el, sid);
      el.querySelector(`[data-uc-add="${sid}"]`).addEventListener('click', () => t1uc_confirmarAdd(el, sid));
    });
  }
}

async function t1uc_confirmarAdd(el, sid) {
  const filtros = t1uc_addFiltros[sid] || {};
  await api.post(`/api/uc/sistemas/${sid}/selecao`, {
    fabricante_uc: filtros.fabricante_uc || null, catalogo_id: filtros.catalogo_id || null,
    tipo_compressor: filtros.tipo_compressor || null, fabricante_compressor: filtros.fabricante_compressor || null,
    numero_compressores: filtros.numero_compressores || null, faixa_operacao: filtros.faixa_operacao || null,
    folga_desejada: parseNumBR(el.querySelector(`[data-add-folga="${sid}"]`).value) || 10,
  });
  t1uc_addFiltros[sid] = {};
  t1uc_render();
}

window.t1uc_render = t1uc_render;
