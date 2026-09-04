// Navegação por teclado padrão do app inteiro (pedido do usuário 2026-08-06): Seta Baixo e Enter
// pulam pro campo de baixo (mesma coluna, se estiver numa tabela); Seta Cima pula pro campo de
// cima. Um listener global só, por delegação — funciona em qualquer tela sem precisar registrar
// nada tela por tela, inclusive telas novas que venham a existir depois.
//
// Esquerda/Direita ficam com o comportamento NATIVO do navegador (mover cursor dentro do texto)
// — sequestrar essas quebraria a edição normal de texto no meio de uma palavra. Enter dentro de
// <textarea> também fica nativo (quebra de linha), não pula campo.
(function () {
  const SELETOR_CAMPO = 'input:not([type=hidden]):not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled])';

  function campoNavegavel(el) {
    return !!(el && el.matches && el.matches(SELETOR_CAMPO));
  }

  // Dentro de tabela: mesma coluna (índice do <td>/<th>), linha visível acima/abaixo. Pula linhas
  // sem campo nenhum naquela coluna (ex.: linha de "Total") até achar uma que tenha.
  function moverEmTabela(el, direcao) {
    const tr = el.closest('tr');
    const table = el.closest('table');
    if (!tr || !table) return false;
    const td = el.closest('td, th');
    const linhas = [...table.querySelectorAll('tr')].filter(r => r.offsetParent !== null);
    const idxLinha = linhas.indexOf(tr);
    const idxCol = td ? [...tr.children].indexOf(td) : -1;
    if (idxLinha === -1 || idxCol === -1) return false;
    for (let prox = idxLinha + direcao; prox >= 0 && prox < linhas.length; prox += direcao) {
      const tdAlvo = linhas[prox].children[idxCol];
      const campo = tdAlvo && tdAlvo.querySelector(SELETOR_CAMPO);
      if (campo) { campo.focus(); if (campo.select) campo.select(); return true; }
    }
    return false;
  }

  // Fora de tabela: ordem do DOM dentro do form/painel mais próximo, restrito pra não pular pra
  // outra seção da tela (ex.: do formulário de cadastro pra dentro de uma tabela mais abaixo).
  function moverForaTabela(el, direcao) {
    const container = el.closest('form, .grid, .body-pad') || document.body;
    // offsetParent não é null pra campos atrás de um overlay com visibility:hidden (ex.: tela de
    // login sobre o app) — sem essa checagem extra, Enter num campo fora de form/.grid/.body-pad
    // (como os da tela de login) pode levar o foco pra dentro do app escondido atrás dela.
    const campos = [...container.querySelectorAll(SELETOR_CAMPO)].filter(c =>
      c.offsetParent !== null && getComputedStyle(c).visibility !== 'hidden');
    const idx = campos.indexOf(el);
    if (idx === -1) return false;
    const alvo = campos[idx + direcao];
    if (!alvo) return false;
    alvo.focus();
    if (alvo.select) alvo.select();
    return true;
  }

  function mover(el, direcao) {
    return el.closest('table') ? moverEmTabela(el, direcao) : moverForaTabela(el, direcao);
  }

  document.addEventListener('keydown', (e) => {
    if (!campoNavegavel(e.target) || e.defaultPrevented) return;
    if (e.key === 'ArrowDown' || (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA')) {
      if (mover(e.target, 1)) e.preventDefault();
    } else if (e.key === 'ArrowUp') {
      if (mover(e.target, -1)) e.preventDefault();
    }
  });
})();
