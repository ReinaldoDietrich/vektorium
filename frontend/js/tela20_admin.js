// Tela 20 — Administração (papéis dinâmicos, CRUD usuários, logs)
(function () {
  let carregou = false;
  let _papeis = [];
  let _usuarios = [];
  let _permissoes = [];
  let _logsOffset = 0;
  const _LOGS_PAGE = 20;

  const MODULOS = [
    'cadastro', 'camara_completo', 'camara_simples', 'expositor',
    'compilacao_linhas', 'rack_paralelo', 'paineis_portas',
    'compilacao_geral', 'consumo_eletrico', 'resumo_materiais',
    'luminotecnico', 'comparativo_revisoes', 'proposta_comercial',
    'catalogo_forcadores', 'catalogo_uc', 'catalogo_condensadores',
    'catalogo_comercial', 'configuracoes'
  ];

  window.telaShowHandlers[20] = async function () {
    if (!AUTH.logado()) { document.getElementById('t20_corpo').innerHTML = '<p>Faça login para acessar.</p>'; return; }
    if (carregou) return;
    carregou = true;
    await carregarPerfil();
    if (!state.isMaster) { document.getElementById('t20_corpo').innerHTML = '<p>Acesso restrito a administradores.</p>'; return; }
    document.getElementById('t20_painelMaster').style.display = 'block';
    await carregarPapeis();
    renderPermHead();
    _popularSelectNovoUsuario();
    await Promise.all([carregarUsuarios(), carregarDispositivos(), carregarPermissoes()]);
  };

  // --- PERFIL ---
  async function carregarPerfil() {
    try {
      const dados = await api.get('/api/admin/meu-perfil');
      const u = dados.usuario;
      const a = dados.assinatura;
      document.getElementById('t20_perfilNome').textContent = u.nome || u.email;
      document.getElementById('t20_perfilEmail').textContent = u.email;
      document.getElementById('t20_perfilPapel').textContent = u.papel;
      document.getElementById('t20_perfilAssinatura').textContent = a
        ? `${a.plano} (${a.status})${a.vence_em ? ' — vence ' + a.vence_em : ''}`
        : 'Nenhuma';
      state.isMaster = u.papel === 'master';
    } catch (e) {
      document.getElementById('t20_perfilNome').textContent = 'Erro ao carregar perfil';
    }
  }

  // --- PAPEIS ---
  async function carregarPapeis() {
    const tbody = document.getElementById('t20_tbPapeis');
    tbody.innerHTML = '<tr><td colspan="4">Carregando…</td></tr>';
    try {
      _papeis = await api.get('/api/admin/papeis');
      renderPapeis();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="4">Erro: ${e.message}</td></tr>`;
    }
  }

  function renderPapeis() {
    const tbody = document.getElementById('t20_tbPapeis');
    if (!_papeis.length) { tbody.innerHTML = '<tr><td colspan="4">Nenhum tipo cadastrado.</td></tr>'; return; }
    tbody.innerHTML = _papeis.map(p => {
      const protegido = p.nome === 'master';
      const btnEdit = `<button class="btn-text" onclick="window._t20_editarPapel(${p.id})">Editar</button>`;
      const btnDel = protegido ? '' : ` <button class="btn-text danger" onclick="window._t20_excluirPapel(${p.id},'${p.nome}')">Excluir</button>`;
      return `<tr data-papel-id="${p.id}">
        <td>${p.nome}</td>
        <td>${p.descricao}</td>
        <td style="text-align:center">${p.is_admin ? 'Sim' : 'Não'}</td>
        <td>${btnEdit}${btnDel}</td>
      </tr>`;
    }).join('');
  }

  window._t20_criarPapel = async function () {
    const nome = document.getElementById('t20_novoPapelNome').value.trim();
    const descricao = document.getElementById('t20_novoPapelDesc').value.trim();
    const is_admin = document.getElementById('t20_novoPapelAdmin').checked;
    const msg = document.getElementById('t20_papelMsg');
    if (!nome) { msg.textContent = 'Informe o nome.'; return; }
    msg.textContent = 'Criando…';
    try {
      await api.post('/api/admin/papeis', { nome, descricao, is_admin });
      document.getElementById('t20_novoPapelNome').value = '';
      document.getElementById('t20_novoPapelDesc').value = '';
      document.getElementById('t20_novoPapelAdmin').checked = false;
      msg.textContent = 'Tipo criado.';
      setTimeout(() => { msg.textContent = ''; }, 3000);
      await carregarPapeis();
      _popularSelectNovoUsuario();
      renderUsuarios();
      renderPermHead();
      renderPermissoes();
    } catch (e) { msg.textContent = 'Erro: ' + e.message; }
  };

  window._t20_editarPapel = function (id) {
    const p = _papeis.find(x => x.id === id);
    if (!p) return;
    vkPrompt('Editar Tipo', [
      {label: 'Nome do tipo', name: 'nome', valor: p.nome},
      {label: 'Descrição', name: 'descricao', valor: p.descricao},
      {label: 'Acesso administrativo', name: 'is_admin', tipo: 'checkbox', valor: p.is_admin}
    ], async (v) => {
      if (!v.nome || !v.nome.trim()) return;
      try {
        await api.put(`/api/admin/papeis/${id}`, { nome: v.nome.trim(), descricao: v.descricao || '', is_admin: v.is_admin });
        await carregarPapeis();
        _popularSelectNovoUsuario();
        await carregarUsuarios();
        renderPermHead();
        await carregarPermissoes();
      } catch (e) { alert('Erro: ' + e.message); }
    });
  };

  window._t20_excluirPapel = async function (id, nome) {
    if (!confirm(`Excluir o tipo "${nome}"? Usuários atribuídos a ele devem ser reatribuídos primeiro.`)) return;
    try {
      await api.del(`/api/admin/papeis/${id}`);
      await carregarPapeis();
      _popularSelectNovoUsuario();
      renderPermHead();
      await carregarPermissoes();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  // --- USUARIOS ---
  function _popularSelectNovoUsuario() {
    const sel = document.getElementById('t20_novoUsuPapel');
    if (!sel) return;
    sel.innerHTML = _papeis.map(p => `<option value="${p.nome}"${p.nome !== 'master' ? ' selected' : ''}>${p.nome}</option>`).join('');
  }

  async function carregarUsuarios() {
    const tbody = document.getElementById('t20_tbUsuarios');
    tbody.innerHTML = '<tr><td colspan="7">Carregando…</td></tr>';
    try {
      _usuarios = await api.get('/api/admin/usuarios');
      renderUsuarios();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7">Erro: ${e.message}</td></tr>`;
    }
  }

  function _badgeStatus(status) {
    if (!status) return '<span class="badge">—</span>';
    const s = status.toLowerCase();
    let cls = '';
    if (s === 'active' || s === 'ativa' || s === 'ativo') cls = 'active';
    else if (s === 'trial' || s === 'teste') cls = 'trial';
    else if (s === 'canceled' || s === 'cancelada' || s === 'cancelado' || s === 'inactive' || s === 'inativa') cls = 'canceled';
    return `<span class="badge ${cls}">${status.toUpperCase()}</span>`;
  }

  function _selectTipo(uid, papelAtual) {
    const opts = _papeis.map(p =>
      `<option value="${p.nome}"${p.nome === papelAtual ? ' selected' : ''}>${p.nome}</option>`
    ).join('');
    return `<select onchange="window._t20_trocarTipo('${uid}',this.value)" style="font-size:12px;padding:2px 4px">${opts}</select>`;
  }

  function renderUsuarios() {
    const tbody = document.getElementById('t20_tbUsuarios');
    if (!_usuarios.length) { tbody.innerHTML = '<tr><td colspan="7">Nenhum usuário.</td></tr>'; return; }
    tbody.innerHTML = _usuarios.map(u => {
      const status = u.assinatura_status || '—';
      const plano = u.assinatura_plano || '—';
      const vence = u.assinatura_vence_em || '—';
      const isTrial = status.toLowerCase() === 'trial' || status.toLowerCase() === 'teste';

      let acoes = `<button class="btn-text" onclick="window._t20_editarUsuario('${u.id}','${(u.email||'').replace(/'/g,"\\'")}','${(u.nome||'').replace(/'/g,"\\'")}','${u.papel}')">Editar</button>`;
      if (isTrial) {
        acoes += ` <button class="btn-text ok" onclick="window._t20_concederVitalicia('${u.id}','${(u.email||'').replace(/'/g,"\\'")}')">Vitalícia</button>`;
      }
      acoes += ` <button class="btn-text danger" onclick="window._t20_excluirUsuario('${u.id}','${(u.email||'').replace(/'/g,"\\'")}')">Excluir</button>`;

      return `<tr>
        <td>${u.email}</td>
        <td>${u.nome || '—'}</td>
        <td>${_selectTipo(u.id, u.papel)}</td>
        <td style="text-align:center">${_badgeStatus(status)}</td>
        <td style="text-align:center">${plano.toUpperCase()}</td>
        <td>${vence}</td>
        <td style="white-space:nowrap">${acoes}</td>
      </tr>`;
    }).join('');
  }

  window._t20_trocarTipo = async function (uid, novoPapel) {
    try {
      await api.put(`/api/admin/usuarios/${uid}`, { papel: novoPapel });
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  window._t20_novoUsuarioInline = function () {
    const email = (document.getElementById('t20_novoUsuEmail').value || '').trim().toLowerCase();
    const nome = (document.getElementById('t20_novoUsuNome').value || '').trim();
    const papel = document.getElementById('t20_novoUsuPapel').value;
    const msg = document.getElementById('t20_usuarioMsg');

    if (!email) { msg.textContent = 'Informe o email.'; return; }

    vkPrompt('Senha do novo usuário', [
      {label: 'Senha (mín. 6 caracteres)', name: 'senha', tipo: 'password'}
    ], async (v) => {
      const senha = (v.senha || '').trim();
      if (!senha || senha.length < 6) { alert('Senha deve ter no mínimo 6 caracteres.'); return; }
      msg.textContent = 'Criando…';
      try {
        await api.post('/api/admin/usuarios', { email, senha, nome, papel });
        document.getElementById('t20_novoUsuEmail').value = '';
        document.getElementById('t20_novoUsuNome').value = '';
        msg.textContent = 'Usuário criado.';
        setTimeout(() => { msg.textContent = ''; }, 3000);
        await carregarUsuarios();
      } catch (e) {
        msg.textContent = '';
        alert('Erro: ' + e.message);
      }
    });
  };

  window._t20_editarUsuario = function (uid, email, nome, papel) {
    vkPrompt('Editar Usuário — ' + email, [
      {label: 'Nome', name: 'nome', valor: nome},
      {label: 'Tipo', name: 'papel', valor: papel}
    ], async (v) => {
      const novoNome = (v.nome || '').trim();
      const novoPapel = (v.papel || '').trim();
      if (!novoNome && !novoPapel) return;
      try {
        await api.put(`/api/admin/usuarios/${uid}`, { nome: novoNome, papel: novoPapel });
        await carregarUsuarios();
      } catch (e) { alert('Erro: ' + e.message); }
    });
  };

  window._t20_concederVitalicia = async function (uid, email) {
    if (!confirm(`Conceder assinatura VITALÍCIA para "${email}"?`)) return;
    try {
      await api.post(`/api/admin/assinaturas/${uid}/conceder-vitalicia`);
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  window._t20_excluirUsuario = async function (uid, email) {
    if (!confirm(`Excluir o usuário "${email}"?\n\nIsso removerá PERMANENTEMENTE do Supabase Auth e de todas as tabelas.`)) return;
    try {
      await api.del(`/api/admin/usuarios/${uid}`);
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  // --- DISPOSITIVOS ---
  async function carregarDispositivos() {
    const tbody = document.getElementById('t20_tbDispositivos');
    tbody.innerHTML = '<tr><td colspan="5">Carregando…</td></tr>';
    try {
      const lista = await api.get('/api/admin/dispositivos');
      if (!lista.length) { tbody.innerHTML = '<tr><td colspan="5">Nenhum dispositivo registrado.</td></tr>'; return; }
      tbody.innerHTML = lista.map(d => {
        const btnAtivo = d.ativo
          ? `<button class="btn-text danger" onclick="window._t20_toggleDisp(${d.id}, false)">Desativar</button>`
          : `<button class="btn-text" onclick="window._t20_toggleDisp(${d.id}, true)">Ativar</button>`;
        return `<tr>
          <td>${d.email}</td>
          <td title="${d.fingerprint}">${(d.fingerprint || '—').substring(0, 16)}…</td>
          <td>${d.ultimo_acesso || '—'}</td>
          <td style="text-align:center">${d.ativo ? 'Sim' : 'Não'}</td>
          <td>${btnAtivo}</td>
        </tr>`;
      }).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5">Erro: ${e.message}</td></tr>`;
    }
  }

  window._t20_toggleDisp = async function (did, ativar) {
    if (!confirm(ativar ? 'Ativar este dispositivo?' : 'Desativar este dispositivo? O usuário perderá acesso.')) return;
    try {
      await api.put(`/api/admin/dispositivos/${did}/${ativar ? 'ativar' : 'desativar'}`);
      await carregarDispositivos();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  // --- PERMISSÕES (dinâmicas por papel) ---
  function renderPermHead() {
    const thead = document.getElementById('t20_permHead');
    const nomes = _papeis.map(p => p.nome);
    thead.innerHTML = `<tr>
      <th rowspan="2" style="border-right:2px solid var(--line)">Módulo</th>
      ${nomes.map((n, i) => `<th colspan="2" style="text-align:center;font-size:11.5px;color:var(--ink);font-weight:700${i > 0 ? ';border-left:2px solid var(--line)' : ''}">${n.toUpperCase()}</th>`).join('')}
    </tr><tr>
      ${nomes.map((_, i) => `<th style="text-align:center${i > 0 ? ';border-left:2px solid var(--line)' : ''}">Ver</th><th style="text-align:center">Editar</th>`).join('')}
    </tr>`;
  }

  async function carregarPermissoes() {
    try {
      _permissoes = await api.get('/api/admin/permissoes');
      renderPermissoes();
    } catch (e) {
      document.getElementById('t20_permMsg').textContent = 'Erro: ' + e.message;
    }
  }

  function _perm(papel, modulo, campo) {
    const p = _permissoes.find(x => x.papel === papel && x.modulo === modulo);
    return p ? !!p[campo] : false;
  }

  function renderPermissoes() {
    const tbody = document.getElementById('t20_tbPermissoes');
    const nomes = _papeis.map(p => p.nome);
    tbody.innerHTML = MODULOS.map(mod => {
      const cells = nomes.map((papel, i) => {
        const ver = _perm(papel, mod, 'ver');
        const editar = _perm(papel, mod, 'editar');
        const bL = i > 0 ? 'border-left:2px solid var(--line);' : '';
        return `<td style="text-align:center;${bL}"><input type="checkbox" data-papel="${papel}" data-modulo="${mod}" data-campo="ver" ${ver ? 'checked' : ''} style="width:14px;height:14px"></td>` +
               `<td style="text-align:center"><input type="checkbox" data-papel="${papel}" data-modulo="${mod}" data-campo="editar" ${editar ? 'checked' : ''} style="width:14px;height:14px"></td>`;
      }).join('');
      return `<tr><td style="border-right:2px solid var(--line)">${mod.toUpperCase()}</td>${cells}</tr>`;
    }).join('');
  }

  window._t20_salvarPermissoes = async function () {
    const checks = document.querySelectorAll('#t20_tbPermissoes input[type=checkbox]');
    const mapa = {};
    checks.forEach(c => {
      const k = c.dataset.papel + '|' + c.dataset.modulo;
      if (!mapa[k]) mapa[k] = { papel: c.dataset.papel, modulo: c.dataset.modulo, ver: false, editar: false };
      mapa[k][c.dataset.campo] = c.checked;
    });
    const permissoes = Object.values(mapa);
    const msg = document.getElementById('t20_permMsg');
    msg.textContent = 'Salvando…';
    try {
      _permissoes = await api.put('/api/admin/permissoes', { permissoes });
      renderPermissoes();
      msg.textContent = 'Salvo com sucesso.';
      setTimeout(() => { msg.textContent = ''; }, 3000);
    } catch (e) {
      msg.textContent = 'Erro: ' + e.message;
    }
  };

  // --- LOGS ---
  let _allLogs = [];

  window._t20_carregarLogs = async function () {
    const container = document.getElementById('t20_logsContainer');
    const msg = document.getElementById('t20_logsMsg');
    container.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:8px 0">Carregando…</div>';
    msg.textContent = '';
    _logsOffset = 0;
    try {
      _allLogs = await api.get('/api/admin/logs');
      _renderLogs();
    } catch (e) {
      container.innerHTML = `<div style="font-size:12px;color:#b91c1c;padding:8px 0">Erro: ${e.message}</div>`;
    }
  };

  function _filtrarLogs() {
    const texto = (document.getElementById('t20_logsFiltro').value || '').trim().toLowerCase();
    const tipo = (document.getElementById('t20_logsTipo').value || '').toLowerCase();
    return _allLogs.filter(l => {
      if (texto && !(l.email || '').toLowerCase().includes(texto) && !(l.acao || '').toLowerCase().includes(texto) && !(l.detalhes || '').toLowerCase().includes(texto)) return false;
      if (tipo === 'login' && !(l.acao || '').toLowerCase().includes('login')) return false;
      if (tipo === 'logout' && !(l.acao || '').toLowerCase().includes('logout')) return false;
      if (tipo === 'admin' && (l.acao || '').toLowerCase().includes('login')) return false;
      return true;
    });
  }

  function _renderLogs() {
    const container = document.getElementById('t20_logsContainer');
    const btnMais = document.getElementById('t20_logsMais');
    const filtrados = _filtrarLogs();
    const mostrar = filtrados.slice(0, _logsOffset + _LOGS_PAGE);

    if (!filtrados.length) {
      container.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:8px 0">Nenhum log encontrado.</div>';
      btnMais.style.display = 'none';
      return;
    }

    container.innerHTML = mostrar.map(l => {
      const data = l.criado_em || '—';
      const email = l.email || '—';
      const acao = l.acao + (l.detalhes ? ' — ' + l.detalhes : '');
      return `<div style="display:flex;gap:12px;padding:5px 0;border-bottom:1px solid var(--line);font-size:12.5px;align-items:baseline">
        <span style="font-size:11px;color:var(--muted);min-width:130px;flex-shrink:0">${data}</span>
        <span style="font-size:11px;color:var(--accent,#2563eb);min-width:160px;flex-shrink:0">${email}</span>
        <span style="font-size:12px">${acao}</span>
      </div>`;
    }).join('');

    btnMais.style.display = mostrar.length < filtrados.length ? '' : 'none';
  }

  window._t20_carregarMaisLogs = function () {
    _logsOffset += _LOGS_PAGE;
    _renderLogs();
  };

  // filtros: re-renderizar ao digitar/selecionar
  document.addEventListener('DOMContentLoaded', () => {
    const filtro = document.getElementById('t20_logsFiltro');
    const tipo = document.getElementById('t20_logsTipo');
    if (filtro) filtro.addEventListener('input', () => { _logsOffset = 0; _renderLogs(); });
    if (tipo) tipo.addEventListener('change', () => { _logsOffset = 0; _renderLogs(); });
  });

  // --- VISIBILIDADE da aba Admin no sidebar ---
  function _atualizarVisibilidadeAdmin() {
    const el = document.querySelector('.sidebar-cat[data-tab="20"]');
    if (el) el.style.display = state.isMaster ? '' : 'none';
    const btn = document.querySelector('.tab-btn[data-tab="20"]');
    if (btn) btn.style.display = state.isMaster ? '' : 'none';
  }

  const _origCarregarPerfil = window._carregarPerfilRemoto;
  if (_origCarregarPerfil) {
    window._carregarPerfilRemoto = async function () {
      await _origCarregarPerfil();
      _atualizarVisibilidadeAdmin();
    };
  }

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(_atualizarVisibilidadeAdmin, 2000);
  });
})();
