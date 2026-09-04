// Teste — Memorial (busca cruzada de Ids Comerciais, item 1.1 do escopo). Página de teste: mostra
// só o que a busca cruzada achou (foto + texto comercial), deduplicado, sem nenhuma edição aqui —
// edição continua na Tela D e nas seleções do Sistema (Tela 1).

function initTela14() {
  window.telaShowHandlers[14] = t14_carregar;
}

async function t14_carregar() {
  const semProjeto = document.getElementById('t14_semProjeto');
  const conteudo = document.getElementById('t14_conteudo');
  if (!state.projetoId) { semProjeto.style.display = 'block'; conteudo.style.display = 'none'; return; }
  semProjeto.style.display = 'none';
  conteudo.style.display = 'block';

  const r = await api.get(`/api/catalogo-comercial/memorial-teste?projeto_id=${state.projetoId}`);
  if (r.erro) { document.getElementById('t14_itens').innerHTML = `<div class="small" style="color:#b91c1c;">${r.erro}</div>`; return; }

  document.getElementById('t14_idsResolvidos').textContent =
    `Ids resolvidos das seleções do projeto: ${r.ids_resolvidos.length ? r.ids_resolvidos.join(', ') : '— nenhum'}`;

  const el = document.getElementById('t14_itens');
  if (!r.itens.length) {
    el.innerHTML = '<div class="small" style="color:#9ca3af;padding:16px;text-align:center;">Nenhum item da Tela D bate com os Ids resolvidos ainda — cadastre o Id Comercial certo no item correspondente da Tela D.</div>';
    return;
  }
  el.innerHTML = r.itens.map(i => `
    <div style="display:flex;gap:14px;border:1px solid var(--line);border-radius:6px;padding:10px;margin-bottom:10px;">
      <div style="flex-shrink:0;width:140px;">
        ${i.imagem_path ? `<img src="${i.imagem_path}" style="max-width:140px;max-height:100px;border:1px solid var(--line);border-radius:4px;">` : '<span class="small" style="color:#9ca3af;">Sem foto.</span>'}
      </div>
      <div style="flex:1;">
        <div style="font-weight:bold;">${i.nome}${i.fabricante ? ` — ${i.fabricante}` : ''}</div>
        <div class="small" style="color:#6b7280;margin-bottom:4px;">${i.categoria} · Id ${i.id_comercial}</div>
        <div class="small">${i.descricao_comercial || '<span style="color:#9ca3af;">— sem descrição comercial cadastrada —</span>'}</div>
      </div>
    </div>`).join('');
}

window.initTela14 = initTela14;
document.addEventListener('DOMContentLoaded', initTela14);
