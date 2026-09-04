/* Componente reaproveitado pelas Telas 2 e 3 — Seção 8 Forçadores e 8.1 Válvulas
   (mesmo padrão de add-row + lista agrupada por fabricante + Excluir). */

async function carregarFabricantes() {
  return api.get('/api/catalogos/fabricantes');
}

async function carregarLinhasDoFabricante(fabricanteId) {
  if (!fabricanteId) return [];
  // apenas_ativos: catálogos marcados Obsoleto somem daqui (seleção de NOVO forçador), mas
  // continuam funcionando normalmente pra câmaras que já os usam (linha_id já fixado na seleção).
  return api.get(`/api/forcadores/linhas?fabricante_id=${fabricanteId}&apenas_ativos=1`);
}

function wireFabricanteLinhaSelects(selectFab, selectLinha, fabricantes) {
  populateSelect(selectFab, fabricantes, 'id', 'nome', '—');
  const atualizarLinhas = async () => {
    const linhas = await carregarLinhasDoFabricante(selectFab.value);
    populateSelect(selectLinha, linhas, 'id', 'nome', '—');
  };
  selectFab.addEventListener('change', atualizarLinhas);
  atualizarLinhas();
}

// Nomenclatura do código de compra do forçador — mesmo princípio da Unidade Condensadora:
// o dicionário (campo -> opções) vem do catálogo (cadastrado em Configurações da linha), a
// escolha de qual opção se aplica é feita aqui, no forçador considerado de cada câmara.
let _nomenclaturaLinhaCache = {};
// Chamado pelas telas de catálogo (Tela A/B) depois de salvar — sem isso, o painel de código de
// compra nas Telas 2/3 continuava mostrando a Nomenclatura antiga até um F5 (item 4).
function nomenc_invalidarCache() { _nomenclaturaLinhaCache = {}; }

function _parseOpcoes(texto) {
  if (!texto) return [];
  return texto.split('\n').map(l => l.trim()).filter(Boolean).map(l => {
    const [codigo, ...resto] = l.split('=');
    return { codigo: codigo.trim(), rotulo: (resto.join('=').trim() || codigo.trim()) };
  });
}

// Extrai (volts, fases) de qualquer formato de tensão (mesma normalização de campo_catalogo.py:
// _normalizar_tensao) — "220V/1F/60Hz" do projeto vs "220V-1F 50-60Hz" digitado no catálogo nunca
// bateriam por igualdade de string exata.
function _normalizarTensao(texto) {
  if (!texto) return null;
  const mv = texto.match(/(\d+)\s*V/i);
  const mf = texto.match(/(\d+)\s*F/i);
  if (!mv || !mf) return null;
  return `${mv[1]}V${mf[1]}F`;
}

// Alguns campos de nomenclatura (ex.: "Produto" em FLA/FLE) na verdade codificam o Tipo de Degelo
// — dado que já existe na linha (Seção 8, escolhido pelo usuário). Nesse caso não faz sentido
// perguntar de novo: detecta pelo texto da opção e deriva automaticamente.
const _DEGELO_PALAVRAS = { 'Natural': ['degelo a ar', 'degelo natural'], 'Elétrico': ['degelo elétrico', 'degelo eletrico'], 'Gás quente': ['gás quente', 'gas quente'] };

// Campo Tipo_Degelo do catálogo (modelo.tipo_degelo) é texto composto e descritivo do fabricante
// (ex.: "Ar forçado ou Elétrico" — significa que o modelo aceita os DOIS tipos), não um valor único
// pra comparar por igualdade exata. "Ar forçado" é como o mercado chama o degelo Natural.
// "a ar" cobre variações mais curtas do mesmo termo, ex.: opção de nomenclatura cadastrada só como
// "A ar" (em vez de "Ar forçado") — bug real: MI_GS2/MIPAL usa exatamente essa forma curta.
const _DEGELO_PALAVRAS_CATALOGO = { 'Natural': ['ar forçado', 'ar forcado', 'a ar', 'natural'],
                                     'Elétrico': ['elétrico', 'eletrico'], 'Gás quente': ['gás quente', 'gas quente'] };
function _catalogoSuportaDegelo(tipoDegeloCatalogo, tipoSelecionado) {
  const palavras = _DEGELO_PALAVRAS_CATALOGO[tipoSelecionado];
  if (!tipoDegeloCatalogo || !palavras) return true; // sem dado suficiente pra afirmar incompatibilidade
  const low = tipoDegeloCatalogo.toLowerCase();
  return palavras.some(p => low.includes(p));
}
function _tipoDegeloDaOpcao(rotulo) {
  const low = rotulo.toLowerCase();
  for (const [tipo, palavras] of Object.entries(_DEGELO_PALAVRAS)) {
    if (palavras.some(p => low.includes(p))) return tipo;
  }
  return null;
}

// Acha a opção de nomenclatura correspondente a um valor de contexto. Pra Tipo de Degelo, o valor
// cadastrado na opção costuma ser um texto descritivo do fabricante (ex.: "Ar forçado ou Elétrico"),
// não bate por igualdade exata com o tipo selecionado ("Elétrico") — mesmo problema já corrigido em
// _catalogoSuportaDegelo, usa a mesma lista de palavras-chave por "contém".
function _opcaoAutomatica(opcoes, valorCtx, campoBuscaSistema) {
  if (!valorCtx) return null;
  if (campoBuscaSistema === 'tipo_degelo') {
    const palavras = _DEGELO_PALAVRAS_CATALOGO[valorCtx];
    if (palavras) return (opcoes || []).find(o => o.valor && palavras.some(p => o.valor.toLowerCase().includes(p)));
  }
  return (opcoes || []).find(o => o.valor === valorCtx);
}

// Ponto único de resolução do campo Automático — usado tanto pra montar o código comercial quanto
// pra exibir o valor no card. Tinha essa lógica duplicada em 2 lugares e só uma cópia foi corrigida
// (bug real: campo de Tensão continuava "defina o dado de origem" mesmo com o valor certo no
// contexto, porque a exibição nunca ganhou a normalização de tensão que a montagem já tinha).
// "tensao" é chave legada (catálogos de antes do desdobro Comando/Equipamentos) — trata como
// Comando, com fallback pra Equipamentos, pra não quebrar código já cadastrado.
function _valorContextoAutomatico(contexto, c) {
  return c.campo_busca_sistema === 'tensao'
    ? (contexto.tensao_comando ?? contexto.tensao_equipamentos)
    : contexto[c.campo_busca_sistema];
}

function _resolverOpcaoAutomatica(contexto, c) {
  const valorCtx = _valorContextoAutomatico(contexto, c);
  if (c.campo_busca_sistema === 'tensao_comando' || c.campo_busca_sistema === 'tensao_equipamentos' || c.campo_busca_sistema === 'tensao') {
    const alvo = _normalizarTensao(valorCtx);
    return alvo ? (c.opcoes || []).find(o => _normalizarTensao(o.valor) === alvo) : null;
  }
  return _opcaoAutomatica(c.opcoes, valorCtx, c.campo_busca_sistema);
}

async function _carregarPainelNomenclaturaForcador(container, forcadores, onNomenclaturaChange) {
  const considerado = (forcadores || []).find(f => f.considerado && f.modelo_resultante);
  const wrap = container.querySelector('[data-nomenc-wrap]');
  if (!wrap) return;
  if (!considerado) { wrap.innerHTML = ''; return; }

  if (!_nomenclaturaLinhaCache[considerado.linha_id]) {
    _nomenclaturaLinhaCache[considerado.linha_id] = await api.get(`/api/forcadores/linhas/${considerado.linha_id}/campos`);
  }
  const campos = _nomenclaturaLinhaCache[considerado.linha_id];
  if (!campos.length) {
    wrap.innerHTML = `<div class="small" style="color:#9ca3af;">Código de compra ainda não disponível — cadastre os Campos do código comercial desta linha em Configurações → Forçadores (extraídos do catálogo do fabricante).</div>`;
    return;
  }
  const selecionado = considerado.nomenclatura_selecionada || {};
  // Contexto pros campos Automáticos (mesma ideia da UC): valores já conhecidos da linha/forçador —
  // seleção do sistema/projeto (tipo_degelo, tensões, gás) + dado do próprio catálogo do modelo
  // escolhido (num_ventiladores, diametro_ventilador_mm), só disponível depois de um modelo resolvido.
  const contexto = {
    tipo_degelo: considerado.tipo_degelo_selecionado,
    tensao_comando: considerado.tensao_comando,
    tensao_equipamentos: considerado.tensao_equipamentos,
    gas: considerado.gas,
    num_ventiladores: considerado.num_ventiladores != null ? String(considerado.num_ventiladores) : null,
    diametro_ventilador_mm: considerado.diametro_ventilador_mm != null ? String(considerado.diametro_ventilador_mm) : null,
  };
  // Monta o código — PADRÃO ÚNICO do sistema (mesmo algoritmo de campo_catalogo.py montar_codigo):
  // o modelo técnico não é mais prefixo fixo hardcoded, é só mais um card (modo="modelo_pesquisa")
  // na MESMA sequência ordenada dos demais, na posição em que o usuário arrastou. Campo Automático
  // puxa do contexto; Fixo usa o código fixo; Manual usa a escolha do usuário; Ignorar nunca entra.
  // Campo marcado "substitui coringa" é guardado à parte e só aplicado depois de montar a sequência
  // inteira, encaixando no '*' onde quer que ele tenha caído (ou como prefixo, se não houver '*').
  const campoManuais = campos.filter(c => c.modo === 'manual');
  const partes = [];
  let coringaCod = null;
  campos.forEach(c => {
    let cod = '';
    if (c.modo === 'modelo_pesquisa') cod = considerado.modelo_resultante || '';
    else if (c.modo === 'fixo') cod = c.codigo_fixo || '';
    else if (c.modo === 'ignorar') cod = '';
    else if (c.modo === 'automatico') {
      const opc = _resolverOpcaoAutomatica(contexto, c);
      cod = opc ? opc.codigo : '';
    } else {
      const v = selecionado[c.nome_campo];
      const opc = v ? (c.opcoes || []).find(o => o.valor === v) : null;
      // Manual sem seleção ainda: "*" no lugar (não pula o campo em silêncio) — sinaliza
      // visualmente no código que falta escolher essa peça.
      cod = opc ? opc.codigo : '*';
    }
    if (!cod) return;
    if (c.substitui_coringa_modelo) coringaCod = cod;
    else partes.push(cod);
  });
  let codigoComercial = partes.join('');
  if (coringaCod !== null) {
    if (/[*x]/.test(codigoComercial)) codigoComercial = codigoComercial.replace(/[*x]/, coringaCod);
    else codigoComercial = coringaCod + codigoComercial;
  }
  // Largura fixa e espaçamento consistente entre campos (sem sobreposição) — cada campo é uma
  // "célula" de mesma largura, com o rótulo em cima e o valor/seleção embaixo, gap real entre elas.
  wrap.innerHTML = `<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start;padding:4px 0;">
      ${campos.map(c => {
        const campoDiv = (conteudo) => `<div style="width:150px;flex:0 0 150px;">
          <label class="lbl" style="display:block;white-space:normal;word-wrap:break-word;text-align:center;" title="${c.nome_campo ?? ''}">${c.nome_campo ?? ''}</label>
          ${conteudo}
        </div>`;
        if (c.modo === 'ignorar') {
          return campoDiv(`<div class="small" style="padding:6px 0;color:#9ca3af;text-align:center;">— (ignorado)</div>`);
        }
        if (c.modo === 'modelo_pesquisa') {
          // Não editável — valor é o próprio modelo técnico selecionado. Só a posição na
          // nomenclatura é livre (arrasta como qualquer card, no editor de Campos).
          return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;text-align:center;" title="Modelo técnico do catálogo — não editável aqui">${considerado.modelo_resultante || '—'}</div>`);
        }
        if (c.modo === 'automatico') {
          const opc = _resolverOpcaoAutomatica(contexto, c);
          const valorOrigem = _valorContextoAutomatico(contexto, c);
          // Distingue "ainda não tem dado de origem" (define lá em cima) de "tem o dado, mas o
          // catálogo não tem opção pra esse valor" (equipamento incompatível de verdade — precisa
          // de sinalização clara, não a mesma mensagem genérica dos dois casos).
          let conteudo;
          if (opc) conteudo = `${opc.valor} (auto)`;
          else if (valorOrigem) conteudo = `<span style="color:#b91c1c;font-weight:bold;">⚠ Sem opção p/ "${valorOrigem}"</span>`;
          else conteudo = '— defina o dado de origem acima';
          return campoDiv(`<div class="small" style="padding:6px 0;${opc ? 'color:#374151;' : (valorOrigem ? 'background:#fef2f2;' : 'color:#374151;')}white-space:normal;word-wrap:break-word;text-align:center;"
              title="${opc ? 'Automático, conforme dado já definido na linha' : (valorOrigem ? 'O catálogo não tem opção de código cadastrada pra esse valor — equipamento incompatível com o dado do projeto/sistema.' : 'Automático, conforme dado já definido na linha')}">
              ${conteudo}
            </div>`);
        }
        if (c.modo === 'fixo') {
          return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;">${c.codigo_fixo || '—'} (fixo)</div>`);
        }
        return campoDiv(`<select data-nomenc-campo="${c.nome_campo}" style="width:100%;">
            <option value="">—</option>
            ${(c.opcoes || []).map(o => `<option value="${o.valor}" title="${o.valor}" ${selecionado[c.nome_campo] === o.valor ? 'selected' : ''}>${o.valor}</option>`).join('')}
          </select>`);
      }).join('')}
    </div>
    <div class="small" style="color:#111827;margin-top:8px;">Código comercial (compra): <code style="font-weight:bold;">${codigoComercial}</code></div>
    ${considerado.observacao_valv_reg_pressao ? `<div class="small" style="color:#1d4ed8;margin-top:4px;">${considerado.observacao_valv_reg_pressao}</div>` : ''}`;
  wrap.querySelectorAll('[data-nomenc-campo]').forEach(sel => sel.addEventListener('change', () => {
    const nova = { ...selecionado, [sel.dataset.nomencCampo]: sel.value || undefined };
    Object.keys(nova).forEach(k => { if (!nova[k]) delete nova[k]; });
    onNomenclaturaChange(considerado.id, nova);
  }));
}

// Mesmo painel de nomenclatura do Forçador (_carregarPainelNomenclaturaForcador), adaptado pro
// Condensador Remoto do Rack Paralelo (Tela 6) — só os Campos em modo Manual são editáveis aqui;
// o código comercial exibido já vem composto do backend (montar_codigo, com a seleção manual salva).
async function _carregarPainelNomenclaturaCondensador(container, dados, onNomenclaturaChange) {
  const wrap = container.querySelector('[data-nomenc-cond-wrap]');
  if (!wrap) return;
  const escolhido = dados && dados.selecao && dados.selecao.escolhido;
  if (!dados || !dados.linha_id || !escolhido) { wrap.innerHTML = ''; return; }

  const chaveCache = `cond_${dados.linha_id}`;
  if (!_nomenclaturaLinhaCache[chaveCache]) {
    _nomenclaturaLinhaCache[chaveCache] = await api.get(`/api/condensadores/linhas/${dados.linha_id}/campos`);
  }
  const campos = _nomenclaturaLinhaCache[chaveCache];
  if (!campos.length) { wrap.innerHTML = ''; return; }
  const selecionado = dados.nomenclatura_selecionada || {};

  wrap.innerHTML = `<div style="display:flex;gap:6px;flex-wrap:nowrap;align-items:flex-start;padding:4px 0;width:100%;">
      ${campos.map(c => {
        const campoDiv = (conteudo) => `<div style="flex:1 1 0;min-width:0;text-align:center;">
          <label class="lbl" style="display:block;font-size:10px;white-space:normal;word-wrap:break-word;text-align:center;" title="${c.nome_campo ?? ''}">${c.nome_campo ?? ''}</label>
          ${conteudo}
        </div>`;
        if (c.modo === 'ignorar') {
          return campoDiv(`<div class="small" style="padding:6px 0;color:#9ca3af;text-align:center;">— (ignorado)</div>`);
        }
        if (c.modo === 'modelo_pesquisa') {
          // Não editável — valor é o próprio modelo técnico escolhido pelo cálculo de seleção.
          return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;text-align:center;" title="Modelo técnico do catálogo — não editável aqui">${escolhido.modelo || '—'}</div>`);
        }
        if (c.modo === 'automatico') {
          return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;text-align:center;">(automático)</div>`);
        }
        if (c.modo === 'fixo') {
          return campoDiv(`<div class="small" style="padding:6px 0;color:#374151;text-align:center;">${c.codigo_fixo || '—'} (fixo)</div>`);
        }
        return campoDiv(`<select data-nomenc-cond-campo="${c.nome_campo}" style="width:100%;text-align:center;text-align-last:center;">
            <option value="">—</option>
            ${(c.opcoes || []).map(o => `<option value="${o.valor}" title="${o.valor}" ${selecionado[c.nome_campo] === o.valor ? 'selected' : ''}>${o.valor}</option>`).join('')}
          </select>`);
      }).join('')}
    </div>
    <div class="small" style="color:#111827;margin-top:8px;">Código comercial (compra): <code style="font-weight:bold;">${escolhido.codigo_comercial || escolhido.modelo}</code></div>`;
  wrap.querySelectorAll('[data-nomenc-cond-campo]').forEach(sel => sel.addEventListener('change', () => {
    const nova = { ...selecionado, [sel.dataset.nomencCondCampo]: sel.value || undefined };
    Object.keys(nova).forEach(k => { if (!nova[k]) delete nova[k]; });
    onNomenclaturaChange(nova);
  }));
}

// Editor completo da estrutura de Nomenclatura (rótulo/opções/ordem/Modo) de UM catálogo —
// compartilhado entre Tela A (Forçador) e Tela B (UC), embutido dentro do próprio catálogo/linha já
// aberto (não mais em Configurações — cada catálogo edita sua própria estrutura, no lugar onde já
// está cadastrando o resto do catálogo). camposApiPath é resolvido pelo chamador (já sabe o id).
function nomenc_criarEditorCampos(containerId, buscaOpcoes) {
  let camposApiPath = null;
  let arrastando = null;

  async function carregar(url) {
    camposApiPath = url;
    const campos = await api.get(camposApiPath);
    document.getElementById(containerId).dataset.campos = JSON.stringify(campos);
    redesenhar();
  }
  function estado() { return JSON.parse(document.getElementById(containerId).dataset.campos || '[]'); }
  function salvarEstadoLocal(c) { document.getElementById(containerId).dataset.campos = JSON.stringify(c); }

  function redesenhar() {
    const el = document.getElementById(containerId);
    if (!el) return;
    const scrollAnterior = el.querySelector(':scope > div')?.scrollLeft || 0;
    const campos = estado();
    el.innerHTML = `<div style="display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;">
      <div style="min-width:90px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <span class="btn-text" data-add-campo>+ Coluna</span>
      </div>
      ${campos.map((c, i) => nomenc_htmlCard(c, i, buscaOpcoes)).join('')}
    </div>`;
    const carrossel = el.querySelector(':scope > div');
    if (carrossel) carrossel.scrollLeft = scrollAnterior;

    el.querySelectorAll('[data-remover-campo]').forEach(b => b.addEventListener('click', () => {
      const c2 = estado();
      c2.splice(Number(b.dataset.removerCampo), 1);
      salvarEstadoLocal(c2);
      redesenhar();
    }));
    el.querySelectorAll('[data-add-opcao]').forEach(b => b.addEventListener('click', () => {
      const c2 = estado();
      c2[Number(b.dataset.addOpcao)].opcoes.push({ valor: '', codigo: '' });
      salvarEstadoLocal(c2);
      redesenhar();
    }));
    el.querySelectorAll('[data-remover-opcao]').forEach(b => b.addEventListener('click', () => {
      const [ci, oi] = b.dataset.removerOpcao.split(':').map(Number);
      const c2 = estado();
      c2[ci].opcoes.splice(oi, 1);
      salvarEstadoLocal(c2);
      redesenhar();
    }));
    const addBtn = el.querySelector('[data-add-campo]');
    if (addBtn) addBtn.addEventListener('click', () => {
      const c2 = estado();
      c2.unshift({ nome_campo: 'Nova Coluna', modo: 'manual', campo_busca_sistema: null,
                codigo_fixo: null, substitui_coringa_modelo: false, opcoes: [] });
      salvarEstadoLocal(c2);
      redesenhar();
    });
    el.querySelectorAll('[data-campo-prop]').forEach(inp => inp.addEventListener((inp.type === 'checkbox' || inp.tagName === 'SELECT') ? 'change' : 'input', () => {
      const c2 = estado();
      const [ci, prop] = inp.dataset.campoProp.split(':');
      c2[Number(ci)][prop] = inp.type === 'checkbox' ? inp.checked : (inp.value || null);
      salvarEstadoLocal(c2);
      if (prop === 'modo') redesenhar();
    }));
    el.querySelectorAll('[data-opcao-prop]').forEach(inp => inp.addEventListener('input', () => {
      const [ci, oi, prop] = inp.dataset.opcaoProp.split(':');
      const c2 = estado();
      c2[Number(ci)].opcoes[Number(oi)][prop] = inp.value;
      salvarEstadoLocal(c2);
    }));
    // Arrastar o card com o mouse pra reordenar (substitui as setas ←/→) — a ordem final só é
    // persistida no banco quando o botão Salvar da tela (fora deste componente) é clicado.
    el.querySelectorAll('[data-campo-card]').forEach(card => {
      card.addEventListener('dragstart', (ev) => {
        arrastando = Number(card.dataset.campoCard);
        ev.dataTransfer.effectAllowed = 'move';
        card.style.opacity = '0.4';
      });
      card.addEventListener('dragend', () => { card.style.opacity = ''; arrastando = null; });
      card.addEventListener('dragover', (ev) => { ev.preventDefault(); ev.dataTransfer.dropEffect = 'move'; });
      card.addEventListener('drop', (ev) => {
        ev.preventDefault();
        const alvo = Number(card.dataset.campoCard);
        if (arrastando === null || arrastando === alvo) return;
        const c2 = estado();
        const [mov] = c2.splice(arrastando, 1);
        c2.splice(alvo, 0, mov);
        salvarEstadoLocal(c2);
        redesenhar();
      });
    });
  }

  // Salva a Nomenclatura junto com o resto do catálogo — chamado pelo botão Salvar da tela que
  // hospeda este editor (Tela A/B), não tem mais botão próprio (item 3: uma única ação de salvar).
  async function salvar() {
    await api.put(camposApiPath, { campos: estado() });
  }

  return { carregar, salvar };
}

function nomenc_htmlCard(c, i, buscaOpcoes) {
  const nomeCurto = (c.nome_campo ?? '').length > 22;
  return `<div data-campo-card="${i}" draggable="true" title="Arraste pra reordenar"
      style="width:190px;flex:0 0 190px;border:1px solid var(--line);border-radius:6px;padding:8px;cursor:grab;background:var(--bg,#fff);">
    <input type="text" data-campo-prop="${i}:nome_campo" value="${c.nome_campo ?? ''}" title="${nomeCurto ? c.nome_campo : ''}"
      style="width:100%;font-weight:bold;margin-bottom:6px;text-overflow:ellipsis;">
    <label class="lbl">Modo</label>
    <select data-campo-prop="${i}:modo" style="width:100%;margin-bottom:6px;">
      <option value="automatico" ${c.modo === 'automatico' ? 'selected' : ''}>Automático</option>
      <option value="fixo" ${c.modo === 'fixo' ? 'selected' : ''}>Fixo</option>
      <option value="manual" ${c.modo === 'manual' ? 'selected' : ''}>Manual</option>
      <option value="ignorar" ${c.modo === 'ignorar' ? 'selected' : ''}>Ignorar campo</option>
      <option value="modelo_pesquisa" ${c.modo === 'modelo_pesquisa' ? 'selected' : ''}>Modelo Pesquisa</option>
    </select>
    ${c.modo === 'automatico' ? `
      <label class="lbl">Fonte Automática</label>
      <select data-campo-prop="${i}:campo_busca_sistema" style="width:100%;margin-bottom:6px;">
        <option value="">—</option>
        ${buscaOpcoes.map(([v, l]) => `<option value="${v}" ${c.campo_busca_sistema === v ? 'selected' : ''}>${l}</option>`).join('')}
      </select>` : ''}
    ${c.modo === 'fixo' ? `
      <label class="lbl">Código Fixo</label>
      <input type="text" data-campo-prop="${i}:codigo_fixo" value="${c.codigo_fixo ?? ''}" style="width:100%;margin-bottom:6px;">
      <label style="display:block;font-size:11px;color:#6b7280;margin-bottom:6px;">
        <input type="checkbox" data-campo-prop="${i}:substitui_coringa_modelo" ${c.substitui_coringa_modelo ? 'checked' : ''}>
        substitui o '*' do modelo (sem '*', vira prefixo no início)</label>` : ''}
    ${c.modo === 'ignorar' ? `
      <div class="small" style="color:#9ca3af;margin-bottom:6px;">Aparece na seleção, não editável, não entra no código.</div>` : ''}
    ${c.modo === 'modelo_pesquisa' ? `
      <div class="small" style="color:#9ca3af;margin-bottom:6px;">Valor = o próprio modelo do catálogo técnico (ex.: "0062", "FL*017") — não editável aqui. Só a posição na nomenclatura é livre (arraste este card). Se o modelo tiver '*', marque "substitui o coringa" em QUALQUER outro card pra ele entrar nessa posição.</div>` : ''}
    ${c.modo !== 'fixo' && c.modo !== 'ignorar' && c.modo !== 'modelo_pesquisa' ? `
      <label style="display:block;font-size:11px;color:#6b7280;margin-bottom:6px;">
        <input type="checkbox" data-campo-prop="${i}:substitui_coringa_modelo" ${c.substitui_coringa_modelo ? 'checked' : ''}>
        substitui o '*' do modelo</label>
      <div style="font-size:11px;color:#6b7280;margin-bottom:2px;">Valor → Código</div>
      <div style="max-height:160px;overflow-y:auto;">
        ${c.opcoes.map((o, oi) => `<div style="display:flex;gap:4px;margin-bottom:3px;">
          <input type="text" placeholder="valor" data-opcao-prop="${i}:${oi}:valor" value="${o.valor ?? ''}"
            title="${(o.valor ?? '').length > 10 ? o.valor : ''}" style="width:60%;text-overflow:ellipsis;">
          <input type="text" placeholder="código" data-opcao-prop="${i}:${oi}:codigo" value="${o.codigo ?? ''}" style="width:30%;">
          <span class="btn-text danger" data-remover-opcao="${i}:${oi}" style="font-size:11px;">x</span>
        </div>`).join('')}
      </div>
      <span class="btn-text" data-add-opcao="${i}" style="font-size:11px;">+ opção</span>` : ''}
    <div style="margin-top:6px;text-align:right;">
      <span class="btn-text danger" data-remover-campo="${i}" style="font-size:11px;">Remover Coluna</span>
    </div>
  </div>`;
}

// Fabricante e Tipo de Expansão vêm do Sistema (Tela 1 — Fornecedor Automação Linhas / Expansão)
// e são só exibidos aqui, não editáveis: a válvula já nasce provisionada junto com o forçador.
// Modelo/Controlador: caixas de seleção alimentadas pela "Tela A - Tabelas de Válvulas de Expansão"
// (Configurações), filtradas por tipo/fabricante/gás/classificação no backend
// (/api/valvulas-expansao/opcoes). Ao escolher o modelo manualmente, a mecânica (conexões/tensão/
// tipo) é preenchida do banco; Capacidade Unit. e Orifício são SEMPRE manuais/importados (catálogos
// imprecisos); Abert. Válv. = (Carga Térmica ÷ Qtd. Coletores) ÷ Capacidade Unit. (calculada no
// backend, somente leitura aqui). Os selects gravam o Id comercial do produto.
let _valvOpcoesAtual = null;   // opções do sistema da câmara aberta (setado pelas Telas 2/3)
let _valvOpcoesSistemaId = null;

async function carregarOpcoesValvulas(sistemaId) {
  if (!sistemaId) { _valvOpcoesAtual = null; _valvOpcoesSistemaId = null; return; }
  if (String(sistemaId) === String(_valvOpcoesSistemaId) && _valvOpcoesAtual) return;
  try {
    _valvOpcoesAtual = await api.get(`/api/valvulas-expansao/opcoes?sistema_id=${sistemaId}`);
    _valvOpcoesSistemaId = sistemaId;
  } catch (e) {
    _valvOpcoesAtual = null;
    _valvOpcoesSistemaId = null;
  }
}

function _valvOptions(lista, atual, rotuloFn) {
  let html = '<option value="">—</option>';
  let achou = false;
  (lista || []).forEach(item => {
    const val = item.modelo;
    if (val === atual) achou = true;
    html += `<option value="${val}" ${val === atual ? 'selected' : ''}>${rotuloFn ? rotuloFn(item) : val}</option>`;
  });
  // valor gravado que não está mais nas opções (importado/reformulação de Ids): preserva visível
  if (atual && !achou) html += `<option value="${atual}" selected>${atual}</option>`;
  return html;
}

function _linhaValvulas(r, ids) {
  const v = (r.valvulas || [])[0];
  if (!v) return '';
  const ehTermostatica = (v.tipo_expansao || '').toLowerCase().startsWith('termo');
  const modelos = (_valvOpcoesAtual && _valvOpcoesAtual.modelos) || [];
  const modeloSel = modelos.find(m_ => m_.modelo === v.modelo_selecao);
  const controladores = modeloSel ? modeloSel.controladores : [];
  const avisoNaoCadastrada = v.modelo_nao_cadastrado
    ? '<div style="color:#b45309;font-size:10px;margin-top:2px;">⚠ Válvula não cadastrada no sistema. Inserir valores manuais ou selecionar outro modelo.</div>' : '';
  const selModelo = `<div><label class="lbl">Modelo</label><select data-valv-modelo="${v.id}" data-id-campo="${ids.valvModelo}">${_valvOptions(modelos, v.modelo_selecao)}</select>${avisoNaoCadastrada}</div>`;
  const selCtrl = `<div><label class="lbl">Controlador</label><select data-valv-controlador="${v.id}" data-id-campo="${ids.valvControlador}">${_valvOptions(controladores, v.controlador,
    c => c.observacao ? `${c.modelo} — ${c.observacao}` : c.modelo)}</select></div>`;
  const campoCap = `<div><label class="lbl">Capacidade Unit. (kcal/h)</label><input type="text" value="${v.capacidade_unit_kcal_h ?? ''}" data-valv-capacidade="${v.id}" data-id-campo="${ids.valvCapacidade}"></div>`;
  const campoAbert = `<div><label class="lbl">Abert. Válvula (%)</label><input type="text" value="${v.carga_abertura_pct ?? ''}" readonly style="background:#f3f4f6;" title="Calculado: (Carga Térmica ÷ Qtd. Coletores) ÷ Capacidade Unit."></div>`;
  const campoEntrada = `<div><label class="lbl">Conexão Entrada</label><input type="text" value="${v.conexao_entrada ?? ''}" data-valv-entrada="${v.id}" data-id-campo="${ids.valvEntrada}"></div>`;
  const campoSaida = `<div><label class="lbl">Conexão Saída</label><input type="text" value="${v.conexao_saida ?? ''}" data-valv-saida="${v.id}" data-id-campo="${ids.valvSaida}"></div>`;
  let campos, colunas;
  if (ehTermostatica) {
    const campoOrificio = `<div><label class="lbl">Orifício</label><input type="text" value="${v.orificio ?? ''}" data-valv-orificio="${v.id}" data-id-campo="${ids.valvOrificio}"></div>`;
    campos = selModelo + campoOrificio + campoCap + campoAbert + campoEntrada + campoSaida + selCtrl;
    colunas = '1.1fr .7fr .9fr .7fr .7fr .7fr 1.2fr';
  } else {
    const campoTensao = `<div><label class="lbl">Tensão</label><input type="text" value="${v.tensao ?? ''}" data-valv-tensao="${v.id}" data-id-campo="${ids.valvTensao}"></div>`;
    const campoTipo = `<div><label class="lbl">Tipo</label><select data-valv-tipomotor="${v.id}" data-id-campo="${ids.valvTipomotor}">
      <option value="">—</option>
      <option value="Unipolar" ${v.tipo_motor === 'Unipolar' ? 'selected' : ''}>Unipolar</option>
      <option value="Bipolar" ${v.tipo_motor === 'Bipolar' ? 'selected' : ''}>Bipolar</option></select></div>`;
    campos = selModelo + campoCap + campoAbert + campoEntrada + campoSaida + campoTensao + campoTipo + selCtrl;
    colunas = '1fr .9fr .7fr .7fr .7fr .8fr .7fr 1.2fr';
  }
  return `<tr><td colspan="7" style="background:#eff6ff;border-bottom:1px solid var(--line);padding:6px 8px;">
    <div style="font-size:10.5px;font-weight:bold;text-transform:uppercase;color:#1d4ed8;margin-bottom:4px;">
      Válvula de Expansão <span style="color:#6b7280;font-weight:normal;text-transform:none;">
      — ${v.fabricante} · ${v.tipo_expansao} (definido no Sistema) · código desta linha para o app do fabricante: <code>${r.codigo_curto || '—'}</code>
      ${v.quantidade ? ` · ${v.quantidade} un. (coletores)` : ''}</span>
    </div>
    <div class="add-row" style="grid-template-columns:${colunas};">${campos}</div>
  </td></tr>`;
}

function _wireValvulas(container, handlers) {
  // Modelo (select): grava o Id comercial + preenche a mecânica do banco (conexões/tensão/tipo) —
  // relatório importado tem prioridade, mas aqui é o fluxo MANUAL (usuário escolhendo do zero).
  container.querySelectorAll('[data-valv-modelo]').forEach(sel => sel.addEventListener('change', () => {
    const payload = { modelo_selecao: sel.value || null };
    const info = (((_valvOpcoesAtual || {}).modelos) || []).find(m_ => m_.modelo === sel.value);
    if (info) {
      payload.conexao_entrada = info.conexao_entrada;
      payload.conexao_saida = info.conexao_saida;
      payload.tensao = info.tensao;
      payload.tipo_motor = info.tipo_motor;
    }
    handlers.onValvulaPayload(sel.dataset.valvModelo, payload);
  }));
  container.querySelectorAll('[data-valv-controlador]').forEach(sel => sel.addEventListener('change', () =>
    handlers.onValvulaPayload(sel.dataset.valvControlador, { controlador: sel.value || null })));
  container.querySelectorAll('[data-valv-capacidade]').forEach(inp => inp.addEventListener('change', () =>
    handlers.onValvulaPayload(inp.dataset.valvCapacidade, { capacidade_unit_kcal_h: parseNumBR(inp.value) })));
  container.querySelectorAll('[data-valv-orificio]').forEach(inp => inp.addEventListener('change', () =>
    handlers.onValvulaPayload(inp.dataset.valvOrificio, { orificio: inp.value || null })));
  container.querySelectorAll('[data-valv-tensao]').forEach(inp => inp.addEventListener('change', () =>
    handlers.onValvulaPayload(inp.dataset.valvTensao, { tensao: inp.value || null })));
  container.querySelectorAll('[data-valv-tipomotor]').forEach(sel => sel.addEventListener('change', () =>
    handlers.onValvulaPayload(sel.dataset.valvTipomotor, { tipo_motor: sel.value || null })));
  container.querySelectorAll('[data-valv-entrada]').forEach(inp => inp.addEventListener('change', () =>
    handlers.onValvulaPayload(inp.dataset.valvEntrada, { conexao_entrada: inp.value })));
  container.querySelectorAll('[data-valv-saida]').forEach(inp => inp.addEventListener('change', () =>
    handlers.onValvulaPayload(inp.dataset.valvSaida, { conexao_saida: inp.value })));
}

// Ids de campo (Configurações Sistema) — a tabela é compartilhada entre Tela 2 e Tela 3, cada
// uma com seu próprio intervalo de Ids (T2xx / T3xx), por isso quem chama passa o mapa certo.
const T2_DYNAMIC_IDS = { folga: 'T252', quantidade: 'T253', considerar: 'T254', tipoDegelo: 'T255',
  valvModelo: 'T256', valvOrificio: 'T257', valvCapacidade: 'T258', valvEntrada: 'T259',
  valvSaida: 'T260', valvTensao: 'T261', valvTipomotor: 'T262', valvControlador: 'T263' };
const T3_DYNAMIC_IDS = { folga: 'T317', quantidade: 'T318', considerar: 'T319', tipoDegelo: 'T320',
  valvModelo: 'T321', valvOrificio: 'T322', valvCapacidade: 'T323', valvEntrada: 'T324',
  valvSaida: 'T325', valvTensao: 'T326', valvTipomotor: 'T327', valvControlador: 'T328' };

function renderizarForcadores(container, forcadores, handlers, ids) {
  if (!forcadores || forcadores.length === 0) {
    container.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhuma linha adicionada ainda.</div>';
    return;
  }
  const grupos = {};
  forcadores.forEach(r => { (grupos[r.fabricante] = grupos[r.fabricante] || []).push(r); });
  let html = '';
  Object.keys(grupos).forEach(fab => {
    html += `<div class="group-head">${fab}</div><table class="list"><tbody>`;
    grupos[fab].forEach(r => {
      const trocasAlerta = (r.trocas_de_ar !== null && r.trocas_de_ar !== undefined && (r.trocas_de_ar < 30 || r.trocas_de_ar > 60)) ? ' ⚠' : '';
      const semResistencia = ['Natural', 'Gás quente'].includes(r.tipo_degelo_selecionado);
      // Não há trava técnica pra impedir escolher um Tipo de Degelo que o modelo não suporta de
      // fábrica — só um alerta visual, o usuário decide se segue assim mesmo. Fonte de verdade:
      // as opções da própria Nomenclatura comercial do catálogo (campo automático "tipo_degelo",
      // ver campo_catalogo.py) — mais confiável que o texto técnico genérico da matriz
      // (modelo.tipo_degelo), que pode ser o mesmo pra toda a linha mesmo quando cada
      // configuração (ex.: nº de aletas) só aceita um subconjunto de fato. Sem essa nomenclatura
      // cadastrada, cai pro texto técnico genérico como aproximação.
      const degeloIncompativel = r.tipo_degelo_selecionado && (
        r.tipo_degelo_opcoes_comerciais
          ? !_opcaoAutomatica(r.tipo_degelo_opcoes_comerciais.map(o => ({ valor: o })), r.tipo_degelo_selecionado, 'tipo_degelo')
          : (r.tipo_degelo_catalogo && !_catalogoSuportaDegelo(r.tipo_degelo_catalogo, r.tipo_degelo_selecionado)));
      html += `<tr>
        <td style="width:14%;font-weight:bold;text-align:center;white-space:normal;word-wrap:break-word;">${r.linha}</td>
        <td style="width:14%;text-align:center;white-space:normal;word-wrap:break-word;"><label style="font-size:10.5px;font-weight:bold;text-transform:uppercase;color:#1d4ed8;display:block;margin-bottom:2px;">Folga Desejada</label>
          <input type="text" value="${r.folga_desejada ?? ''}" style="width:60px;display:inline-block;" data-folga="${r.id}" data-id-campo="${ids.folga}"> %</td>
        <td style="width:9%;text-align:center;white-space:normal;word-wrap:break-word;"><label style="font-size:10.5px;font-weight:bold;text-transform:uppercase;color:#1d4ed8;display:block;margin-bottom:2px;">Qtd.</label>
          <input type="number" min="1" value="${r.quantidade ?? 1}" style="width:52px;" data-quantidade="${r.id}" data-id-campo="${ids.quantidade}"></td>
        <td style="width:19%;text-align:center;white-space:normal;word-wrap:break-word;color:#6b7280;">${r.modelo_resultante || '— sem modelo'}</td>
        <td style="width:14%;text-align:center;white-space:normal;word-wrap:break-word;color:#6b7280;">${r.folga_real !== null && r.folga_real !== undefined ? r.folga_real + '%' : '—'}</td>
        <td style="width:16%;text-align:center;white-space:normal;word-wrap:break-word;"><label style="font-size:11.5px;font-weight:${r.considerado ? 'bold' : 'normal'};color:${r.considerado ? '#15803d' : '#6b7280'};">
          <input type="radio" name="considerar-${container.id}" ${r.considerado ? 'checked' : ''} data-considerar="${r.id}" data-id-campo="${ids.considerar}"> Considerar</label></td>
        <td style="width:14%;text-align:center;white-space:normal;word-wrap:break-word;"><span class="btn-text danger" data-excluir="${r.id}">Excluir</span></td>
      </tr>
      <tr><td colspan="7" style="background:#fafafa;border-bottom:1px solid var(--line);padding:5px 8px;">
        <label style="font-size:10.5px;font-weight:bold;text-transform:uppercase;color:#1d4ed8;margin-right:4px;">Tipo de Degelo</label>
        <select data-tipo-degelo="${r.id}" data-id-campo="${ids.tipoDegelo}" style="width:120px;display:inline-block;margin-right:12px;${degeloIncompativel ? 'border:1px solid #b91c1c;background:#fef2f2;' : ''}"
          title="${degeloIncompativel ? `Catálogo desse modelo só tem degelo ${(r.tipo_degelo_opcoes_comerciais || [r.tipo_degelo_catalogo]).join(' ou ')}` : ''}">
          <option value="">—</option>
          <option value="Natural" ${r.tipo_degelo_selecionado === 'Natural' ? 'selected' : ''}>Natural</option>
          <option value="Elétrico" ${r.tipo_degelo_selecionado === 'Elétrico' ? 'selected' : ''}>Elétrico</option>
          <option value="Gás quente" ${r.tipo_degelo_selecionado === 'Gás quente' ? 'selected' : ''}>Gás quente</option>
        </select>
        ${degeloIncompativel ? `<span class="techspec" style="color:#b91c1c;font-weight:bold;">⚠ Deg. Incompatível</span>` : ''}
        ${r.capacidade_tabelada_kcal_h ? `<span class="techspec">Capacidade tabelada: ${fmtNum(r.capacidade_tabelada_kcal_h)}kcal/h</span>` : ''}
        ${r.capacidade_corrigida_unitaria ? `<span class="techspec" style="font-weight:bold;color:#1d4ed8;">Capacidade corrigida (unit.): ${fmtNum(r.capacidade_corrigida_unitaria)}kcal/h</span>` : ''}
        ${r.quantidade > 1 && r.capacidade_instalada_total ? `<span class="techspec" style="font-weight:bold;">Total instalado (${r.quantidade}x): ${fmtNum(r.capacidade_instalada_total)}kcal/h</span>` : ''}
        ${r.fator_gas_aplicado ? `<span class="techspec">Fator gás aplicado: ${r.fator_gas_aplicado}</span>` : ''}
        ${r.fator_gas_pendente ? `<span class="techspec" style="color:#b45309;">⚠ fator de correção do gás ainda não preenchido nessa linha</span>` : ''}
        ${r.diametro_ventilador_mm ? `<span class="techspec">${r.num_ventiladores ? r.num_ventiladores + 'x ' : ''}Ventilador Ø${r.diametro_ventilador_mm}mm</span>` : ''}
        ${r.tipo_degelo_catalogo ? `<span class="techspec">Degelo (catálogo): ${r.tipo_degelo_catalogo}</span>` : ''}
        ${r.carga_gas_kg ? `<span class="techspec">Carga de gás: ${r.carga_gas_kg}kg</span>` : ''}
        ${r.pot_resistencia_degelo_w && !semResistencia ? `<span class="techspec">Pot. resist. degelo: ${fmtNum(r.pot_resistencia_degelo_w)}W</span>` : ''}
        ${r.vazao_ar_m3h ? `<span class="techspec">Vazão unitária: ${fmtNum(r.vazao_ar_m3h)}m³/h</span>` : ''}
        ${r.trocas_de_ar !== null && r.trocas_de_ar !== undefined ? `<span class="techspec" style="font-weight:bold;color:#1d4ed8;">Trocas de ar: ${r.trocas_de_ar}/h${trocasAlerta}</span>` : ''}
        ${r.flecha_ar_m ? `<span class="techspec">Flecha: ${r.flecha_ar_m}m</span>` : ''}
        ${r.altura_max_instalacao_m ? `<span class="techspec">Altura máx. instalação: ${r.altura_max_instalacao_m}m</span>` : ''}
        ${r.pdl_referencia_m ? `<span class="techspec">PDL Máximo: ${r.pdl_referencia_m}m</span>` : ''}
        ${r.coletores_por_forcador ? `<span class="techspec">Coletores/forçador: ${r.coletores_por_forcador}</span>` : ''}
      </td></tr>
      ${r.considerado ? `<tr><td colspan="7" style="background:#f9fafb;padding:8px;" data-nomenc-wrap></td></tr>` : ''}
      ${_linhaValvulas(r, ids)}`;
    });
    html += '</tbody></table>';
  });
  container.innerHTML = html;
  container.querySelectorAll('[data-folga]').forEach(inp => inp.addEventListener('change', () => handlers.onFolgaChange(inp.dataset.folga, inp.value)));
  container.querySelectorAll('[data-quantidade]').forEach(inp => inp.addEventListener('change', () => handlers.onQuantidadeChange(inp.dataset.quantidade, inp.value)));
  container.querySelectorAll('[data-tipo-degelo]').forEach(sel => sel.addEventListener('change', () => handlers.onTipoDegeloChange(sel.dataset.tipoDegelo, sel.value)));
  container.querySelectorAll('[data-considerar]').forEach(inp => inp.addEventListener('change', () => handlers.onConsiderar(inp.dataset.considerar)));
  container.querySelectorAll('[data-excluir]').forEach(btn => btn.addEventListener('click', () => handlers.onExcluir(btn.dataset.excluir)));
  if (handlers.onNomenclaturaChange) {
    _carregarPainelNomenclaturaForcador(container, forcadores, handlers.onNomenclaturaChange);
  }
  _wireValvulas(container, handlers);
}

function renderizarAlertas(container, alertas) {
  if (!alertas || alertas.length === 0) { container.innerHTML = ''; return; }
  container.innerHTML = '<div class="alert-title">⚠ Alertas Ativos</div>' +
    alertas.map(a => `<div class="alert-item">• ${a}</div>`).join('');
}
