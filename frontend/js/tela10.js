// Tela E — Painéis Térmicos e Portas.
let t10_camaras = [];      // {value:"C:1"/"S:2", label}
let t10_lookup = [];
let t10_modoResumo = 'total';

function fmt2(v) { return v == null || v === '' ? '—' : Number(v).toFixed(2); }

function initTela10() {
  document.getElementById('t10_btnSalvarPlacas').addEventListener('click', t10_salvarPlacas);
  document.getElementById('t10_btnAddPainel').addEventListener('click', t10_addPainel);
  document.getElementById('t10_btnAddPorta').addEventListener('click', t10_addPorta);
  document.querySelectorAll('[data-t10-modo]').forEach(b => b.addEventListener('click', () => {
    t10_modoResumo = b.dataset.t10Modo;
    document.querySelectorAll('[data-t10-modo]').forEach(x => x.classList.toggle('active', x === b));
    t10_carregarResumo();
  }));
  document.getElementById('t10_btnExportarExcel').addEventListener('click', () => {
    if (state.projetoId) api.baixarOuSalvar(`/api/paineis-portas/resumo/exportar/excel?projeto_id=${state.projetoId}&modo=${t10_modoResumo}`);
  });
  document.getElementById('t10_btnImprimir').addEventListener('click', () => {
    document.body.classList.add('t10-imprimindo');
    window.print();
    document.body.classList.remove('t10-imprimindo');
  });
  document.getElementById('t10_btnLimparTudo').addEventListener('click', t10_limparTudo);
  document.addEventListener('projeto-changed', t10_carregar);
  window.telaShowHandlers[10] = t10_carregar;
}

function t10_lookupPor(categoria) {
  return t10_lookup.filter(l => l.categoria === categoria).sort((a, b) => a.ordem - b.ordem);
}

// Grupo da Função vem 100% do cadastro (coluna Grupo da Função Porta em Configurações) — sem mapa
// fixo no código. Função sem grupo => null => não filtra Modelo/Sentido (mostra tudo).
function t10_grupoFuncao(funcao) {
  const f = t10_lookupPor('Função Porta').find(o => o.valor === funcao);
  return (f && f.grupo) ? f.grupo : null;
}

async function t10_carregarCamaras() {
  if (!state.projetoId) { t10_camaras = []; return; }
  const [completo, simples] = await Promise.all([
    api.get(`/api/camaras-completo?projeto_id=${state.projetoId}`),
    api.get(`/api/camaras-simples?projeto_id=${state.projetoId}`),
  ]);
  t10_camaras = [
    ...completo.map(c => ({ value: `C:${c.id}`, label: `${c.codigo} — ${c.nome}` })),
    ...simples.map(c => ({ value: `S:${c.id}`, label: `${c.codigo} — ${c.nome}` })),
  ];
}

function t10_opcoesCamaraHtml(selecionado) {
  const val = selecionado ?? '';
  return `<option value="">—</option>${t10_camaras.map(c =>
    `<option value="${c.value}" ${c.value === val ? 'selected' : ''}>${c.label}</option>`).join('')}
    <option value="AMB" ${val === 'AMB' ? 'selected' : ''}>Ambiente Não Climatizado</option>`;
}

function t10_camaraValueDe(item) {
  if (item.camara_completo_id) return `C:${item.camara_completo_id}`;
  if (item.camara_simples_id) return `S:${item.camara_simples_id}`;
  if (item.ambiente_nao_climatizado_nome !== null && item.ambiente_nao_climatizado_nome !== undefined) return 'AMB';
  return '';
}

function t10_camaraPayloadDe(valor) {
  if (valor === 'AMB') return { camara_completo_id: null, camara_simples_id: null, ambiente_nao_climatizado_nome: '' };
  if (valor.startsWith('C:')) return { camara_completo_id: Number(valor.slice(2)), camara_simples_id: null, ambiente_nao_climatizado_nome: null };
  if (valor.startsWith('S:')) return { camara_completo_id: null, camara_simples_id: Number(valor.slice(2)), ambiente_nao_climatizado_nome: null };
  return { camara_completo_id: null, camara_simples_id: null, ambiente_nao_climatizado_nome: null };
}

// Coluna Câmara: select + campo de texto do nome do ambiente, revelado só quando "AMB" selecionado.
function t10_celulaCamaraHtml(item, idCampoCamara, idCampoAmbiente) {
  const val = t10_camaraValueDe(item);
  const mostrar = val === 'AMB';
  return `<select data-campo="camara" data-id-campo="${idCampoCamara}" style="min-width:160px;">${t10_opcoesCamaraHtml(val)}</select>
    <input type="text" data-campo="ambiente_nome" data-id-campo="${idCampoAmbiente}" placeholder="Nome do Ambiente"
      value="${item.ambiente_nao_climatizado_nome ?? ''}"
      style="display:${mostrar ? 'inline-block' : 'none'};margin-left:4px;width:130px;">`;
}

async function t10_limparTudo() {
  if (!state.projetoId) return;
  if (!confirm('Apagar TODOS os painéis e portas deste projeto? Não pode ser desfeito.')) return;
  try {
    const r = await api.del(`/api/paineis-portas/limpar?projeto_id=${state.projetoId}`);
    alert(`Removidos: ${r.paineis_removidos} painéis, ${r.portas_removidas} portas.`);
    await t10_carregarPaineis();
    await t10_carregarPortas();
    await t10_carregarResumo();
  } catch (err) { alert('Erro ao limpar: ' + err.message); }
}

async function t10_carregar() {
  const semProjeto = document.getElementById('t10_semProjeto');
  const conteudo = document.getElementById('t10_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';

  const [projeto, lookup] = await Promise.all([
    api.get(`/api/projetos/${state.projetoId}`),
    api.get('/api/paineis-portas/lookup'),
  ]);
  t10_lookup = lookup;
  document.getElementById('t10_largPlaca').value = projeto.largura_placa_painel_m ?? '';
  document.getElementById('t10_pisoLarg').value = projeto.piso_placa_largura_m ?? '';
  document.getElementById('t10_pisoComp').value = projeto.piso_placa_comprimento_m ?? '';
  document.getElementById('t10_larguraMinAprov').value = projeto.largura_min_aproveitamento_placa_m ?? '';

  await t10_carregarCamaras();
  await t10_carregarPaineis();
  await t10_carregarPortas();
  await t10_carregarResumo();
}

async function t10_salvarPlacas() {
  try {
    await api.put(`/api/projetos/${state.projetoId}`, {
      largura_placa_painel_m: parseNumBR(document.getElementById('t10_largPlaca').value),
      piso_placa_largura_m: parseNumBR(document.getElementById('t10_pisoLarg').value),
      piso_placa_comprimento_m: parseNumBR(document.getElementById('t10_pisoComp').value),
      largura_min_aproveitamento_placa_m: parseNumBR(document.getElementById('t10_larguraMinAprov').value),
    });
    await t10_carregarPaineis();
    await t10_carregarResumo();
  } catch (err) { alert('Erro ao salvar placas: ' + err.message); }
}

// ---------------- Painéis ----------------
// Edição não recria a linha inteira (só os campos calculados são atualizados por texto) — evita
// que o cursor "pule" ou perca o foco ao usar Tab entre campos.

const T10_CAMPOS_PAINEL_NUM = ['dimensao_1', 'dimensao_2'];
const T10_CAMPOS_QUE_MUDAM_OPCOES_PAINEL = ['tipo'];

function t10_linhaPainelHtml(p) {
  return `
    <td class="t10-drag" title="Arraste para reordenar (recalcula o reaproveitamento)" style="cursor:grab;color:#9ca3af;text-align:center;user-select:none;">⠿</td>
    <td data-out="id_planta">${p.id_planta || '—'}</td>
    <td style="font-weight:bold;" data-out="id_painel">${p.id_painel || '—'}</td>
    <td>${t10_celulaCamaraHtml(p, 'T75', 'T76')}</td>
    <td><select data-campo="tipo" data-id-campo="T77">${t10_lookupPor('Tipo Painel').map(o =>
      `<option value="${o.valor}" ${o.valor === p.tipo ? 'selected' : ''}>${o.valor}</option>`).join('')}</select></td>
    <td data-cel="espessura"><select data-campo="espessura" data-id-campo="T78">${t10_lookupPor(p.tipo === 'Isolamento Piso' ? 'Espessura Piso' : 'Espessura Parede/Teto').map(o =>
      `<option value="${o.valor}" ${o.valor === p.espessura ? 'selected' : ''}>${o.valor}</option>`).join('')}</select></td>
    <td><input type="text" data-campo="dimensao_1" data-id-campo="T79" value="${p.dimensao_1 ?? ''}" style="width:80px;"></td>
    <td><input type="text" data-campo="dimensao_2" data-id-campo="T710" value="${p.dimensao_2 ?? ''}" style="width:80px;"></td>
    <td style="color:#6b7280;text-align:center;" data-out="comp_placa_m">${p.tipo === 'Isolamento Piso' ? '—' : (p.comp_placa_m != null ? fmt2(p.comp_placa_m) : '—')}</td>
    <td style="color:#6b7280;" data-out="largura_placa_m">${p.tipo === 'Isolamento Piso' ? '—' : fmt2(p.largura_placa_m)}</td>
    <td style="color:#6b7280;" data-out="area_total_m2">${fmt2(p.area_total_m2)}</td>
    <td style="color:#6b7280;" data-out="qtd_placas">${p.qtd_placas ?? '—'}</td>
    <td style="color:#6b7280;" data-out="area_considerada_m2">${fmt2(p.area_considerada_m2)}</td>
    <td style="color:#6b7280;" data-out="saldo_m">${fmt2(p.saldo_m)}</td>
    <td><span class="btn-text danger" data-excluir-painel="${p.id}">Excluir</span></td>`;
}

async function t10_carregarPaineis() {
  const paineis = await api.get(`/api/paineis-portas/paineis?projeto_id=${state.projetoId}`);
  const el = document.getElementById('t10_paineisTabela');
  if (!paineis.length) {
    el.innerHTML = '<div class="small" style="padding:10px;color:#9ca3af;">Nenhum painel lançado ainda.</div>';
    return;
  }
  el.innerHTML = `<table class="list"><thead><tr>
    <th style="width:22px;"></th>
    <th style="white-space:normal;">Id. Planta</th><th style="white-space:normal;">Id. Painel</th>
    <th style="white-space:normal;">Câmara</th><th style="white-space:normal;">Tipo</th><th style="white-space:normal;">Espessura</th>
    <th style="white-space:normal;width:120px;">Perímetro (Parede) / Larg. (Teto e Piso) (m)</th>
    <th style="white-space:normal;width:120px;">Altura (Parede) / Comp. (Teto e Piso) (m)</th>
    <th style="white-space:normal;width:120px;">Comprimento Placas (m)</th>
    <th style="white-space:normal;">Larg. Placa (m)</th><th style="white-space:normal;">Área (m²)</th>
    <th style="white-space:normal;">Qtd. Placas</th><th style="white-space:normal;">Área Consid. (m²)</th>
    <th style="white-space:normal;">Saldo (m)</th><th></th></tr></thead>
    <tbody>${paineis.map(p => `<tr draggable="true" data-painel-id="${p.id}" ${p.fechada ? 'class="entidade-fechada"' : ''}>${t10_linhaPainelHtml(p)}</tr>`).join('')}</tbody></table>`;
  t10_wirePaineis(el);
  t10_wireDragPaineis(el);
}

// Arrastar-e-soltar pra reordenar painéis. A ordem de lançamento é o que o motor usa pro
// reaproveitamento de sobra (linhas anteriores geram sobra p/ as seguintes) — então mover uma
// linha e persistir a nova `ordem` faz o servidor recompor qtd/área/saldo/reuso na releitura.
function t10_wireDragPaineis(el) {
  const tbody = el.querySelector('tbody');
  if (!tbody) return;
  let arrastada = null;
  tbody.querySelectorAll('tr[data-painel-id]').forEach(tr => {
    tr.addEventListener('dragstart', () => { arrastada = tr; tr.style.opacity = '0.4'; });
    tr.addEventListener('dragend', async () => {
      tr.style.opacity = '';
      if (!arrastada) return;
      arrastada = null;
      try {
        const ids = [...tbody.querySelectorAll('tr[data-painel-id]')].map(r => Number(r.dataset.painelId));
        await Promise.all(ids.map((id, i) => api.put(`/api/paineis-portas/paineis/${id}`, { ordem: i })));
        await t10_carregarPaineis();
        await t10_carregarResumo();
      } catch (err) { alert('Erro ao reordenar: ' + err.message); }
    });
    tr.addEventListener('dragover', (e) => {
      e.preventDefault();
      if (!arrastada || arrastada === tr) return;
      const r = tr.getBoundingClientRect();
      const depois = (e.clientY - r.top) > r.height / 2;   // solta na metade de baixo => vai depois
      tr.parentNode.insertBefore(arrastada, depois ? tr.nextSibling : tr);
    });
  });
}

function t10_wirePaineis(el) {
  el.querySelectorAll('tr[data-painel-id]').forEach(tr => {
    const id = tr.dataset.painelId;
    tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async () => {
      const campo = inp.dataset.campo;
      let payload;
      if (campo === 'camara') payload = t10_camaraPayloadDe(inp.value);
      else if (campo === 'ambiente_nome') payload = { ambiente_nao_climatizado_nome: inp.value };
      else if (T10_CAMPOS_PAINEL_NUM.includes(campo)) payload = { [campo]: parseNumBR(inp.value) };
      else payload = { [campo]: inp.value };
      const salvo = await api.put(`/api/paineis-portas/paineis/${id}`, payload);
      if (campo === 'camara') {
        const inputNome = tr.querySelector('[data-campo="ambiente_nome"]');
        const mostrar = inp.value === 'AMB';
        inputNome.style.display = mostrar ? 'inline-block' : 'none';
        if (!mostrar) inputNome.value = '';
      }
      if (T10_CAMPOS_QUE_MUDAM_OPCOES_PAINEL.includes(campo)) {
        // tipo mudou -> as opções de espessura mudam, precisa recriar só essa célula
        const paineis = await api.get(`/api/paineis-portas/paineis?projeto_id=${state.projetoId}`);
        const atual = paineis.find(p => String(p.id) === String(id));
        tr.querySelector('[data-cel="espessura"]').outerHTML =
          `<td data-cel="espessura"><select data-campo="espessura" data-id-campo="T78">${t10_lookupPor(atual.tipo === 'Isolamento Piso' ? 'Espessura Piso' : 'Espessura Parede/Teto').map(o =>
            `<option value="${o.valor}">${o.valor}</option>`).join('')}</select></td>`;
        tr.querySelector('[data-cel="espessura"] select').addEventListener('change', async (e) => {
          await api.put(`/api/paineis-portas/paineis/${id}`, { espessura: e.target.value });
          await t10_atualizarCalculosPaineis();
          await t10_carregarResumo();
        });
      }
      await t10_atualizarCalculosPaineis();
      await t10_carregarResumo();
    }));
  });
  el.querySelectorAll('[data-excluir-painel]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir este painel?')) return;
    try {
      await api.del(`/api/paineis-portas/paineis/${b.dataset.excluirPainel}`);
      await t10_carregarPaineis();
      await t10_carregarResumo();
    } catch (err) { alert('Erro ao excluir painel: ' + err.message); }
  }));
}

async function t10_atualizarCalculosPaineis() {
  const paineis = await api.get(`/api/paineis-portas/paineis?projeto_id=${state.projetoId}`);
  const el = document.getElementById('t10_paineisTabela');
  paineis.forEach(p => {
    const tr = el.querySelector(`tr[data-painel-id="${p.id}"]`);
    if (!tr) return;
    tr.querySelector('[data-out="id_planta"]').textContent = p.id_planta || '—';
    tr.querySelector('[data-out="id_painel"]').textContent = p.id_painel || '—';
    tr.querySelector('[data-out="largura_placa_m"]').textContent = p.tipo === 'Isolamento Piso' ? '—' : fmt2(p.largura_placa_m);
    tr.querySelector('[data-out="area_total_m2"]').textContent = fmt2(p.area_total_m2);
    tr.querySelector('[data-out="qtd_placas"]').textContent = p.qtd_placas ?? '—';
    tr.querySelector('[data-out="area_considerada_m2"]').textContent = fmt2(p.area_considerada_m2);
    tr.querySelector('[data-out="saldo_m"]').textContent = fmt2(p.saldo_m);
    tr.querySelector('[data-out="comp_placa_m"]').textContent = p.tipo === 'Isolamento Piso' ? '—' : (p.comp_placa_m != null ? fmt2(p.comp_placa_m) : '—');
  });
}

async function t10_addPainel() {
  try {
    await api.post(`/api/paineis-portas/paineis?projeto_id=${state.projetoId}`, { tipo: 'Parede' });
    await t10_carregarPaineis();
    await t10_carregarResumo();
  } catch (err) { alert('Erro ao adicionar painel: ' + err.message); }
}

// ---------------- Portas ----------------

const T10_CAMPOS_PORTA_NUM = ['vao_largura_mm', 'vao_altura_mm', 'espessura_fixacao_mm', 'quantidade'];
const T10_CAMPOS_QUE_MUDAM_OPCOES_PORTA = ['funcao', 'modelo'];

function t10_selectModeloSentidoHtml(p) {
  const grupo = t10_grupoFuncao(p.funcao);
  const modelo = `<select data-campo="modelo" data-id-campo="T714">${t10_lookupPor('Modelo Porta').filter(o => !grupo || o.grupo === grupo).map(o =>
    `<option value="${o.valor}" ${o.valor === p.modelo ? 'selected' : ''}>${o.valor}</option>`).join('')}</select>`;
  const sentido = `<select data-campo="sentido" data-id-campo="T715">${t10_lookupPor('Sentido Porta').filter(o => !grupo || o.grupo === grupo).map(o =>
    `<option value="${o.valor}" ${o.valor === p.sentido ? 'selected' : ''}>${o.valor}</option>`).join('')}</select>`;
  return { modelo, sentido };
}

function t10_linhaPortaHtml(p) {
  const { modelo, sentido } = t10_selectModeloSentidoHtml(p);
  return `
    <td data-out="id_planta">${p.id_planta || '—'}</td>
    <td style="font-weight:bold;" data-out="id_porta">${p.id_porta || '—'}</td>
    <td>${t10_celulaCamaraHtml(p, 'T711', 'T712')}</td>
    <td><select data-campo="funcao" data-id-campo="T713">${t10_lookupPor('Função Porta').map(o =>
      `<option value="${o.valor}" ${o.valor === p.funcao ? 'selected' : ''}>${o.valor}</option>`).join('')}</select></td>
    <td data-cel="modelo">${modelo}</td>
    <td data-cel="sentido">${sentido}</td>
    <td><input type="text" data-campo="vao_largura_mm" data-id-campo="T716" value="${p.vao_largura_mm ?? ''}" style="width:70px;"></td>
    <td><input type="text" data-campo="vao_altura_mm" data-id-campo="T717" value="${p.vao_altura_mm ?? ''}" style="width:70px;"></td>
    <td><select data-campo="fixacao" data-id-campo="T718">${t10_lookupPor('Fixação Porta').map(o =>
      `<option value="${o.valor}" ${o.valor === p.fixacao ? 'selected' : ''}>${o.valor}</option>`).join('')}</select></td>
    <td><input type="text" data-campo="espessura_fixacao_mm" data-id-campo="T719" value="${p.espessura_fixacao_mm ?? ''}" style="width:60px;"></td>
    <td><select data-campo="tensao" data-id-campo="T720"><option value="">—</option>${t10_lookupPor('Tensão Porta').map(o =>
      `<option value="${o.valor}" ${o.valor === p.tensao ? 'selected' : ''}>${o.valor}</option>`).join('')}</select></td>
    <td><input type="number" data-campo="quantidade" value="${p.quantidade ?? 1}" min="1" max="99" style="width:50px;"></td>
    <td><input type="text" data-campo="observacoes" data-id-campo="T721" value="${p.observacoes ?? ''}" style="width:100px;"></td>
    <td style="color:#6b7280;max-width:240px;white-space:normal;" data-out="descricao">${p.descricao || '—'}</td>
    <td><span class="btn-text danger" data-excluir-porta="${p.id}">Excluir</span></td>`;
}

async function t10_carregarPortas() {
  const portas = await api.get(`/api/paineis-portas/portas?projeto_id=${state.projetoId}`);
  const el = document.getElementById('t10_portasTabela');
  if (!portas.length) {
    el.innerHTML = '<div class="small" style="padding:10px;color:#9ca3af;">Nenhuma porta lançada ainda.</div>';
    return;
  }
  el.innerHTML = `<table class="list"><thead><tr>
    <th style="white-space:normal;">Id. Planta</th><th style="white-space:normal;">Id. Porta</th>
    <th style="white-space:normal;">Câmara</th><th style="white-space:normal;">Função</th>
    <th style="white-space:normal;">Modelo</th><th style="white-space:normal;">Sentido</th>
    <th style="white-space:normal;">Vão Larg. (mm)</th><th style="white-space:normal;">Vão Alt. (mm)</th>
    <th style="white-space:normal;">Fixação</th><th style="white-space:normal;">Esp. Fix. (mm)</th>
    <th style="white-space:normal;">Tensão</th><th style="white-space:normal;">Qtd.</th><th style="white-space:normal;">Obs.</th>
    <th style="white-space:normal;">Descrição</th><th></th></tr></thead>
    <tbody>${portas.map(p => `<tr data-porta-id="${p.id}" ${p.fechada ? 'class="entidade-fechada"' : ''}>${t10_linhaPortaHtml(p)}</tr>`).join('')}</tbody></table>`;
  t10_wirePortas(el);
}

// Quando Função muda, as opções de Modelo mudam (filtradas pelo grupo) — se o Modelo atualmente
// gravado no banco não existir mais na lista filtrada, o <select> do navegador cai visualmente
// na primeira opção da lista nova SEM disparar 'change' (e sem eu gravar isso no banco) — banco e
// tela ficam dessincronizados (Id./Descrição do banco continuam com o Modelo antigo). Por isso,
// depois de qualquer troca de Função/Modelo, valido e — se preciso — gravo explicitamente o novo
// Modelo/Sentido "default" antes de recalcular Id./Descrição.
async function t10_corrigirModeloSentidoPorta(id, atual) {
  const grupo = t10_grupoFuncao(atual.funcao);
  const modelosValidos = t10_lookupPor('Modelo Porta').filter(o => !grupo || o.grupo === grupo);
  let modelo = atual.modelo;
  let precisaCorrigir = false;
  if (!modelosValidos.some(o => o.valor === modelo)) {
    modelo = modelosValidos.length ? modelosValidos[0].valor : null;
    precisaCorrigir = true;
  }
  let sentido = atual.sentido;
  const sentidosValidos = t10_lookupPor('Sentido Porta').filter(o => !grupo || o.grupo === grupo);
  if (!sentidosValidos.some(o => o.valor === sentido)) {
    sentido = sentidosValidos.length ? sentidosValidos[0].valor : null;
    precisaCorrigir = true;
  }
  if (precisaCorrigir) {
    await api.put(`/api/paineis-portas/portas/${id}`, { modelo, sentido });
    return { ...atual, modelo, sentido };
  }
  return atual;
}

function t10_wirePortas(el) {
  el.querySelectorAll('tr[data-porta-id]').forEach(tr => {
    const id = tr.dataset.portaId;
    tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', () => t10_onCampoPortaChange(tr, id, inp)));
  });
  el.querySelectorAll('[data-excluir-porta]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir esta porta?')) return;
    try {
      await api.del(`/api/paineis-portas/portas/${b.dataset.excluirPorta}`);
      await t10_carregarPortas();
      await t10_carregarResumo();
    } catch (err) { alert('Erro ao excluir porta: ' + err.message); }
  }));
}

async function t10_onCampoPortaChange(tr, id, inp) {
  const campo = inp.dataset.campo;
  let payload;
  if (campo === 'camara') payload = t10_camaraPayloadDe(inp.value);
  else if (campo === 'ambiente_nome') payload = { ambiente_nao_climatizado_nome: inp.value || null };
  else if (T10_CAMPOS_PORTA_NUM.includes(campo)) payload = { [campo]: parseNumBR(inp.value) };
  else payload = { [campo]: inp.value || null };
  await api.put(`/api/paineis-portas/portas/${id}`, payload);

  if (campo === 'camara') {
    const inputNome = tr.querySelector('[data-campo="ambiente_nome"]');
    const mostrar = inp.value === 'AMB';
    inputNome.style.display = mostrar ? 'inline-block' : 'none';
    if (!mostrar) inputNome.value = '';
  }

  if (T10_CAMPOS_QUE_MUDAM_OPCOES_PORTA.includes(campo)) {
    const portas = await api.get(`/api/paineis-portas/portas?projeto_id=${state.projetoId}`);
    let atual = portas.find(p => String(p.id) === String(id));
    atual = await t10_corrigirModeloSentidoPorta(id, atual); // garante banco == o que a tela vai mostrar
    const { modelo, sentido } = t10_selectModeloSentidoHtml(atual);
    tr.querySelector('[data-cel="modelo"]').outerHTML = `<td data-cel="modelo">${modelo}</td>`;
    tr.querySelector('[data-cel="sentido"]').outerHTML = `<td data-cel="sentido">${sentido}</td>`;
    const novoInpModelo = tr.querySelector('[data-cel="modelo"] [data-campo]');
    if (novoInpModelo) novoInpModelo.addEventListener('change', () => t10_onCampoPortaChange(tr, id, novoInpModelo));
    const novoInpSentido = tr.querySelector('[data-cel="sentido"] [data-campo]');
    if (novoInpSentido) novoInpSentido.addEventListener('change', () => t10_onCampoPortaChange(tr, id, novoInpSentido));
  }
  await t10_atualizarCalculosPortas();
  await t10_carregarResumo();
}

async function t10_atualizarCalculosPortas() {
  const portas = await api.get(`/api/paineis-portas/portas?projeto_id=${state.projetoId}`);
  const el = document.getElementById('t10_portasTabela');
  portas.forEach(p => {
    const tr = el.querySelector(`tr[data-porta-id="${p.id}"]`);
    if (!tr) return;
    tr.querySelector('[data-out="id_planta"]').textContent = p.id_planta || '—';
    tr.querySelector('[data-out="id_porta"]').textContent = p.id_porta || '—';
    tr.querySelector('[data-out="descricao"]').textContent = p.descricao || '—';
  });
}

async function t10_addPorta() {
  try {
    await api.post(`/api/paineis-portas/portas?projeto_id=${state.projetoId}`, { funcao: 'Resfriados', modelo: 'Correr' });
    await t10_carregarPortas();
    await t10_carregarResumo();
  } catch (err) { alert('Erro ao adicionar porta: ' + err.message); }
}

// ---------------- Resumo ----------------

async function t10_carregarResumo() {
  const r = await api.get(`/api/paineis-portas/resumo?projeto_id=${state.projetoId}&modo=${t10_modoResumo}`);
  document.getElementById('t10_resumo').innerHTML = t10_renderResumo(r);
}

// Toda linha do resumo tem UMA quantidade com SUA unidade (m² ou un) — nunca duas colunas
// concorrentes. Padrão único pra tudo: Item | Unid. | Quantidade.
function t10_fmtQtd(l) { return l.unidade === 'm²' ? fmt2(l.quantidade) : (l.quantidade ?? '—'); }

function t10_tabelaItens(linhas, titulo, comArea) {
  if (!linhas.length) return `<div class="small" style="color:#9ca3af;padding:4px 0;">${titulo}: nenhum lançamento.</div>`;
  const colArea = comArea ? '<th style="text-align:right;">Área (m²)</th>' : '';
  return `<div style="margin-bottom:10px;width:fit-content;max-width:100%;">
    <div class="small" style="font-weight:bold;margin-bottom:4px;">${titulo}</div>
    <table class="list" style="width:auto;"><thead><tr><th>Item</th><th>Unid.</th><th style="text-align:right;">Quantidade</th>${colArea}</tr></thead>
    <tbody>${linhas.map(l => `<tr><td>${l.item}</td><td>${l.unidade}</td><td style="text-align:right;">${t10_fmtQtd(l)}</td>${
      comArea ? `<td style="text-align:right;">${l.area_m2 != null ? fmt2(l.area_m2) : '—'}</td>` : ''}</tr>`).join('')}</tbody></table>
  </div>`;
}

function t10_tabelaPortasFlat(portas, titulo) {
  const html = !portas.length ? '<div class="small" style="color:#9ca3af;">Nenhuma porta lançada.</div>' :
    `<div style="width:fit-content;max-width:100%;"><table class="list" style="width:auto;"><thead><tr><th>Descrição</th><th>Id.</th><th>Unid.</th><th style="text-align:right;">Quantidade</th><th>Tensão</th><th>Observação</th></tr></thead>
    <tbody>${portas.map(p => `<tr><td>${p.descricao}</td><td style="font-weight:bold;">${p.id_porta}</td><td>${p.unidade}</td><td style="text-align:right;">${p.quantidade}</td><td>${p.tensao || '—'}</td><td>${p.observacoes || '—'}</td></tr>`).join('')}</tbody></table></div>`;
  return titulo ? `<div class="sec-title" style="margin-top:4px;">${titulo}</div>${html}` : html;
}

function t10_renderResumo(r) {
  if (r.modo === 'total') {
    return `${t10_tabelaItens(r.paineis_parede_teto, 'Painéis — Parede e Teto')}
      ${t10_tabelaItens(r.isolamento_piso, 'Isolamento de Piso')}
      ${t10_tabelaPortasFlat(r.portas, 'Portas')}`;
  }
  if (r.modo === 'painel_portas' || r.modo === 'painel_portas_geral') {
    let html = `${t10_tabelaItens(r.paineis_parede_teto, 'Painéis — por Id.', true)}
      ${t10_tabelaItens(r.isolamento_piso, 'Isolamento de Piso')}`;
    if (r.modo === 'painel_portas') {
      html += `<div class="sec-title" style="margin-top:4px;">Portas por Câmara</div>
        ${r.portas_por_camara.map(c => `<div style="margin-bottom:10px;"><div class="small" style="font-weight:bold;">${c.id_planta || '—'} — ${c.camara_nome}</div>
          ${t10_tabelaPortasFlat(c.portas)}</div>`).join('')}`;
    } else {
      html += t10_tabelaPortasFlat(r.portas, 'Portas — Lista Geral');
    }
    return html;
  }
  if (r.modo === 'camara') {
    return r.camaras.map(c => `<div style="border:1px solid var(--line);border-radius:6px;margin-bottom:12px;overflow:hidden;width:fit-content;max-width:100%;">
      <div style="background:#111827;color:#fff;padding:6px 10px;font-size:12px;font-weight:bold;">${c.id_planta || '—'} — ${c.camara_nome}</div>
      <div style="padding:10px;">
        ${t10_tabelaItens(c.paineis_parede_teto, 'Painéis — Parede e Teto')}
        ${t10_tabelaItens(c.isolamento_piso, 'Isolamento de Piso')}
        ${t10_tabelaPortasFlat(c.portas, 'Portas')}
      </div></div>`).join('');
  }
  return '';
}

window.initTela10 = initTela10;
document.addEventListener('DOMContentLoaded', initTela10);
