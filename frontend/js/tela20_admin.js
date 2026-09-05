// Tela 20 — Administração (master only)
(function () {
  let carregou = false;

  window.telaShowHandlers[20] = async function () {
    if (!AUTH.logado()) { document.getElementById('t20_corpo').innerHTML = '<p>Faça login para acessar.</p>'; return; }
    if (carregou) return;
    carregou = true;
    await carregarPerfil();
    if (!state.isMaster) { document.getElementById('t20_corpo').innerHTML = '<p>Acesso restrito a administradores.</p>'; return; }
    document.getElementById('t20_painelMaster').style.display = 'block';
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
      console.error('admin perfil:', e);
    }
  }

  // --- USUARIOS ---
  let _usuarios = [];

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
    tbody.innerHTML = _usuarios.map(u => {
      const outroP = u.papel === 'master' ? 'comum' : 'master';
      const btnPapel = `<button class="btn-sm" onclick="window._t20_alterarPapel('${u.id}','${outroP}')">→ ${outroP}</button>`;
      const btnVit = u.assinatura_plano === 'vitalicio' && u.assinatura_status === 'active'
        ? `<button class="btn-sm btn-danger" onclick="window._t20_revogar('${u.id}')">Revogar</button>`
        : `<button class="btn-sm btn-ok" onclick="window._t20_concederVitalicia('${u.id}')">Conceder vitalícia</button>`;
      return `<tr>
        <td>${u.email}</td>
        <td>${u.nome || '—'}</td>
        <td>${u.papel}</td>
        <td>${btnPapel}</td>
        <td>${u.assinatura_status || '—'}</td>
        <td>${u.assinatura_plano || '—'}</td>
        <td>${u.assinatura_vence_em || '—'}</td>
        <td>${btnVit}</td>
      </tr>`;
    }).join('');
  }

  window._t20_alterarPapel = async function (uid, novoPapel) {
    if (!confirm(`Alterar papel para "${novoPapel}"?`)) return;
    try {
      await api.put(`/api/admin/usuarios/${uid}/papel`, { papel: novoPapel });
      await carregarUsuarios();
    } catch (e) { alert('Erro: ' + e.message); }
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
    tbody.innerHTML = '<tr><td colspan="6">Carregando…</td></tr>';
    try {
      const lista = await api.get('/api/admin/dispositivos');
      if (!lista.length) { tbody.innerHTML = '<tr><td colspan="6">Nenhum dispositivo registrado.</td></tr>'; return; }
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
      tbody.innerHTML = `<tr><td colspan="6">Erro: ${e.message}</td></tr>`;
    }
  }

  window._t20_toggleDisp = async function (did, ativar) {
    try {
      await api.put(`/api/admin/dispositivos/${did}/${ativar ? 'ativar' : 'desativar'}`);
      await carregarDispositivos();
    } catch (e) { alert('Erro: ' + e.message); }
  };

  // --- PERMISSÕES ---
  const MODULOS = [
    'cadastro', 'camara_completo', 'camara_simples', 'expositor',
    'compilacao_linhas', 'rack_paralelo', 'paineis_portas',
    'compilacao_geral', 'consumo_eletrico', 'resumo_materiais',
    'luminotecnico', 'comparativo_revisoes', 'proposta_comercial',
    'catalogo_forcadores', 'catalogo_uc', 'catalogo_condensadores',
    'catalogo_comercial', 'configuracoes'
  ];
  const PAPEIS = ['master', 'comum'];
  let _permissoes = [];

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
    tbody.innerHTML = MODULOS.map(mod => {
      const cells = PAPEIS.map(papel => {
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
