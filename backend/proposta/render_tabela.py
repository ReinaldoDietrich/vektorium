# -*- coding: utf-8 -*-
"""Renderizador genérico de tabela -> imagem(ns) PNG (Pillow), com as regras do usuário:
 - largura de cada coluna ajustada ao conteúdo, com MÍNIMO 75 px e MÁXIMO 150 px;
 - conteúdo maior que o máximo QUEBRA o texto (várias linhas na célula);
 - se a tabela não couber na largura útil da página, a TABELA é quebrada em vários blocos/imagens
   (cada bloco repete as primeiras `repetir` colunas de identificação).
Nunca estica para a largura da folha — cada imagem tem a largura do seu conteúdo.

desenhar_tabela devolve uma LISTA de imagens (uma, ou várias se precisou quebrar):
  [{"png": bytes, "w_px": largura_logica}, ...]
A largura lógica (px em 96 dpi) é usada pelo gerador para inserir a imagem no Word no tamanho
natural (mm), respeitando o teto da largura útil da página (PAGE_MAX_PX)."""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

MIN_COL_PX = 75
MAX_COL_PX = 150
PAGE_MAX_PX = 643          # ~17 cm úteis (A4 retrato, margens de 2 cm) a 96 dpi -> ~170 mm
MAX_LINHAS_IMG = 30        # nº de linhas de texto (cabeçalho + corpo) por imagem, p/ caber na altura
                           # da página — evita imagem alta demais que o Word não exibe.

_COR_TEXTO = (17, 24, 39)
_COR_LINHA = (209, 213, 219)
_COR_HEADER_BG = (17, 24, 39)
_COR_HEADER_TXT = (255, 255, 255)
_COR_ZEBRA = (243, 244, 246)
_BRANCO = (255, 255, 255)

_FONTES = {"regular": [r"C:\Windows\Fonts\arial.ttf"], "bold": [r"C:\Windows\Fonts\arialbd.ttf"]}


def _fonte(tipo, tamanho):
    for caminho in _FONTES.get(tipo, []):
        if Path(caminho).exists():
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                pass
    return ImageFont.load_default()


def _largura_texto(draw, texto, fonte):
    return draw.textlength(str(texto), font=fonte)


def _quebrar(draw, texto, fonte, largura_max):
    texto = "" if texto is None else str(texto)
    linhas = []
    for bruta in texto.split("\n"):
        atual = ""
        for palavra in bruta.split(" "):
            teste = palavra if not atual else atual + " " + palavra
            if _largura_texto(draw, teste, fonte) <= largura_max or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas or [""]


def _larguras_colunas(colunas, linhas, fonte, fonte_b, pad):
    """Largura lógica de cada coluna: conteúdo, limitado a [MIN, MAX]. (px, sem escala)."""
    tmp = Image.new("RGB", (4, 4), _BRANCO)
    d = ImageDraw.Draw(tmp)
    larg = []
    for j, cab in enumerate(colunas):
        w = _largura_texto(d, cab, fonte_b)
        for row in linhas:
            valor = row[j] if j < len(row) else ""
            w = max(w, _largura_texto(d, str(valor), fonte))
        larg.append(int(min(MAX_COL_PX, max(MIN_COL_PX, w + 2 * pad))))
    return larg


def _grupos_colunas(larguras, repetir):
    """Divide os índices de coluna em grupos que caibam em PAGE_MAX_PX, repetindo as `repetir`
    primeiras colunas de identificação em cada grupo."""
    n = len(larguras)
    fixas = list(range(min(repetir, n)))
    largura_fixas = sum(larguras[i] for i in fixas)
    demais = list(range(len(fixas), n))
    if largura_fixas + sum(larguras[i] for i in demais) <= PAGE_MAX_PX:
        return [list(range(n))]
    grupos = []
    atual = list(fixas)
    largura_atual = largura_fixas
    for i in demais:
        if atual != fixas and largura_atual + larguras[i] > PAGE_MAX_PX:
            grupos.append(atual)
            atual = list(fixas)
            largura_atual = largura_fixas
        atual.append(i)
        largura_atual += larguras[i]
    if atual and atual != fixas:
        grupos.append(atual)
    return grupos or [list(range(n))]


def _desenhar_bloco(colunas, linhas, larguras, alinhamentos, escala, tamanho_fonte, pad_base):
    pad = pad_base * escala
    fonte = _fonte("regular", tamanho_fonte * escala)
    fonte_b = _fonte("bold", tamanho_fonte * escala)
    col_px = [w * escala for w in larguras]
    W = sum(col_px)
    col_x = [0]
    for c in col_px:
        col_x.append(col_x[-1] + c)

    tmp = Image.new("RGB", (4, 4), _BRANCO)
    d0 = ImageDraw.Draw(tmp)
    alt_linha = (fonte.getbbox("Ay")[3] - fonte.getbbox("Ay")[1]) + 4 * escala

    def altura(cells, fonte_cel):
        n_linhas = 1
        wraps = []
        for j, txt in enumerate(cells):
            ls = _quebrar(d0, txt, fonte_cel, col_px[j] - 2 * pad)
            wraps.append(ls)
            n_linhas = max(n_linhas, len(ls))
        return wraps, n_linhas * alt_linha + 2 * pad

    hdr_wraps, h_hdr = altura(colunas, fonte_b)
    linhas_wraps, alturas = [], []
    for row in linhas:
        cells = [row[j] if j < len(row) else "" for j in range(len(colunas))]
        wraps, h = altura(cells, fonte)
        linhas_wraps.append(wraps)
        alturas.append(h)

    H = h_hdr + sum(alturas) + 2 * escala
    img = Image.new("RGB", (int(W) + escala, int(H)), _BRANCO)
    draw = ImageDraw.Draw(img)

    def escrever(wraps, y0, fonte_cel, cor):
        for j, ls in enumerate(wraps):
            yy = y0 + pad
            for linha_txt in ls:
                w = _largura_texto(draw, linha_txt, fonte_cel)
                a = alinhamentos[j] if j < len(alinhamentos) else "l"
                if a == "r":
                    xx = col_x[j] + col_px[j] - pad - w
                elif a == "c":
                    xx = col_x[j] + (col_px[j] - w) / 2
                else:
                    xx = col_x[j] + pad
                draw.text((xx, yy), linha_txt, font=fonte_cel, fill=cor)
                yy += alt_linha

    y = 0
    draw.rectangle([0, y, W, y + h_hdr], fill=_COR_HEADER_BG)
    escrever(hdr_wraps, y, fonte_b, _COR_HEADER_TXT)
    y += h_hdr
    for i, wraps in enumerate(linhas_wraps):
        if i % 2 == 1:
            draw.rectangle([0, y, W, y + alturas[i]], fill=_COR_ZEBRA)
        escrever(wraps, y, fonte, _COR_TEXTO)
        y += alturas[i]

    draw.rectangle([0, 0, W - 1, y - 1], outline=_COR_LINHA, width=escala)
    yy = h_hdr
    draw.line([0, yy, W, yy], fill=_COR_LINHA, width=escala)
    for h in alturas:
        yy += h
        draw.line([0, yy, W, yy], fill=_COR_LINHA, width=escala)
    for cx in col_x[1:-1]:
        draw.line([cx, 0, cx, y], fill=_COR_LINHA, width=escala)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), int(W / escala), int(H / escala)


def _n_linhas_wrap(draw, cells, larguras, fonte, pad):
    """Nº de linhas de texto que a linha ocupa (máximo entre as células, após quebra)."""
    n = 1
    for j, txt in enumerate(cells):
        n = max(n, len(_quebrar(draw, txt, fonte, larguras[j] - 2 * pad)))
    return n


def _quebrar_linhas_altura(linhas_g, larguras, fonte, pad):
    """Divide as linhas do corpo em blocos que caibam na altura da página (MAX_LINHAS_IMG linhas de
    texto por bloco, contando quebras de célula). Devolve lista de sub-listas de linhas."""
    tmp = Image.new("RGB", (4, 4), _BRANCO)
    d = ImageDraw.Draw(tmp)
    orcamento = max(6, MAX_LINHAS_IMG - 2)   # reserva 2 linhas p/ o cabeçalho
    blocos, atual, soma = [], [], 0
    for row in linhas_g:
        nl = _n_linhas_wrap(d, row, larguras, fonte, pad)
        if atual and soma + nl > orcamento:
            blocos.append(atual)
            atual, soma = [], 0
        atual.append(row)
        soma += nl
    if atual:
        blocos.append(atual)
    return blocos or [[]]


def desenhar_tabela(colunas, linhas, alinhamentos=None, repetir=0, escala=2,
                    tamanho_fonte=12, pad_base=6, quebrar=False):
    """Devolve lista de imagens [{png, w_px, h_px}].

    quebrar=False (padrão): UMA imagem única com todas as colunas e linhas (o gerador a redimensiona
    para caber na página). quebrar=True: quebra em vários blocos por colunas E por linhas (repetindo
    o cabeçalho) — usado só na Compilação de Linhas."""
    if not linhas:
        return []
    if alinhamentos is None:
        alinhamentos = ["l"] * len(colunas)
    fonte = _fonte("regular", tamanho_fonte)
    fonte_b = _fonte("bold", tamanho_fonte)
    larguras = _larguras_colunas(colunas, linhas, fonte, fonte_b, pad_base)

    if not quebrar:
        png, w_px, h_px = _desenhar_bloco(colunas, linhas, larguras, alinhamentos, escala,
                                          tamanho_fonte, pad_base)
        return [{"png": png, "w_px": w_px, "h_px": h_px}]

    imagens = []
    for grupo in _grupos_colunas(larguras, repetir):
        cols_g = [colunas[i] for i in grupo]
        larg_g = [larguras[i] for i in grupo]
        alin_g = [alinhamentos[i] if i < len(alinhamentos) else "l" for i in grupo]
        linhas_g = [[row[i] if i < len(row) else "" for i in grupo] for row in linhas]
        for bloco in _quebrar_linhas_altura(linhas_g, larg_g, fonte, pad_base):
            png, w_px, h_px = _desenhar_bloco(cols_g, bloco, larg_g, alin_g, escala, tamanho_fonte, pad_base)
            imagens.append({"png": png, "w_px": w_px, "h_px": h_px})
    return imagens
