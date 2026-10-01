function montarHtmlImpressao(conteudoHtml) {
  return '<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n' +
    '<style>\n' +
    '@page { size: A4; margin: 30mm 20mm 20mm 30mm; }\n' +
    'body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #000; background: #fff; line-height: 1.4; margin: 0; padding: 0; }\n' +
    '* { overflow: visible !important; max-width: none !important; box-sizing: border-box; }\n' +
    'table { border-collapse: collapse; width: 100% !important; table-layout: auto !important; margin-bottom: 14pt; page-break-inside: auto; break-inside: auto; }\n' +
    'thead { display: table-header-group; }\n' +
    'tfoot { display: table-footer-group; }\n' +
    'tr { page-break-inside: avoid; break-inside: avoid; }\n' +
    'th, td { border: 1px solid #333; padding: 3pt 5pt; text-align: left; font-size: 9pt; vertical-align: top; word-wrap: break-word; overflow-wrap: break-word; }\n' +
    'th { background: #e8e8e8 !important; font-weight: bold; -webkit-print-color-adjust: exact; print-color-adjust: exact; }\n' +
    'td[colspan] { text-align: center; }\n' +
    '[style*="background"] { -webkit-print-color-adjust: exact; print-color-adjust: exact; }\n' +
    'h2 { font-size: 13pt; margin: 14pt 0 8pt; }\n' +
    'h3 { font-size: 11pt; margin: 10pt 0 6pt; }\n' +
    'p { margin: 4pt 0; font-size: 9pt; }\n' +
    '.small { font-size: 8pt; }\n' +
    '::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }\n' +
    '</style></head><body>\n' + conteudoHtml + '\n</body></html>';
}

function extrairConteudoIds(ids) {
  var html = '';
  for (var i = 0; i < ids.length; i++) {
    var el = document.getElementById(ids[i]);
    if (!el) continue;
    var clone = el.cloneNode(true);

    var remover = clone.querySelectorAll('button, input[type="button"], .btn, .btn-wide, .btn-text, select, .no-print');
    for (var j = 0; j < remover.length; j++) remover[j].remove();

    var todos = clone.querySelectorAll('*');
    for (var k = 0; k < todos.length; k++) {
      var s = todos[k].style;
      if (s.overflowX) s.overflowX = 'visible';
      if (s.overflowY) s.overflowY = 'visible';
      if (s.overflow) s.overflow = 'visible';
      if (s.maxWidth) s.maxWidth = 'none';
      if (s.maxHeight) s.maxHeight = 'none';
      if (s.minWidth) s.minWidth = '0';
      if (s.height && s.height !== 'auto') s.height = 'auto';
      if (s.position === 'sticky' || s.position === 'fixed') s.position = 'static';

      if (todos[k].tagName === 'TABLE') {
        s.width = '100%';
        s.tableLayout = 'auto';
        s.maxWidth = 'none';
      }

      if (todos[k].tagName === 'DIV' || todos[k].tagName === 'SECTION') {
        s.width = '';
        s.maxWidth = '';
        s.minWidth = '';
      }
    }

    clone.style.overflow = 'visible';
    clone.style.maxWidth = 'none';
    clone.style.width = '100%';

    html += clone.innerHTML;
  }
  return html;
}

async function abrirImpressao(conteudo) {
  var html;
  if (Array.isArray(conteudo)) {
    html = extrairConteudoIds(conteudo);
  } else {
    html = conteudo;
  }
  if (!html || !html.trim()) {
    alert('Nenhum conteúdo para imprimir.');
    return;
  }
  var doc = montarHtmlImpressao(html);
  if (window.vektorium && typeof window.vektorium.abrirImpressao === 'function') {
    var resultado = await window.vektorium.abrirImpressao(doc);
    if (resultado && !resultado.ok) {
      alert('Erro ao gerar PDF: ' + (resultado.erro || 'desconhecido'));
    }
  } else {
    var w = window.open('', '_blank');
    w.document.write(doc);
    w.document.close();
    w.print();
  }
}
