// Seções da Tela E sempre em ordem alfabética (automático, ver discussão real 2026-07-18) — não
// depende de onde cada `<details class="cfg-accordion">` foi inserido no HTML.
function t7_ordenarSecoesAlfabeticamente() {
  const container = document.querySelector('#tela7 .body-pad');
  if (!container) return;
  const secoes = [...container.querySelectorAll(':scope > details.cfg-accordion')];
  secoes.sort((a, b) => a.querySelector('summary').textContent.localeCompare(
    b.querySelector('summary').textContent, 'pt-BR', { numeric: true }));
  secoes.forEach(s => container.appendChild(s));
}

function initTela7() {
  window.onShowTab = (function (orig) {
    return function (n) { if (orig) orig(n); if (n === 7) t7_carregar(); };
  })(window.onShowTab);
  t7_ordenarSecoesAlfabeticamente();
  document.getElementById('cfg_btnAddEspessura').addEventListener('click', t7_addEspessura);
  document.getElementById('cfg_btnAddPiso').addEventListener('click', t7_addPiso);
  document.getElementById('cfg_btnAddInsolacao').addEventListener('click', () => t7_tabelaGenerica.insolacao.add());
  document.getElementById('cfg_btnAddAmbienteLuminotecnico').addEventListener('click', () => t7_tabelaGenerica.ambientesLuminotecnico.add());
  document.getElementById('cfg_btnAddLampada').addEventListener('click', () => t7_tabelaGenerica.lampadas.add());
  document.getElementById('cfg_btnAddTabela02').addEventListener('click', () => t7_tabelaGenerica.tabela02.add());
  document.getElementById('cfg_btnSalvarTabela02Faixas').addEventListener('click', t7_salvarTabela02Faixas);
  document.getElementById('cfg_btnAddFaixaTabela02').addEventListener('click', t7_addFaixaTabela02);
  document.getElementById('cfg_btnAddEquipamento').addEventListener('click', () => t7_tabelaGenerica.equipamentos.add());
  document.getElementById('cfg_btnAddProduto').addEventListener('click', () => t7_tabelaGenerica.produtos.add());
  document.getElementById('cfg_btnAddIdComercial').addEventListener('click', () => t7_arvoreIdsComerciais.addNivel1());
  document.getElementById('cfg_btnAddClassificacaoSistema').addEventListener('click', () => t7_tabelaGenerica.classificacaoSistema.add());
  document.getElementById('cfg_btnAddLubrificanteCompressor').addEventListener('click', () => t7_tabelaGenerica.lubrificanteCompressor.add());
  document.getElementById('cfg_btnAddDadosFisicosBitzer').addEventListener('click', () => t7_tabelaGenerica.dadosFisicosBitzer.add());
  document.getElementById('cfg_btnAddTabelaDisjuntorTermomagnetico').addEventListener('click', () => t7_tabelaGenerica.tabelaDisjuntorTermomagnetico.add());
  document.getElementById('cfg_btnAddTabelaDisjuntorDdr').addEventListener('click', () => t7_tabelaGenerica.tabelaDisjuntorDdr.add());
  document.getElementById('cfg_btnAddTabelaValvulaExpansao').addEventListener('click', () => t7_tabelaGenerica.tabelaValvulaExpansao.add());
  document.getElementById('cfg_btnAddTabelaControladorValvula').addEventListener('click', () => t7_tabelaGenerica.tabelaControladorValvula.add());
  document.getElementById('cfg_btnAddTabelaCompatibilidadeValvula').addEventListener('click', () => t7_tabelaGenerica.tabelaCompatibilidadeValvula.add());
  document.getElementById('cfg_btnAddEstadoBrasileiro').addEventListener('click', () => t7_tabelaGenerica.estadosBrasileiros.add());
  document.getElementById('cfg_btnAddDadosClimatologicosInmet').addEventListener('click', () => t7_tabelaGenerica.dadosClimatologicosInmet.add());
  document.getElementById('cfg_btnBackupBanco').addEventListener('click', t7_backupBanco);
  document.getElementById('cfg_btnExportarCamposExcel').addEventListener('click', () =>
    api.baixarOuSalvar('/api/sistema/campos/exportar/excel'));
  t7_carregarCamposSistema();
  document.getElementById('cfg_btnAddCentroCusto').addEventListener('click', t7_addCentroCusto);
  t7_carregarCentroCusto();
}

// ---------- Tela 10 — Tabela Centro de Custos (mestre global) ----------

async function t7_carregarCentroCusto() {
  const conteudo = document.getElementById('cfg_centroCusto');
  conteudo.style.display = 'block';
  const [itens, idsComerciais] = await Promise.all([
    api.get('/api/tela10/centro-custo'),
    api.get('/api/catalogos/ids-comerciais'),
  ]);
  const optsIds = (selecionado) => '<option value="">—</option>' + idsComerciais.map(i =>
    `<option value="${i.codigo}" ${i.codigo === selecionado ? 'selected' : ''}>${i.codigo} — ${i.nome}</option>`).join('');
  const tbody = document.getElementById('cfg_centroCustoLista');
  tbody.innerHTML = itens.map(it => `<tr data-id="${it.id}">
    <td><input type="text" data-campo="codigo" value="${it.codigo ?? ''}"></td>
    <td><select data-campo="referencia_id">${optsIds(it.referencia_id)}</select></td>
    <td><input type="text" data-campo="descricao" value="${it.descricao ?? ''}" style="width:100%;"></td>
    <td><span class="btn-text danger" data-excluir>Excluir</span></td>
  </tr>`).join('');
  tbody.querySelectorAll('tr').forEach(tr => {
    tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', () => t7_salvarCentroCusto(tr)));
    tr.querySelector('[data-excluir]').addEventListener('click', async () => {
      if (!confirm('Excluir este centro de custo?')) return;
      await api.del(`/api/tela10/centro-custo/${tr.dataset.id}`);
      t7_carregarCentroCusto();
    });
  });
}

async function t7_salvarCentroCusto(tr) {
  const payload = {};
  tr.querySelectorAll('[data-campo]').forEach(inp => { payload[inp.dataset.campo] = inp.value; });
  await api.put(`/api/tela10/centro-custo/${tr.dataset.id}`, payload);
}

async function t7_addCentroCusto() {
  await api.post('/api/tela10/centro-custo', { codigo: '', referencia_id: '', etapa: '', descricao: '' });
  t7_carregarCentroCusto();
}

// ---------- Configurações Sistema — lista somente-leitura dos Ids de campo (Telas 1 a 7) ----------

let t7_camposSistemaCache = [];

async function t7_carregarCamposSistema() {
  t7_camposSistemaCache = await api.get('/api/sistema/campos');
  const el = document.getElementById('cfg_camposSistema');
  el.innerHTML = `<div style="overflow-x:auto;width:100%;"><table class="list">
    <thead><tr><th style="width:80px;">Id</th><th style="width:70px;">Tela</th><th>Rótulo</th></tr></thead>
    <tbody>${t7_camposSistemaCache.map(c =>
      `<tr><td style="font-family:monospace;">${c.campo_id}</td><td>${c.tela}</td><td>${c.rotulo}</td></tr>`).join('')}</tbody>
  </table></div>`;
}

async function t7_backupBanco() {
  try {
    const r = await fetch('/api/sistema/backup-banco', { method: 'POST' });
    if (!r.ok) throw new Error(await _extrairErro(r));
    const blob = await r.blob();
    const disp = r.headers.get('Content-Disposition') || '';
    const nome = disp.match(/filename="?([^";]+)"?/)?.[1] || 'backup.db';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert('Erro ao fazer backup: ' + e.message);
  }
}

// ---------- Tabelas genéricas editáveis (lista simples + inputs inline) ----------

function t7_criarTabelaGenerica(containerId, apiPath, campos, defaults) {
  async function carregar() {
    const itens = await api.get(apiPath);
    const el = document.getElementById(containerId);
    el.innerHTML = `<div style="overflow-x:auto;width:100%;"><table class="list" style="white-space:nowrap;">
      <thead><tr>${campos.map(c => `<th>${c.label}</th>`).join('')}<th></th></tr></thead>
      <tbody>${itens.map(it => `<tr data-id="${it.id}">${campos.map(c =>
        `<td><input type="text" data-campo="${c.key}" value="${it[c.key] ?? ''}" style="width:${c.width || 90}px;"></td>`).join('')}
        <td><span class="btn-text danger" data-excluir>Excluir</span></td></tr>`).join('')}</tbody></table></div>`;
    el.querySelectorAll('tbody tr').forEach(tr => {
      tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', () => salvarLinha(tr)));
      tr.querySelector('[data-excluir]').addEventListener('click', async () => {
        if (!confirm('Excluir este item?')) return;
        await api.del(`${apiPath}/${tr.dataset.id}`);
        carregar();
      });
    });
  }
  async function salvarLinha(tr) {
    const payload = {};
    campos.forEach(c => {
      const v = tr.querySelector(`[data-campo="${c.key}"]`).value;
      payload[c.key] = c.tipo === 'number' ? parseNumBR(v) : v;
    });
    await api.put(`${apiPath}/${tr.dataset.id}`, payload);
  }
  async function add() {
    const el = document.getElementById(containerId);
    await Promise.all(Array.from(el.querySelectorAll('tbody tr')).map(tr => salvarLinha(tr)));
    const payload = typeof defaults === 'function' ? defaults() : (defaults || {});
    await api.post(apiPath, payload);
    carregar();
  }
  return { carregar, add };
}

// Configurações de Painéis/Portas em MATRIZ: cada categoria é uma coluna (lista independente),
// linhas por posição (Ordem 0,1,2...). Portas têm uma coluna Grupo (Frio/Preparo/Doca) depois de
// Sentido, obrigatória só p/ Modelo/Sentido — é o grupo que filtra o dropdown de Modelo/Sentido no
// lançamento (ver t10_grupoFuncao). Só apresentação: usa o CRUD /api/paineis-portas/lookup e não
// altera nenhum dado existente.
const t7_paineisPortasMatriz = (function () {
  const API = '/api/paineis-portas/lookup';
  // Cada coluna pode ter "extras": campos do próprio item (grupo, descrição inicial, prefixo do Id),
  // que viram colunas à direita do valor. Grupo é combo (sugere grupos existentes + digitar novo).
  const GRUPO = { campo: 'grupo', label: 'Grupo', width: 100, combo: true };
  // Id Comercial: select em cascata sobre a árvore de id_comercial.py (categoria "8 Painéis") —
  // liga essa Espessura/Modelo Porta à ficha comercial correspondente (Tela 13), pra
  // montar_memorial_projeto() puxar Painéis/Portas automaticamente (ver resolver_ids_paineis_portas).
  // Em Painéis, o material (PIR/EPS/PUR) fica embutido no VALOR da Espessura (ex.: "PIR 70mm"),
  // não em Tipo Painel (que é só Parede/Teto/Isolamento Piso) — por isso o seletor vai nas colunas
  // de Espessura, não em Tipo Painel.
  const ID_COMERCIAL = { campo: 'id_comercial', label: 'Id Comercial', width: 210, arvore: true, opcional: true };
  const TABELAS = [
    { container: 'cfg_lkp_painelPiso',
      colunas: [{ cat: 'Tipo Painel' },
                { cat: 'Espessura Parede/Teto', extras: [{ campo: 'descricao_inicial', label: 'Descrição', width: 230 }, ID_COMERCIAL] },
                { cat: 'Espessura Piso', extras: [ID_COMERCIAL] }] },
    { container: 'cfg_lkp_portas',
      colunas: [
        { cat: 'Função Porta', extras: [GRUPO] },
        { cat: 'Modelo Porta', extras: [
            { campo: 'descricao_inicial', label: 'Descrição Inicial', width: 230 },
            { campo: 'prefixo_id', label: 'Prefixo Id', width: 90 }, GRUPO, ID_COMERCIAL] },
        { cat: 'Sentido Porta', extras: [GRUPO] },
        { cat: 'Fixação Porta' }, { cat: 'Tensão Porta' }] },
  ];
  let cache = [];
  let arvoreIds = [];
  const esc = s => String(s ?? '').replace(/"/g, '&quot;');
  const gruposExistentes = () => [...new Set(cache.map(x => x.grupo).filter(Boolean))].sort();
  const itensDe = cat => cache.filter(x => x.categoria === cat).sort((a, b) => (a.ordem - b.ordem) || (a.id - b.id));
  const proxOrdem = cat => { const it = itensDe(cat); return it.length ? Math.max(...it.map(x => x.ordem || 0)) + 1 : 0; };
  function htmlOpcoesArvoreId(selecionado) {
    return arvoreIds.map(n => {
      const prof = (n.codigo.match(/\./g) || []).length;
      return `<option value="${n.codigo}" ${n.codigo === selecionado ? 'selected' : ''}>${'    '.repeat(prof)}${n.codigo} — ${n.nome}</option>`;
    }).join('');
  }

  async function carregar() {
    [cache, arvoreIds] = await Promise.all([api.get(API), api.get('/api/catalogo-comercial/arvore-ids')]);
    render();
  }

  function render() {
    for (const tab of TABELAS) {
      const el = document.getElementById(tab.container);
      if (!el) continue;
      const colItens = tab.colunas.map(c => itensDe(c.cat));
      const maxLen = Math.max(0, ...colItens.map(a => a.length));
      let ths = '<th style="width:52px;">Ordem</th>';
      tab.colunas.forEach(c => { ths += `<th>${c.cat}</th>`; (c.extras || []).forEach(x => ths += `<th>${x.label}</th>`); });
      let rows = '';
      for (let r = 0; r <= maxLen; r++) {          // maxLen itens + 1 linha de inclusão no fim
        const inclusao = r === maxLen;
        let tds = `<td style="text-align:center;color:#6b7280;">${inclusao ? '' : r}</td>`;
        tab.colunas.forEach((c, i) => {
          const it = colItens[i][r];
          const larg = c.cat.startsWith('Espessura') ? 200 : 130;
          tds += `<td><input type="text" data-cat="${esc(c.cat)}" data-id="${it ? it.id : ''}" data-row="${r}"
                    value="${it ? esc(it.valor) : ''}" placeholder="${inclusao ? '+ novo' : ''}" style="width:${larg}px;"></td>`;
          (c.extras || []).forEach(x => {
            const v = it && it[x.campo] ? it[x.campo] : '';
            if (x.arvore) {
              tds += `<td><select data-extrafor="${esc(c.cat)}" data-campo="${x.campo}" data-row="${r}" style="width:${x.width}px;">
                        <option value="">— nenhum —</option>${htmlOpcoesArvoreId(v)}</select></td>`;
              return;
            }
            const lista = x.combo ? ' list="cfg_lkp_grupos"' : '';
            tds += `<td><input${lista} data-extrafor="${esc(c.cat)}" data-campo="${x.campo}" data-row="${r}" value="${esc(v)}"
                      placeholder="${esc(x.label.toLowerCase())}" style="width:${x.width}px;"></td>`;
          });
        });
        rows += `<tr>${tds}</tr>`;
      }
      const datalist = `<datalist id="cfg_lkp_grupos">${gruposExistentes().map(g => `<option value="${esc(g)}"></option>`).join('')}</datalist>`;
      el.innerHTML = `${datalist}<div style="overflow-x:auto;width:fit-content;max-width:100%;"><table class="list" style="width:auto;white-space:nowrap;">
        <thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table></div>`;
      el.querySelectorAll('input[data-cat]').forEach(inp => inp.addEventListener('change', () => onCelula(inp, el)));
      el.querySelectorAll('input[data-extrafor], select[data-extrafor]').forEach(inp => inp.addEventListener('change', () => onExtra(inp)));
    }
  }

  function extrasDaColuna(cat) {
    for (const tab of TABELAS) for (const c of tab.colunas) if (c.cat === cat) return c.extras || [];
    return [];
  }

  async function onCelula(inp, el) {
    const cat = inp.dataset.cat, id = inp.dataset.id, val = inp.value.trim(), row = inp.dataset.row;
    if (id) {
      if (val === '') {
        const it = cache.find(x => String(x.id) === String(id));
        if (!confirm(`Excluir "${it ? it.valor : ''}" de ${cat}?`)) { render(); return; }
        await api.del(`${API}/${id}`);
      } else {
        await api.put(`${API}/${id}`, { valor: val });
      }
    } else if (val !== '') {
      const payload = { categoria: cat, valor: val, ordem: proxOrdem(cat) };
      // Ao INCLUIR, os campos extras (Descrição Inicial/Prefixo Id/Grupo) são obrigatórios.
      for (const x of extrasDaColuna(cat)) {
        const ex = el.querySelector(`[data-extrafor="${cat}"][data-campo="${x.campo}"][data-row="${row}"]`);
        const v = ex ? ex.value.trim() : '';
        if (!v && !x.opcional) { alert(`Preencha "${x.label}" para incluir em ${cat}.`); render(); return; }
        if (v) payload[x.campo] = v;
      }
      await api.post(API, payload);
    } else { return; }
    carregar();
  }

  async function onExtra(inp) {
    const cat = inp.dataset.extrafor, campo = inp.dataset.campo, row = Number(inp.dataset.row), v = inp.value.trim();
    const it = itensDe(cat)[row];        // só o item DESTA coluna nesta linha
    if (!it) return;                     // linha de inclusão: mantém o valor no DOM p/ o POST
    if ((it[campo] || '') === v) return;
    await api.put(`${API}/${it.id}`, { [campo]: v });
    carregar();
  }

  return { carregar, add: () => {} };
})();

const t7_tabelaGenerica = {
  insolacao: t7_criarTabelaGenerica('cfg_fatorInsolacao', '/api/catalogos/fator-insolacao',
    [{ key: 'orientacao', label: 'Orientação', width: 260 }, { key: 'fator', label: 'Fator', tipo: 'number', width: 80 }],
    { orientacao: 'Nova orientação', fator: 1.0 }),
  ambientesLuminotecnico: t7_criarTabelaGenerica('cfg_ambientesLuminotecnico', '/api/catalogos/ambientes-luminotecnico',
    [{ key: 'nome', label: 'Ambiente / Atividade', width: 320 }, { key: 'lux_recomendado', label: 'Lux Recomendado', tipo: 'number', width: 100 }],
    { nome: 'Novo ambiente', lux_recomendado: 200 }),
  // Lâmpadas: id_comercial vem sozinho da cascata (Modelo → árvore), não editável aqui. Fabricante
  // (aprovado 2026-08-10) é opcional -- puxado pra Composição de Preço; vazio aqui = fica em
  // branco lá pro usuário completar manual.
  lampadas: t7_criarTabelaGenerica('cfg_lampadas', '/api/luminotecnico/lampadas',
    [{ key: 'modelo', label: 'Modelo', width: 260 }, { key: 'fabricante', label: 'Fabricante', width: 160 },
     { key: 'potencia_w', label: 'Potência (W)', tipo: 'number', width: 90 },
     { key: 'fluxo_lumens', label: 'Fluxo Luminoso (lm)', tipo: 'number', width: 100 }, { key: 'ip', label: 'IP', width: 70 },
     { key: 'temperatura_cor_k', label: 'Temperatura Cor (K)', tipo: 'number', width: 100 }, { key: 'tensao', label: 'Tensão', width: 80 }],
    { modelo: 'Novo modelo', fabricante: '', potencia_w: 0, fluxo_lumens: 0, ip: '', temperatura_cor_k: 0, tensao: '' }),
  tabela02: t7_criarTabelaGenerica('cfg_tabela02', '/api/catalogos/tabela-tipo02',
    [{ key: 'tipo', label: 'Tipo de Produto', width: 320 }, { key: 'temp_interna_default', label: 'Temp. Interna Default (°C)', tipo: 'number', width: 90 }],
    { tipo: 'Novo tipo', temp_interna_default: 0 }),
  equipamentos: t7_criarTabelaGenerica('cfg_equipamentos', '/api/catalogos/tipos-equipamento',
    [{ key: 'nome', label: 'Nome', width: 280 }, { key: 'potencia_tipica_w', label: 'Potência Típica (W)', tipo: 'number', width: 90 },
     { key: 'fator_calor_rejeitado', label: 'Fator Calor Rejeitado (0-1)', tipo: 'number', width: 90 },
     { key: 'fator_simultaneidade', label: 'Fator Simultaneidade (0-1)', tipo: 'number', width: 90 }],
    { nome: 'Novo equipamento', potencia_tipica_w: 0, fator_calor_rejeitado: 1, fator_simultaneidade: 1 }),
  paineisPortasLookup: t7_paineisPortasMatriz,
  produtos: t7_criarTabelaGenerica('cfg_produtos', '/api/catalogos/produtos',
    [{ key: 'nome', label: 'Produto', width: 180 }, { key: 'temp_conservacao', label: 'Temp. Conservação', width: 100 },
     { key: 'umidade_relativa', label: 'UR (%)', width: 80 }, { key: 'tempo_conservacao', label: 'Tempo Conservação', width: 110 },
     { key: 'pct_agua', label: '% Água', tipo: 'number', width: 70 }, { key: 'ponto_congelamento', label: 'Pt. Congel. (°C)', tipo: 'number', width: 80 },
     { key: 'calor_esp_antes', label: 'Calor Esp. Antes', tipo: 'number', width: 90 }, { key: 'calor_esp_depois', label: 'Calor Esp. Depois', tipo: 'number', width: 90 },
     { key: 'calor_latente', label: 'Calor Latente', tipo: 'number', width: 90 }, { key: 'calor_respiracao', label: 'Calor Respiração', tipo: 'number', width: 90 },
     { key: 'classe', label: 'Classe', tipo: 'number', width: 60 }, { key: 'fonte_status', label: 'Fonte/Status', width: 140 }],
    { nome: 'Novo produto' }),
  classificacaoSistema: t7_criarTabelaGenerica('cfg_classificacaoSistema', '/api/catalogos/classificacao-sistema-compressor',
    [{ key: 'tipo', label: 'Tipo', width: 160 },
     { key: 'temp_evap_sistema_min', label: 'Temp. Evap. Sistema Mín (°C)', tipo: 'number', width: 90 },
     { key: 'temp_evap_sistema_max', label: 'Temp. Evap. Sistema Máx (°C)', tipo: 'number', width: 90 },
     { key: 'motor_compressor', label: 'Motor Compressor', tipo: 'number', width: 80 },
     { key: 'semi_hermetico_te_min', label: 'Bitzer Semi-Hermético Regra Mín (°C)', tipo: 'number', width: 90 },
     { key: 'semi_hermetico_te_max', label: 'Bitzer Semi-Hermético Regra Máx (°C)', tipo: 'number', width: 90 },
     { key: 'duplo_estagio_te_min', label: 'Bitzer Duplo Estágio Regra Mín (°C) — vazio = Não Aplicável', tipo: 'number', width: 90 },
     { key: 'duplo_estagio_te_max', label: 'Bitzer Duplo Estágio Regra Máx (°C) — vazio = Não Aplicável', tipo: 'number', width: 90 }],
    { tipo: 'Novo tipo', motor_compressor: 0 }),
  lubrificanteCompressor: t7_criarTabelaGenerica('cfg_lubrificanteCompressor', '/api/catalogos/lubrificante-compressor',
    [{ key: 'fabricante', label: 'Fabricante', width: 140 }, { key: 'gas', label: 'Gás', width: 120 },
     { key: 'tipo_oleo', label: 'Tipo de Óleo', width: 120 }],
    { fabricante: 'Bitzer', gas: 'Novo gás', tipo_oleo: '' }),
  dadosFisicosBitzer: t7_criarTabelaGenerica('cfg_dadosFisicosBitzer', '/api/catalogos/dados-fisicos-compressor-bitzer',
    [{ key: 'linha', label: 'Linha', width: 130 }, { key: 'modelo', label: 'Modelo', width: 110 },
     { key: 'vazao', label: 'Vazão (1750/min 60Hz)', width: 130 },
     { key: 'numero_cilindros_diametro_curso', label: 'Nº Cilindros x Diâmetro x Curso', width: 170 },
     { key: 'peso', label: 'Peso', width: 90 },
     { key: 'sobrepressao_maxima', label: 'Sobrepressão Máxima', width: 130 },
     { key: 'conexao_succao', label: 'Conexão Sucção', width: 130 },
     { key: 'conexao_pressao', label: 'Conexão Pressão', width: 130 },
     { key: 'protetor_motor', label: 'Protetor de Motor', width: 130 },
     { key: 'classe_protecao', label: 'Classe de Proteção', width: 100 },
     { key: 'qtd_enchimento_oleo', label: 'Qtd. Enchimento de Óleo', width: 130 },
     { key: 'regulacao_desempenho', label: 'Regulação de Desempenho', width: 150 },
     { key: 'aquecimento_carter_oleo', label: 'Aquecimento do Cárter de Óleo', width: 170 },
     { key: 'monitoramento_pressao_oleo', label: 'Monitoramento Pressão de Óleo', width: 170 },
     { key: 'versao_motor', label: 'Versão do Motor', width: 100 },
     { key: 'corrente_maxima_operacao', label: 'Corrente Máxima de Operação', width: 150 },
     { key: 'corrente_partida', label: 'Corrente de Partida (rotor bloqueado)', width: 170 },
     { key: 'potencia_sonora_10_45', label: 'Potência Sonora (-10°C/45°C)', width: 150 },
     { key: 'potencia_sonora_35_40', label: 'Potência Sonora (-35°C/40°C)', width: 150 },
     { key: 'pressao_sonora_1m_10_45', label: 'Pressão Sonora 1m (-10°C/45°C)', width: 150 }],
    { linha: 'Semi-Hermético', modelo: 'Novo modelo' }),
  tabelaDisjuntorTermomagnetico: t7_criarTabelaGenerica('cfg_tabelaDisjuntorTermomagnetico', '/api/catalogos/tabela-disjuntor-termomagnetico',
    [{ key: 'utilizacao', label: 'Utilizações', width: 110 },
     { key: 'corrente_nominal_a', label: 'Corrente Nominal (A)', tipo: 'number', width: 100 },
     { key: 'desc_proj_127v_1p', label: '127V 1P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_127v_1p', label: '127V 1P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_220v_1p', label: '220V 1P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_220v_1p', label: '220V 1P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_220v_3p', label: '220V 3P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_220v_3p', label: '220V 3P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_380v_3p', label: '380V 3P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_380v_3p', label: '380V 3P — Descrição Comercial', width: 260 }],
    { corrente_nominal_a: 0 }),
  tabelaDisjuntorDdr: t7_criarTabelaGenerica('cfg_tabelaDisjuntorDdr', '/api/catalogos/tabela-disjuntor-ddr',
    [{ key: 'utilizacao', label: 'Utilizações', width: 110 },
     { key: 'corrente_nominal_a', label: 'Corrente Nominal (A)', tipo: 'number', width: 100 },
     { key: 'desc_proj_127v_1p', label: '127V 1P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_127v_1p', label: '127V 1P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_220v_1p', label: '220V 1P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_220v_1p', label: '220V 1P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_220v_3p', label: '220V 3P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_220v_3p', label: '220V 3P — Descrição Comercial', width: 260 },
     { key: 'desc_proj_380v_3p', label: '380V 3P — Descrição Proj.', width: 130 },
     { key: 'desc_comercial_380v_3p', label: '380V 3P — Descrição Comercial', width: 260 }],
    { corrente_nominal_a: 0 }),
  // Tela A - Tabelas de Válvulas de Expansão — 3 tabelas (Válvulas / Controladores / Compatibi-
  // lidade). Defaults do "+ adicionar" cobrem TODOS os campos NOT NULL do schema (fabricante/
  // tipo_expansao/modelo etc.) — nunca deixar NOT NULL sem default (bug real do passado).
  tabelaValvulaExpansao: t7_criarTabelaGenerica('cfg_tabelaValvulaExpansao', '/api/catalogos/tabela-valvula-expansao',
    [{ key: 'fabricante', label: 'Fabricante', width: 100 },
     { key: 'tipo_expansao', label: 'Tipo (Eletrônica/Termostática)', width: 130 },
     { key: 'modelo', label: 'Modelo', width: 100 },
     { key: 'conexao_entrada', label: 'Conexão Entrada', width: 100 },
     { key: 'conexao_saida', label: 'Conexão Saída', width: 100 },
     { key: 'tensao', label: 'Tensão', width: 110 },
     { key: 'tipo_motor', label: 'Tipo Motor (Unipolar/Bipolar)', width: 130 },
     { key: 'equalizacao', label: 'Equalização', width: 90 },
     { key: 'gas_compativel', label: 'Gás Compatível', width: 110 }],
    { fabricante: 'Novo fabricante', tipo_expansao: 'Eletrônica', modelo: 'Novo modelo' }),
  tabelaControladorValvula: t7_criarTabelaGenerica('cfg_tabelaControladorValvula', '/api/catalogos/tabela-controlador-valvula',
    [{ key: 'fabricante', label: 'Fabricante', width: 100 },
     { key: 'modelo', label: 'Modelo', width: 130 },
     { key: 'tipo_expansao', label: 'Tipo de Válvula que Atende', width: 130 },
     { key: 'classificacao', label: 'Classificação (Universal/Alta-Média/Baixa)', width: 160 },
     { key: 'observacao', label: 'Observação', width: 300 }],
    { fabricante: 'Novo fabricante', modelo: 'Novo modelo', tipo_expansao: 'Eletrônica' }),
  tabelaCompatibilidadeValvula: t7_criarTabelaGenerica('cfg_tabelaCompatibilidadeValvula', '/api/catalogos/tabela-compatibilidade-valvula',
    [{ key: 'valvula_modelo', label: 'Modelo da Válvula', width: 140 },
     { key: 'controlador_modelo', label: 'Modelo do Controlador/Driver', width: 180 }],
    { valvula_modelo: 'Novo modelo', controlador_modelo: 'Novo controlador' }),
  estadosBrasileiros: t7_criarTabelaGenerica('cfg_estadosBrasileiros', '/api/catalogos/estados-brasileiros',
    [{ key: 'estado', label: 'Estado', width: 180 }, { key: 'sigla', label: 'Sigla', width: 70 },
     { key: 'capital', label: 'Capital', width: 150 }, { key: 'regiao', label: 'Região', width: 120 }],
    () => ({ estado: 'Novo estado', sigla: '?' + Date.now() % 100000, capital: '', regiao: '' })),
  dadosClimatologicosInmet: t7_criarTabelaGenerica('cfg_dadosClimatologicosInmet', '/api/catalogos/dados-climatologicos-inmet',
    [{ key: 'codigo', label: 'Código', width: 90 }, { key: 'nome_estacao', label: 'Nome da Estação', width: 200 },
     { key: 'uf', label: 'UF', width: 60 },
     { key: 'temp_maxima_historica', label: 'Histórica — Temp. Máx. Absoluta (°C)', tipo: 'number', width: 130 },
     { key: 'ur_media_historica', label: 'Histórica — UR Média (%)', tipo: 'number', width: 110 }],
    { codigo: '', nome_estacao: 'Nova estação', uf: '' }),
};

// ---------- Tabela de Ids Comerciais — árvore hierárquica (não lista plana) ----------
// Cada código (ex.: "2.2.1.1") é lido direto pela profundidade (nº de pontos): nós com filhos são
// "etapa" (categoria, sem texto comercial próprio) e recolhem/expandem; nós folha são o item final
// que de fato recebe Id no seletor em cascata do Catálogo Comercial.

const t7_arvoreIdsComerciais = (function () {
  const containerId = 'cfg_idsComerciais';
  const apiPath = '/api/catalogos/ids-comerciais';
  let cache = [];
  let camposSistema = [];
  let fatoresVenda = [];
  let centrosCusto = [];
  const colapsados = new Set(); // códigos de nível 1 recolhidos

  function chaveCodigo(codigo) {
    return codigo.split('.').map(p => parseInt(p, 10) || 0);
  }
  function comparaCodigo(a, b) {
    const ca = chaveCodigo(a), cb = chaveCodigo(b);
    for (let i = 0; i < Math.max(ca.length, cb.length); i++) {
      const diff = (ca[i] || 0) - (cb[i] || 0);
      if (diff !== 0) return diff;
    }
    return 0;
  }
  function temFilho(codigo) {
    return cache.some(i => i.codigo !== codigo && i.codigo.startsWith(codigo + '.'));
  }
  function nivel1De(codigo) {
    return codigo.split('.')[0];
  }
  function proximoCodigoFilho(paiCodigo) {
    if (!paiCodigo) {
      const topos = cache.map(i => parseInt(i.codigo.split('.')[0], 10) || 0);
      return String((topos.length ? Math.max(...topos) : 0) + 1);
    }
    const prefixo = paiCodigo + '.';
    const filhos = cache.filter(i => i.codigo.startsWith(prefixo) && i.codigo.slice(prefixo.length).indexOf('.') === -1);
    const nums = filhos.map(i => parseInt(i.codigo.slice(prefixo.length), 10) || 0);
    return prefixo + String((nums.length ? Math.max(...nums) : 0) + 1);
  }

  async function carregar() {
    const [arvore, campos, fatores, centros] = await Promise.all([
      api.get(apiPath), api.get('/api/sistema/campos'), api.get('/api/composicao-preco/fatores'),
      api.get('/api/tela10/centro-custo'),
    ]);
    cache = arvore.slice().sort((a, b) => comparaCodigo(a.codigo, b.codigo));
    camposSistema = campos;
    fatoresVenda = fatores;
    centrosCusto = centros;
    render();
  }

  function nivelBadge(n) {
    const cores = { 1: '#E6F1FB;color:#0C447C', 2: '#EEEDFE;color:#3C3489', 3: '#E1F5EE;color:#085041', 4: '#FAEEDA;color:#633806' };
    const par = (cores[n] || '#F1EFE8;color:#444441').split(';color:');
    return `<span style="background:${par[0]};color:${par[1]};font-size:11px;padding:2px 8px;border-radius:4px;white-space:nowrap;">Nível ${n}</span>`;
  }

  function optsCampo(selecionado) {
    return '<option value="">—</option>' + camposSistema.map(c =>
      `<option value="${c.campo_id}" ${c.campo_id === selecionado ? 'selected' : ''}>${c.campo_id} — ${c.rotulo}</option>`).join('');
  }
  function optsFator(selecionado) {
    return '<option value="">—</option>' + fatoresVenda.map(f =>
      `<option value="${f.id}" ${f.id === selecionado ? 'selected' : ''}>${f.codigo} — ${f.descricao}</option>`).join('');
  }
  function optsCC(selecionado) {
    return '<option value="">—</option>' + centrosCusto.map(c =>
      `<option value="${c.codigo}" ${c.codigo === selecionado ? 'selected' : ''}>${c.codigo} — ${c.descricao || ''}</option>`).join('');
  }

  function render() {
    const el = document.getElementById(containerId);
    const linhas = cache.map(it => {
      const prof = (it.codigo.match(/\./g) || []).length;
      const nivel = prof + 1;
      const n1 = nivel1De(it.codigo);
      if (prof > 0 && colapsados.has(n1)) return '';
      const filho = temFilho(it.codigo);
      const indentPx = prof * 22;
      const toggle = (prof === 0 && filho)
        ? `<span class="btn-text" data-toggle="${it.codigo}" style="margin-right:6px;cursor:pointer;">${colapsados.has(it.codigo) ? '▸' : '▾'}</span>`
        : `<span style="display:inline-block;width:18px;"></span>`;
      const estiloNome = filho ? 'font-weight:bold;' : '';
      // "Campo em si": nó-container que corresponde 1:1 a um <select> real das telas (ex.: "1.2 —
      // Tipo Automação Linhas") — não recebe Campo (Id)/Centro de Custo/Fator de Venda próprio
      // porque ele NÃO é uma opção, é o campo. Os filhos dele (ex.: "1.2.1 — Controle",
      // "1.2.1.1 — Danfoss") SÃO opções desse campo (mesmo tendo filhos por sua vez, ex. fornecedor
      // -> modelo) e por isso recebem Campo (Id) normalmente (aprovado 2026-08-08). Só as 5 seções-
      // raiz (Elétrica/Mecânica/Válvula de Expansão/Equipamentos/Instalação) e os campos de nível 2
      // que já têm T-code próprio na Tela 1 ficam nessa lista.
      const ANCORAS_CAMPO = new Set(['1', '2', '3', '4', '5', '1.1', '1.2', '1.3', '2.1']);
      const ehAncoraCampo = ANCORAS_CAMPO.has(it.codigo);
      // Só nó de catálogo de verdade (Forçador de Ar/Unidade Condensadora Comercial/Condensador
      // Remoto a Ar — produto com ficha técnica própria noutra tabela) não tem Campo (Id) — o valor
      // vem de escolher aquele produto específico, não de um campo de formulário simples. Nó de
      // MODELO AVULSO (Válvula/Automação/Controlador/Lâmpada, criado via resolver_no_modelo) é uma
      // opção de campo igual a qualquer outra folha da árvore, mesmo quando origem_automatica=True
      // (só foi criado na hora em vez de vir semeado) — libera Campo (Id) normalmente (aprovado
      // 2026-08-09, corrige bloqueio indevido detectado em 1.2.2.2.1/1.4.1.1). Centro de Custo/
      // Fator de Venda padrão continuam fazendo sentido e ficam editáveis normalmente em ambos.
      const ANCORAS_CATALOGO = ['4.2.', '4.1.1.', '4.4.1.'];
      const ehNoCatalogo = ANCORAS_CATALOGO.some(prefixo => it.codigo.startsWith(prefixo));
      const campoIdCol = ehNoCatalogo
        ? `<td style="color:var(--muted,#9ca3af);text-align:center;" title="Não se aplica a nó de catálogo (Forçador/UC/Condensador)">—</td>`
        : `<td><select data-campo="campo_id" style="width:150px;">${optsCampo(it.campo_id)}</select></td>`;
      const camposExtras = ehAncoraCampo
        ? `<td colspan="3" style="color:var(--muted,#9ca3af);text-align:center;" title="Campo em si — contém as opções abaixo, não recebe Campo (Id) próprio">— (campo)</td>`
        : `${campoIdCol}
           <td><select data-campo="centro_custo_padrao_codigo" style="width:150px;">${optsCC(it.centro_custo_padrao_codigo)}</select></td>
           <td><select data-campo="fator_venda_padrao_id" style="width:120px;">${optsFator(it.fator_venda_padrao_id)}</select></td>`;
      return `<tr data-id="${it.id}" data-codigo="${it.codigo}">
        <td style="white-space:nowrap;padding-left:${indentPx}px;"><span class="drag-handle" draggable="true" data-drag-codigo="${it.codigo}" title="Arrastar para dentro de outro item, pra mudar o nível" style="cursor:grab;margin-right:4px;user-select:none;">⋮⋮</span>${toggle}<input type="text" data-campo="codigo" value="${it.codigo}" style="width:90px;"></td>
        <td style="${estiloNome}"><input type="text" data-campo="nome" value="${it.nome}" style="width:100%;min-width:220px;${estiloNome}"></td>
        <td>${nivelBadge(nivel)}</td>
        ${camposExtras}
        <td style="white-space:nowrap;">
          <span class="btn-text" data-add-filho="${it.codigo}">+ item abaixo</span>
          <span class="btn-text danger" data-excluir="${it.id}" style="margin-left:10px;">Excluir</span>
        </td>
      </tr>`;
    }).join('');
    el.innerHTML = `<div style="overflow-x:auto;width:100%;"><table class="list" style="white-space:nowrap;">
      <thead><tr><th>Código</th><th>Nome (gabarito da árvore — negrito = etapa, normal = item final)</th><th>Nível</th>
      <th>Campo (Id)</th><th>Centro de Custo padrão</th><th>Fator de Venda padrão</th><th></th></tr></thead>
      <tbody>${linhas}</tbody></table></div>`;

    el.querySelectorAll('[data-toggle]').forEach(b => b.addEventListener('click', () => {
      const c = b.dataset.toggle;
      if (colapsados.has(c)) colapsados.delete(c); else colapsados.add(c);
      render();
    }));
    el.querySelectorAll('tbody tr').forEach(tr => {
      tr.querySelectorAll('[data-campo]').forEach(inp => inp.addEventListener('change', () => salvarLinha(tr)));
      tr.querySelector('[data-excluir]').addEventListener('click', async () => {
        if (!confirm('Excluir este item (e possíveis itens abaixo dele ficarão órfãos)?')) return;
        await api.del(`${apiPath}/${tr.querySelector('[data-excluir]').dataset.excluir}`);
        await carregar();
      });
      tr.querySelector('[data-add-filho]').addEventListener('click', () => addFilho(tr.querySelector('[data-add-filho]').dataset.addFilho));
    });
    el.querySelectorAll('[data-drag-codigo]').forEach(handle => {
      handle.addEventListener('dragstart', ev => {
        ev.dataTransfer.setData('text/plain', handle.dataset.dragCodigo);
        ev.dataTransfer.effectAllowed = 'move';
      });
    });
    el.querySelectorAll('tbody tr').forEach(tr => {
      tr.addEventListener('dragover', ev => { ev.preventDefault(); ev.dataTransfer.dropEffect = 'move'; });
      tr.addEventListener('drop', ev => {
        ev.preventDefault();
        const codigoOrigem = ev.dataTransfer.getData('text/plain');
        const codigoDestino = tr.dataset.codigo;
        if (codigoOrigem) mover(codigoOrigem, codigoDestino);
      });
    });
  }

  // Arrastar um nó "para dentro" de outro (novoPaiCodigo) — muda o código dele e de todo
  // descendente em cascata, sempre com preview (mostra tudo que vai mudar) antes de gravar
  // (aprovado 2026-08-09, "só arrastar", sem edição direta da coluna Nível).
  async function mover(codigoOrigem, novoPaiCodigo) {
    if (codigoOrigem === novoPaiCodigo || novoPaiCodigo.startsWith(codigoOrigem + '.')) {
      alert('Não é possível mover um item para dentro dele mesmo.');
      return;
    }
    const origem = cache.find(i => i.codigo === codigoOrigem);
    if (!origem) return;
    let preview;
    try {
      preview = await api.post(`${apiPath}/${origem.id}/mover-preview`, { novo_pai_codigo: novoPaiCodigo });
    } catch (e) {
      alert('Não foi possível calcular a movimentação: ' + (e.message || e));
      return;
    }
    const linhasMapa = Object.entries(preview.mapa).map(([de, para]) => `  ${de}  →  ${para}`).join('\n');
    const linhasAfetados = preview.afetados.length
      ? preview.afetados.map(a => `  ${a.tabela} #${a.id} (${a.identificacao ?? ''}), campo "${a.campo}": ${a.de} → ${a.para}`).join('\n')
      : '  (nenhuma referência solta encontrada)';
    const msg = `Mover "${codigoOrigem}" pra dentro de "${novoPaiCodigo}"?\n\n`
      + `Códigos que vão mudar:\n${linhasMapa}\n\n`
      + `Referências que serão atualizadas junto:\n${linhasAfetados}\n\n`
      + `Confirma?`;
    if (!confirm(msg)) return;
    await api.post(`${apiPath}/${origem.id}/mover-confirmar`, { novo_pai_codigo: novoPaiCodigo });
    await carregar();
  }

  async function salvarLinha(tr) {
    const payload = {
      codigo: tr.querySelector('[data-campo="codigo"]').value.trim(),
      nome: tr.querySelector('[data-campo="nome"]').value.trim(),
    };
    const campoId = tr.querySelector('[data-campo="campo_id"]');
    if (campoId) payload.campo_id = campoId.value || null;
    const cc = tr.querySelector('[data-campo="centro_custo_padrao_codigo"]');
    if (cc) payload.centro_custo_padrao_codigo = cc.value || null;
    const fator = tr.querySelector('[data-campo="fator_venda_padrao_id"]');
    if (fator) payload.fator_venda_padrao_id = fator.value ? Number(fator.value) : null;
    await api.put(`${apiPath}/${tr.dataset.id}`, payload);
    await carregar();
  }

  async function addFilho(paiCodigo) {
    const nome = prompt(`Nome do novo item dentro de "${paiCodigo}":`);
    if (!nome) return;
    const codigo = proximoCodigoFilho(paiCodigo);
    await api.post(apiPath, { codigo, nome: nome.trim(), ordem: 0 });
    await carregar();
  }

  async function addNivel1() {
    const nome = prompt('Nome da nova etapa principal (nível 1):');
    if (!nome) return;
    const codigo = proximoCodigoFilho(null);
    await api.post(apiPath, { codigo, nome: nome.trim(), ordem: 0 });
    await carregar();
  }

  return { carregar, addNivel1 };
})();

// ---------- Tabela 02 — matriz de faixas de área x tipo (carga tabelada, kcal/h) ----------

let t7_tabela02FaixasCache = null;

async function t7_carregarTabela02Faixas() {
  const dados = await api.get('/api/catalogos/tabela02-faixas');
  t7_tabela02FaixasCache = dados;
  t7_renderTabela02Faixas();
}

function t7_renderTabela02Faixas() {
  const { tipos, faixas } = t7_tabela02FaixasCache;
  const el = document.getElementById('cfg_tabela02Faixas');
  el.innerHTML = `<div style="overflow-x:auto;width:100%;"><table class="list" style="white-space:nowrap;">
    <thead><tr><th>Área de (m²)</th><th>Área até (m²)</th>${tipos.map(t => `<th>${t.tipo}</th>`).join('')}</tr></thead>
    <tbody>${faixas.map((f, i) => `<tr data-idx="${i}">
      <td><input type="text" data-campo="area_de" value="${f.area_de}" style="width:70px;"></td>
      <td><input type="text" data-campo="area_ate" value="${f.area_ate}" style="width:70px;"></td>
      ${tipos.map(t => `<td><input type="text" data-tipo="${t.id}" value="${f.valores[t.id] ?? ''}" style="width:80px;"></td>`).join('')}
    </tr>`).join('')}</tbody></table></div>`;
}

function t7_addFaixaTabela02() {
  if (!t7_tabela02FaixasCache) return;
  const ultima = t7_tabela02FaixasCache.faixas[t7_tabela02FaixasCache.faixas.length - 1];
  const de = ultima ? ultima.area_ate : 0;
  t7_tabela02FaixasCache.faixas.push({ area_de: de, area_ate: de + 1, valores: {} });
  t7_renderTabela02Faixas();
}

async function t7_salvarTabela02Faixas() {
  const el = document.getElementById('cfg_tabela02Faixas');
  const { tipos } = t7_tabela02FaixasCache;
  const faixas = [...el.querySelectorAll('tbody tr')].map(tr => {
    const valores = {};
    tipos.forEach(t => {
      const v = tr.querySelector(`[data-tipo="${t.id}"]`).value;
      if (v !== '') valores[t.id] = parseNumBR(v);
    });
    return {
      area_de: parseNumBR(tr.querySelector('[data-campo="area_de"]').value),
      area_ate: parseNumBR(tr.querySelector('[data-campo="area_ate"]').value),
      valores,
    };
  });
  await api.put('/api/catalogos/tabela02-faixas', { faixas });
  alert('Tabela 02 (faixas de área) salva.');
  t7_carregarTabela02Faixas();
}

// ---------- Painéis Isolantes — Parede/Teto (tabela cruzada Espessura × PIR/EPS) ----------

async function t7_carregarIsolamentoParedeTeto() {
  const itens = await api.get('/api/catalogos/isolamento-parede-teto');
  const espessuras = [...new Set(itens.map(i => i.espessura_mm))].sort((a, b) => a - b);
  const porEspessura = {};
  espessuras.forEach(e => { porEspessura[e] = { pir: null, eps: null }; });
  itens.forEach(i => {
    const alvo = i.material.toUpperCase().startsWith('EPS') ? 'eps' : 'pir';
    porEspessura[i.espessura_mm][alvo] = i;
  });

  const el = document.getElementById('cfg_isolamentoParedeTeto');
  el.innerHTML = `<table class="list mf-table">
    <thead><tr><th>Espessura (mm)</th><th>PIR — U (kcal/h·m²·°C)</th><th>EPS — U (kcal/h·m²·°C)</th>
      <th>PIR — Vão máx. apoios (mm)</th><th>EPS — Vão máx. apoios (mm)</th><th></th></tr></thead>
    <tbody>${espessuras.map(e => `
      <tr data-espessura="${e}">
        <td style="font-weight:bold;">${e}</td>
        <td><input type="number" step="any" data-mat="pir" data-campo="u_valor" data-esp="${e}" data-id="${porEspessura[e].pir ? porEspessura[e].pir.id : ''}"
              value="${porEspessura[e].pir ? porEspessura[e].pir.u_valor : ''}" placeholder="—" style="width:80px;"></td>
        <td><input type="number" step="any" data-mat="eps" data-campo="u_valor" data-esp="${e}" data-id="${porEspessura[e].eps ? porEspessura[e].eps.id : ''}"
              value="${porEspessura[e].eps ? porEspessura[e].eps.u_valor : ''}" placeholder="—" style="width:80px;"></td>
        <td><input type="number" step="any" data-mat="pir" data-campo="vao_maximo_apoios_mm" data-esp="${e}" data-id="${porEspessura[e].pir ? porEspessura[e].pir.id : ''}"
              value="${porEspessura[e].pir && porEspessura[e].pir.vao_maximo_apoios_mm != null ? porEspessura[e].pir.vao_maximo_apoios_mm : ''}" placeholder="—" style="width:100px;"></td>
        <td><input type="number" step="any" data-mat="eps" data-campo="vao_maximo_apoios_mm" data-esp="${e}" data-id="${porEspessura[e].eps ? porEspessura[e].eps.id : ''}"
              value="${porEspessura[e].eps && porEspessura[e].eps.vao_maximo_apoios_mm != null ? porEspessura[e].eps.vao_maximo_apoios_mm : ''}" placeholder="—" style="width:100px;"></td>
        <td style="text-align:right;"><span class="btn-text danger" data-excluir-espessura="${e}">Excluir</span></td>
      </tr>`).join('')}</tbody>
  </table>`;

  el.querySelectorAll('input[data-mat]').forEach(inp => inp.addEventListener('change', () => t7_salvarCelulaParedeTeto(inp)));
  el.querySelectorAll('[data-excluir-espessura]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm(`Excluir a espessura ${b.dataset.excluirEspessura}mm (PIR e EPS)?`)) return;
    const e = Number(b.dataset.excluirEspessura);
    if (porEspessura[e].pir) await api.del(`/api/catalogos/isolamento-parede-teto/${porEspessura[e].pir.id}`);
    if (porEspessura[e].eps) await api.del(`/api/catalogos/isolamento-parede-teto/${porEspessura[e].eps.id}`);
    t7_carregarIsolamentoParedeTeto();
  }));
}

async function t7_salvarCelulaParedeTeto(inp) {
  const mat = inp.dataset.mat, esp = Number(inp.dataset.esp), id = inp.dataset.id;
  const campo = inp.dataset.campo || 'u_valor', valor = inp.value.trim();
  const materialLabel = `${mat.toUpperCase()} ${esp}mm`;
  if (campo === 'u_valor') {
    // U é a coluna que define a existência do registro (NOT NULL): esvaziar apaga a linha.
    if (id && valor === '') {
      await api.del(`/api/catalogos/isolamento-parede-teto/${id}`);
    } else if (id && valor !== '') {
      await api.put(`/api/catalogos/isolamento-parede-teto/${id}`, { u_valor: parseNumBR(valor) });
    } else if (!id && valor !== '') {
      await api.post('/api/catalogos/isolamento-parede-teto', { material: materialLabel, espessura_mm: esp, u_valor: parseNumBR(valor) });
    }
  } else {
    // Vão máx. só edita um registro existente (não cria linha — U é obrigatório para criar).
    if (!id) {
      if (valor !== '') alert('Preencha primeiro o U desta célula (PIR/EPS) para depois informar o Vão máx.');
      t7_carregarIsolamentoParedeTeto();
      return;
    }
    await api.put(`/api/catalogos/isolamento-parede-teto/${id}`, { vao_maximo_apoios_mm: valor === '' ? null : Number(valor) });
  }
  t7_carregarIsolamentoParedeTeto();
}

function t7_addEspessura() {
  const valor = prompt('Nova espessura (mm):');
  const esp = Number(valor);
  if (!esp) return;
  const el = document.getElementById('cfg_isolamentoParedeTeto');
  if (el.querySelector(`tr[data-espessura="${esp}"]`)) { alert('Essa espessura já existe.'); return; }
  const tbody = el.querySelector('tbody');
  tbody.insertAdjacentHTML('beforeend', `
    <tr data-espessura="${esp}">
      <td style="font-weight:bold;">${esp}</td>
      <td><input type="number" step="any" data-mat="pir" data-campo="u_valor" data-esp="${esp}" data-id="" placeholder="—" style="width:80px;"></td>
      <td><input type="number" step="any" data-mat="eps" data-campo="u_valor" data-esp="${esp}" data-id="" placeholder="—" style="width:80px;"></td>
      <td><input type="number" step="any" data-mat="pir" data-campo="vao_maximo_apoios_mm" data-esp="${esp}" data-id="" placeholder="—" style="width:100px;"></td>
      <td><input type="number" step="any" data-mat="eps" data-campo="vao_maximo_apoios_mm" data-esp="${esp}" data-id="" placeholder="—" style="width:100px;"></td>
      <td style="text-align:right;"><span class="btn-text danger" data-excluir-espessura="${esp}">Excluir</span></td>
    </tr>`);
  tbody.lastElementChild.querySelectorAll('input[data-mat]').forEach(inp => inp.addEventListener('change', () => t7_salvarCelulaParedeTeto(inp)));
  tbody.lastElementChild.querySelector('[data-excluir-espessura]').addEventListener('click', async (e) => {
    e.target.closest('tr').remove();
  });
}

// ---------- Painéis Isolantes — Piso (lista simples, não é cruzada PIR/EPS) ----------

async function t7_carregarIsolamentoPiso() {
  const itens = await api.get('/api/catalogos/isolamento-piso');
  const el = document.getElementById('cfg_isolamentoPiso');
  el.innerHTML = `<table class="list">
    <thead><tr><th>Material</th><th>Espessura (mm)</th><th>U (kcal/h·m²·°C)</th><th>Só válido ≥0°C</th><th></th></tr></thead>
    <tbody>${itens.map(i => `
      <tr data-id="${i.id}">
        <td><input type="text" data-f="material" value="${i.material}" style="width:220px;"></td>
        <td><input type="number" data-f="espessura_mm" value="${i.espessura_mm != null ? i.espessura_mm : ''}" style="width:70px;"></td>
        <td><input type="number" step="any" data-f="u_valor" value="${i.u_valor}" style="width:70px;"></td>
        <td style="text-align:center;"><input type="checkbox" data-f="valido_apenas_acima_zero" ${i.valido_apenas_acima_zero ? 'checked' : ''}></td>
        <td style="text-align:right;"><span class="btn-text danger" data-excluir-piso="${i.id}">Excluir</span></td>
      </tr>`).join('')}</tbody>
  </table>`;

  el.querySelectorAll('tbody tr').forEach(tr => {
    tr.querySelectorAll('[data-f]').forEach(inp => inp.addEventListener('change', () => t7_salvarLinhaPiso(tr)));
  });
  el.querySelectorAll('[data-excluir-piso]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir esta opção de piso?')) return;
    await api.del(`/api/catalogos/isolamento-piso/${b.dataset.excluirPiso}`);
    t7_carregarIsolamentoPiso();
  }));
}

async function t7_salvarLinhaPiso(tr) {
  const id = tr.dataset.id;
  const get = (f) => tr.querySelector(`[data-f="${f}"]`);
  const payload = {
    material: get('material').value.trim(),
    espessura_mm: get('espessura_mm').value === '' ? null : Number(get('espessura_mm').value),
    u_valor: parseNumBR(get('u_valor').value),
    valido_apenas_acima_zero: get('valido_apenas_acima_zero').checked,
  };
  await api.put(`/api/catalogos/isolamento-piso/${id}`, payload);
}

async function t7_addPiso() {
  const obj = await api.post('/api/catalogos/isolamento-piso', { material: 'Novo material', u_valor: 0 });
  t7_carregarIsolamentoPiso();
}

// ---------- Polinomios de Compressor (visualizacao, importados via script) ----------

async function t7_carregarPolinomios() {
  const selFab = document.getElementById('cfg_poli_fabricante');
  const selLinha = document.getElementById('cfg_poli_linha');
  const selGas = document.getElementById('cfg_poli_gas');
  const selModelo = document.getElementById('cfg_poli_modelo');

  const fabricantes = await api.get('/api/polinomios/fabricantes');
  if (!fabricantes.length) {
    document.getElementById('cfg_poli_tabela').innerHTML = '<p class="small">Nenhum polinômio importado ainda.</p>';
    return;
  }
  populateSelect(selFab, fabricantes.map(f => ({ v: f, l: f })), 'v', 'l');
  if (!selFab.value) selFab.value = fabricantes[0];

  async function recarregarLinhas() {
    const linhas = await api.get(`/api/polinomios/linhas?fabricante=${encodeURIComponent(selFab.value)}`);
    populateSelect(selLinha, linhas.map(l => ({ v: l, l })), 'v', 'l');
    await recarregarGases();
  }
  async function recarregarGases() {
    const gases = await api.get(`/api/polinomios/gases?fabricante=${encodeURIComponent(selFab.value)}&linha=${encodeURIComponent(selLinha.value)}`);
    populateSelect(selGas, gases.map(g => ({ v: g, l: g })), 'v', 'l');
    await recarregarModelos();
  }
  async function recarregarModelos() {
    const modelos = await api.get(`/api/polinomios/modelos?fabricante=${encodeURIComponent(selFab.value)}&linha=${encodeURIComponent(selLinha.value)}&gas=${encodeURIComponent(selGas.value)}`);
    selModelo.innerHTML = '<option value="">— todos —</option>' + modelos.map(m => `<option>${m}</option>`).join('');
    await renderTabela();
  }
  async function renderTabela() {
    const itens = await api.get(`/api/polinomios/lista`);
    const filtrados = itens.filter(i => i.fabricante === selFab.value && i.linha === selLinha.value
      && i.gas === selGas.value && (!selModelo.value || i.modelo === selModelo.value));
    const el = document.getElementById('cfg_poli_tabela');
    if (!filtrados.length) {
      el.innerHTML = '<p class="small">Nenhum registro para esse filtro.</p>';
      return;
    }
    el.innerHTML = `<div style="overflow:auto;width:100%;max-height:420px;border:1px solid var(--line);"><table class="list" style="white-space:nowrap;">
      <thead><tr><th>Modelo</th><th>Tensão</th><th>Grandeza</th><th>Unidade</th>
        <th>c1</th><th>c2</th><th>c3</th><th>c4</th><th>c5</th><th>c6</th><th>c7</th><th>c8</th><th>c9</th><th>c10</th>
        <th>Te válido</th><th>Tc válido</th></tr></thead>
      <tbody>${filtrados.map(i => `<tr>
        <td>${i.modelo}</td><td>${i.tensao}</td><td>${i.grandeza}</td><td>${i.unidade}</td>
        <td>${fmtCoef(i.c1)}</td><td>${fmtCoef(i.c2)}</td><td>${fmtCoef(i.c3)}</td><td>${fmtCoef(i.c4)}</td>
        <td>${fmtCoef(i.c5)}</td><td>${fmtCoef(i.c6)}</td><td>${fmtCoef(i.c7)}</td><td>${fmtCoef(i.c8)}</td>
        <td>${fmtCoef(i.c9)}</td><td>${fmtCoef(i.c10)}</td>
        <td>${i.te_min ?? '—'} a ${i.te_max ?? '—'}</td><td>${i.tc_min ?? '—'} a ${i.tc_max ?? '—'}</td>
      </tr>`).join('')}</tbody></table></div>`;
  }
  function fmtCoef(v) { return v == null ? '—' : Number(v).toPrecision(6); }

  selFab.onchange = recarregarLinhas;
  selLinha.onchange = recarregarGases;
  selGas.onchange = recarregarModelos;
  selModelo.onchange = renderTabela;

  await recarregarLinhas();
}

async function t7_carregar() {
  await t7_carregarCentroCusto();
  await t7_carregarIsolamentoParedeTeto();
  await t7_carregarIsolamentoPiso();
  await t7_tabelaGenerica.insolacao.carregar();
  await t7_tabelaGenerica.ambientesLuminotecnico.carregar();
  await t7_tabelaGenerica.lampadas.carregar();
  await t7_tabelaGenerica.tabela02.carregar();
  await t7_carregarTabela02Faixas();
  await t7_tabelaGenerica.equipamentos.carregar();
  await t7_tabelaGenerica.produtos.carregar();
  await t7_tabelaGenerica.paineisPortasLookup.carregar();
  await t7_arvoreIdsComerciais.carregar();
  await t7_carregarPolinomios();
  await t7_tabelaGenerica.classificacaoSistema.carregar();
  await t7_tabelaGenerica.lubrificanteCompressor.carregar();
  await t7_tabelaGenerica.dadosFisicosBitzer.carregar();
  await t7_tabelaGenerica.tabelaDisjuntorTermomagnetico.carregar();
  await t7_tabelaGenerica.tabelaDisjuntorDdr.carregar();
  await t7_tabelaGenerica.tabelaValvulaExpansao.carregar();
  await t7_tabelaGenerica.tabelaControladorValvula.carregar();
  await t7_tabelaGenerica.tabelaCompatibilidadeValvula.carregar();
  await t7_tabelaGenerica.estadosBrasileiros.carregar();
  await t7_tabelaGenerica.dadosClimatologicosInmet.carregar();
  const itens = await api.get('/api/catalogos/configuracao-global');
  const el = document.getElementById('cfg_lista');
  el.innerHTML = '<table class="list"><tbody>' + itens.map(c => `
    <tr><td style="width:30%;font-weight:bold;">${c.chave}</td>
      <td style="width:15%;"><input type="text" value="${c.valor}" data-cfg-valor="${c.id}" style="max-width:120px;"></td>
      <td style="color:#6b7280;font-size:11.5px;">${c.descricao || ''}</td>
      <td style="text-align:right;width:90px;"><span class="btn-text" data-cfg-salvar="${c.id}">Salvar</span></td></tr>`).join('') + '</tbody></table>';
  el.querySelectorAll('[data-cfg-salvar]').forEach(b => b.addEventListener('click', async () => {
    const id = b.dataset.cfgSalvar;
    const valor = parseNumBR(document.querySelector(`[data-cfg-valor="${id}"]`).value);
    await api.put(`/api/catalogos/configuracao-global/${id}`, { valor });
    alert('Configuração salva.');
  }));
}

window.initTela7 = initTela7;
document.addEventListener('DOMContentLoaded', initTela7);
