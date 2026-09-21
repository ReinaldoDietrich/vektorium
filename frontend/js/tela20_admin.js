// Tela 20 — Administração (papéis dinâmicos)
(function () {
  let carregou = false;
  let _papeis = [];
  let _usuarios = [];
  let _permissoes = [];

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
      const btnEdit = `<button class="btn-sm" onclick="window._t20_editarPapel(${p.id})">Editar</button>`;
      const btnDel = protegido ? '' : ` <button class="btn-sm btn-danger" onclick="window._t20_excluirPapel(${p.id},'${p.nome}')">Excluir</button>`;
      return `<tr data-papel-id="${p.id}">
        <td><span class="t20-papel-nome">${p.nome}</span></td>
        <td><span class="t20-papel-desc">${p.descricao}</span></td>
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
      renderPermHead();
      await carregarPermissoes();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  // --- USUARIOS ---
  async function carregarUsuarios() {
    const tbody = document.getElementById('t20_tbUsuarios');
    tbody.innerHTML = '<tr><td colspan="8">Carregando…</td></tr>';
    try {
      _usuarios = await api.get('/api/admin/usuarios');
      renderUsuarios();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="8">Erro: ${e.message}</td></tr>`;
    }
  }

  function renderUsuarios() {
    const tbody = document.getElementById('t20_tbUsuarios');
    if (!_usuarios.length) { tbody.innerHTML = '<tr><td colspan="8">Nenhum usuário.</td></tr>'; return; }
    const opcoes = _papeis.map(p => p.nome);
    tbody.innerHTML = _usuarios.map(u => {
      const select = `<select onchange="window._t20_alterarPapel('${u.id}', this.value)">${
        opcoes.map(o => `<option value="${o}"${o === u.papel ? ' selected' : ''}>${o}</option>`).join('')
      }</select>`;
      const btnVit = u.assinatura_plano === 'vitalicio' && u.assinatura_status === 'active'
        ? `<button class="btn-sm btn-danger" onclick="window._t20_revogar('${u.id}')">Revogar</button>`
        : `<button class="btn-sm btn-ok" onclick="window._t20_concederVitalicia('${u.id}')">Conceder vitalícia</button>`;
      return `<tr>
        <td>${u.email}</td>
        <td>${u.nome || '—'}</td>
        <td>${u.papel}</td>
        <td>${select}</td>
        <td>${u.assinatura_status || '—'}</td>
        <td>${u.assinatura_plano || '—'}</td>
        <td>${u.assinatura_vence_em || '—'}</td>
        <td>${btnVit}</td>
      </tr>`;
    }).join('');
  }

  window._t20_alterarPapel = async function (uid, novoPapel) {
    if (!confirm(`Alterar tipo para "${novoPapel}"?`)) {
      renderUsuarios();
      return;
    }
    try {
      await api.put(`/api/admin/usuarios/${uid}/papel`, { papel: novoPapel });
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); renderUsuarios(); }
  };

  window._t20_concederVitalicia = async function (uid) {
    if (!confirm('Conceder assinatura vitalícia?')) return;
    try {
      await api.post(`/api/admin/assinaturas/${uid}/conceder-vitalicia`);
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  window._t20_revogar = async function (uid) {
    if (!confirm('Revogar assinatura deste usuário?')) return;
    try {
      await api.post(`/api/admin/assinaturas/${uid}/revogar`);
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
          ? `<button class="btn-sm btn-danger" onclick="window._t20_toggleDisp(${d.id}, false)">Desativar</button>`
          : `<button class="btn-sm btn-ok" onclick="window._t20_toggleDisp(${d.id}, true)">Ativar</button>`;
        return `<tr>
          <td>${d.email}</td>
          <td title="${d.fingerprint}">${(d.fingerprint || '—').substring(0, 16)}…</td>
          <td>${d.ultimo_acesso || '—'}</td>
          <td>${d.ativo ? 'Sim' : 'Não'}</td>
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
      <th rowspan="2">Módulo</th>
      ${nomes.map(n => `<th colspan="2" style="text-align:center">${n}</th>`).join('')}
    </tr><tr>
      ${nomes.map(() => '<th style="text-align:center">Ver</th><th style="text-align:center">Editar</th>').join('')}
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
      const cells = nomes.map(papel => {
        const ver = _perm(papel, mod, 'ver');
        const editar = _perm(papel, mod, 'editar');
        return `<td style="text-align:center"><input type="checkbox" data-papel="${papel}" data-modulo="${mod}" data-campo="ver" ${ver ? 'checked' : ''}></td>` +
               `<td style="text-align:center"><input type="checkbox" data-papel="${papel}" data-modulo="${mod}" data-campo="editar" ${editar ? 'checked' : ''}></td>`;
      }).join('');
      return `<tr><td>${mod}</td>${cells}</tr>`;
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
