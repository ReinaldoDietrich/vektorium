function montarHtmlImpressao(conteudoHtml) {
  return '<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n' +
    '<style>\n' +
    '@page { size: A4 landscape; margin: 15mm 10mm 15mm 10mm; }\n' +
    'body { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #000; background: #fff; line-height: 1.3; margin: 0; padding: 0; }\n' +
    '* { overflow: visible !important; max-width: none !important; max-height: none !important; box-sizing: border-box; }\n' +
    'table { border-collapse: collapse; width: 100% !important; table-layout: fixed !important; margin-bottom: 10pt; page-break-inside: auto; break-inside: auto; }\n' +
    'thead { display: table-header-group; }\n' +
    'tfoot { display: table-footer-group; }\n' +
    'tr { page-break-inside: avoid; break-inside: avoid; }\n' +
    'th, td { border: 1px solid #333; padding: 2pt 3pt; text-align: left; font-size: 7pt; vertical-align: top; word-wrap: break-word; overflow-wrap: break-word; white-space: normal !important; }\n' +
    'th { background: #e8e8e8 !important; font-weight: bold; -webkit-print-color-adjust: exact; print-color-adjust: exact; }\n' +
    'td[colspan] { text-align: center; }\n' +
    '[style*="background"] { -webkit-print-color-adjust: exact; print-color-adjust: exact; }\n' +
    'h2 { font-size: 12pt; margin: 10pt 0 6pt; }\n' +
    'h3 { font-size: 10pt; margin: 8pt 0 4pt; }\n' +
    'p { margin: 4pt 0; font-size: 8pt; }\n' +
    '.small { font-size: 7pt; }\n' +
    '.obs-impressao { white-space: pre-wrap; border: 1px solid #999; padding: 6pt 8pt; font-size: 8pt; margin-top: 8pt; }\n' +
    '::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }\n' +
    '</style></head><body>\n' + conteudoHtml + '\n</body></html>';
}

function extrairConteudoIds(ids) {
  var html = '';
  for (var i = 0; i < ids.length; i++) {
    var el = document.getElementById(ids[i]);
    if (!el) continue;

    // SE-075: preservar valor atual de textareas antes de clonar
    var textareas = el.querySelectorAll('textarea');
    for (var t = 0; t < textareas.length; t++) {
      textareas[t].textContent = textareas[t].value;
    }

    var clone = el.cloneNode(true);

    var remover = clone.querySelectorAll('button, input[type="button"], .btn, .btn-wide, .btn-text, select, .no-print');
    for (var j = 0; j < remover.length; j++) remover[j].remove();

    // SE-075: converter textareas em divs para impressão
    var cloneTextareas = clone.querySelectorAll('textarea');
    for (var ct = 0; ct < cloneTextareas.length; ct++) {
      var div = document.createElement('div');
      div.className = 'obs-impressao';
      div.textContent = cloneTextareas[ct].value || cloneTextareas[ct].textContent;
      cloneTextareas[ct].replaceWith(div);
    }

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
      // SE-075: remover white-space:nowrap para permitir quebra de texto no PDF
      if (s.whiteSpace === 'nowrap') s.whiteSpace = 'normal';

      if (todos[k].tagName === 'TABLE') {
        s.width = '100%';
        s.tableLayout = 'fixed';
        s.maxWidth = 'none';
      }

      if (todos[k].tagName === 'TH' || todos[k].tagName === 'TD') {
        s.whiteSpace = 'normal';
        s.wordWrap = 'break-word';
        s.overflowWrap = 'break-word';
      }

      if (todos[k].tagName === 'DIV' || todos[k].tagName === 'SECTION') {
        s.width = '';
        s.maxWidth = '';
        s.minWidth = '';
        s.maxHeight = '';
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
