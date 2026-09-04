// Tela 13 — Proposta Comercial. Reúne dados do projeto (leitura), campos manuais (default por
// usuário), seleção de conteúdo (árvore de Ids), tabelas técnicas e tabela de exceções, e gera o
// .docx sobre o papel de carta. Nunca exibe "Flexbox" — o rótulo é sempre "empresa contratada".

// Obs.: tipo_painel NÃO é campo manual — é puxado da Tela 7 (só leitura), preenchido em t19_carregar.
const T19_CAMPOS = {
  t19_titulo: 'titulo_fornecimento', t19_empresa: 'empresa_contratada',
  t19_dias: 'dias_proposta', t19_garantia: 'meses_garantia',
  t19_embEquip: 'embarque_equipamentos', t19_embIso: 'embarque_isopainel',
  t19_vendNome: 'vendedor_nome', t19_vendCargo: 'vendedor_cargo',
  t19_vendTel: 'vendedor_telefone', t19_vendEmail: 'vendedor_email',
  // Dados de Faturamento (dados do usuário para receber o pagamento)
  t19_fatRazao: 'fat_razao_social', t19_fatCnpj: 'fat_cnpj',
  t19_fatIscMun: 'fat_insc_municipal', t19_fatIscEst: 'fat_insc_estadual',
  t19_fatEndereco: 'fat_endereco', t19_fatCidadeUf: 'fat_cidade_uf',
  t19_fatBanco: 'fat_banco', t19_fatAgencia: 'fat_agencia',
  t19_fatConta: 'fat_conta', t19_fatPix: 'fat_pix',
};

let t19_ctx = null;
let t19_plantaPath = null;

function initTela13Proposta() {
  window.telaShowHandlers[19] = t19_carregar;
  document.addEventListener('DOMContentLoaded', () => {
    const g = document.getElementById('t19_btnGerar');
    if (g) g.addEventListener('click', t19_gerar);
    const s = document.getElementById('t19_btnSalvarDefaults');
    if (s) s.addEventListener('click', t19_salvarDefaults);
    t19_ligarUpload('t19_papelCarta', 'papel_carta', 't19_papelCartaAtual');
    t19_ligarUpload('t19_logo', 'logo', 't19_logoAtual');
    t19_ligarUpload('t19_planta', 'planta', 't19_plantaAtual');
    t19_ligarSelecaoArvore();
    t19_ligarMascaras();
  });
}

// Máscaras de formatação (mesmo padrão da Tela 1): CNPJ, telefone e campos só-dígitos.
function t19_maskCnpj(el) {
  const d = el.value.replace(/\D/g, '').slice(0, 14); let o = d;
  if (d.length > 12) o = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2}).*/, '$1.$2.$3/$4-$5');
  else if (d.length > 8) o = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{0,4}).*/, '$1.$2.$3/$4');
  else if (d.length > 5) o = d.replace(/^(\d{2})(\d{3})(\d{0,3}).*/, '$1.$2.$3');
  else if (d.length > 2) o = d.replace(/^(\d{2})(\d{0,3}).*/, '$1.$2');
  el.value = o;
}
function t19_maskTel(el) {
  const d = el.value.replace(/\D/g, '').slice(0, 11); let o = d;
  if (d.length > 10) o = d.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3');
  else if (d.length > 6) o = d.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
  else if (d.length > 2) o = d.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
  else if (d.length > 0) o = d.replace(/^(\d{0,2}).*/, '($1');
  el.value = o;
}
function t19_maskDigitos(el) { el.value = el.value.replace(/\D/g, ''); }
function t19_ligarMascaras() {
  const on = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener('input', () => fn(e)); };
  on('t19_fatCnpj', t19_maskCnpj);
  on('t19_vendTel', t19_maskTel);
  ['t19_dias', 't19_garantia', 't19_embEquip', 't19_embIso'].forEach(id => on(id, t19_maskDigitos));
}

async function t19_carregar() {
  const semProjeto = document.getElementById('t19_semProjeto');
  const conteudo = document.getElementById('t19_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';
  document.getElementById('t19_msg').textContent = 'Carregando…';

  t19_ctx = await api.get(`/api/proposta/contexto?projeto_id=${state.projetoId}`);
  const p = t19_ctx.projeto;
  document.getElementById('t19_projetoInfo').innerHTML =
    `<b>${p.codigo_revisao}</b> · ${p.razao_social || p.cliente || '—'} · ${p.cidade_estado} · A/C ${p.contato || '—'}`;

  // Campos manuais (default por usuário)
  const d = t19_ctx.defaults || {};
  for (const [id, chave] of Object.entries(T19_CAMPOS)) {
    document.getElementById(id).value = d[chave] || '';
  }
  // Tipo de painel: automático da Tela 7 (só leitura).
  document.getElementById('t19_tipoPainel').value = p.tipo_painel || '';
  document.getElementById('t19_papelCartaAtual').textContent = d.papel_carta_path ? `Atual: ${d.papel_carta_path}` : 'Usando papel de carta padrão.';
  document.getElementById('t19_logoAtual').textContent = d.logo_path ? `Atual: ${d.logo_path}` : 'Sem logomarca enviada.';
  document.getElementById('t19_plantaAtual').textContent = t19_plantaPath ? `Atual: ${t19_plantaPath}` : 'Nenhuma imagem de planta enviada.';
  document.getElementById('t19_exEmpresaHdr').textContent = d.empresa_contratada || 'Empresa contratada';

  t19_renderTabelas();
  t19_renderArvore();
  t19_renderExcecoes();
  document.getElementById('t19_msg').textContent = '';
}

function t19_renderTabelas() {
  const box = document.getElementById('t19_tabelas');
  box.innerHTML = (t19_ctx.tabelas || []).map(t => {
    const disp = t.disponivel !== false;
    const checked = disp ? 'checked' : '';
    const disabled = disp ? '' : 'disabled';
    const estilo = disp ? '' : 'opacity:0.45;cursor:not-allowed;';
    const hint = disp ? '' : ' (sem dados)';
    return `<label class="checkrow" style="white-space:nowrap;${estilo}"><input type="checkbox" class="t19-tab" data-chave="${t.chave}" ${checked} ${disabled}> ${t.rotulo}${hint}</label>`;
  }).join('');
}

function t19_renderExcecoes() {
  const tb = document.getElementById('t19_excecoes');
  tb.innerHTML = (t19_ctx.excecoes_padrao || []).map((r, i) => `
    <tr>
      <td>${r.atividade}</td>
      <td style="text-align:center;"><input type="checkbox" class="t19-ex-emp" data-i="${i}" ${r.empresa ? 'checked' : ''}></td>
      <td style="text-align:center;"><input type="checkbox" class="t19-ex-cli" data-i="${i}" ${r.cliente ? 'checked' : ''}></td>
    </tr>`).join('');
}

function t19_renderArvore() {
  const projeto = new Set(t19_ctx.ids_projeto || []);
  const comTexto = new Set(t19_ctx.ids_com_texto || []);
  const nos = (t19_ctx.arvore_ids || []).slice().sort((a, b) =>
    a.codigo.localeCompare(b.codigo, undefined, { numeric: true }));
  const box = document.getElementById('t19_arvore');
  box.innerHTML = nos.map(n => {
    const nivel = String(n.codigo).split('.').length - 1;
    const marcado = projeto.has(n.codigo);
    const temTexto = comTexto.has(n.codigo);
    return `<div style="padding-left:${nivel * 16}px;line-height:1.7;">
      <label class="checkrow"><input type="checkbox" class="t19-id" data-codigo="${n.codigo}" ${marcado ? 'checked' : ''}>
      <span style="color:#6b7280;">${n.codigo}</span> ${n.nome}${temTexto ? ' <span class="sub" style="color:#15803d;">· texto</span>' : ''}</label>
    </div>`;
  }).join('');
  box.querySelectorAll('.t19-id').forEach(cb => {
    cb.addEventListener('change', () => {
      const prefixo = cb.dataset.codigo + '.';
      box.querySelectorAll('.t19-id').forEach(filho => {
        if (filho.dataset.codigo.startsWith(prefixo)) filho.checked = cb.checked;
      });
    });
  });
}

function t19_ligarSelecaoArvore() {
  const marca = (fn) => document.querySelectorAll('.t19-id').forEach(fn);
  const btn = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener('click', fn); };
  btn('t19_idsTodos', () => marca(c => c.checked = true));
  btn('t19_idsNenhum', () => marca(c => c.checked = false));
  btn('t19_idsProjeto', () => { const s = new Set(t19_ctx.ids_projeto || []); marca(c => c.checked = s.has(c.dataset.codigo)); });
  btn('t19_idsTexto', () => { const s = new Set(t19_ctx.ids_com_texto || []); marca(c => c.checked = s.has(c.dataset.codigo)); });
}

function t19_ligarUpload(inputId, tipo, alvoId) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  inp.addEventListener('change', async () => {
    if (!inp.files.length) return;
    document.getElementById(alvoId).textContent = 'Enviando…';
    try {
      const r = await api.upload(`/api/proposta/upload?tipo=${tipo}`, inp.files[0]);
      if (tipo === 'planta') t19_plantaPath = r.path;
      document.getElementById(alvoId).textContent = `Atual: ${r.path}`;
    } catch (e) {
      document.getElementById(alvoId).textContent = 'Falha no envio: ' + e.message;
    }
  });
}

function t19_coletarCampos() {
  const campos = {};
  for (const [id, chave] of Object.entries(T19_CAMPOS)) {
    campos[chave] = document.getElementById(id).value.trim();
  }
  return campos;
}

function t19_coletarOpcoes() {
  const tabelas = {};
  document.querySelectorAll('.t19-tab').forEach(c => { tabelas[c.dataset.chave] = c.checked; });
  const ids = [];
  document.querySelectorAll('.t19-id:checked').forEach(c => ids.push(c.dataset.codigo));
  const excecoes = (t19_ctx.excecoes_padrao || []).map((r, i) => ({
    atividade: r.atividade,
    empresa: document.querySelector(`.t19-ex-emp[data-i="${i}"]`).checked,
    cliente: document.querySelector(`.t19-ex-cli[data-i="${i}"]`).checked,
  }));
  return {
    campos: t19_coletarCampos(), tabelas, ids_selecionados: ids, excecoes,
    planta_path: t19_plantaPath, orcamento_filtro: t19_filtroOrcamento(),
  };
}

// Lê o filtro AO VIVO da Tabela de Orçamento da Tela 10 (mesmos controles), para a proposta sair
// idêntica ao que está na tela. Se a Tela 10 nunca foi aberta, usa o padrão dos próprios controles.
function t19_filtroOrcamento() {
  const g = (id) => document.getElementById(id);
  return {
    agrupar: g('t17_orcAgrupar') ? g('t17_orcAgrupar').value : 'bloco_cc',
    exibir: g('t17_orcExibir') ? g('t17_orcExibir').value : 'individual',
    ocultar_qtd: g('t17_orcOcultarQtd') ? g('t17_orcOcultarQtd').checked : false,
  };
}

async function t19_salvarDefaults() {
  const msg = document.getElementById('t19_msg');
  msg.textContent = 'Salvando padrões…';
  try {
    await api.put('/api/proposta/defaults', t19_coletarCampos());
    document.getElementById('t19_exEmpresaHdr').textContent =
      document.getElementById('t19_empresa').value.trim() || 'Empresa contratada';
    msg.textContent = 'Padrões salvos.';
  } catch (e) { msg.textContent = 'Erro ao salvar: ' + e.message; }
}

async function t19_gerar() {
  const msg = document.getElementById('t19_msg');
  if (!state.projetoId) { msg.textContent = 'Nenhum projeto ativo. Selecione um projeto primeiro.'; return; }
  msg.textContent = 'Gerando proposta… (pode levar alguns segundos)';
  try {
    // Salva na Pasta de Salvamento do projeto (ou Downloads) — o backend devolve {salvo_em}.
    const r = await fetch(`/api/proposta/gerar?projeto_id=${state.projetoId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(t19_coletarOpcoes()),
    });
    if (!r.ok) {
      let detalhe;
      try { const j = await r.json(); detalhe = j.detail || JSON.stringify(j); } catch (_) { detalhe = await r.text(); }
      throw new Error(detalhe || `HTTP ${r.status}`);
    }
    const dados = await r.json();
    if (dados.aberto) {
      msg.textContent = 'Proposta aberta para visualização. Salve manualmente onde desejar.';
    } else if (dados.salvo_em) {
      msg.textContent = `Proposta salva em: ${dados.salvo_em}`;
    } else {
      msg.textContent = 'Proposta gerada.';
    }
  } catch (e) { msg.textContent = 'Erro ao gerar: ' + e.message; }
}

window.initTela13Proposta = initTela13Proposta;
initTela13Proposta();
