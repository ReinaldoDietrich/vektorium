let t4_editandoId = null;
let t4_catalogos = null;
let t4_projetoAtual = null;
let t4_fechada = false;

const T4_CAMPOS = ['sistema_id', 'linha_succao', 'linha_eletrica', 'setor_id', 'modelo_expositor_id'];

function initTela4() {
  document.getElementById('c4_btnNovo').addEventListener('click', t4_novoExpositor);
  document.getElementById('c4_btnNovoTopo').addEventListener('click', () => { t4_novoExpositor(); t4_abrirForm(); });
  document.getElementById('c4_btnFecharForm').addEventListener('click', t4_fecharForm);
  document.getElementById('c4_btnSalvar').addEventListener('click', t4_salvarExpositor);
  document.getElementById('c4_btnExcluir').addEventListener('click', t4_excluirExpositor);
  document.getElementById('c4_btnAddModulo').addEventListener('click', t4_addModulo);
  document.getElementById('c4_banco_id').addEventListener('change', t4_onBancoChange);
  document.getElementById('c4_modelo_expositor_id').addEventListener('change', t4_previewCarga);
  document.getElementById('c4_btnEditar').addEventListener('click', t4_editarEntidade);
  document.addEventListener('projeto-changed', t4_onProjetoChanged);
}

function t4_abrirForm() { document.getElementById('c4_formWrap').style.display = 'block'; }
function t4_fecharForm() { document.getElementById('c4_formWrap').style.display = 'none'; }

async function t4_carregarCatalogos() {
  const [setores, bancos] = await Promise.all([api.get('/api/catalogos/setores-expositor'), api.get('/api/catalogos/bancos-expositor')]);
  t4_catalogos = { setores, bancos };
  return t4_catalogos;
}

async function t4_onProjetoChanged() {
  const semProjeto = !state.projetoId;
  document.getElementById('t4_aviso_sem_projeto').style.display = semProjeto ? 'block' : 'none';
  document.getElementById('t4_conteudo').style.display = semProjeto ? 'none' : 'block';
  if (semProjeto) return;
  t4_projetoAtual = await api.get(`/api/projetos/${state.projetoId}`);
  const cat = await t4_carregarCatalogos();
  popularSelectsSistema([document.getElementById('c4_sistema_id')]);
  populateSelect(document.getElementById('c4_setor_id'), cat.setores, 'id', 'nome', '—');
  populateSelect(document.getElementById('c4_banco_id'), cat.bancos, 'id', 'nome', '—');
  t4_novoExpositor();
  t4_fecharForm();
  t4_carregarLista();
}

function t4_onBancoChange() {
  const banco = t4_catalogos.bancos.find(b => String(b.id) === document.getElementById('c4_banco_id').value);
  populateSelect(document.getElementById('c4_modelo_expositor_id'), banco ? banco.modelos : [], 'id', 'nome', '—');
  t4_previewCarga();
}

function t4_previewCarga() {
  const banco = t4_catalogos.bancos.find(b => String(b.id) === document.getElementById('c4_banco_id').value);
  const modelo = banco && banco.modelos.find(m => String(m.id) === document.getElementById('c4_modelo_expositor_id').value);
  if (!modelo) { document.getElementById('c4_cargaExpositor').value = '—'; return; }
  const usar28 = t4_projetoAtual && t4_projetoAtual.condicao_salao && t4_projetoAtual.condicao_salao.startsWith('28');
  document.getElementById('c4_cargaExpositor').value = fmtKcal(usar28 ? modelo.carga_termica_28 : modelo.carga_termica_25);
}

function t4_novoExpositor() {
  t4_editandoId = null;
  t4_fechada = false;
  T4_CAMPOS.forEach(c => { const el = document.getElementById('c4_' + c); if (el && el.tagName !== 'SELECT') el.value = ''; });
  document.getElementById('c4_modelo_expositor_id').innerHTML = '<option value="">—</option>';
  document.getElementById('c4_cargaExpositor').value = '—';
  document.getElementById('c4_modulacaoResultado').textContent = '—';
  document.getElementById('c4_modulosList').innerHTML = '';
  document.getElementById('c4_btnExcluir').style.display = 'none';
  t4_aplicarEstadoFechada(null);
}

async function t4_salvarExpositor() {
  const payload = {};
  T4_CAMPOS.forEach(c => { const el = document.getElementById('c4_' + c); payload[c] = el.value ? Number(el.value) : null; });
  if (!payload.sistema_id) { alert('Selecione o Sistema.'); return; }
  let resultado;
  if (t4_editandoId) resultado = await api.put(`/api/expositores/${t4_editandoId}`, payload);
  else resultado = await api.post('/api/expositores', payload);
  t4_editandoId = resultado.id;
  document.getElementById('c4_btnExcluir').style.display = 'inline-block';
  await t4_abrirExpositor(t4_editandoId);
  t4_carregarLista();
}

async function t4_excluirExpositor() {
  if (!t4_editandoId) return;
  if (!confirm('Excluir este expositor?')) return;
  await api.del(`/api/expositores/${t4_editandoId}`);
  t4_novoExpositor();
  t4_carregarLista();
}

async function t4_abrirExpositor(id) {
  const e = await api.get(`/api/expositores/${id}`);
  t4_editandoId = id;
  t4_fechada = !!e.fechada;
  T4_CAMPOS.forEach(c => { document.getElementById('c4_' + c).value = e[c] ?? ''; });
  if (e.modelo_expositor_id) {
    const banco = t4_catalogos.bancos.find(b => b.modelos.some(m => m.id === e.modelo_expositor_id));
    if (banco) {
      document.getElementById('c4_banco_id').value = banco.id;
      populateSelect(document.getElementById('c4_modelo_expositor_id'), banco.modelos, 'id', 'nome', '—');
      document.getElementById('c4_modelo_expositor_id').value = e.modelo_expositor_id;
    }
  }
  document.getElementById('c4_cargaExpositor').value = fmtKcal(e.carga_termica);
  document.getElementById('c4_modulacaoResultado').textContent = e.modulacao;
  document.getElementById('c4_btnExcluir').style.display = 'inline-block';
  t4_renderModulos(e.modulos);
  t4_aplicarEstadoFechada(e);
  t4_abrirForm();
}

function t4_aplicarEstadoFechada(e) {
  const wrap = document.getElementById('c4_formWrap');
  const btnSalvar = document.getElementById('c4_btnSalvar');
  const btnEditar = document.getElementById('c4_btnEditar');
  const barraFechada = document.getElementById('c4_barraFechada');
  const barraDesatualizada = document.getElementById('c4_barraDesatualizada');
  if (t4_fechada) {
    wrap.classList.add('entidade-fechada');
    btnSalvar.style.display = 'none';
    btnEditar.style.display = 'inline-block';
    barraFechada.style.display = 'flex';
    barraDesatualizada.style.display = e && e.calculo_desatualizado ? 'flex' : 'none';
  } else {
    wrap.classList.remove('entidade-fechada');
    btnSalvar.style.display = '';
    btnEditar.style.display = 'none';
    barraFechada.style.display = 'none';
    barraDesatualizada.style.display = 'none';
  }
}

async function t4_editarEntidade() {
  if (!t4_editandoId) return;
  await api.post(`/api/expositores/${t4_editandoId}/editar`, {});
  t4_fechada = false;
  t4_aplicarEstadoFechada(null);
  await t4_carregarLista();
}

function t4_renderModulos(modulos) {
  const el = document.getElementById('c4_modulosList');
  if (!modulos || modulos.length === 0) { el.innerHTML = ''; return; }
  el.innerHTML = '<table class="list"><tbody>' + modulos.map(m =>
    `<tr><td>${m.qtd}x ${m.comprimento_modulo}m</td><td style="text-align:right;"><span class="btn-text danger" data-excluir-modulo="${m.id}">Excluir</span></td></tr>`).join('') + '</tbody></table>';
  el.querySelectorAll('[data-excluir-modulo]').forEach(b => b.addEventListener('click', async () => {
    if (!confirm('Excluir este módulo?')) return;
    try {
      await api.del(`/api/expositores/${t4_editandoId}/modulos/${b.dataset.excluirModulo}`);
      t4_abrirExpositor(t4_editandoId);
    } catch (err) { alert('Erro ao excluir módulo: ' + err.message); }
  }));
}

async function t4_addModulo() {
  if (!t4_editandoId) { alert('Salve o expositor primeiro.'); return; }
  const comprimento_modulo = parseNumBR(document.getElementById('c4_modCompr').value.replace(',', '.'));
  const qtd = Number(document.getElementById('c4_modQtd').value) || 1;
  await api.post(`/api/expositores/${t4_editandoId}/modulos`, { comprimento_modulo, qtd });
  t4_abrirExpositor(t4_editandoId);
}

async function t4_carregarLista() {
  const el = document.getElementById('c4_lista');
  if (!state.projetoId) { el.innerHTML = ''; return; }
  const todas = await api.get(`/api/expositores?projeto_id=${state.projetoId}`);
  if (todas.length === 0) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Nenhum expositor cadastrado ainda.</div>'; return; }
  el.innerHTML = todas.map(e => {
    let badge = '';
    if (e.fechada) {
      badge = e.calculo_desatualizado
        ? '<span class="badge-fechada desatualizada">desatualizado</span>'
        : '<span class="badge-fechada ok">fechada</span>';
    }
    return `
    <div class="lista-card" data-exp="${e.id}">
      <div class="nome">${e.codigo} — ${e.modelo_nome || '(sem modelo)'} ${e.setor_nome ? '- ' + e.setor_nome : ''}${badge}</div>
      <div class="meta">Carga: ${fmtKcal(e.carga_termica)} · ${e.modulacao}</div>
    </div>`;
  }).join('');
  el.querySelectorAll('[data-exp]').forEach(card => card.addEventListener('click', () => t4_abrirExpositor(Number(card.dataset.exp))));
}

window.initTela4 = initTela4;
window.telaShowHandlers[4] = async () => {
  if (!state.projetoId) return;
  await carregarSistemasDoProjeto();
  popularSelectsSistema([document.getElementById('c4_sistema_id')]);
  t4_carregarLista();
};
document.addEventListener('DOMContentLoaded', initTela4);
