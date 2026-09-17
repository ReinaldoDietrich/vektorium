# -*- coding: utf-8 -*-
"""Gera o .docx da Proposta Comercial. Tabelas nativas (tabelas_word) com AutoFit determinístico;
escopo do SISTEMA com layout do ChatGPT: título com numeração AUTOMÁTICA do Word, foto FLUTUANTE no
canto superior direito, legenda por campo SEQ, texto Arial Narrow 11 justificado. Nada é gravado no
banco. As fotos entram como InlineImage do docxtpl e são convertidas para flutuante por XML (sem
add_picture, que corromperia o arquivo)."""
import logging
from copy import deepcopy
from io import BytesIO
from pathlib import Path

logger = logging.getLogger("proposta.gerador")

from docxtpl import DocxTemplate, InlineImage
from docx import Document
from docx.shared import Mm, Pt, Twips, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from . import config
from . import tabelas_word as tw
from .preparar_template import garantir_template

import os as _os
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_APPDATA_DIR = Path(_os.environ["VEKTORIUM_APPDATA"]) if _os.environ.get("VEKTORIUM_APPDATA") else None
UPLOADS_DIR = _APPDATA_DIR / "uploads" if _APPDATA_DIR else BASE_DIR / "uploads"
DADOS_PROPOSTA = BASE_DIR / "dados" / "proposta"
XLSX_EXCECOES = DADOS_PROPOSTA / "Tabela de exceções.xlsx"

CATEGORIAS_EQUIP = ("válvula", "valvula", "rack")
CATEGORIAS_PAINEL_PORTA = ("painel", "porta")

FONTE_TEXTO = "Arial Narrow"
MARCA_TITULO = ""    # sentinela (uso privado) que identifica um TITULO do escopo


def _sub(tpl, fn, *args):
    sd = tpl.new_subdoc()
    fn(sd, *args)
    return [sd]


# ------------------------------------------------------------------- formatação de texto
def fmt_num(v, dec=0):
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v)


def fmt_moeda(v):
    if v is None or v == "":
        return "—"
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v)


def _t(v, padrao="—"):
    return padrao if v is None or v == "" else str(v)


# ------------------------------------------------------------------- coleta (leitura)
def _tipos_painel(db, projeto_id):
    from .. import models as m
    vistos = []
    for (esp,) in (db.query(m.PainelTermico.espessura)
                   .filter(m.PainelTermico.projeto_id == projeto_id,
                           m.PainelTermico.tipo.in_(["Parede", "Teto"]),
                           m.PainelTermico.espessura.isnot(None))
                   .distinct().all()):
        familia = (esp or "").strip().split()[0] if (esp or "").strip() else ""
        if familia and familia not in vistos:
            vistos.append(familia)
    return " / ".join(vistos)


def _orcamento_filtrado(db, projeto_id):
    from .. import composicao_preco as cp
    from .. import models as m
    margem = cp._margem_negociacao(db, projeto_id)
    itens = (db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id)
             .order_by(m.ComposicaoPrecoItem.bloco, m.ComposicaoPrecoItem.ordem, m.ComposicaoPrecoItem.id).all())
    blocos = {b: [] for b in cp.BLOCOS_COMPOSICAO}
    for i in itens:
        c = cp.calcular_item(i, margem)
        blocos.setdefault(c["bloco"], []).append(c)
    return cp.tabela_orcamento({"blocos": blocos, "margem_negociacao_pct": margem})


def _coletar(db, projeto_id):
    from .. import models as m
    from .. import id_comercial
    from ..routers import (compilacao, compilacao_geral, consumo, luminotecnico,
                           composicao_preco, paineis_portas)
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise ValueError(f"Projeto {projeto_id} não encontrado")

    def tenta(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            logger.exception("Erro ao coletar %s: %s", getattr(fn, "__name__", fn), e)
            return {"__erro__": str(e)}

    return {
        "projeto": projeto,
        "comp_linhas": tenta(compilacao.compilacao, projeto_id=projeto_id, db=db),
        "comp_geral": tenta(compilacao_geral.compilacao_geral, projeto_id=projeto_id, db=db),
        "consumo": tenta(consumo.consumo_projeto, projeto_id=projeto_id, db=db),
        "lumino": tenta(luminotecnico.estudo_luminotecnico, projeto_id=projeto_id, db=db),
        "orcamento_tab": tenta(_orcamento_filtrado, db, projeto_id),
        "pagamento": tenta(composicao_preco.obter_condicao_pagamento, projeto_id=projeto_id, db=db),
        "resumo_paineis": tenta(paineis_portas.resumo, projeto_id=projeto_id, modo="total", db=db),
        "memorial": tenta(id_comercial.montar_memorial_projeto, db, projeto_id),
    }


def _expandir_ids_filhos(db, ids_selecionados):
    """Expande códigos-pai para incluir todos os códigos-filhos da árvore de Ids Comerciais.
    Quando o usuário marca um nó-pai (ex.: '1'), inclui automaticamente todos os filhos
    ('1.1', '1.1.1', etc.), garantindo que o escopo reflita a seleção hierárquica completa."""
    from .. import models as m
    ids = set(str(x) for x in (ids_selecionados or []))
    if not ids:
        return ids
    todos = {str(i.codigo) for i in db.query(m.IdComercial).all()}
    expandidos = set(ids)
    for codigo in ids:
        prefixo = codigo + "."
        for c in todos:
            if c.startswith(prefixo):
                expandidos.add(c)
    return expandidos


def _conteudo_comercial(db, ids):
    from .. import models as m
    ids = _expandir_ids_filhos(db, ids)
    equipamentos, paineis_portas, detalhes = [], [], []

    def add(lista, nome, texto, imagem, ordem):
        lista.append({"titulo": nome, "texto": texto or "", "imagem": imagem, "ordem": ordem})

    if ids:
        for classe, ordem in ((m.LinhaForcador, 1), (m.CatalogoUC, 2), (m.LinhaCondensadorRemoto, 3)):
            for obj in db.query(classe).filter(classe.id_comercial.in_(ids)).all():
                add(equipamentos, obj.nome, obj.descricao_comercial, obj.imagem_path, ordem)
        for obj in db.query(m.CatalogoComercial).filter(m.CatalogoComercial.id_comercial.in_(ids)).all():
            cat = (obj.categoria or "").lower()
            if any(k in cat for k in CATEGORIAS_EQUIP):
                add(equipamentos, obj.nome, obj.descricao_comercial, obj.imagem_path, 4)
            elif any(k in cat for k in CATEGORIAS_PAINEL_PORTA):
                add(paineis_portas, obj.nome, obj.descricao_comercial, obj.imagem_path, 5)
            else:
                add(detalhes, obj.nome, obj.descricao_comercial, obj.imagem_path, 6)
    equipamentos.sort(key=lambda x: x["ordem"])
    return {"equipamentos": equipamentos, "paineis_portas": paineis_portas, "detalhes": detalhes}


def _foto_png(imagem_path):
    if not imagem_path:
        return None
    from PIL import Image
    import base64 as b64mod
    if str(imagem_path).startswith("data:"):
        header, dados = str(imagem_path).split(",", 1)
        im = Image.open(BytesIO(b64mod.b64decode(dados))).convert("RGB")
    else:
        nome = str(imagem_path).lstrip("/")
        if nome.startswith("uploads/"):
            nome = nome[len("uploads/"):]
        caminho = UPLOADS_DIR / nome
        if not caminho.exists():
            return None
        im = Image.open(caminho).convert("RGB")
    im.thumbnail((700, 700))
    w, h = im.size
    buf = BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf, w, h


def _blocos_lista(tpl, itens):
    """Lista para o laço docxtpl do escopo: [MARCA+título, texto, InlineImage(foto), ...]. O título
    leva a sentinela (MARCA_TITULO) para o pós-processamento aplicar numeração automática (o "1."
    NÃO é digitado — a numeração é do Word, via numPr)."""
    from docx.shared import Cm
    out = []
    if not itens:
        return out
    for it in itens:
        out.append(MARCA_TITULO + _t(it.get("titulo"), ""))
        # cada quebra de linha da descrição vira um PARÁGRAFO próprio (justificado sem buracos)
        for linha in str(it.get("texto") or "").split("\n"):
            if linha.strip():
                out.append(linha.strip())
        # FOTO — TODAS com 5 cm de largura, altura pela proporção (decisão do usuário).
        foto = _foto_png(it.get("imagem"))
        if foto:
            buf, w, h = foto
            out.append(InlineImage(tpl, buf, width=Cm(5)))
    return out


# ------------------------------------------------------------------- exceções / faturamento
def _excecoes_linhas(override):
    if override:
        return [{"atividade": r.get("atividade"), "empresa": bool(r.get("empresa")),
                 "cliente": bool(r.get("cliente"))} for r in override]
    linhas = []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(XLSX_EXCECOES, data_only=True)
        ws = wb["Planilha1"] if "Planilha1" in wb.sheetnames else wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            ce = str(row[1]).strip().upper() if len(row) > 1 and row[1] else ""
            cc = str(row[2]).strip().upper() if len(row) > 2 and row[2] else ""
            linhas.append({"atividade": str(row[0]).strip(), "empresa": ce == "X", "cliente": cc == "X"})
    except Exception as e:
        linhas.append({"atividade": f"(erro ao ler exceções: {e})", "empresa": False, "cliente": False})
    return linhas


def _fat_pares(campos):
    return [("Razão Social", campos.get("fat_razao_social")), ("CNPJ", campos.get("fat_cnpj")),
            ("Inscrição Municipal", campos.get("fat_insc_municipal")),
            ("Inscrição Estadual", campos.get("fat_insc_estadual")),
            ("Endereço", campos.get("fat_endereco")), ("Cidade / UF", campos.get("fat_cidade_uf")),
            ("Banco", campos.get("fat_banco")), ("Agência", campos.get("fat_agencia")),
            ("Conta Corrente", campos.get("fat_conta")), ("PIX", campos.get("fat_pix"))]


def _pagamento_tab(sd, dados):
    parcelas = (dados or {}).get("parcelas", []) or []
    cols = ["Parcela", "Descrição", "Data", "Valor"]
    t = tw._tabela(sd, 4)
    tw._cabecalho(t, cols, esq_ate=2)
    cont = tw._novo_conteudo(cols)
    for p in parcelas:
        row = t.add_row().cells
        vals = [tw._txt(p.get("ordem")), tw._txt(p.get("descricao")), tw._txt(p.get("data")),
                "R$ " + tw._fmt(p.get("valor"), 2)]
        tw._set(row[0], vals[0], align="c"); tw._set(row[1], vals[1], align="l")
        tw._set(row[2], vals[2], align="c"); tw._set(row[3], vals[3], align="c")
        tw._ac(cont, vals)
    tw.aplicar_autofit(t, cont)


# ------------------------------------------------------------------- motor de estilo do escopo
def configurar_estilo_normal(doc):
    st = doc.styles["Normal"]
    st.font.name = FONTE_TEXTO
    st.font.size = Pt(11)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    rPr = st.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.insert(0, rFonts)
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rFonts.set(qn(f"w:{a}"), FONTE_TEXTO)


def _arial11(par, bold=False, cor=None, justificar=True):
    if justificar:
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pPr = par._p.get_or_add_pPr()
        jc = pPr.find(qn("w:jc"))
        if jc is None:
            jc = OxmlElement("w:jc"); pPr.append(jc)
        jc.set(qn("w:val"), "both")
    for run in par.runs:
        run.font.name = FONTE_TEXTO
        run.font.size = Pt(11)
        run.bold = bold
        if cor is not None:
            run.font.color.rgb = cor
        rPr = run._r.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts"); rPr.insert(0, rFonts)
        for a in ("ascii", "hAnsi", "cs", "eastAsia"):
            rFonts.set(qn(f"w:{a}"), FONTE_TEXTO)


def _cor_subtitulo(doc):
    """Lê a COR dos subtítulos do template (ex.: 'DISTRIBUIÇÃO DE LINHAS') para os títulos de
    equipamento/detalhe ficarem no MESMO padrão de cor."""
    for p in doc.paragraphs:
        if _norm(p.text) in ("DISTRIBUICAO DE LINHAS", "EQUIPAMENTOS", "FORMA DE PAGAMENTO"):
            for r in p.runs:
                c = r.font.color
                if c is not None and c.rgb is not None:
                    return c.rgb
    return RGBColor(0x2E, 0x74, 0xB5)   # azul padrão de subtítulo (fallback)


def _indentar_descricoes(doc):
    """Paragrafação por NÍVEL: cada texto de descrição recua conforme o nível do título a que
    pertence (o texto 'volta um nível' quando está fora). Não mexe em tabelas, listas do template,
    nem na capa (antes do 1º título numerado)."""
    nivel = 0
    comecou = False
    for p in doc.paragraphs:
        pPr = p._p.find(qn("w:pPr"))
        ilvl = None
        if pPr is not None:
            numPr = pPr.find(qn("w:numPr"))
            if numPr is not None:
                el = numPr.find(qn("w:ilvl"))
                if el is not None:
                    ilvl = int(el.get(qn("w:val")))
        estilo = (p.style.name or "") if p.style is not None else ""
        if ilvl is not None:                 # título numerado -> define o nível corrente
            nivel = ilvl
            comecou = True
            continue
        if not comecou:                      # ainda na capa -> não indenta
            continue
        if "List Paragraph" in estilo or estilo.lower().startswith("heading"):
            continue                         # títulos não numerados / itens de lista: não mexe
        txt = p.text.strip()
        if txt and estilo == "Normal":
            bullet_match = None
            for marker in ("•", "–", "—", "-"):
                if txt.startswith(marker):
                    bullet_match = marker
                    break
            if bullet_match is not None:
                for r in p.runs:
                    if bullet_match in r.text:
                        r.text = r.text.replace(bullet_match, "", 1).lstrip()
                        break
                try:
                    p.style = doc.styles["List Bullet"]
                except KeyError:
                    pass
                p.paragraph_format.left_indent = Twips(840 + nivel * 480)
                continue
            pPr_el = p._p.find(qn("w:pPr"))
            ind_existente = pPr_el.find(qn("w:ind")) if pPr_el is not None else None
            if ind_existente is not None:
                continue
            p.paragraph_format.left_indent = Twips(420 + nivel * 480)
            pPr_k = p._p.get_or_add_pPr()
            if pPr_k.find(qn("w:keepLines")) is None:
                pPr_k.append(OxmlElement("w:keepLines"))


def criar_numeracao(doc):
    """Numeração MULTINÍVEL (1 / 1.1 / 1.1.1 / 1.1.1.1) com recuo crescente por nível."""
    numbering = doc.part.numbering_part.element
    aid = max([int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))], default=0) + 1
    nid = max([int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))], default=0) + 1
    abstract = OxmlElement("w:abstractNum"); abstract.set(qn("w:abstractNumId"), str(aid))
    multi = OxmlElement("w:multiLevelType"); multi.set(qn("w:val"), "multilevel"); abstract.append(multi)
    # Nível 0 = decimal (1.), Nível 1 = letra minúscula (1.a.), Nível 2 = romano minúsculo (1.a.i.),
    # Nível 3 = decimal — full path, como o usuário pediu ("1 / 1.a / 1.a.i").
    formatos = ["decimal", "lowerLetter", "lowerRoman", "decimal"]
    for il in range(4):
        lvl = OxmlElement("w:lvl"); lvl.set(qn("w:ilvl"), str(il))
        s = OxmlElement("w:start"); s.set(qn("w:val"), "1"); lvl.append(s)
        nf = OxmlElement("w:numFmt"); nf.set(qn("w:val"), formatos[il]); lvl.append(nf)
        texto = ".".join("%%%d" % (k + 1) for k in range(il + 1)) + "."   # %1.  %1.%2.  %1.%2.%3.
        lt = OxmlElement("w:lvlText"); lt.set(qn("w:val"), texto); lvl.append(lt)
        jc = OxmlElement("w:lvlJc"); jc.set(qn("w:val"), "left"); lvl.append(jc)
        pPr = OxmlElement("w:pPr"); ind = OxmlElement("w:ind")
        esq = 420 + il * 480                                             # recuo crescente por nível
        ind.set(qn("w:left"), str(esq)); ind.set(qn("w:hanging"), "420")
        pPr.append(ind); lvl.append(pPr)
        abstract.append(lvl)
    numbering.append(abstract)
    num = OxmlElement("w:num"); num.set(qn("w:numId"), str(nid))
    ani = OxmlElement("w:abstractNumId"); ani.set(qn("w:val"), str(aid)); num.append(ani)
    numbering.append(num)
    return nid


def aplicar_numeracao(par, num_id, nivel=0):
    pPr = par._p.get_or_add_pPr()
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        numPr = OxmlElement("w:numPr"); pPr.insert(0, numPr)
    for tag, val in (("w:ilvl", str(nivel)), ("w:numId", str(num_id))):
        el = numPr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag); numPr.append(el)
        el.set(qn("w:val"), val)


# Nível de cada título de seção (0 = TÍTULO "1."; 1 = SUBTÍTULO "1.1"; 2 = SUBTÍTULO 2 "1.1.1"),
# conforme os balões de anotação do modelo.
def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", (s or "").upper()).encode("ascii", "ignore").decode()
    return " ".join(s.split())


NIVEL_TITULOS = {
    # Nível 0 (título "1.")
    "LAYOUT DE INSTALACAO": 0, "ESCOPO DE MONTAGEM": 0, "SERVICOS DE MONTAGEM": 0,
    "EXCLUSOES DA PROPOSTA": 0, "CONDICOES DE FORNECIMENTO": 0, "GARANTIA": 0,
    # Nível 1 (subtítulo "1.a") — filhos de LAYOUT
    "DISTRIBUICAO DE LINHAS": 1, "PARAMETRO DE DIMENSIONAMENTO E SELECAO DOS EQUIPAMENTOS": 1,
    "ESTUDO DE CONSUMO ELETRICO": 1, "ESTUDO LUMINOTECNICO": 1,
    # Nível 1 — filhos de ESCOPO (Equipamentos 2.a, Montagem de Isopaineis 2.b, Detalhes 2.c)
    "EQUIPAMENTOS": 1, "MONTAGEM DE ISOPAINEIS": 1, "DETALHES DE INSTALACAO": 1,
    # Nível 1 — filhos de CONDIÇÕES
    "FORMA DE PAGAMENTO": 1, "DADOS DE FATURAMENTO": 1, "PRAZO DE ENTREGA": 1, "VALIDADE": 1,
    # Nível 1 — filhos de GARANTIA
    "RESPONSABILIDADES CONTRATADA": 1, "RESPONSABILIDADES CONTRATANTE": 1, "LIMITACOES": 1,
    "INVALIDACAO DA GARANTIA": 1, "REPOSICAO EM GARANTIA": 1, "OBSERVACAO IMPORTANTE": 1,
}


def _forcar_pagina_nova(doc):
    """Garante pageBreakBefore nos títulos que devem iniciar em página nova (OOXML ECMA-376 §17.3.1.20).
    Aplicado no pós-processamento para sobreviver ao render do docxtpl."""
    for p in doc.paragraphs:
        n = _norm(p.text)
        if n in ("GARANTIA", "LAYOUT DE INSTALACAO"):
            pPr = p._p.get_or_add_pPr()
            if pPr.find(qn("w:pageBreakBefore")) is None:
                pPr.append(OxmlElement("w:pageBreakBefore"))


def _numerar_titulos(doc, num_id):
    """Aplica a numeração multinível + recuo a cada TÍTULO de seção do documento, conforme o nível
    anotado (NIVEL_TITULOS). Adiciona keepNext+keepLines (ECMA-376 §17.3.1.15/§17.3.1.14) para
    que o título nunca fique separado do conteúdo seguinte."""
    for p in doc.paragraphs:
        n = _norm(p.text)
        if n in NIVEL_TITULOS:
            aplicar_numeracao(p, num_id, NIVEL_TITULOS[n])
            pPr = p._p.get_or_add_pPr()
            if pPr.find(qn("w:keepNext")) is None:
                pPr.append(OxmlElement("w:keepNext"))
            if pPr.find(qn("w:keepLines")) is None:
                pPr.append(OxmlElement("w:keepLines"))


def inline_para_anchor(inline):
    anchor = OxmlElement("wp:anchor")
    for k, v in (("distT", "0"), ("distB", "91440"), ("distL", "114300"), ("distR", "114300"),
                 ("simplePos", "0"), ("relativeHeight", "251658240"), ("behindDoc", "0"),
                 ("locked", "0"), ("layoutInCell", "1"), ("allowOverlap", "1")):
        anchor.set(k, v)
    sp = OxmlElement("wp:simplePos"); sp.set("x", "0"); sp.set("y", "0"); anchor.append(sp)
    ph = OxmlElement("wp:positionH"); ph.set("relativeFrom", "column")
    al = OxmlElement("wp:align"); al.text = "right"; ph.append(al); anchor.append(ph)   # DIREITA
    pv = OxmlElement("wp:positionV"); pv.set("relativeFrom", "paragraph")
    av = OxmlElement("wp:align"); av.text = "top"; pv.append(av); anchor.append(pv)     # TOPO
    ext = inline.find(qn("wp:extent"))
    if ext is not None:
        anchor.append(deepcopy(ext))
    eff = OxmlElement("wp:effectExtent")
    for a in ("l", "t", "r", "b"):
        eff.set(a, "0")
    anchor.append(eff)
    wrap = OxmlElement("wp:wrapSquare"); wrap.set("wrapText", "bothSides"); anchor.append(wrap)
    for tag in ("wp:docPr", "wp:cNvGraphicFramePr", "a:graphic"):
        el = inline.find(qn(tag))
        if el is not None:
            anchor.append(deepcopy(el))
    inline.getparent().replace(inline, anchor)


def _keep_next(par):
    pPr = par._p.get_or_add_pPr()
    if pPr.find(qn("w:keepNext")) is None:
        pPr.append(OxmlElement("w:keepNext"))


_LEGENDA_ID = [900]
_LEGENDA_MODELO = [False]     # run <w:r> da caixa de legenda, clonado do modelo do ChatGPT


def _modelo_legenda():
    """Pega, do modelo do ChatGPT, o RUN que contém a caixa de texto '*Foto ilustrativa' — XML
    válido do Word, para clonar (sem risco de corromper). Cacheado."""
    if _LEGENDA_MODELO[0] is False:
        _LEGENDA_MODELO[0] = None
        cam = DADOS_PROPOSTA / "PROPOSTA COMERCIAL PADRÃO - CHAT GPT.docx"
        try:
            d = Document(str(cam))
            for dr in d.element.body.iter(qn("w:drawing")):
                txt = "".join(t.text or "" for t in dr.iter(qn("w:t")))
                if "ilustrativ" in txt.lower():
                    run = dr
                    while run is not None and run.tag != qn("w:r"):
                        run = run.getparent()
                    _LEGENDA_MODELO[0] = run
                    break
        except Exception:
            _LEGENDA_MODELO[0] = None
    return _LEGENDA_MODELO[0]


def _add_legenda(para_el, texto="*Imagem ilustrativa;"):
    """Legenda robusta (Word-safe): parágrafo à DIREITA, itálico, Arial Narrow 8, inserido logo após
    a 1ª linha da descrição — fica junto à foto flutuante. (A caixa de texto flutuante do Word
    corrompe o arquivo no destino, então não a uso.)"""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    # ordem do schema: w:spacing ANTES de w:jc (senão o Word considera corrompido)
    esp = OxmlElement("w:spacing"); esp.set(qn("w:before"), "0"); esp.set(qn("w:after"), "0"); pPr.append(esp)
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "right"); pPr.append(jc)
    p.append(pPr)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONTE_TEXTO)
    rPr.append(rf)
    rPr.append(OxmlElement("w:i"))
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "16"); rPr.append(sz)
    r.append(rPr)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = texto
    r.append(t)
    p.append(r)
    para_el.addnext(p)


def legenda_seq(par, rotulo="Figura", texto=" — Foto ilustrativa."):
    # Ordem correta: "Figura " + campo SEQ (número) + " — Foto ilustrativa."
    par.add_run(f"{rotulo} ")
    run = par.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = f" SEQ {rotulo} \\* ARABIC "
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    for el in (b, instr, sep, t, end):
        run._r.append(el)
    par.add_run(texto)
    _arial11(par)



def habilitar_update_fields(doc):
    settings = doc.settings.element
    uf = settings.find(qn("w:updateFields"))
    if uf is None:
        uf = OxmlElement("w:updateFields"); settings.append(uf)
    uf.set(qn("w:val"), "true")


def _legenda_no_fim(par):
    """Insere a legenda '*Imagem ilustrativa;' (direita, itálico, Arial Narrow 8) LOGO APÓS o
    parágrafo `par` — via API do python-docx (Word-safe). Fica abaixo da foto flutuante."""
    prox_el = par._p.getnext()
    if prox_el is not None and prox_el.tag == qn("w:p"):
        from docx.text.paragraph import Paragraph
        cap = Paragraph(prox_el, par._parent).insert_paragraph_before()
    else:
        cap = par.insert_paragraph_before()   # fallback (não há próximo parágrafo)
    cap.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rc = cap.add_run("*Imagem ilustrativa;"); rc.italic = True
    rc.font.name = FONTE_TEXTO; rc.font.size = Pt(8)
    rcpr = rc._r.get_or_add_rPr()
    rf = rcpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rcpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONTE_TEXTO)


def formatar_escopo(doc, num_id, cor_sub=None):
    """Formata o ESCOPO por BLOCO (título + descrição + foto): título nível 2 (x.y.i) na COR do
    subtítulo padrão, texto Arial Narrow 11 justificado, foto flutuante à direita/TOPO da 1ª linha
    da descrição. Títulos/listas do template ficam intactos."""
    titulo = [None]; textos = []; img_run = [None]; img_p = [None]

    def finaliza():
        if titulo[0] is not None:
            aplicar_numeracao(titulo[0], num_id, 2)
            _arial11(titulo[0], bold=True, cor=cor_sub, justificar=False)
        for tp in textos:
            _arial11(tp)
        if img_run[0] is not None and textos:
            primeiro = textos[0]._p
            pPr = primeiro.find(qn("w:pPr"))
            if pPr is not None:
                pPr.addnext(img_run[0])
            else:
                primeiro.insert(0, img_run[0])
            if img_p[0] is not None and not any(c.tag == qn("w:r") for c in list(img_p[0]._p)):
                img_p[0]._p.getparent().remove(img_p[0]._p)
            # (sem legenda nas fotos — decisão do usuário)
        titulo[0] = None; textos.clear(); img_run[0] = None; img_p[0] = None

    dentro = False
    for p in list(doc.paragraphs):
        up = p.text.strip().upper()
        if up.startswith("ESCOPO DE MONTAGEM"):
            dentro = True
        if up.startswith("EXCLUSÕES DA PROPOSTA") or up.startswith("EXCLUSOES DA PROPOSTA"):
            finaliza(); dentro = False
        if not dentro:
            continue
        estilo = (p.style.name or "") if p.style is not None else ""
        drawing = p._p.find(".//" + qn("w:drawing"))
        txt = p.text
        if txt.startswith(MARCA_TITULO):                 # início de um bloco de equipamento/detalhe
            finaliza()
            for r in p.runs:
                if MARCA_TITULO in r.text:
                    r.text = r.text.replace(MARCA_TITULO, "")
            titulo[0] = p
        elif drawing is not None:                        # foto do bloco
            inline = drawing.find(qn("wp:inline"))
            if inline is not None:
                inline_para_anchor(inline)
            img_run[0] = drawing.getparent()
            img_p[0] = p
        elif "List Paragraph" in estilo or estilo.lower().startswith("heading"):
            finaliza()                                   # título/lista do template = fronteira
        elif txt.strip():                                # descrição (texto inserido)
            textos.append(p)
    finaliza()
    habilitar_update_fields(doc)


# ------------------------------------------------------------------- imagem simples (planta/logo)
def _img_arquivo(tpl, caminho, largura_mm):
    if not caminho:
        return ""
    p = Path(caminho)
    if not p.is_absolute():
        p = config.UPLOADS_PROPOSTA / caminho
    if not p.exists():
        return ""
    return InlineImage(tpl, str(p), width=Mm(largura_mm))


# ------------------------------------------------------------------- papel de carta (item 3)
def _abrir_docx_ou_dotx(caminho):
    """Abre .docx E .dotx. O python-docx recusa .dotx (content-type de template); então, quando é
    template, faz uma cópia em memória trocando o content-type do documento principal para o de
    documento comum e aí abre. É por isso que o papel de carta em .dotx não estava sendo aplicado."""
    import io
    import zipfile
    data = Path(caminho).read_bytes()
    saida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            conteudo = zin.read(item)
            if item == "[Content_Types].xml":
                conteudo = conteudo.decode("utf-8").replace(
                    "wordprocessingml.template.main+xml",
                    "wordprocessingml.document.main+xml").encode("utf-8")
            zout.writestr(item, conteudo)
    saida.seek(0)
    return Document(saida)


def _aplicar_papel_carta(doc, caminho):
    """Aplica o papel de carta do usuário: usa o arquivo dele (.docx OU .dotx) e substitui os
    CABEÇALHOS e RODAPÉS (padrão, 1ª página e par) do documento gerado pelos dele — assim o timbre
    aparece em todas as páginas, esteja ele no cabeçalho, no rodapé ou nos dois. Vale para qualquer
    papel de carta."""
    p = Path(caminho)
    if not p.is_absolute():
        p = config.UPLOADS_PROPOSTA / caminho
    if not p.exists():
        return
    origem = _abrir_docx_ou_dotx(str(p))       # abre .docx e .dotx (não engole erro em silêncio)
    sec_o = origem.sections[0]
    sec_d = doc.sections[0]
    sec_d.different_first_page_header_footer = sec_o.different_first_page_header_footer
    for attr in ("left_margin", "right_margin", "top_margin", "bottom_margin",
                 "header_distance", "footer_distance"):
        v = getattr(sec_o, attr, None)
        if v is not None:
            setattr(sec_d, attr, v)

    R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    from docx.opc.packuri import PackURI
    pacote = doc.part.package
    _renomeados = {}     # id(parte_origem) -> já renomeada (evita colisão e repetição)

    def _parte_unica(parte):
        """Renomeia a parte (imagem) do papel de carta para um partname livre no pacote destino —
        evita a colisão 'word/media/imageN.png' que corrompe o arquivo."""
        if id(parte) in _renomeados:
            return
        usados = {str(p.partname) for p in pacote.iter_parts()}
        ext = str(parte.partname).rsplit(".", 1)[-1]
        i = 1
        while True:
            cand = f"/word/media/papelcarta{i}.{ext}"
            if cand not in usados:
                break
            i += 1
        parte.partname = PackURI(cand)
        _renomeados[id(parte)] = True

    def _copiar_hf(orig, dest):
        """Substitui inteiramente um cabeçalho/rodapé destino pelo de origem, reembutindo TODAS as
        referências de relacionamento (r:embed do DrawingML, r:id do VML/.emf, r:link, etc.) em
        novos relacionamentos no destino — senão o Word considera o arquivo corrompido."""
        if orig.is_linked_to_previous:
            return
        dest.is_linked_to_previous = False
        el_o, el_d = orig._element, dest._element
        for child in list(el_d):
            el_d.remove(child)
        for child in list(el_o):
            novo = deepcopy(child)
            for el in novo.iter():
                for attr in list(el.attrib):
                    if not attr.startswith(R_NS):
                        continue
                    rid = el.attrib[attr]
                    try:
                        rel = orig.part.rels[rid]
                        if rel.is_external:
                            novo_rid = dest.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
                        else:
                            _parte_unica(rel.target_part)
                            novo_rid = dest.part.relate_to(rel.target_part, rel.reltype)
                        el.attrib[attr] = novo_rid
                    except Exception:
                        pass
            el_d.append(novo)

    # cabeçalhos E rodapés, os 3 variantes de cada
    _copiar_hf(sec_o.header, sec_d.header)
    _copiar_hf(sec_o.first_page_header, sec_d.first_page_header)
    _copiar_hf(sec_o.even_page_header, sec_d.even_page_header)
    _copiar_hf(sec_o.footer, sec_d.footer)
    _copiar_hf(sec_o.first_page_footer, sec_d.first_page_footer)
    _copiar_hf(sec_o.even_page_footer, sec_d.even_page_footer)


# ------------------------------------------------------------------- geração
def gerar(db, projeto_id, opcoes=None):
    opcoes = opcoes or {}
    tw._SEQ_TABELA[0] = 0
    tpl = DocxTemplate(str(garantir_template()))
    d = _coletar(db, projeto_id)
    projeto = d["projeto"]

    defaults = config.carregar_defaults()
    campos = dict(defaults)
    campos.update({k: v for k, v in (opcoes.get("campos") or {}).items() if v is not None})
    empresa = campos.get("empresa_contratada") or "Empresa contratada"

    ids_sel = opcoes.get("ids_selecionados")
    if ids_sel is None:
        ids_sel = (d.get("memorial") or {}).get("ids_resolvidos") or []
    conteudo = _conteudo_comercial(db, ids_sel)

    tabelas_on = opcoes.get("tabelas")

    def liga(chave):
        return tabelas_on is None or tabelas_on.get(chave, True)

    codigo = _t(getattr(projeto, "codigo_base", None) or projeto.codigo_projeto, "")
    rev = int(getattr(projeto, "revisao", 0) or 0)

    contexto = {
        "logomarca": _img_arquivo(tpl, campos.get("logo_path"), 50),
        "titulo_fornecimento": campos.get("titulo_fornecimento", ""),
        "codigo_revisao": f"{codigo} - R{rev:02d}",
        "contato": _t(projeto.contato, ""),
        "razao_social": _t(getattr(projeto, "razao_social_faturamento", None) or projeto.cliente, ""),
        "cnpj": _t(getattr(projeto, "cnpj_faturamento", None), ""),
        "cidade_estado": f"{_t(projeto.cidade_instalacao,'')}/{_t(projeto.estado_uf,'')}",
        "tipo_painel": _tipos_painel(db, projeto_id),
        "empresa_contratada": empresa,
        "dias_proposta": campos.get("dias_proposta", ""),
        "meses_garantia": campos.get("meses_garantia", ""),
        "embarque_equipamentos": campos.get("embarque_equipamentos", ""),
        "embarque_isopainel": campos.get("embarque_isopainel", ""),
        "vendedor_nome": campos.get("vendedor_nome", ""),
        "vendedor_cargo": campos.get("vendedor_cargo", ""),
        "vendedor_telefone": campos.get("vendedor_telefone", ""),
        "vendedor_email": campos.get("vendedor_email", ""),
        "imagem_planta": _img_arquivo(tpl, campos.get("planta_path") or opcoes.get("planta_path"), 160),
        "tab_comp_linhas": _sub(tpl, tw.comp_linhas, d.get("comp_linhas") or {}) if liga("comp_linhas") else [],
        "tab_comp_geral": _sub(tpl, tw.comp_geral, d.get("comp_geral") or {}) if liga("comp_geral") else [],
        "tab_consumo": _sub(tpl, tw.consumo, d.get("consumo") or {}) if liga("consumo") else [],
        "tab_lumino": _sub(tpl, tw.lumino, d.get("lumino") or {}) if liga("lumino") else [],
        "tab_resumo_paineis": _sub(tpl, tw.paineis, d.get("resumo_paineis") or {}) if liga("resumo_paineis") else [],
        "tab_exclusoes": _sub(tpl, tw.excecoes, empresa, _excecoes_linhas(opcoes.get("excecoes"))),
        "tab_orcamento": _sub(tpl, tw.orcamento, d.get("orcamento_tab") or {}, opcoes.get("orcamento_filtro") or {}) if liga("orcamento") else [],
        "tab_pagamento": _sub(tpl, _pagamento_tab, d.get("pagamento") or {}) if liga("pagamento") else [],
        "tab_faturamento": _sub(tpl, tw.faturamento, _fat_pares(campos)),
        "escopo_equipamentos": _blocos_lista(tpl, conteudo.get("equipamentos")),
        "escopo_paineis": _blocos_lista(tpl, conteudo.get("paineis_portas")),
        "detalhes_instalacao": _blocos_lista(tpl, conteudo.get("detalhes")),
    }
    _legendas_base = {
        "logo": "", "planta": "",
        "comp_linhas": "",
        "comp_geral": "",
        "consumo": "",
        "lumino": "",
        "resumo_paineis": "",
        "exclusoes": "",
        "orcamento": "",
        "pagamento": "", "faturamento": "", "geral": "",
    }
    for k, v in _legendas_base.items():
        contexto[f"legenda_{k}"] = v if liga(k) else ""

    tpl.render(contexto)
    buf = BytesIO()
    tpl.save(buf)
    buf.seek(0)

    # Pós-processamento (fonte/justificado/numeração/foto flutuante/legenda) — sem add_picture.
    # NÃO altera o estilo Normal global (isso estragava a paragrafação/numeração do template);
    # formata apenas os parágrafos do ESCOPO que este gerador insere.
    doc = Document(buf)
    cor_sub = _cor_subtitulo(doc)          # cor padrão dos subtítulos (para unificar)
    num_id = criar_numeracao(doc)          # numeração multinível compartilhada
    _numerar_titulos(doc, num_id)          # títulos de seção (1 / 1.a) com recuo por nível
    _forcar_pagina_nova(doc)               # GARANTIA e LAYOUT sempre em página nova (item 5/6)
    formatar_escopo(doc, num_id, cor_sub)  # escopo + títulos de equip./detalhe (x.y.i) na cor padrão
    _indentar_descricoes(doc)              # paragrafação: texto acompanha o recuo do nível
    if campos.get("papel_carta_path"):
        _aplicar_papel_carta(doc, campos.get("papel_carta_path"))
    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue(), f"Proposta {codigo} R{rev:02d}.docx".replace("/", "-")
