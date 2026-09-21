// Tabela larga editável (padrão FBA-6) para forçadores de ar — usada tanto para ver/editar uma
// linha já salva quanto para revisar/corrigir um Excel antes de confirmar a importação.

// O backend (Python) gera as chaves do dict de capacidades com str(float) — ex.: "10.0", "-40.0".
// O front-end tem os temps como Number (10, -40). String(10) !== "10.0", então um match direto
// de string nunca bate — precisa comparar como número dos dois lados.
function mf_capValor(capacidades, temp) {
  if (!capacidades) return null;
  const alvo = parseFloat(temp);
  for (const chave in capacidades) {
    if (parseFloat(chave) === alvo) return capacidades[chave];
  }
  return null;
}

function mf_renderMatriz(container, matriz, opts) {
  opts = opts || {};
  const temps = (matriz.temps || []).slice();
  const tensoes = (matriz.tensoes || []).slice();
  const eletLabels = [['Degelo W', 'degelo_w'], ['Degelo A', 'degelo_a'], ['Motor W', 'motores_w'], ['Motor A', 'motores_a']];

  const stickyColStyle = 'position:sticky;left:0;';

  const theadRow1 = `<tr><th rowspan="2" style="${stickyColStyle}background:#f3f4f6;z-index:3;box-shadow:2px 0 3px -2px rgba(0,0,0,.25);">Modelo</th>` +
    `<th colspan="${Math.max(temps.length, 1)}" style="text-align:center;">Capacidade (kcal/h) por Temp. Evap. (°C)</th>` +
    '<th rowspan="2">Vent.</th><th rowspan="2">Diâm.<br>(mm)</th><th rowspan="2">Vazão<br>(m³/h)</th><th rowspan="2">Flecha<br>(m)</th>' +
    tensoes.map((t, ti) => `<th colspan="4" style="text-align:center;"><input class="mf-header-tensao" data-tensao-idx="${ti}" value="${t}" style="width:110px;text-align:center;font-weight:bold;"></th>`).join('') +
    '<th rowspan="2">Linha<br>Líquido</th><th rowspan="2">Linha<br>Sucção</th><th rowspan="2">Equaliz.</th><th rowspan="2">Dreno</th>' +
    '<th rowspan="2">Peso Líq.<br>(kg)</th><th rowspan="2">Carga Gás<br>(kg)</th>' +
    '<th rowspan="2">Compr.<br>(mm)</th><th rowspan="2">Larg.<br>(mm)</th><th rowspan="2">Alt.<br>(mm)</th><th rowspan="2">Nº<br>Fixações</th>' +
    (opts.readOnly ? '' : '<th rowspan="2"></th>') + '</tr>';

  const theadRow2 = '<tr>' +
    temps.map((t, ti) => `<th><input class="mf-header-temp" data-temp-idx="${ti}" value="${t}" style="width:56px;text-align:center;font-weight:bold;"></th>`).join('') +
    tensoes.map(() => eletLabels.map(([lbl]) => `<th style="font-weight:normal;font-size:10px;">${lbl}</th>`).join('')).join('') +
    '</tr>';

  const linhasHtml = matriz.modelos.map((md, ri) => {
    let tds = `<td style="${stickyColStyle}background:#fff;z-index:1;box-shadow:2px 0 3px -2px rgba(0,0,0,.25);"><input class="mf-cell" data-r="${ri}" data-f="modelo" value="${md.modelo || ''}" style="width:100px;font-weight:bold;"></td>`;
    tds += temps.map(t => {
      const v = mf_capValor(md.capacidades, t);
      return `<td><input class="mf-cell mf-cap" data-r="${ri}" data-temp="${t}" type="number" step="any" value="${v != null ? v : ''}" style="width:64px;"></td>`;
    }).join('');
    ['num_ventiladores', 'diametro_ventilador_mm', 'vazao_ar_m3h', 'flecha_ar_m'].forEach(f => {
      tds += `<td><input class="mf-cell" data-r="${ri}" data-f="${f}" type="number" step="any" value="${md[f] != null ? md[f] : ''}" style="width:64px;"></td>`;
    });
    tds += tensoes.map(t => eletLabels.map(([, campo]) =>
      `<td><input class="mf-cell mf-elet" data-r="${ri}" data-tensao="${t}" data-campo="${campo}" type="number" step="any" value="${md.eletricas && md.eletricas[t] && md.eletricas[t][campo] != null ? md.eletricas[t][campo] : ''}" style="width:60px;"></td>`
    ).join('')).join('');
    ['linha_liquido', 'linha_succao', 'equalizador', 'dreno'].forEach(f => {
      tds += `<td><input class="mf-cell" data-r="${ri}" data-f="${f}" value="${md[f] != null ? md[f] : ''}" style="width:64px;"></td>`;
    });
    ['peso_liquido_kg', 'carga_gas_kg', 'comprimento_mm', 'largura_mm', 'altura_mm', 'num_fixacoes'].forEach(f => {
      tds += `<td><input class="mf-cell" data-r="${ri}" data-f="${f}" type="number" step="any" value="${md[f] != null ? md[f] : ''}" style="width:64px;"></td>`;
    });
    if (!opts.readOnly) {
      tds += `<td><span class="btn-text danger mf-excluir-linha" data-r="${ri}">Excluir</span></td>`;
    }
    const orig = { id: md.id, fpi: md.fpi, tipo_degelo: md.tipo_degelo, carga_refrigerante_kg: md.carga_refrigerante_kg,
      pot_resistencia_degelo_w: md.pot_resistencia_degelo_w, dt_referencia_c: md.dt_referencia_c,
      pdl_referencia_m: md.pdl_referencia_m, coletores_por_forcador: md.coletores_por_forcador,
      altura_max_instalacao_m: md.altura_max_instalacao_m, descricao_comercial: md.descricao_comercial };
    return `<tr data-row="${ri}" data-orig='${JSON.stringify(orig).replace(/'/g, "&#39;")}'>${tds}</tr>`;
  }).join('');

  container.innerHTML = `
    <div style="overflow-x:auto;width:100%;">
      <table class="list mf-table" style="table-layout:auto;white-space:nowrap;">
        <thead>${theadRow1}${theadRow2}</thead>
        <tbody class="mf-body">${linhasHtml}</tbody>
      </table>
    </div>
    ${opts.readOnly ? '' : '<p style="margin-top:8px;"><span class="btn-text" id="mf-add-modelo">+ adicionar modelo</span></p>'}
  `;

  if (!opts.readOnly) {
    container.querySelectorAll('.mf-excluir-linha').forEach(b => b.addEventListener('click', () => {
      if (!confirm('Excluir este modelo da grade?')) return;
      b.closest('tr').remove();
    }));
    const addBtn = container.querySelector('#mf-add-modelo');
    if (addBtn) addBtn.addEventListener('click', () => {
      matriz.modelos.push({ modelo: '', capacidades: {}, eletricas: {} });
      mf_renderMatriz(container, matriz, opts);
    });
  }
}

// Lê o estado atual dos inputs da tabela e devolve uma matriz no mesmo formato usado pelo backend.
function mf_coletarMatriz(container, matrizBase) {
  const temps = Array.from(container.querySelectorAll('.mf-header-temp')).map(el => el.value.trim());
  const tensoes = Array.from(container.querySelectorAll('.mf-header-tensao')).map(el => el.value.trim());
  const linhas = Array.from(container.querySelectorAll('.mf-body > tr'));

  const modelos = linhas.map((tr) => {
    const get = (f) => { const el = tr.querySelector(`[data-f="${f}"]`); return el ? el.value.trim() : ''; };
    const num = (f) => { const v = get(f); return v === '' ? null : parseNumBR(v); };
    const original = JSON.parse(tr.dataset.orig || '{}');
    const capacidades = {};
    // recoleta capacidades por posição de coluna (não pelo valor antigo do header, para suportar renomeação)
    const capInputs = Array.from(tr.querySelectorAll('.mf-cap'));
    capInputs.forEach((el, idx) => {
      const t = temps[idx];
      if (t !== '' && el.value !== '') capacidades[t] = parseNumBR(el.value);
    });
    const eletricas = {};
    const eletInputs = Array.from(tr.querySelectorAll('.mf-elet'));
    const camposEletPorTensao = 4;
    tensoes.forEach((t, ti) => {
      if (t === '') return;
      const grupo = eletInputs.slice(ti * camposEletPorTensao, ti * camposEletPorTensao + camposEletPorTensao);
      const obj = {};
      const campos = ['degelo_w', 'degelo_a', 'motores_w', 'motores_a'];
      grupo.forEach((el, gi) => { obj[campos[gi]] = el.value === '' ? null : parseNumBR(el.value); });
      eletricas[t] = obj;
    });
    return {
      modelo: get('modelo'), num_ventiladores: num('num_ventiladores'),
      diametro_ventilador_mm: num('diametro_ventilador_mm'), vazao_ar_m3h: num('vazao_ar_m3h'),
      flecha_ar_m: num('flecha_ar_m'), linha_liquido: get('linha_liquido') || null,
      linha_succao: get('linha_succao') || null, equalizador: get('equalizador') || null,
      dreno: get('dreno') || null, peso_liquido_kg: num('peso_liquido_kg'),
      carga_gas_kg: num('carga_gas_kg'), comprimento_mm: num('comprimento_mm'),
      largura_mm: num('largura_mm'), altura_mm: num('altura_mm'), num_fixacoes: num('num_fixacoes'),
      capacidades, eletricas,
      fpi: original.fpi, tipo_degelo: original.tipo_degelo, carga_refrigerante_kg: original.carga_refrigerante_kg,
      pot_resistencia_degelo_w: original.pot_resistencia_degelo_w, dt_referencia_c: original.dt_referencia_c,
      pdl_referencia_m: original.pdl_referencia_m, coletores_por_forcador: original.coletores_por_forcador,
      altura_max_instalacao_m: original.altura_max_instalacao_m,
      descricao_comercial: original.descricao_comercial || null,
      id: original.id || null,
    };
  }).filter(md => md.modelo);

  return {
    fabricante: matrizBase.fabricante, linha: matrizBase.linha, versao_catalogo: matrizBase.versao_catalogo,
    temps: temps.filter(t => t !== ''), tensoes: tensoes.filter(t => t !== ''), modelos,
  };
}
