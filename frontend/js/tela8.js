// Tela B — Unidades Condensadoras Comerciais
async function t8_carregarSubtreeIdPai() {
  const sel = document.getElementById('uc_idPai');
  sel.innerHTML = '<option value="">(automático)</option>';
  try {
    const nos = await api.get('/api/catalogos/ids-comerciais/subtree?raiz=4.1.1');
    for (const n of nos) {
      const indent = '  '.repeat(n.codigo.split('.').length - 3);
      sel.innerHTML += `<option value="${n.codigo}">${indent}${n.codigo} — ${n.nome}</option>`;
    }
  } catch (e) { /* mantém só a opção automático */ }
}

let t8_previewArquivo = null;
let t8_previewDados = null; // {unidades:[{unidade,capacidades,...}], campos:[...]} — editável na tela
let t8_unidadeAtual = null;

// Mecânica: identidade + físico/dimensional — NÃO varia por tensão. Elétrica (Tensão × Modelo de
// Compressor) fica na sub-aba própria (T8_CAMPOS_ELETRICA_EDIT), uma unidade pode ter várias linhas.
// Fabricante/Versão/Nome/Descrição/Foto do catálogo NÃO ficam aqui — são do CatalogoUC (editados
// no painel do catálogo, ver t8_abrirCatalogo), igual ao padrão do Forçador (LinhaForcador).
const T8_CAMPOS_EDIT = [
  ['modelo', 'Modelo'],
  ['sistema', 'Sistema'], ['gas', 'Gás'], ['tipo_compressor', 'Tipo Compressor'],
  ['fabricante_compressor', 'Fabricante Compressor'], ['numero_compressores', 'Nº de Compressores'],
  ['hp', 'HP'], ['vent_qtd', 'Vent. Qtd'], ['ventilador_diametro_mm', 'Vent. Ø (mm)'],
  ['conexao_liquido', 'Conexão Líquido'], ['conexao_succao', 'Conexão Sucção'],
  ['tanque_liquido_l', 'Tanque Líq. (L)'], ['nivel_ruido_db', 'Ruído (dB)'],
  ['comprimento_mm', 'Comprimento (mm)'], ['largura_mm', 'Largura (mm)'], ['altura_mm', 'Altura (mm)'],
  ['peso_liquido_kg', 'Peso Líq. (kg)'], ['peso_bruto_kg', 'Peso Bruto (kg)'],
];

const T8_CAMPOS_ELETRICA_EDIT = [
  ['tensao', 'Tensão'], ['fases', 'Fases'], ['frequencia', 'Frequência'],
  ['modelo_compressor', 'Modelo Compressor'], ['mcc_a', 'MCC (A)'], ['rla_a', 'RLA (A)'], ['lra_a', 'LRA (A)'],
  ['vent_tensao', 'Vent. Tensão'], ['vent_fases', 'Vent. Fases'], ['vent_frequencia', 'Vent. Freq.'],
  ['vent_corrente_a', 'Vent. Corr. (A)'],
];
const T8_NUM_ELETRICA = ['fases', 'mcc_a', 'rla_a', 'lra_a', 'vent_fases', 'vent_corrente_a'];

function initTela8() {
  document.getElementById('ucBtnTemplate').addEventListener('click', () => { window.location.href = '/api/uc/template'; });
  document.getElementById('ucBtnDocumento').addEventListener('click', () => { window.location.href = '/api/uc/documento'; });
  document.getElementById('ucArquivo').addEventListener('change', t8_preview);
  document.getElementById('ucPrevTabMec').addEventListener('click', () => t8_previewTab('mec'));
  document.getElementById('ucPrevTabEle').addEventListener('click', () => t8_previewTab('ele'));
  document.getElementById('ucBtnConfirmar').addEventListener('click', t8_confirmar);
  document.getElementById('ucBtnCancelar').addEventListener('click', t8_cancelarPreview);
  document.getElementById('ucBtnFechar').addEventListener('click', t8_fechar);
  document.getElementById('ucBtnSalvar').addEventListener('click', t8_salvar);
  document.getElementById('ucBtnExcluir').addEventListener('click', t8_excluir);
  document.getElementById('ucBtnExportar').addEventListener('click', () => { window.location.href = '/api/uc/exportar-bd'; });
  document.getElementById('ucDetTabMec').addEventListener('click', () => t8_detTab('mec'));
  document.getElementById('ucDetTabEle').addEventListener('click', () => t8_detTab('ele'));
  window.telaShowHandlers[8] = t8_carregarCatalogo;
}

function t8_detTab(qual) {
  document.getElementById('ucDetTabMec').classList.toggle('active', qual === 'mec');
  document.getElementById('ucDetTabEle').classList.toggle('active', qual === 'ele');
  document.getElementById('ucDetalhe').style.display = qual === 'mec' ? 'block' : 'none';
  document.getElementById('ucDetalheEletrica').style.display = qual === 'ele' ? 'block' : 'none';
}

function t8_previewTab(qual) {
  document.getElementById('ucPrevTabMec').classList.toggle('active', qual === 'mec');
  document.getElementById('ucPrevTabEle').classList.toggle('active', qual === 'ele');
  document.getElementById('ucPreviewMecanica').style.display = qual === 'mec' ? 'block' : 'none';
  document.getElementById('ucPreviewEletrica').style.display = qual === 'ele' ? 'block' : 'none';
}

// Unidade: identidade + físico/dimensional (não varia por tensão). Elétrica fica em tabela à parte
// por unidade — uma linha por Tensão × Modelo de Compressor (T8_CAMPOS_ELETRICA_PREVIEW).
const T8_CAMPOS_ELETRICA = [
  ['Fabricante_UC', 'Fabricante'], ['Modelo', 'Modelo'], ['Versao_Catalogo', 'Versão'],
  ['Sistema', 'Sistema'], ['Gas', 'Gás'], ['Tipo_Compressor', 'Tipo Compressor'],
  ['Fabricante_Compressor', 'Fab. Compressor'], ['Numero_Compressores', 'Nº Compressores'], ['HP', 'HP'],
  ['Vent_Qtd', 'Qtd Vent.'], ['Conexao_Liquido', 'Conex. Líq.'], ['Conexao_Succao', 'Conex. Sucção'],
  ['Tanque_Liquido_L', 'Tanque (L)'], ['Nivel_Ruido_dB', 'Ruído (dB)'],
  ['Ventilador_Diametro_mm', 'Ø Vent. (mm)'], ['Comprimento_mm', 'Compr. (mm)'],
  ['Largura_mm', 'Larg. (mm)'], ['Altura_mm', 'Alt. (mm)'], ['Peso_Liquido_kg', 'Peso Líq. (kg)'],
  ['Peso_Bruto_kg', 'Peso Bruto (kg)'], ['Descricao_Comercial', 'Descrição Comercial'],
];
const T8_CAMPOS_ELETRICA_PREVIEW = [
  ['Tensao', 'Tensão'], ['Fases', 'Fases'], ['Frequencia', 'Freq.'], ['Modelo_Compressor', 'Modelo Compressor'],
  ['MCC_A', 'MCC (A)'], ['RLA_A', 'RLA (A)'], ['LRA_A', 'LRA (A)'],
  ['Vent_Tensao', 'Tensão Vent.'], ['Vent_Fases', 'Fases Vent.'], ['Vent_Frequencia', 'Freq. Vent.'],
  ['Vent_Corrente_A', 'Corr. Vent. (A)'],
];
const T8_NUM_ELETRICA_PREVIEW = ['Fases', 'MCC_A', 'RLA_A', 'LRA_A', 'Vent_Fases', 'Vent_Corrente_A'];

async function t8_preview(ev) {
  const file = ev.target.files[0];
  if (!file) return;
  t8_previewArquivo = file;
  const fd = new FormData();
  fd.append('arquivo', file);
  const r = await fetch('/api/uc/preview', { method: 'POST', body: fd }).then(x => x.json());
  const el = document.getElementById('ucResultado');
  if (r.erro) { el.innerHTML = `<span style="color:#b91c1c;">${r.erro}</span>`; return; }
  t8_previewDados = r;
  el.innerHTML = `${r.unidades.length} unidade(s) lida(s), ${r.campos.length} campo(s) de nomenclatura — confira e corrija abaixo antes de gravar.`;
  t8_renderPreviewMatriz();
  t8_previewTab('mec');
  document.getElementById('ucPreviewWrap').style.display = 'block';
  t8_carregarSubtreeIdPai();
}

// Reabre um catálogo já confirmado antes, direto do banco, na mesma matriz de edição em lote
// usada na importação — sem precisar do arquivo .xlsx original (item pedido pelo usuário).
async function t8_editarCatalogoMatriz(catalogoId) {
  const r = await api.get(`/api/uc/catalogos-detalhe/${catalogoId}/matriz`);
  if (r.erro) { alert(r.erro); return; }
  t8_previewArquivo = null;
  t8_previewDados = r;
  document.getElementById('ucResultado').innerHTML = `${r.unidades.length} unidade(s) carregada(s) do catálogo — confira e corrija abaixo, depois clique em Confirmar Importação pra salvar.`;
  t8_renderPreviewMatriz();
  t8_previewTab('mec');
  document.getElementById('ucPreviewWrap').style.display = 'block';
  t8_carregarSubtreeIdPai();
  document.getElementById('ucPreviewWrap').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function t8_renderPreviewMatriz() {
  const itens = t8_previewDados.unidades;

  // ---- aba Mecânica: uma tabela por unidade (Temp.Amb × Temp.Evap, Q/P editáveis) ----
  const mec = document.getElementById('ucPreviewMecanica');
  mec.innerHTML = itens.map((it, ui) => {
    const ambs = it.temps_ambiente.length ? it.temps_ambiente : [null];
    const evaps = it.temps_evaporacao;
    const idx = {};
    it.capacidades.forEach(c => { idx[`${c.Temp_Ambiente_C}_${c.Temp_Evaporacao_C}`] = c; });
    let tbl = `<div style="margin-bottom:14px;border:1px solid var(--line);border-radius:6px;padding:8px;">
      <div style="font-weight:bold;font-size:12px;margin-bottom:6px;">${it.unidade.Modelo || '(sem modelo)'} — ${it.unidade.Gas || ''}</div>
      <div style="overflow-x:auto;"><table class="list" style="white-space:nowrap;"><thead><tr><th>T.Amb \\ T.Evap</th>`;
    evaps.forEach(e => { tbl += `<th style="text-align:center;">${e}°C</th>`; });
    tbl += '</tr></thead><tbody>';
    ambs.forEach(amb => {
      ['Q', 'P'].forEach(tipo => {
        tbl += `<tr><td style="font-weight:bold;">${amb ?? '—'}°C ${tipo}</td>`;
        evaps.forEach(e => {
          const c = idx[`${amb}_${e}`];
          const campo = tipo === 'Q' ? 'Capacidade_kcal_h' : 'Potencia_kW';
          const v = c ? c[campo] : null;
          tbl += `<td><input type="text" data-uc-cap="${ui}" data-amb="${amb}" data-evap="${e}" data-campo="${campo}" value="${v ?? ''}" style="width:64px;"></td>`;
        });
        tbl += '</tr>';
      });
    });
    tbl += '</tbody></table></div></div>';
    return tbl;
  }).join('');

  // ---- aba Elétrica/Física/Dimensional: 1 linha escalar por unidade (físico) + tabela aninhada
  // de elétrica (várias linhas por unidade, uma por Tensão × Modelo de Compressor) ----
  const ele = document.getElementById('ucPreviewEletrica');
  ele.innerHTML = itens.map((it, ui) => {
    let bloco = `<div style="margin-bottom:14px;border:1px solid var(--line);border-radius:6px;padding:8px;">
      <div style="font-weight:bold;font-size:12px;margin-bottom:6px;">${it.unidade.Modelo || '(sem modelo)'} — ${it.unidade.Gas || ''}</div>
      <div style="overflow-x:auto;"><table class="list" style="white-space:nowrap;"><thead><tr>
        ${T8_CAMPOS_ELETRICA.map(([, lbl]) => `<th>${lbl}</th>`).join('')}</tr></thead><tbody><tr>
        ${T8_CAMPOS_ELETRICA.map(([campo]) =>
          `<td><input type="text" data-uc-escalar="${ui}" data-campo="${campo}" value="${it.unidade[campo] ?? ''}" style="width:${campo === 'Descricao_Comercial' ? 130 : 76}px;"></td>`).join('')}
        </tr></tbody></table></div>
      <div class="small" style="margin:8px 0 4px;color:#6b7280;">Elétrica — uma linha por Tensão × Modelo de Compressor</div>
      <div style="overflow-x:auto;"><table class="list" style="white-space:nowrap;"><thead><tr>
        ${T8_CAMPOS_ELETRICA_PREVIEW.map(([, lbl]) => `<th>${lbl}</th>`).join('')}<th></th></tr></thead><tbody>`;
    (it.eletricas || []).forEach((e, ei) => {
      bloco += `<tr>${T8_CAMPOS_ELETRICA_PREVIEW.map(([campo]) =>
        `<td><input type="text" data-uc-elet="${ui}" data-elet-idx="${ei}" data-campo="${campo}" value="${e[campo] ?? ''}" style="width:76px;"></td>`).join('')}
        <td><span class="btn-text danger" data-uc-elet-del="${ui}" data-elet-del-idx="${ei}">Excluir</span></td></tr>`;
    });
    bloco += `</tbody></table></div>
      <p style="margin-top:6px;"><span class="btn-text" data-uc-elet-add="${ui}">+ Adicionar linha de Elétrica</span></p>
      </div>`;
    return bloco;
  }).join('');

  ele.querySelectorAll('[data-uc-elet-add]').forEach(b => b.addEventListener('click', () => {
    const dados = t8_coletarPreviewEditado();
    const ui = Number(b.dataset.ucEletAdd);
    dados.unidades[ui].eletricas = dados.unidades[ui].eletricas || [];
    dados.unidades[ui].eletricas.push({ Modelo: dados.unidades[ui].unidade.Modelo });
    t8_previewDados = dados;
    t8_renderPreviewMatriz();
    t8_previewTab('ele');
  }));
  ele.querySelectorAll('[data-uc-elet-del]').forEach(b => b.addEventListener('click', () => {
    const dados = t8_coletarPreviewEditado();
    const ui = Number(b.dataset.ucEletDel), ei = Number(b.dataset.eletDelIdx);
    dados.unidades[ui].eletricas.splice(ei, 1);
    t8_previewDados = dados;
    t8_renderPreviewMatriz();
    t8_previewTab('ele');
  }));
}

function t8_coletarPreviewEditado() {
  const dados = JSON.parse(JSON.stringify(t8_previewDados)); // clona
  document.querySelectorAll('[data-uc-escalar]').forEach(inp => {
    const ui = Number(inp.dataset.ucEscalar);
    const campo = inp.dataset.campo;
    const numericos = ['Numero_Compressores', 'HP', 'Vent_Qtd', 'Tanque_Liquido_L', 'Nivel_Ruido_dB',
      'Ventilador_Diametro_mm', 'Comprimento_mm', 'Largura_mm', 'Altura_mm', 'Peso_Liquido_kg', 'Peso_Bruto_kg'];
    const v = inp.value.trim();
    dados.unidades[ui].unidade[campo] = v === '' ? null : (numericos.includes(campo) ? parseNumBR(v) : v);
  });
  document.querySelectorAll('[data-uc-elet]').forEach(inp => {
    const ui = Number(inp.dataset.ucElet);
    const ei = Number(inp.dataset.eletIdx);
    const campo = inp.dataset.campo;
    const v = inp.value.trim();
    dados.unidades[ui].eletricas[ei][campo] = v === '' ? null : (T8_NUM_ELETRICA_PREVIEW.includes(campo) ? parseNumBR(v) : v);
    dados.unidades[ui].eletricas[ei].Modelo = dados.unidades[ui].unidade.Modelo;
  });
  document.querySelectorAll('[data-uc-cap]').forEach(inp => {
    const ui = Number(inp.dataset.ucCap);
    const amb = inp.dataset.amb === 'null' ? null : parseNumBR(inp.dataset.amb);
    const evap = parseNumBR(inp.dataset.evap);
    const campo = inp.dataset.campo;
    const v = inp.value.trim();
    if (v === '') return;
    let caps = dados.unidades[ui].capacidades;
    let c = caps.find(x => x.Temp_Ambiente_C === amb && x.Temp_Evaporacao_C === evap);
    if (!c) { c = { Modelo: dados.unidades[ui].unidade.Modelo, Temp_Ambiente_C: amb, Temp_Evaporacao_C: evap }; caps.push(c); }
    c[campo] = parseNumBR(v);
  });
  return dados;
}

async function t8_confirmar() {
  if (!t8_previewDados) return;
  const dados = t8_coletarPreviewEditado();
  const idPai = document.getElementById('uc_idPai').value;
  if (idPai) dados.id_pai = idPai;
  const r = await api.post('/api/uc/confirmar-editado', dados);
  if (r.erro) { alert(r.erro); return; }
  document.getElementById('ucResultado').innerHTML = `Importado: ${r.criadas} criada(s), ${r.atualizadas} atualizada(s).`;
  t8_cancelarPreview();
  t8_carregarCatalogo();
}

function t8_cancelarPreview() {
  t8_previewArquivo = null;
  t8_previewDados = null;
  document.getElementById('ucArquivo').value = '';
  document.getElementById('ucPreviewWrap').style.display = 'none';
  document.getElementById('ucPreviewMecanica').innerHTML = '';
  document.getElementById('ucPreviewEletrica').innerHTML = '';
}

// Fabricante → Catálogo colapsados, como a Tela A (Fabricante → Linha). Só carrega/mostra os
// modelos de um catálogo quando ele é clicado — não faz sentido renderizar milhares de linhas de
// uma vez (item 13). Nome/Descrição/Foto do catálogo são editáveis aqui, mesmo padrão do Forçador.
let t8_catalogosAbertos = new Set();

async function t8_carregarCatalogo() {
  const cats = await api.get('/api/uc/catalogos-detalhe');
  const el = document.getElementById('ucCatalogo');
  if (!cats.length) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma unidade cadastrada ainda. Importe um catálogo acima.</div>';
    return;
  }
  const porFabricante = {};
  cats.forEach(c => { (porFabricante[c.fabricante_uc || '—'] = porFabricante[c.fabricante_uc || '—'] || []).push(c); });

  let html = '';
  Object.keys(porFabricante).sort().forEach(fab => {
    html += `<div class="group-head">${fab}</div><table class="list"><tbody>`;
    porFabricante[fab].forEach(c => {
      html += `<tr class="clickable" data-cat-toggle="${c.id}">
        <td style="font-weight:bold;">${c.nome}</td>
        <td style="color:#6b7280;">versão ${c.versao_catalogo || '—'}</td>
        <td>${c.qtd_unidades} unidade(s)</td>
        <td>${c.ativo_comercial === false ? '<span class="badge badge-pendente">Obsoleto</span>' : ''}</td>
        <td style="text-align:right;">
          <span class="btn-text" data-editar-cat="${c.id}">Editar Catálogo</span>
          <span class="btn-text danger" data-excluir-cat="${c.id}" style="margin-left:10px;">Excluir Catálogo</span>
        </td></tr>
        <tr data-cat-corpo="${c.id}" style="display:${t8_catalogosAbertos.has(c.id) ? 'table-row' : 'none'};"><td colspan="5" style="padding:0;"><div data-cat-conteudo="${c.id}"></div></td></tr>`;
    });
    html += '</tbody></table>';
  });
  el.innerHTML = html;

  el.querySelectorAll('[data-cat-toggle]').forEach(tr => tr.addEventListener('click', async (e) => {
    if (e.target.dataset.excluirCat || e.target.dataset.editarCat) return;
    const id = Number(tr.dataset.catToggle);
    const corpo = el.querySelector(`[data-cat-corpo="${id}"]`);
    if (t8_catalogosAbertos.has(id)) {
      t8_catalogosAbertos.delete(id);
      corpo.style.display = 'none';
      return;
    }
    t8_catalogosAbertos.add(id);
    corpo.style.display = 'table-row';
    await t8_renderCatalogoConteudo(el.querySelector(`[data-cat-conteudo="${id}"]`), id);
  }));
  el.querySelectorAll('[data-editar-cat]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    await t8_editarCatalogoMatriz(Number(b.dataset.editarCat));
  }));
  el.querySelectorAll('[data-excluir-cat]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    const id = Number(b.dataset.excluirCat);
    const cat = cats.find(c => c.id === id);
    if (!confirm(`Excluir o catálogo inteiro "${cat.nome}" e todas as suas unidades?`)) return;
    await api.del(`/api/uc/catalogos-detalhe/${id}`);
    t8_fechar();
    t8_carregarCatalogo();
  }));
}

const t8_editoresNomenclatura = {};
function t8_obterEditorNomenclatura(catalogoId) {
  if (!t8_editoresNomenclatura[catalogoId]) {
    t8_editoresNomenclatura[catalogoId] = nomenc_criarEditorCampos(`catNomenc_${catalogoId}`, T8_CAMPO_BUSCA_SISTEMA_OPCOES);
  }
  return t8_editoresNomenclatura[catalogoId];
}

async function t8_renderCatalogoConteudo(container, catalogoId) {
  const c = await api.get(`/api/uc/catalogos-detalhe/${catalogoId}`);
  const us = await api.get('/api/uc/unidades');
  const lista = us.filter(u => u.catalogo_id === catalogoId);
  container.innerHTML = `
    <div style="padding:10px;background:#f9fafb;border-top:1px solid var(--line);border-bottom:1px solid var(--line);">
      <div class="grid g3">
        <div><label class="lbl">Nome do Catálogo</label><input type="text" id="catNome_${catalogoId}" value="${c.nome ?? ''}"></div>
        <div><label class="lbl">Fabricante</label><input type="text" id="catFab_${catalogoId}" value="${c.fabricante_uc ?? ''}"></div>
        <div><label class="lbl">Versão</label><input type="text" id="catVersao_${catalogoId}" value="${c.versao_catalogo ?? ''}"></div>
        <div><label class="lbl">Id Comercial <span class="sub">— auto-gerado, categoria 2.1</span></label>
          <input type="text" value="${c.id_comercial ?? '—'}" disabled></div>
        <div><label class="checkrow"><input type="checkbox" id="catObsoleto_${catalogoId}" ${c.ativo_comercial === false ? 'checked' : ''}> Obsoleto
          <span class="sub" style="margin-left:6px;">— some da seleção automática de UC, continua salvo no banco</span></label></div>
      </div>
      <div class="grid g2" style="margin-top:8px;">
        <div><label class="lbl">Descrição Comercial <span class="sub">— vale pro catálogo inteiro</span></label>
          <textarea id="catDesc_${catalogoId}" rows="3" style="width:100%;">${c.descricao_comercial ?? ''}</textarea></div>
        <div><label class="lbl">Foto do Equipamento <span class="sub">— vale pro catálogo inteiro</span></label>
          <input type="file" id="catFotoInput_${catalogoId}" accept="image/*">
          <div id="catFotoPreview_${catalogoId}" style="margin-top:8px;">${c.imagem_path ? `<img src="${c.imagem_path}" style="max-width:220px;max-height:160px;border:1px solid var(--line);border-radius:4px;">` : '<span class="small" style="color:#9ca3af;">Nenhuma foto enviada ainda.</span>'}</div></div>
      </div>
      <p style="margin-top:8px;"><button class="btn" id="catBtnSalvar_${catalogoId}">Salvar Catálogo</button></p>
    </div>
    <div style="padding:10px;border-bottom:1px solid var(--line);">
      <div class="sec-title">Nomenclatura de Compra <span class="sub">— rótulo, opções, ordem e Modo de cada coluna do código comercial deste catálogo (a seleção por unidade continua na Tela 1)</span></div>
      <div id="catNomenc_${catalogoId}"></div>
    </div>
    <table class="list"><thead><tr>
      <th>Modelo</th><th>Gás</th><th>Sistema</th><th>Tipo</th><th>Compressor</th><th>HP</th><th>Capac.</th><th></th></tr></thead>
      <tbody>${lista.map(u => `<tr class="clickable" data-uc="${u.id}">
        <td style="font-weight:bold;">${u.modelo || '—'}</td><td>${u.gas || '—'}</td><td>${u.sistema || '—'}</td>
        <td>${u.tipo_compressor || '—'}</td><td>${u.fabricante_compressor || '—'}</td><td>${u.hp ?? '—'}</td>
        <td>${u.qtd_capacidades}</td>
        <td style="text-align:right;"><span class="btn-text danger" data-excluir-uc="${u.id}">Excluir</span></td></tr>`).join('')}</tbody></table>`;

  document.getElementById(`catBtnSalvar_${catalogoId}`).addEventListener('click', async () => {
    const btn = document.getElementById(`catBtnSalvar_${catalogoId}`);
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const tarefas = [
        { nome: 'Cabeçalho', fn: () => api.put(`/api/uc/catalogos-detalhe/${catalogoId}`, {
            nome: document.getElementById(`catNome_${catalogoId}`).value,
            fabricante_uc: document.getElementById(`catFab_${catalogoId}`).value,
            versao_catalogo: document.getElementById(`catVersao_${catalogoId}`).value || null,
            descricao_comercial: document.getElementById(`catDesc_${catalogoId}`).value || null,
            ativo_comercial: !document.getElementById(`catObsoleto_${catalogoId}`).checked,
          }) },
        { nome: 'Nomenclatura de Compra', fn: () => t8_obterEditorNomenclatura(catalogoId).salvar() },
      ];
      const erros = [];
      for (const t of tarefas) {
        try { await t.fn(); } catch (err) { erros.push(`${t.nome}: ${err.message}`); }
      }
      nomenc_invalidarCache();
      await t8_carregarCatalogo();
      if (t8_catalogosAbertos.has(catalogoId)) {
        const conteudo = document.querySelector(`[data-cat-conteudo="${catalogoId}"]`);
        if (conteudo) await t8_renderCatalogoConteudo(conteudo, catalogoId);
      }
      if (erros.length) {
        alert('Algumas partes NÃO foram salvas:\n' + erros.join('\n') + '\n\nAs demais partes foram salvas normalmente.');
      }
    } finally {
      const b = document.getElementById(`catBtnSalvar_${catalogoId}`);
      if (b) b.disabled = false;
    }
  });
  document.getElementById(`catFotoInput_${catalogoId}`).addEventListener('change', async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const r = await api.upload(`/api/uc/catalogos-detalhe/${catalogoId}/foto`, file);
    document.getElementById(`catFotoPreview_${catalogoId}`).innerHTML = `<img src="${r.imagem_path}" style="max-width:220px;max-height:160px;border:1px solid var(--line);border-radius:4px;">`;
  });
  await t8_obterEditorNomenclatura(catalogoId).carregar(`/api/uc/catalogos-detalhe/${catalogoId}/campos`);

  container.querySelectorAll('[data-uc]').forEach(tr => tr.addEventListener('click', (e) => {
    if (e.target.dataset.excluirUc) return;
    t8_abrir(Number(tr.dataset.uc));
  }));
  container.querySelectorAll('[data-excluir-uc]').forEach(b => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!confirm('Excluir esta unidade?')) return;
    await api.del(`/api/uc/unidades/${b.dataset.excluirUc}`);
    if (t8_unidadeAtual === Number(b.dataset.excluirUc)) t8_fechar();
    await t8_renderCatalogoConteudo(container, catalogoId);
    t8_carregarCatalogo();
  }));

}

// ---------------- Campos do Código Comercial: estrutura editada aqui mesmo, dentro do catálogo
// (ver nomenc_criarEditorCampos em componentes.js) — este bloco só mantém a lista de fontes
// Automáticas. ----------

const T8_CAMPO_BUSCA_SISTEMA_OPCOES = [
  ['tensao_comando', 'Tensão Comando'], ['tensao_equipamentos', 'Tensão Equipamentos'],
  ['gas', 'Gás'], ['sistema', 'Sistema'],
  ['tipo_compressor', 'Tipo Compressor'], ['fabricante_compressor', 'Fabricante Compressor'],
  ['numero_compressores', 'Nº Compressores'],
];

async function t8_abrir(id) {
  const u = await api.get(`/api/uc/unidades/${id}`);
  t8_unidadeAtual = id;
  document.getElementById('ucDetalheWrap').style.display = 'block';
  document.querySelector('#ucDetalheTitulo').childNodes[0].textContent = `Unidade — ${u.modelo} `;
  let html = '<div class="grid g3">';
  T8_CAMPOS_EDIT.forEach(([campo, label]) => {
    html += `<div><label class="lbl">${label}</label><input type="text" data-uc-campo="${campo}" value="${u[campo] ?? ''}"></div>`;
  });
  html += '</div>';
  html += t8_tabelaCapacidades(u.capacidades);
  document.getElementById('ucDetalhe').innerHTML = html;
  document.getElementById('ucDetalheEletrica').innerHTML = t8_tabelaEletricas(u.eletricas);
  t8_wireEletricas();
  t8_detTab('mec');
  document.getElementById('ucDetalheWrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function t8_tabelaEletricas(eletricas) {
  let html = '<p class="small" style="margin:6px 0 10px;color:#6b7280;">Uma linha por Tensão × Modelo de Compressor — o mesmo modelo pode ter mais de uma opção de compressor, cada uma com corrente própria.</p>';
  html += '<div style="overflow-x:auto;"><table class="list" style="white-space:nowrap;"><thead><tr>';
  T8_CAMPOS_ELETRICA_EDIT.forEach(([, lbl]) => { html += `<th>${lbl}</th>`; });
  html += '<th></th></tr></thead><tbody>';
  (eletricas || []).forEach(e => {
    html += `<tr data-elet-row="${e.id}">`;
    T8_CAMPOS_ELETRICA_EDIT.forEach(([campo]) => {
      html += `<td><input type="text" data-elet-campo="${campo}" value="${e[campo] ?? ''}" style="width:90px;"></td>`;
    });
    html += `<td><span class="btn-text" data-elet-salvar="${e.id}">Salvar</span> <span class="btn-text danger" data-elet-excluir="${e.id}">Excluir</span></td></tr>`;
  });
  html += `<tr data-elet-row="novo">`;
  T8_CAMPOS_ELETRICA_EDIT.forEach(([campo]) => {
    html += `<td><input type="text" data-elet-campo="${campo}" value="" style="width:90px;"></td>`;
  });
  html += `<td><span class="btn-text" data-elet-add="1">+ Adicionar</span></td></tr>`;
  html += '</tbody></table></div>';
  return html;
}

function t8_lerLinhaEletrica(tr) {
  const payload = {};
  tr.querySelectorAll('[data-elet-campo]').forEach(inp => {
    const campo = inp.dataset.eletCampo;
    const v = inp.value.trim();
    payload[campo] = v === '' ? null : (T8_NUM_ELETRICA.includes(campo) ? parseNumBR(v) : v);
  });
  return payload;
}

function t8_wireEletricas() {
  const cont = document.getElementById('ucDetalheEletrica');
  cont.querySelectorAll('[data-elet-salvar]').forEach(b => b.addEventListener('click', async () => {
    const tr = b.closest('tr');
    await api.put(`/api/uc/eletricas/${b.dataset.eletSalvar}`, t8_lerLinhaEletrica(tr));
    t8_abrir(t8_unidadeAtual);
  }));
  cont.querySelectorAll('[data-elet-excluir]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir esta linha de elétrica?')) return;
    await api.del(`/api/uc/eletricas/${b.dataset.eletExcluir}`);
    t8_abrir(t8_unidadeAtual);
  }));
  cont.querySelectorAll('[data-elet-add]').forEach(b => b.addEventListener('click', async () => {
    const tr = b.closest('tr');
    await api.post(`/api/uc/unidades/${t8_unidadeAtual}/eletricas`, t8_lerLinhaEletrica(tr));
    t8_abrir(t8_unidadeAtual);
  }));
}

function t8_tabelaCapacidades(caps) {
  if (!caps || !caps.length) return '<p class="small" style="margin-top:10px;">Sem capacidades cadastradas.</p>';
  const ambientes = [...new Set(caps.map(c => c.temp_ambiente_c))].sort((a, b) => a - b);
  const evaps = [...new Set(caps.map(c => c.temp_evaporacao_c))].sort((a, b) => a - b);
  const idx = {};
  caps.forEach(c => { idx[`${c.temp_ambiente_c}_${c.temp_evaporacao_c}`] = c; });
  let html = '<div class="sec-title" style="margin-top:14px;">Capacidades (Q kcal/h · P kW) por Temp. Ambiente × Temp. Evaporação</div>';
  html += '<div style="overflow-x:auto;"><table class="list" style="white-space:nowrap;"><thead><tr><th>T.Amb \\ T.Evap</th>';
  evaps.forEach(e => { html += `<th style="text-align:center;">${e}°C</th>`; });
  html += '</tr></thead><tbody>';
  ambientes.forEach(amb => {
    html += `<tr><td style="font-weight:bold;">${amb}°C</td>`;
    evaps.forEach(e => {
      const c = idx[`${amb}_${e}`];
      html += `<td style="text-align:center;">${c && c.capacidade_kcal_h != null ? fmtNum(c.capacidade_kcal_h) : '—'}${c && c.potencia_kw != null ? `<br><span style="color:#6b7280;font-size:10px;">${c.potencia_kw} kW</span>` : ''}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  return html;
}

async function t8_salvar() {
  if (!t8_unidadeAtual) return;
  const payload = {};
  document.querySelectorAll('#ucDetalhe [data-uc-campo]').forEach(inp => {
    const campo = inp.dataset.ucCampo;
    const num = ['numero_compressores', 'hp', 'vent_qtd', 'ventilador_diametro_mm', 'tanque_liquido_l',
      'nivel_ruido_db', 'comprimento_mm', 'largura_mm', 'altura_mm', 'peso_liquido_kg', 'peso_bruto_kg'].includes(campo);
    payload[campo] = inp.value === '' ? null : (num ? parseNumBR(inp.value) : inp.value);
  });
  await api.put(`/api/uc/unidades/${t8_unidadeAtual}`, payload);
  await t8_carregarCatalogo();
  await t8_abrir(t8_unidadeAtual);
}

function t8_fechar() {
  t8_unidadeAtual = null;
  document.getElementById('ucDetalheWrap').style.display = 'none';
  document.getElementById('ucDetalhe').innerHTML = '';
}

async function t8_excluir() {
  if (!t8_unidadeAtual) return;
  if (!confirm('Excluir esta unidade inteira?')) return;
  await api.del(`/api/uc/unidades/${t8_unidadeAtual}`);
  t8_fechar();
  t8_carregarCatalogo();
}

window.initTela8 = initTela8;
document.addEventListener('DOMContentLoaded', initTela8);
