// Navegação lateral (árvore de projetos) + tela de boas-vindas.
// Nativo: a estrutura HTML (topbar/sidebar/main/welcome) já nasce correta em index.html —
// este arquivo só popula dados e liga eventos, sem mover nenhum elemento existente no DOM.

function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

function clickTab(tabId) {
  if (typeof window.showTab === 'function') window.showTab(Number(tabId));
}

function setCrumbs(parts) {
  const el = document.getElementById('crumbs');
  if (!el) return;
  const all = ['Projetos'].concat(parts || []);
  el.innerHTML = all.map((p, i) => i === all.length - 1 ? `<b>${esc(p)}</b>` : esc(p)).join(' <span>›</span> ');
}

function selectRow(row) {
  document.querySelectorAll('.sidebar-row.sel').forEach(x => x.classList.remove('sel'));
  row.classList.add('sel');
}

function mkRow(cls, label, meta, hasKids) {
  return `<div class="sidebar-row ${cls}" title="${esc(label)}">`
    + `<span class="sidebar-tw">${hasKids ? '&#9656;' : ''}</span>`
    + `<span class="sidebar-nm">${esc(label)}</span>`
    + (meta ? `<span class="sidebar-mt">${esc(meta)}</span>` : '')
    + `</div>`;
}

function area(c) {
  const l = parseFloat(c.largura), w = parseFloat(c.comprimento);
  return (l && w) ? (Math.round(l * w * 10) / 10) + ' m²' : '';
}

const TELAS_PROJETO = [
  { tab: '1', nome: 'Cadastro' },
  { tab: '2', nome: 'Câmara Completo' },
  { tab: '3', nome: 'Câmara Simples' },
  { tab: '4', nome: 'Expositor' },
  { tab: '5', nome: 'Compilação Linhas' },
  { tab: '11', nome: 'Rack / Cond. Remoto' },
  { tab: '10', nome: 'Painéis e Portas' },
  { tab: '12', nome: 'Compilação Geral' },
  { tab: '9', nome: 'Consumo Elétrico' },
  { tab: '17', nome: 'Resumo Materiais' },
  { tab: '18', nome: 'Luminotécnico' },
  { tab: '16', nome: 'Comparativo de Revisões' },
  { tab: '19', nome: 'Proposta Comercial' },
];

async function loadCamaras(proj, sistema, kids) {
  let completos = [], simples = [];
  try { completos = await api.get('/api/camaras-completo?projeto_id=' + proj.id); } catch (e) {}
  try { simples = await api.get('/api/camaras-simples?projeto_id=' + proj.id); } catch (e) {}
  const todas = (completos || []).concat(simples || []).filter(c => c.sistema_id === sistema.id);
  if (!todas.length) { kids.innerHTML = '<div class="sidebar-load">— sem câmaras</div>'; return; }
  kids.innerHTML = '';
  todas.forEach(c => {
    const isSimples = (simples || []).some(s => s.id === c.id);
    const tabAlvo = isSimples ? '3' : '2';
    const abrirFn = isSimples ? 't3_abrirCamara' : 't2_abrirCamara';
    const d = document.createElement('div');
    d.innerHTML = mkRow('sidebar-cam', c.nome || 'Câmara', area(c), false);
    const row = d.firstElementChild;
    row.addEventListener('click', ev => {
      ev.stopPropagation();
      selectRow(row);
      setCrumbs([proj.codigo_projeto || ('Projeto ' + proj.id), sistema.nome || 'Sistema', c.nome || 'Câmara']);
      clickTab(tabAlvo);
      if (window[abrirFn]) { try { window[abrirFn](c.id); } catch (e) { console.warn(abrirFn, e); } }
    });
    kids.appendChild(row);
  });
}

async function loadSistemas(proj, kids) {
  let sistemas;
  try { sistemas = await api.get('/api/projetos/' + proj.id + '/sistemas'); } catch (e) { kids.innerHTML = '<div class="sidebar-load">erro</div>'; return; }
  if (!sistemas || !sistemas.length) { kids.innerHTML = '<div class="sidebar-load">— sem sistemas</div>'; return; }
  kids.innerHTML = '';
  sistemas.forEach(s => {
    const box = document.createElement('div');
    box.className = 'sidebar-node';
    box.dataset.sid = s.id;
    box.innerHTML = mkRow('sidebar-sis', s.nome || 'Sistema', (s.temp_evaporacao != null ? s.temp_evaporacao + '°C' : ''), true) + '<div class="sidebar-kids"></div>';
    const srow = box.querySelector('.sidebar-row'), skids = box.querySelector('.sidebar-kids');
    box._abrir = async () => {
      box.classList.add('open');
      if (skids.dataset.loaded) return;
      skids.dataset.loaded = '1';
      skids.innerHTML = '<div class="sidebar-load">carregando…</div>';
      await loadCamaras(proj, s, skids);
    };
    srow.addEventListener('click', ev => {
      ev.stopPropagation();
      selectRow(srow);
      setCrumbs([proj.codigo_projeto || ('Projeto ' + proj.id), s.nome || 'Sistema']);
      if (box.classList.contains('open')) { box.classList.remove('open'); return; }
      box._abrir();
    });
    kids.appendChild(box);
  });
}

async function ativarProjetoNaTela(proj) {
  if (window.t1_abrirProjeto) {
    try {
      await window.t1_abrirProjeto(proj.id, window.__projetosCache || [proj]);
      // t1_abrirProjeto (tela1.js) retrai todos os accordions ao carregar — sem isso, os dados
      // do projeto clicado na árvore carregam mas ficam invisíveis (parece que "não abriu nada").
      const acc = document.getElementById('accDadosCliente');
      if (acc) acc.open = true;
    } catch (e) { console.warn('abrirProjeto', e); }
  }
}

function mkRevisaoBox(proj, isMaisRecente) {
  const box = document.createElement('div');
  box.className = 'sidebar-node sidebar-rev' + (isMaisRecente ? ' sidebar-rev-top' : '');
  box.dataset.rid = proj.id;
  const rev = 'R' + String(proj.revisao || 0).padStart(2, '0');
  box.innerHTML = mkRow(isMaisRecente ? 'sidebar-revrow sidebar-atual' : 'sidebar-revrow',
    isMaisRecente ? 'Revisão atual' : 'Revisão anterior', rev, true) + '<div class="sidebar-kids"></div>';
  const rrow = box.querySelector('.sidebar-row'), rkids = box.querySelector('.sidebar-kids');
  box._abrir = () => {
    box.classList.add('open');
    if (rkids.dataset.loaded) return; rkids.dataset.loaded = '1';
    rkids.innerHTML = '';
    const d0 = document.createElement('div');
    d0.innerHTML = mkRow('sidebar-tela', TELAS_PROJETO[0].nome, 'T' + TELAS_PROJETO[0].tab, false);
    rkids.appendChild(d0.firstElementChild);
    const camPasta = document.createElement('div');
    camPasta.className = 'sidebar-node sidebar-camp-node';
    camPasta.innerHTML = mkRow('sidebar-camp', 'Câmaras', '', true) + '<div class="sidebar-kids"></div>';
    const camRow = camPasta.querySelector('.sidebar-row'), camKids = camPasta.querySelector('.sidebar-kids');
    camPasta._abrir = async () => {
      camPasta.classList.add('open');
      if (camKids.dataset.loaded) return;
      camKids.dataset.loaded = '1';
      camKids.innerHTML = '<div class="sidebar-load">carregando…</div>';
      await loadSistemas(proj, camKids);
    };
    camRow.addEventListener('click', ev2 => {
      ev2.stopPropagation();
      selectRow(camRow); setCrumbs([proj.codigo_projeto || ('Projeto ' + proj.id), rev, 'Câmaras']);
      if (camPasta.classList.contains('open')) { camPasta.classList.remove('open'); return; }
      camPasta._abrir();
    });
    rkids.appendChild(camPasta);
    TELAS_PROJETO.slice(1).forEach(t => {
      const d = document.createElement('div');
      d.innerHTML = mkRow('sidebar-tela', t.nome, 'T' + t.tab, false);
      rkids.appendChild(d.firstElementChild);
    });
  };
  rrow.addEventListener('click', ev => {
    ev.stopPropagation();
    selectRow(rrow);
    setCrumbs([proj.codigo_projeto || ('Projeto ' + proj.id), rev]);
    ativarProjetoNaTela(proj);   // roda em paralelo — não trava a árvore esperando a Tela 1 carregar
    clickTab('1');
    if (box.classList.contains('open')) { box.classList.remove('open'); return; }
    box._abrir();
  });
  return box;
}

// Guarda qual projeto/revisão/pasta de Câmaras/sistema estava aberto antes de reconstruir a
// árvore (ex.: ao salvar o projeto), pra reabrir tudo igual depois — sem isso, refreshArvoreProjetos
// sempre nascia com tudo fechado, mesmo no meio de uma navegação.
function _capturarAbertos(tree) {
  const projBox = tree.querySelector(':scope > .sidebar-projbox.open');
  if (!projBox) return null;
  const estado = { pid: projBox.dataset.pid };
  const revBox = projBox.querySelector(':scope > .sidebar-kids > .sidebar-rev.open');
  if (!revBox) return estado;
  estado.rid = revBox.dataset.rid;
  const camBox = revBox.querySelector(':scope > .sidebar-kids > .sidebar-camp-node.open');
  if (!camBox) return estado;
  estado.cam = true;
  const sisBox = camBox.querySelector(':scope > .sidebar-kids > .sidebar-node.open[data-sid]');
  if (!sisBox) return estado;
  estado.sid = sisBox.dataset.sid;
  return estado;
}

async function _restaurarAbertos(tree, estado) {
  if (!estado) return;
  const projBox = tree.querySelector(`.sidebar-projbox[data-pid="${estado.pid}"]`);
  if (!projBox || !projBox._abrir) return;
  await projBox._abrir();
  if (!estado.rid) return;
  const revBox = projBox.querySelector(`.sidebar-rev[data-rid="${estado.rid}"]`);
  if (!revBox || !revBox._abrir) return;
  await revBox._abrir();
  if (!estado.cam) return;
  const camBox = revBox.querySelector('.sidebar-camp-node');
  if (!camBox || !camBox._abrir) return;
  await camBox._abrir();
  if (!estado.sid) return;
  const sisBox = camBox.querySelector(`[data-sid="${estado.sid}"]`);
  if (!sisBox || !sisBox._abrir) return;
  await sisBox._abrir();
}

async function loadProjetosArvore() {
  const tree = document.getElementById('arvoreProjetos');
  if (!tree) return;
  const estadoAberto = _capturarAbertos(tree);
  try {
    const todos = await api.get('/api/projetos');
    window.__projetosCache = todos || [];

    let abertos = [];
    try { abertos = await api.get('/api/workspace/abertos'); } catch (_) {}

    if (!window.__projetosCache.length) { tree.innerHTML = '<div class="sidebar-empty">Nenhum projeto aberto.</div>'; return; }

    const idParaVek = {};
    abertos.forEach(a => (a.projeto_ids || []).forEach(pid => { idParaVek[pid] = a.path; }));

    const porArquivo = {};
    const ordemArquivos = [];
    window.__projetosCache.forEach(p => {
      const vek = idParaVek[p.id] || '__sem_arquivo';
      if (!porArquivo[vek]) { porArquivo[vek] = []; ordemArquivos.push(vek); }
      porArquivo[vek].push(p);
    });

    tree.innerHTML = '';
    ordemArquivos.forEach(vekPath => {
      const projetos = porArquivo[vekPath];
      const nomeArquivo = vekPath === '__sem_arquivo' ? 'Sem arquivo' : vekPath.replace(/\\/g, '/').split('/').pop().replace(/\.vek$/i, '');

      const fileBox = document.createElement('div');
      fileBox.className = 'sidebar-node sidebar-filebox open';
      fileBox.dataset.vek = vekPath;
      const headerHtml = `<div class="sidebar-row sidebar-file" title="${esc(vekPath)}">` +
        `<span class="sidebar-tw">&#9662;</span>` +
        `<span class="sidebar-nm" style="font-weight:600;">${esc(nomeArquivo)}</span>` +
        (vekPath !== '__sem_arquivo' ? `<span class="sidebar-close" title="Descarregar arquivo">&times;</span>` : '') +
        `</div><div class="sidebar-kids"></div>`;
      fileBox.innerHTML = headerHtml;
      const fileRow = fileBox.querySelector('.sidebar-row');
      const fileKids = fileBox.querySelector('.sidebar-kids');
      const btnClose = fileBox.querySelector('.sidebar-close');

      fileRow.addEventListener('click', ev => {
        ev.stopPropagation();
        if (ev.target === btnClose) return;
        fileBox.classList.toggle('open');
      });

      if (btnClose) {
        btnClose.addEventListener('click', async ev => {
          ev.stopPropagation();
          if (!confirm(`Descarregar o arquivo "${nomeArquivo}"?\nOs dados serão salvos antes de fechar.`)) return;
          try {
            await api.post('/api/workspace/fechar', { path: vekPath });
            if (state.projetoId && idParaVek[state.projetoId] === vekPath) {
              await fecharProjetoAtivo();
            }
            loadProjetosArvore();
          } catch (e) { alert('Erro ao descarregar: ' + (e.message || e)); }
        });
      }

      const grupos = {}, ordem = [];
      projetos.forEach(p => {
        const k = p.codigo_base || ('__id:' + p.id);
        if (!grupos[k]) { grupos[k] = []; ordem.push(k); }
        grupos[k].push(p);
      });

      ordem.forEach(k => {
        const revs = grupos[k].sort((a, b) => (b.revisao || 0) - (a.revisao || 0));
        const pai = revs[0];
        const box = document.createElement('div');
        box.className = 'sidebar-node sidebar-projbox';
        box.dataset.pid = pai.id;
        box.innerHTML = mkRow('sidebar-proj', pai.codigo_projeto || ('Projeto ' + pai.id), pai.cliente || '', true) + '<div class="sidebar-kids"></div>';
        const prow = box.querySelector('.sidebar-row'), pkids = box.querySelector('.sidebar-kids');
        box._abrir = () => {
          box.classList.add('open');
          if (pkids.dataset.loaded) return; pkids.dataset.loaded = '1';
          revs.forEach((p, i) => pkids.appendChild(mkRevisaoBox(p, i === 0)));
        };
        prow.addEventListener('click', ev => {
          ev.stopPropagation();
          selectRow(prow);
          setCrumbs([nomeArquivo, pai.codigo_projeto || ('Projeto ' + pai.id)]);
          ativarProjetoNaTela(pai);
          clickTab('1');
          if (box.classList.contains('open')) { box.classList.remove('open'); return; }
          box._abrir();
        });
        fileKids.appendChild(box);
      });

      tree.appendChild(fileBox);
    });
    await _restaurarAbertos(tree, estadoAberto);
  } catch (e) { tree.innerHTML = '<div class="sidebar-empty">Erro: ' + esc(e) + '</div>'; }
}
window.refreshArvoreProjetos = loadProjetosArvore;

// Delegação de eventos (captura): navega direto pra tela clicada, sem subir pro clique do pai.
document.addEventListener('click', ev => {
  const row = ev.target.closest && ev.target.closest('.sidebar-tela');
  if (!row) return;
  const mt = row.querySelector('.sidebar-mt');
  if (!mt) return;
  const m = String(mt.textContent || '').match(/^T(\d+)$/);
  if (!m) return;
  ev.stopPropagation();
  selectRow(row);
  const projbox = row.closest('.sidebar-projbox');
  const revbox = row.closest('.sidebar-rev');
  const partes = [];
  if (projbox) { const nm = projbox.querySelector(':scope > .sidebar-row .sidebar-nm'); if (nm) partes.push(nm.textContent); }
  if (revbox) { const mtRev = revbox.querySelector(':scope > .sidebar-row .sidebar-mt'); if (mtRev) partes.push(mtRev.textContent); }
  const nmTela = row.querySelector('.sidebar-nm'); if (nmTela) partes.push(nmTela.textContent);
  setCrumbs(partes);
  clickTab(m[1]);
}, true);

// Tela de boas-vindas: mostra/esconde com base no #projetoStatus (chamado de imediato, sem
// setTimeout — o texto já está pronto no HTML no carregamento, não precisa esperar nada).
function atualizarModoBoasVindas() {
  const st = document.getElementById('projetoStatus');
  const ativo = st && st.textContent && st.textContent.indexOf('nenhum') === -1;
  // "+ Novo Projeto" abre o form antes de qualquer save (projetoStatus continua "nenhum ativo").
  // Sem este OR, a boas-vindas voltaria por cima do form assim que fecharProjetoAtivo() rodasse.
  const form = document.getElementById('formProjetoWrap');
  const formAberto = form && form.style.display === 'block';
  document.body.classList.toggle('sem-projeto', !ativo && !formAberto);
}
window.atualizarModoBoasVindas = atualizarModoBoasVindas;

function initSidebar() {
  loadProjetosArvore();
  atualizarModoBoasVindas();


  const st = document.getElementById('projetoStatus');
  if (st) new MutationObserver(atualizarModoBoasVindas).observe(st, { childList: true, characterData: true, subtree: true });
  const form = document.getElementById('formProjetoWrap');
  if (form) new MutationObserver(atualizarModoBoasVindas).observe(form, { attributes: true, attributeFilter: ['style'] });

  const btnNovoSide = document.getElementById('btnNovoProjetoSidebar');
  if (btnNovoSide) btnNovoSide.addEventListener('click', () => {
    clickTab('1');
    const b = document.getElementById('btnNovoProjeto'); if (b) b.click();
  });
  const btnNovoWelcome = document.getElementById('btnNovoProjetoWelcome');
  if (btnNovoWelcome) btnNovoWelcome.addEventListener('click', () => {
    clickTab('1');
    const b = document.getElementById('btnNovoProjeto'); if (b) b.click();
  });

  async function abrirArquivoVek() {
    if (!window.vektorium || !window.vektorium.abrirArquivo) {
      alert('Função disponível apenas no aplicativo desktop.');
      return;
    }
    const caminho = await window.vektorium.abrirArquivo();
    if (!caminho) return;
    try {
      const r = await api.post('/api/workspace/abrir', { path: caminho });
      if (r.ok || r.ja_aberto) {
        await loadProjetosArvore();
        if (r.projeto_ids && r.projeto_ids.length) {
          await definirProjetoAtivo(r.projeto_ids[0]);
          clickTab('1');
        }
      }
    } catch (e) {
      alert('Erro ao abrir arquivo: ' + (e.message || e));
    }
  }
  window.abrirArquivoVek = abrirArquivoVek;

  const btnAbrirSide = document.getElementById('btnAbrirProjetoSidebar');
  if (btnAbrirSide) btnAbrirSide.addEventListener('click', abrirArquivoVek);
  const btnAbrirWelcome = document.getElementById('btnAbrirProjetoWelcome');
  if (btnAbrirWelcome) btnAbrirWelcome.addEventListener('click', abrirArquivoVek);

  document.querySelectorAll('.sidebar-cat').forEach(a => {
    a.addEventListener('click', () => { clickTab(a.dataset.tab); setCrumbs(['Catálogos & config.', a.textContent.trim()]); });
  });

  const busca = document.getElementById('buscaProjetoSidebar');
  if (busca) busca.addEventListener('input', () => {
    const q = busca.value.toLowerCase();
    document.querySelectorAll('.sidebar-projbox').forEach(n => {
      n.style.display = n.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    });
  });

  const side = document.getElementById('sidebar');
  const col = document.getElementById('btnColapsarSidebar');
  if (col) col.addEventListener('click', () => side.classList.toggle('collapsed'));
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key && e.key.toLowerCase() === 'b') { e.preventDefault(); side.classList.toggle('collapsed'); }
  });

  initLoginUI();
  if (AUTH.logado()) {
    _aplicarPermissoesTelas();
    if (typeof iniciarVerificacaoPeriodicaLicenca === 'function') iniciarVerificacaoPeriodicaLicenca();
  }

  const elVersao = document.getElementById('sidebarVersao');
  if (elVersao) {
    if (window.vektorium && window.vektorium.versao) {
      elVersao.textContent = 'v' + window.vektorium.versao;
    } else {
      fetch('/api/versao').then(r => r.json()).then(d => { elVersao.textContent = 'v' + (d.versao || '?'); }).catch(() => {});
    }
  }

  document.body.style.visibility = 'visible';
}

// Sem sessão ativa (nunca logou, pulou o login ou saiu): telas de projeto ficam em modo
// só-visualização, com o mesmo congelamento visual/de clique do "Projeto Fechado" (ver style.css).
// Chamada em todo ponto que muda o estado de login, pra nunca ficar dessincronizada.
function _atualizarModoSomenteVisualizacao() {
  document.body.classList.toggle('modo-visualizacao', !AUTH.logado());
}

const _MODULO_TAB = {
  cadastro: '1', camara_completo: '2', camara_simples: '3', expositor: '4',
  compilacao_linhas: '5', catalogo_forcadores: '6', configuracoes: '7',
  catalogo_uc: '8', consumo_eletrico: '9', paineis_portas: '10',
  rack_paralelo: '11', compilacao_geral: '12', catalogo_comercial: '13',
  catalogo_condensadores: '15', comparativo_revisoes: '16',
  resumo_materiais: '17', luminotecnico: '18', proposta_comercial: '19'
};

async function _aplicarPermissoesTelas() {
  try {
    const dados = await api.get('/api/admin/minhas-permissoes');
    if (dados.is_admin) return;
    const permitidos = new Set();
    (dados.permissoes || []).forEach(p => {
      if (p.ver && _MODULO_TAB[p.modulo]) permitidos.add(_MODULO_TAB[p.modulo]);
    });
    Object.values(_MODULO_TAB).forEach(tab => {
      const show = permitidos.has(tab);
      const cat = document.querySelector(`.sidebar-cat[data-tab="${tab}"]`);
      if (cat) cat.style.display = show ? '' : 'none';
      const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
      if (btn) btn.style.display = show ? '' : 'none';
    });
  } catch (_) {}
}

function _atualizarBotaoLogin() {
  const btn = document.getElementById('btnLogin');
  if (btn) btn.textContent = AUTH.logado() ? (AUTH.email() || 'Logado') : 'Entrar';
  _atualizarModoSomenteVisualizacao();
}

function _mostrarTelaLogin() {
  document.getElementById('login_erro').style.display = 'none';
  document.getElementById('login_email').value = '';
  document.getElementById('login_senha').value = '';
  document.body.classList.add('sem-login');
  _atualizarModoSomenteVisualizacao();
}

function _esconderTelaLogin() {
  document.body.classList.remove('sem-login');
  _atualizarBotaoLogin();
}

function initLoginUI() {
  _atualizarBotaoLogin();

  // Link de recuperação de senha (Supabase redireciona pro app com o token na URL) — mostra a
  // tela de "definir senha nova" em vez do login normal. Verifica ANTES de tudo, ainda com a
  // URL intacta (mostrarTelaLogin/recovery limpa a URL depois de ler).
  // Tudo isso protegido por try/catch: se alguma coisa aqui falhar (token velho, elemento
  // ausente etc.), a tela de login NUNCA pode travar por causa disso.
  let recuperacao = null;
  try { recuperacao = AUTH.lerTokenRecuperacao(); } catch (e) { console.warn('lerTokenRecuperacao falhou', e); }
  try {
  if (recuperacao) {
    document.body.classList.add('sem-login');
    document.querySelector('#loginScreen .login-form').style.display = 'none';
    const formNovaSenha = document.getElementById('novaSenhaForm');
    formNovaSenha.style.display = 'block';
    document.querySelector('#loginScreen h2').textContent = 'Definir nova senha';
    document.querySelector('#loginScreen p').textContent = recuperacao.email
      ? `Conta: ${recuperacao.email}` : 'Defina sua nova senha.';

    const erroNovaSenha = document.getElementById('nova_senha_erro');
    const btnSalvar = document.getElementById('btnDefinirNovaSenha');
    btnSalvar.addEventListener('click', async () => {
      const s1 = document.getElementById('nova_senha_1').value;
      const s2 = document.getElementById('nova_senha_2').value;
      erroNovaSenha.style.display = 'none';
      if (!s1 || s1.length < 6) { erroNovaSenha.textContent = 'A senha precisa ter pelo menos 6 caracteres.'; erroNovaSenha.style.display = 'block'; return; }
      if (s1 !== s2) { erroNovaSenha.textContent = 'As senhas não coincidem.'; erroNovaSenha.style.display = 'block'; return; }
      if (btnSalvar.disabled) return;
      btnSalvar.disabled = true; btnSalvar.textContent = 'Salvando...';
      try {
        await AUTH.definirNovaSenha(recuperacao.access_token, s1);
        alert('Senha definida com sucesso! Faça login com a senha nova.');
        formNovaSenha.style.display = 'none';
        document.querySelector('#loginScreen .login-form').style.display = 'block';
        document.querySelector('#loginScreen h2').textContent = 'Entrar';
        document.querySelector('#loginScreen p').textContent = 'Login com assinatura ativa para acessar o sistema.';
        if (recuperacao.email) document.getElementById('login_email').value = recuperacao.email;
      } catch (e) {
        erroNovaSenha.textContent = e.message || 'Falha ao salvar a senha.';
        erroNovaSenha.style.display = 'block';
      } finally {
        btnSalvar.disabled = false; btnSalvar.textContent = 'Salvar nova senha';
      }
    });
  } else if (!AUTH.logado()) {
    // Login aparece automaticamente ao abrir o app, direto (sem esconder atrás de botão) — só
    // pula se já existir sessão válida guardada de uma vez anterior.
    _mostrarTelaLogin();
  }
  } catch (e) {
    console.warn('Falha ao montar tela de login/recuperação — app segue liberado mesmo assim', e);
    document.body.classList.remove('sem-login');   // nunca deixa o usuário trancado por causa disso
  }

  const btnLogin = document.getElementById('btnLogin');
  const btnEntrar = document.getElementById('btnLoginEntrar');
  const erroEl = document.getElementById('login_erro');

  btnLogin.addEventListener('click', async () => {
    if (AUTH.logado()) {
      if (!confirm(`Sair da conta ${AUTH.email() || ''}?`)) return;
      sairDoApp();
      return;
    }
    _mostrarTelaLogin();
  });

  // Guarda contra cliques/Enter repetidos: só a chamada mais recente pode atualizar a tela — uma
  // resposta antiga (de um clique anterior) que chega depois é descartada, nunca sobrescreve um
  // sucesso já mostrado. Enter no campo de senha também tenta login (antes só o clique funcionava).
  let _tentativaAtual = 0;
  let _heartbeatInterval = null;

  function _iniciarHeartbeat(uid, jwt) {
    _pararHeartbeat();
    _heartbeatInterval = setInterval(() => {
      var t = AUTH.token();
      if (!t) { _pararHeartbeat(); return; }
      api.post('/api/cloud/create-lock', { user_id: uid, token: t }).catch(function () {});
    }, 30000);
  }

  function _pararHeartbeat() {
    if (_heartbeatInterval) { clearInterval(_heartbeatInterval); _heartbeatInterval = null; }
  }

  window._pararHeartbeat = _pararHeartbeat;

  async function tentarLogin() {
    if (btnEntrar.disabled) return;   // já tem uma tentativa em andamento — ignora clique extra
    const email = document.getElementById('login_email').value.trim().toLowerCase();
    const senha = document.getElementById('login_senha').value;
    if (!email || !senha) { erroEl.textContent = 'Preencha e-mail e senha.'; erroEl.style.display = 'block'; return; }
    const minhaTentativa = ++_tentativaAtual;
    btnEntrar.disabled = true; btnEntrar.textContent = 'Entrando...';
    erroEl.style.display = 'none';
    try {
      await AUTH.login(email, senha);
      if (minhaTentativa !== _tentativaAtual) return;
      // SE-032 FASE D — check-lock → create-lock → pull-novos
      const _uid = AUTH._sessao && AUTH._sessao.user ? AUTH._sessao.user.id : null;
      const _jwt = AUTH.token();
      if (_uid && _jwt) {
        btnEntrar.textContent = 'Verificando sessão...';
        let _lockResp = null;
        try { _lockResp = await api.post('/api/cloud/check-lock', { user_id: _uid, token: _jwt }); } catch (_) {}
        if (_lockResp && _lockResp.locked) {
          const _host = _lockResp.hostname || 'outro dispositivo';
          if (!confirm(`Sessão ativa detectada em: ${_host}\n\nForçar entrada aqui? (A sessão anterior será encerrada.)`)) {
            AUTH.limpar();
            throw new Error('Login cancelado.');
          }
          try { await api.post('/api/cloud/delete-lock', { user_id: _uid, token: _jwt }); } catch (_) {}
        }
        try { await api.post('/api/cloud/create-lock', { user_id: _uid, token: _jwt }); } catch (_) {}
        _iniciarHeartbeat(_uid, _jwt);
        btnEntrar.textContent = 'Sincronizando projetos...';
        try { await api.post('/api/cloud/pull-novos', { user_id: _uid, token: _jwt }); } catch (_) {}
      }
      _esconderTelaLogin();
      _aplicarPermissoesTelas();
      if (typeof iniciarVerificacaoPeriodicaLicenca === 'function') iniciarVerificacaoPeriodicaLicenca();
    } catch (e) {
      if (minhaTentativa !== _tentativaAtual) return;
      erroEl.textContent = e.message || 'Falha no login.';
      erroEl.style.display = 'block';
      document.getElementById('login_senha').select();
    } finally {
      if (minhaTentativa === _tentativaAtual) { btnEntrar.disabled = false; btnEntrar.textContent = 'Entrar'; }
    }
  }
  btnEntrar.addEventListener('click', tentarLogin);
  document.getElementById('login_senha').addEventListener('keydown', ev => { if (ev.key === 'Enter') tentarLogin(); });
  document.getElementById('login_email').addEventListener('keydown', ev => { if (ev.key === 'Enter') document.getElementById('login_senha').focus(); });

}

if (document.readyState !== 'loading') initSidebar();
else document.addEventListener('DOMContentLoaded', initSidebar);
