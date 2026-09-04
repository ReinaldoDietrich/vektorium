// Tela D — Cadastro Comercial: texto + foto unificados por categoria (Painéis, Portas, Válvulas
// de Expansão, Rack Paralelo, Expositor, Supervisório e outras que surgirem), sem importação.
// Extraída de dentro de Configurações pra tela própria (usuário quer padronizar sua proposta
// aqui, fora da tela de administração do banco).

function initTela13() {
  window.telaShowHandlers[13] = () => {
    t13_carregarCatalogoComercial();
    t13_carregarFatores();
    t13_carregarItensDefault();
    t13_carregarVendedores();
  };
  document.getElementById('t13_btnAddFator').addEventListener('click', t13_addFator);
  document.getElementById('t13_btnAddItemDefault').addEventListener('click', t13_addItemDefault);
  document.getElementById('t13_btnAddVendedor').addEventListener('click', t13_addVendedorMestre);
}

// Monta as <option> do seletor de Id Comercial: uma linha por nó da árvore (categoria OU item
// final), indentada pela profundidade do código (nº de pontos) — assim o usuário navega
// Categoria > Subcategoria > Item em vez de digitar/decorar o código na mão (ver id_comercial.py).
function t13_htmlOpcoesArvoreId(arvore, selecionado) {
  return arvore.map(n => {
    const prof = (n.codigo.match(/\./g) || []).length;
    const indent = '    '.repeat(prof);
    return `<option value="${n.codigo}" ${n.codigo === selecionado ? 'selected' : ''}>${indent}${n.codigo} — ${n.nome}</option>`;
  }).join('');
}

// Nó-PAI de um código da árvore ("8.1"->"8"; "1.2.1.4"->"1.2.1"; código de 1 nível -> ele mesmo).
// Organiza os itens do Cadastro Comercial pelo pai do Id Comercial que cada um já tem (aprovado 2026-08-14).
function t13_grupoPorIdPai(idComercial, arvoreIds) {
  if (!idComercial) return null;
  const raizCodigo = String(idComercial).split('.')[0];   // ID pai = nó raiz (gera todos os demais, nada acima)
  const no = arvoreIds.find(n => n.codigo === raizCodigo);
  return { codigo: raizCodigo, nome: no ? no.nome : raizCodigo };
}

// Ids recem-criados nesta sessao da tela que ainda nao foram confirmados com "Salvar" -- ficam
// destacados no topo (fora dos grupos por categoria) pra nao se perder no meio dos demais
// enquanto o usuario ainda vai preencher Descricao Comercial + Foto. Some da lista quando o
// usuario clica "Salvar" nesse item (nao precisa ter todos os campos preenchidos pra sair daqui,
// só precisa da confirmação explícita de Salvar).
const t13_catalogoComercialPendentes = new Set();

// Categorias com o card-list expandido — vazio por padrão, ou seja, tudo retraído toda vez que o
// aplicativo é aberto (recarregado). Fica no módulo (não é salvo no banco nem em localStorage) —
// alternar entre telas dentro da mesma sessão mantém o estado; só um reload zera pra tudo fechado.
const t13_categoriasAbertas = new Set();

function t13_htmlCardCatalogoComercial(c, arvoreIds) {
  return `<div style="border:1px solid var(--line);border-radius:6px;padding:8px;margin-bottom:8px;">
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start;">
      <div style="min-width:150px;">
        <label class="lbl">Fabricante</label><input type="text" id="cc_fab_${c.id}" value="${c.fabricante ?? ''}">
        <label class="lbl" style="margin-top:4px;">Modelo</label><input type="text" id="cc_modelo_${c.id}" value="${c.modelo ?? ''}">
        <label class="lbl" style="margin-top:4px;">Nome</label><input type="text" id="cc_nome_${c.id}" value="${c.nome}">
      </div>
      <div style="flex:1;min-width:220px;align-self:stretch;display:flex;flex-direction:column;">
        <label class="lbl">Descrição Comercial</label>
        <textarea id="cc_desc_${c.id}" rows="2" style="width:100%;flex:1;min-height:44px;resize:vertical;">${c.descricao_comercial ?? ''}</textarea>
      </div>
      <div style="min-width:190px;">
        <label class="lbl">Id Comercial</label>
        <select id="cc_id_${c.id}" style="width:100%;"><option value="">— nenhum —</option>${t13_htmlOpcoesArvoreId(arvoreIds, c.id_comercial)}</select>
        <label class="lbl" style="margin-top:4px;">Id Cadastro</label>
        <input type="text" value="${c.id_cadastro ?? '— salve pra gerar —'}" disabled style="width:100%;">
      </div>
      <div>
        <div id="cc_foto_${c.id}">${c.imagem_path ? `<img src="${c.imagem_path}" style="max-width:110px;max-height:70px;border:1px solid var(--line);border-radius:4px;">` : '<span class="small" style="color:#9ca3af;">Sem foto.</span>'}</div>
        <label class="lbl" style="margin-top:4px;">Foto</label>
        <input type="file" id="cc_fotoInput_${c.id}" accept="image/*">
      </div>
    </div>
    <p style="margin-top:6px;margin-bottom:0;"><span class="btn-text" data-cc-salvar="${c.id}">Salvar</span>
      <span class="btn-text danger" data-cc-excluir="${c.id}" style="margin-left:8px;">Excluir</span></p>
  </div>`;
}

async function t13_carregarCatalogoComercial() {
  const [itens, arvoreIds] = await Promise.all([
    api.get('/api/catalogo-comercial'),
    api.get('/api/catalogo-comercial/arvore-ids'),
  ]);
  const el = document.getElementById('t13_catalogoComercial');

  const pendentes = itens.filter(c => t13_catalogoComercialPendentes.has(c.id));
  const restantes = itens.filter(c => !t13_catalogoComercialPendentes.has(c.id));

  // Organização pelo nó-PAI do Id Comercial que cada item já tem — reorganiza automaticamente os
  // cadastros existentes, sem tocar no banco. Chave = código do pai; valor = { nome, itens }.
  const grupos = {};
  restantes.forEach(c => {
    const g = t13_grupoPorIdPai(c.id_comercial, arvoreIds);
    const chave = g ? g.codigo : '—';
    (grupos[chave] = grupos[chave] || { nome: g ? g.nome : '—', itens: [] }).itens.push(c);
  });

  // Categoria é lista FECHADA de propósito — as mesmas strings que o app grava nos campos reais
  // de seleção do sistema (Automação Linhas/Equipamentos) ou o nome do equipamento/insumo. Isso é
  // o que vai permitir a futura Tela de Memorial linkar a ficha certa automaticamente.
  // Id Comercial é OUTRA ligação, mais precisa (ver id_comercial.py) — escolhida por navegação na
  // árvore, não digitada, pra não decorar código.
  let html = `<div class="add-row" style="grid-template-columns:0.9fr 0.9fr 1.3fr 1.5fr 56px;margin-bottom:14px;">
      <div><label class="lbl">Fabricante</label><input type="text" id="cc_novoFabricante"></div>
      <div><label class="lbl">Modelo</label><input type="text" id="cc_novoModelo"></div>
      <div><label class="lbl">Nome</label><input type="text" id="cc_novoNome"></div>
      <div><label class="lbl">Id Comercial</label><select id="cc_novoIdComercial"><option value="">— nenhum —</option>${t13_htmlOpcoesArvoreId(arvoreIds)}</select></div>
      <div><label class="lbl">&nbsp;</label><button class="btn" id="cc_btnAdd">+</button></div>
    </div>`;

  if (pendentes.length) {
    html += `<div class="group-head">Novo cadastro (ainda não salvo) — complete e clique Salvar</div>`;
    pendentes.forEach(c => { html += t13_htmlCardCatalogoComercial(c, arvoreIds); });
  }

  Object.keys(grupos).sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).forEach(chave => {
    const g = grupos[chave];
    g.itens.sort((x, y) => String(x.id_comercial || '').localeCompare(String(y.id_comercial || ''), undefined, { numeric: true }));
    const aberto = t13_categoriasAbertas.has(chave);
    html += `<div class="group-head" data-cc-cat-toggle="${chave}" style="cursor:pointer;user-select:none;">
      ${aberto ? '▾' : '▸'} ${chave} — ${g.nome} <span class="small" style="color:#9ca3af;font-weight:normal;">(${g.itens.length})</span></div>`;
    if (aberto) g.itens.forEach(c => { html += t13_htmlCardCatalogoComercial(c, arvoreIds); });
  });
  el.innerHTML = html;

  el.querySelectorAll('[data-cc-cat-toggle]').forEach(h => h.addEventListener('click', () => {
    const cat = h.dataset.ccCatToggle;
    if (t13_categoriasAbertas.has(cat)) t13_categoriasAbertas.delete(cat); else t13_categoriasAbertas.add(cat);
    t13_carregarCatalogoComercial();
  }));

  document.getElementById('cc_btnAdd').addEventListener('click', async () => {
    const nome = document.getElementById('cc_novoNome').value.trim();
    const idComercial = document.getElementById('cc_novoIdComercial').value || null;
    if (!nome) { alert('Preencha ao menos o Nome.'); return; }
    if (!idComercial) { alert('Escolha o Id Comercial — ele define a categoria do cadastro.'); return; }
    const criado = await api.post('/api/catalogo-comercial', {
      nome, fabricante: document.getElementById('cc_novoFabricante').value || null,
      modelo: document.getElementById('cc_novoModelo').value || null,
      id_comercial: idComercial,
    });
    t13_catalogoComercialPendentes.add(criado.id);
    await t13_carregarCatalogoComercial();
  });

  // Só os itens realmente renderizados (pendentes + categorias abertas) têm card no DOM — os
  // demais (categoria retraída) não têm elemento pra ligar listener nenhum.
  const itensRenderizados = pendentes.concat(restantes.filter(c => {
    const g = t13_grupoPorIdPai(c.id_comercial, arvoreIds);
    return t13_categoriasAbertas.has(g ? g.codigo : '—');
  }));
  itensRenderizados.forEach(c => {
    document.querySelector(`[data-cc-salvar="${c.id}"]`).addEventListener('click', async () => {
      await api.put(`/api/catalogo-comercial/${c.id}`, {
        fabricante: document.getElementById(`cc_fab_${c.id}`).value || null,
        modelo: document.getElementById(`cc_modelo_${c.id}`).value || null,
        nome: document.getElementById(`cc_nome_${c.id}`).value,
        descricao_comercial: document.getElementById(`cc_desc_${c.id}`).value || null,
        id_comercial: document.getElementById(`cc_id_${c.id}`).value || null,
      });
      t13_catalogoComercialPendentes.delete(c.id);
      alert('Cadastro salvo.');
      await t13_carregarCatalogoComercial();
    });
    document.querySelector(`[data-cc-excluir="${c.id}"]`).addEventListener('click', async () => {
      if (!confirm(`Excluir "${c.nome}"?`)) return;
      await api.del(`/api/catalogo-comercial/${c.id}`);
      await t13_carregarCatalogoComercial();
    });
    document.getElementById(`cc_fotoInput_${c.id}`).addEventListener('change', async (ev) => {
      const file = ev.target.files[0];
      if (!file) return;
      const r = await api.upload(`/api/catalogo-comercial/${c.id}/foto`, file);
      document.getElementById(`cc_foto_${c.id}`).innerHTML = `<img src="${r.imagem_path}" style="max-width:140px;max-height:100px;border:1px solid var(--line);border-radius:4px;">`;
    });
  });
}

// ---------------- Fatores de Venda ----------------

const T13_BLOCOS_COMPOSICAO = ['Equipamentos', 'Materiais Mecânicos', 'Materiais Elétricos',
  'Painéis Térmicos', 'Mão de Obra', 'Outros Serviços', 'Fretes e Transporte Vertical',
  'Comissões por Indicação de Negócio'];

async function t13_carregarFatores() {
  const fatores = await api.get('/api/composicao-preco/fatores');
  const tbody = document.getElementById('t13_fatores');
  tbody.innerHTML = fatores.map(f => `
    <tr data-fator-id="${f.id}">
      <td><input data-campo="codigo" value="${f.codigo}" style="width:70px;"></td>
      <td><input data-campo="tipo" value="${f.tipo || ''}" style="width:100px;"></td>
      <td><input data-campo="descricao" value="${f.descricao}" style="width:100%;"></td>
      <td><input data-campo="pct_impostos" value="${(f.pct_impostos * 100).toFixed(1)}" style="width:70px;"></td>
      <td><input data-campo="pct_comissao" value="${(f.pct_comissao * 100).toFixed(1)}" style="width:70px;"></td>
      <td><input data-campo="pct_margem" value="${(f.pct_margem * 100).toFixed(1)}" style="width:70px;"></td>
      <td><span class="btn-text danger" data-del-fator>x</span></td>
    </tr>`).join('');
  tbody.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async (e) => {
    const tr = e.target.closest('tr');
    const campo = inp.dataset.campo;
    let valor = inp.value;
    if (campo.startsWith('pct_')) valor = parseNumBR(valor) / 100;
    await api.put(`/api/composicao-preco/fatores/${tr.dataset.fatorId}`, { [campo]: valor });
  }));
  tbody.querySelectorAll('[data-del-fator]').forEach(b => b.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr');
    try { await api.del(`/api/composicao-preco/fatores/${tr.dataset.fatorId}`); t13_carregarFatores(); }
    catch (err) { alert(JSON.parse(await err.message).detail || 'Erro ao excluir.'); }
  }));
}

async function t13_addFator() {
  const codigo = prompt('Código do fator (ex.: FT1):');
  if (!codigo) return;
  const descricao = prompt('Descrição:') || codigo;
  await api.post('/api/composicao-preco/fatores', { codigo, descricao, tipo: '', pct_impostos: 0, pct_comissao: 0, pct_margem: 0 });
  t13_carregarFatores();
}

// ---------------- Itens Default ----------------

async function t13_carregarItensDefault() {
  const [itens, fatores, centros] = await Promise.all([
    api.get('/api/composicao-preco/itens-mestre'),
    api.get('/api/composicao-preco/fatores'),
    api.get('/api/tela10/centro-custo'),
  ]);
  const opcoesBloco = b => T13_BLOCOS_COMPOSICAO.map(x => `<option value="${x}" ${x === b ? 'selected' : ''}>${x}</option>`).join('');
  const opcoesFator = fid => '<option value="">—</option>' + fatores.map(f =>
    `<option value="${f.id}" ${f.id === fid ? 'selected' : ''}>${f.codigo}</option>`).join('');
  const opcoesCC = ccId => '<option value="">—</option>' + centros.map(c =>
    `<option value="${c.id}" ${c.id === ccId ? 'selected' : ''}>${c.codigo} — ${c.descricao || ''}</option>`).join('');
  const tbody = document.getElementById('t13_itensDefault');
  tbody.innerHTML = itens.map(it => `
    <tr data-item-id="${it.id}">
      <td><select data-campo="bloco">${opcoesBloco(it.bloco)}</select></td>
      <td><input data-campo="descricao" value="${it.descricao}" style="width:100%;"></td>
      <td><select data-campo="centro_custo_id">${opcoesCC(it.centro_custo_id)}</select></td>
      <td><select data-campo="fator_id">${opcoesFator(it.fator_id)}</select></td>
      <td><input data-campo="custo_unitario_padrao" type="number" step="0.01" value="${it.custo_unitario_padrao || 0}" style="width:100%;text-align:right;"></td>
      <td><span class="btn-text danger" data-del-item>x</span></td>
    </tr>`).join('');
  tbody.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async (e) => {
    const tr = e.target.closest('tr');
    const campo = inp.dataset.campo;
    let valor;
    if (campo === 'fator_id' || campo === 'centro_custo_id') valor = inp.value ? Number(inp.value) : null;
    else if (campo === 'custo_unitario_padrao') valor = parseFloat(inp.value) || 0;
    else valor = inp.value;
    await api.put(`/api/composicao-preco/itens-mestre/${tr.dataset.itemId}`, { [campo]: valor });
  }));
  tbody.querySelectorAll('[data-del-item]').forEach(b => b.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr');
    await api.del(`/api/composicao-preco/itens-mestre/${tr.dataset.itemId}`);
    t13_carregarItensDefault();
  }));
}

async function t13_addItemDefault() {
  const descricao = prompt('Descrição do item (ex.: Mão de Obra de Instalação):');
  if (!descricao) return;
  await api.post('/api/composicao-preco/itens-mestre', { bloco: T13_BLOCOS_COMPOSICAO[0], descricao });
  t13_carregarItensDefault();
}

// ---------------- Vendedores (mestre) ----------------

async function t13_carregarVendedores() {
  const vendedores = await api.get('/api/composicao-preco/vendedores');
  const tbody = document.getElementById('t13_vendedores');
  tbody.innerHTML = vendedores.map(v => `
    <tr data-vendedor-id="${v.id}">
      <td><input data-campo="nome" value="${v.nome}" style="width:100%;"></td>
      <td><input data-campo="pct_comissao_padrao" value="${(v.pct_comissao_padrao * 100).toFixed(1)}" style="width:70px;"></td>
      <td style="text-align:center;"><input type="checkbox" data-campo="default" ${v.default ? 'checked' : ''}></td>
      <td><span class="btn-text danger" data-del-vendedor>x</span></td>
    </tr>`).join('');
  tbody.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', async (e) => {
    const tr = e.target.closest('tr');
    const campo = inp.dataset.campo;
    let valor = inp.type === 'checkbox' ? inp.checked : inp.value;
    if (campo === 'pct_comissao_padrao') valor = parseNumBR(valor) / 100;
    await api.put(`/api/composicao-preco/vendedores/${tr.dataset.vendedorId}`, { [campo]: valor });
  }));
  tbody.querySelectorAll('[data-del-vendedor]').forEach(b => b.addEventListener('click', async (e) => {
    const tr = e.target.closest('tr');
    try { await api.del(`/api/composicao-preco/vendedores/${tr.dataset.vendedorId}`); t13_carregarVendedores(); }
    catch (err) { alert(JSON.parse(await err.message).detail || 'Erro ao excluir.'); }
  }));
}

async function t13_addVendedorMestre() {
  const nome = prompt('Nome do vendedor:');
  if (!nome) return;
  await api.post('/api/composicao-preco/vendedores', { nome, pct_comissao_padrao: 0, default: false });
  t13_carregarVendedores();
}

window.initTela13 = initTela13;
document.addEventListener('DOMContentLoaded', initTela13);
