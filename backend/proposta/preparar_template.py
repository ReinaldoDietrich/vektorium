# -*- coding: utf-8 -*-
"""Constrói o template docxtpl (template_proposta.docx) a partir do MODELO DO CHATGPT
(PROPOSTA COMERCIAL PADRÃO - CHAT GPT.docx), que já traz a proposta inteira pronta: papel de carta,
todo o ESCOPO DE MONTAGEM (títulos, textos e FOTOS FLUTUANTES) e apenas os marcadores de campo/tabela
a preencher pelo sistema.

Regra central (decisão do usuário): o escopo NÃO é regerado — o modelo do ChatGPT é a base e seus
textos/fotos ficam intactos. O preparo só:
  - troca os [TOKENS] de campo por {{ variavel }} (inteiros no parágrafo ou inline);
  - troca os 9 [TABELA ...] por um laço docxtpl que insere a TABELA NATIVA (subdoc);
  - numera as legendas: [LEGENDA TABELA AUTOMÁTICA] -> "Tabela N — ..." (ACIMA da tabela, ABNT);
    [LEGENDA IMAGEM AUTOMÁTICA] -> "Figura N — ..." (ABAIXO da figura, ABNT).

Roda uma vez; o gerador chama garantir_template() e reconstrói se o modelo for mais novo."""
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

DIR = Path(__file__).resolve().parent
MODELO_PADRAO = (DIR.parent.parent / "dados" / "proposta"
                 / "PROPOSTA COMERCIAL PADRÃO - Novas Anotações Claude.docx")
TEMPLATE_SAIDA = DIR / "template_proposta.docx"

# Placeholder que ocupa o parágrafo inteiro -> tag/laço. (chave = trecho MAIÚSCULO presente no texto)
# tipo: None = texto; "img" = imagem; "tab" = tabela nativa (laço de subdoc).
MAPA_INTEIRO = [
    ("LOGOMARCA", "{{ logomarca }}", "img"),
    ("TÍTULO DE FORNECIMENTO", "{{ titulo_fornecimento }}", None),
    ("CÓDIGO PROJETO", "{{ codigo_revisao }}", None),
    ("RAZÃO SOCIAL FATURAMENTO", "{{ razao_social }}", None),
    ("CNPJ FATURAMENTO", "{{ cnpj }}", None),
    ("CIDADE/", "{{ cidade_estado }}", None),
    ("IMAGEM PLANTA", "{{ imagem_planta }}", "img"),
    ("TABELA COMPILAÇÃO LINHAS", "tab_comp_linhas", "tab"),
    ("TABELA COMPILAÇÃO GERAL", "tab_comp_geral", "tab"),
    ("TABELA CONSUMO", "tab_consumo", "tab"),
    ("TABELA ESTUDO LUMINOTÉCNICO", "tab_lumino", "tab"),
    ("TABELA RESUMO PAINÉIS", "tab_resumo_paineis", "tab"),
    ("TABELA DE EXCLUSÕES", "tab_exclusoes", "tab"),
    ("TABELA DE ORÇAMENTO", "tab_orcamento", "tab"),
    ("TABELA DE FORMAS DE PAGAMENTO", "tab_pagamento", "tab"),
    ("TABELA DE DADOS DE FATURAMENTO", "tab_faturamento", "tab"),
    ("NOME VENDENDOR", "{{ vendedor_nome }}", None),
    ("NOME VENDEDOR", "{{ vendedor_nome }}", None),
    ("TÍTULO CARGO", "{{ vendedor_cargo }}", None),
    ("TELEFONE VENDEDOR", "{{ vendedor_telefone }}", None),
    ("EMAIL VENDEDOR", "{{ vendedor_email }}", None),
    ("EMPRESA USUÁRIO", "{{ empresa_contratada }}", None),
]

# Placeholder no meio de um texto maior -> troca direta (inline).
MAPA_INLINE = [
    ("[EMPRESA DO USUÁRIO]", "{{ empresa_contratada }}"),
    ("[EMPRESA USUÁRIO]", "{{ empresa_contratada }}"),
    ("[EMBARQUE EQUIPAMENTOS]", "{{ embarque_equipamentos }}"),
    ("[EMBARQUE ISOPAINÉIS]", "{{ embarque_isopainel }}"),
    ("[EMBARQUE ISOPAINEL]", "{{ embarque_isopainel }}"),
    ("[DIAS PROPOSTA]", "{{ dias_proposta }}"),
    ("[MESES GARANTIA]", "{{ meses_garantia }}"),
    ("[TIPO PAINEL]", "{{ tipo_painel }}"),
    ("[CONTATO]", "{{ contato }}"),
    # Rede de segurança: qualquer "[EMPRESA CONTRATADA]"/"Empresa contratada" escrito como texto
    # também vira o nome da empresa do usuário (item 1).
    ("[EMPRESA CONTRATADA]", "{{ empresa_contratada }}"),
    ("[EMPRESA DA CONTRATADA]", "{{ empresa_contratada }}"),
    ("Empresa contratada", "{{ empresa_contratada }}"),
    ("Empresa Contratada", "{{ empresa_contratada }}"),
    ("EMPRESA CONTRATADA", "{{ empresa_contratada }}"),
]

# Cada [TABELA ...] gera uma legenda "Tabela N"; cada [IMAGEM ...] gera "Figura N". A legenda usa a
# chave do último visual para o texto descritivo (legenda_<chave>), definido no gerador.
_VISUAL_POR_CHAVE = {
    "tab_comp_linhas": "comp_linhas", "tab_comp_geral": "comp_geral", "tab_consumo": "consumo",
    "tab_lumino": "lumino", "tab_resumo_paineis": "resumo_paineis", "tab_exclusoes": "exclusoes",
    "tab_orcamento": "orcamento", "tab_pagamento": "pagamento", "tab_faturamento": "faturamento",
}


def _texto(p):
    return "".join(r.text for r in p.runs)


def _remover(p):
    p._element.getparent().remove(p._element)


def _set_texto(p, novo):
    if p.runs:
        p.runs[0].text = novo
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(novo)


def _p_element(texto):
    p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = texto
    r.append(t)
    p.append(r)
    return p


def _set_loop(p, nome):
    """Transforma o parágrafo do marcador de tabela em um laço docxtpl de 3 parágrafos:
        {%p for _i in nome %}
        {{ _i }}
        {%p endfor %}
    O gerador passa nome -> [subdoc] com a tabela nativa; o Word abre normalmente (tabela nativa em
    subdoc é compatível; imagem em subdoc não é — por isso só tabelas entram aqui)."""
    _set_texto(p, "{%%p for _i in %s %%}" % nome)
    e_item = _p_element("{{ _i }}")
    p._p.addnext(e_item)
    e_end = _p_element("{%p endfor %}")
    e_item.addnext(e_end)


def construir():
    if not MODELO_PADRAO.exists():
        raise FileNotFoundError(f"Modelo padrão (ChatGPT) não encontrado: {MODELO_PADRAO}")
    doc = Document(str(MODELO_PADRAO))

    ultimo_visual = None      # chave do último visual, p/ o texto da legenda (legenda_<chave>)
    n_tabela = 0              # contador ABNT de tabelas
    n_figura = 0              # contador ABNT de figuras
    apagando = None           # 'equip' | 'detalhes' — apagando o bloco-EXEMPLO do ChatGPT
    paineis_inserido = False  # marcador de especificações de painéis/portas já inserido?

    for p in list(doc.paragraphs):
        txt = _texto(p).strip()
        up = txt.upper()

        # --- nota instrucional "{...}" do modelo: removida ---
        if txt.startswith("{"):
            _remover(p); continue

        # --- ESCOPO: o conteúdo vem do SISTEMA (não do exemplo do ChatGPT). Os blocos-exemplo do
        #     modelo são substituídos por marcadores que o gerador preenche depois do render, com
        #     o MESMO layout (título numerado + foto flutuante no canto + texto ao redor). ---
        if apagando == "equip":
            if up.startswith("MONTAGEM DE ISOPAIN"):
                apagando = None            # fim do bloco de equipamentos; segue processando a seção
            else:
                _remover(p); continue
        if apagando == "detalhes":
            if up.startswith("SERVIÇOS DE MONTAGEM"):
                apagando = None
            else:
                _remover(p); continue
        if txt.startswith("Forçador de Ar"):
            _set_loop(p, "escopo_equipamentos"); apagando = "equip"; continue
        if txt.startswith("Suportes de tubulação"):
            _set_loop(p, "detalhes_instalacao"); apagando = "detalhes"; continue
        # especificações de painéis/portas (do sistema) entram ao final da seção de isopainéis,
        # logo antes de "Detalhes de Instalação" — como um laço docxtpl de 3 parágrafos.
        if not paineis_inserido and up.startswith("DETALHES DE INSTALAÇÃO"):
            ini = _p_element("{%p for _i in escopo_paineis %}")
            item = _p_element("{{ _i }}")
            fim = _p_element("{%p endfor %}")
            p._p.addprevious(ini); ini.addnext(item); item.addnext(fim)
            paineis_inserido = True
            e_if = _p_element("{%p if detalhes_instalacao %}")
            p._p.addprevious(e_if)
            e_endif = _p_element("{%p endif %}")
            p._p.addnext(e_endif)

        # --- placeholder que ocupa o parágrafo inteiro (campo, imagem ou tabela) ---
        if txt.startswith("[") and txt.endswith("]"):
            tratou = False
            for chave, tag, tipo in MAPA_INTEIRO:
                if chave in up:
                    if tipo == "tab":
                        _set_loop(p, tag)               # tabela nativa via laço de subdoc
                        ultimo_visual = _VISUAL_POR_CHAVE.get(tag, "geral")
                    elif tipo == "img":
                        _set_texto(p, tag)
                        ultimo_visual = "planta" if "PLANTA" in up else "logo"
                    else:
                        _set_texto(p, tag)
                    tratou = True
                    break
            if tratou:
                continue

        # --- legendas automáticas numeradas (ABNT) ---
        if "LEGENDA TABELA" in up:
            n_tabela += 1
            chave_leg = ultimo_visual or "geral"
            e_if = _p_element("{%%p if legenda_%s %%}" % chave_leg)
            p._p.addprevious(e_if)
            _set_texto(p, "Tabela %d — {{ legenda_%s }}" % (n_tabela, chave_leg))
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            pPr = p._p.get_or_add_pPr()
            if pPr.find(qn("w:keepNext")) is None:
                pPr.append(OxmlElement("w:keepNext"))
            e_endif = _p_element("{%p endif %}")
            p._p.addnext(e_endif)
            continue
        if "LEGENDA IMAGEM" in up:
            n_figura += 1
            chave_leg = ultimo_visual or "geral"
            e_if = _p_element("{%%p if legenda_%s %%}" % chave_leg)
            p._p.addprevious(e_if)
            _set_texto(p, "Figura %d — {{ legenda_%s }}" % (n_figura, chave_leg))
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            pPr = p._p.get_or_add_pPr()
            if pPr.find(qn("w:keepNext")) is None:
                pPr.append(OxmlElement("w:keepNext"))
            e_endif = _p_element("{%p endif %}")
            p._p.addnext(e_endif)
            continue

        # --- substituições inline (placeholder no meio de um texto) ---
        novo = _texto(p)
        for alvo, tag in MAPA_INLINE:
            if alvo in novo:
                novo = novo.replace(alvo, tag)

        # --- texto padrão "(...)": remove os parênteses-marcadores externos e mantém o texto ---
        if "A/C" in novo and "{{ contato }}" in novo:
            novo = "A/C Sr.(a) {{ contato }}"   # trata o "(A/C Sr.(a))" à parte (tem "(a)" interno)
        else:
            if novo.lstrip().startswith("("):
                novo = novo.replace("(", "", 1)
            if novo.rstrip().endswith(")"):
                novo = "".join(novo.rsplit(")", 1))

        if novo != _texto(p):
            _set_texto(p, novo)
        # o restante fica INTACTO (títulos/listas do template).

    # --- remove CAIXAS DE TEXTO de instrução (legenda da convenção, notas na capa) ---
    _remover_caixas_instrucao(doc)
    # --- compacta a CAPA para caber tudo na 1ª página ---
    _compactar_capa(doc)
    # --- NUNCA título sozinho: cola cada título de seção ao conteúdo seguinte (keepNext) ---
    _colar_titulos(doc)
    # --- seções condicionais: título só aparece quando há dados (ECMA-376 / docxtpl §if) ---
    _condicionar_titulos(doc)

    doc.save(str(TEMPLATE_SAIDA))
    return TEMPLATE_SAIDA


def _compactar_capa(doc):
    """Mantém o LAYOUT da capa (logomarca no topo, título ao centro, dados do cliente embaixo à
    direita) e apenas REDUZ o espaçamento — encolhe a altura das linhas vazias — para que tudo caiba
    na 1ª página, sem eliminar a distribuição vertical."""
    for p in list(doc.paragraphs):
        if p.text.strip().upper().startswith("LAYOUT DE INSTALAÇÃO"):
            break
        tem_img = p._p.find(".//" + qn("w:drawing")) is not None or p._p.find(".//" + qn("w:pict")) is not None
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        if not p.text.strip() and not tem_img:
            p.paragraph_format.line_spacing = Pt(9)         # linha vazia baixa (encolhe o vão)


def _colar_titulos(doc):
    """Aplica keepNext em cada TÍTULO/SUBTÍTULO de seção para nunca ficar sozinho no fim da página
    (quando não couber, o Word joga o título junto com o conteúdo para a próxima página). Heurística:
    parágrafo de estilo de título/lista, curto e SEM pontuação final (títulos), diferente dos itens
    de lista (que terminam com ';' ou '.')."""
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        # LAYOUT DE INSTALAÇÃO (1ª seção) sempre começa no topo da página 2 (capa fica sozinha na 1ª)
        # GARANTIA sempre começa em página nova (item 5)
        if t.upper().startswith("LAYOUT DE INSTALAÇÃO") or t.upper().startswith("GARANTIA"):
            p.paragraph_format.page_break_before = True
        estilo = (p.style.name or "") if p.style is not None else ""
        eh_lista_ou_titulo = ("List Paragraph" in estilo) or estilo.lower().startswith("heading") or "título" in estilo.lower()
        if not eh_lista_ou_titulo:
            continue
        if len(t) <= 70 and not t.endswith((";", ".", ",", ":")):
            pPr = p._p.get_or_add_pPr()
            if pPr.find(qn("w:keepNext")) is None:
                pPr.append(OxmlElement("w:keepNext"))
            if pPr.find(qn("w:keepLines")) is None:
                pPr.append(OxmlElement("w:keepLines"))


_TITULO_CONDICIONAL = {
    "DISTRIBUICAO DE LINHAS": "tab_comp_linhas",
    "PARAMETRO DE DIMENSIONAMENTO": "tab_comp_geral",
    "ESTUDO DE CONSUMO ELETRICO": "tab_consumo",
    "ESTUDO LUMINOTECNICO": "tab_lumino",
    "MONTAGEM DE ISOPAINEIS": "escopo_paineis",
    "FORMA DE PAGAMENTO": "tab_pagamento",
    "DADOS DE FATURAMENTO": "tab_faturamento",
}


def _condicionar_titulos(doc):
    """Envolve cada título de seção de dados em {%p if variavel %}...{%p endif %} para que
    títulos sem dados associados não apareçam no documento gerado (seções 100% dinâmicas,
    conforme ISO 29500 / docxtpl conditional blocks)."""
    import unicodedata
    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        norm = unicodedata.normalize("NFKD", txt.upper()).encode("ascii", "ignore").decode()
        norm = " ".join(norm.split())
        for chave, var in _TITULO_CONDICIONAL.items():
            if norm.startswith(chave):
                e_if = _p_element("{%%p if %s %%}" % var)
                p._p.addprevious(e_if)
                e_endif = _p_element("{%p endif %}")
                p._p.addnext(e_endif)
                break


def _remover_caixas_instrucao(doc):
    """Remove do CORPO todos os balões/anotações do usuário e o retângulo vermelho da capa — ou seja,
    CAIXAS DE TEXTO e FORMAS (shapes) que NÃO são imagem. Mantém as fotos e a logomarca (drawings
    com imagem: a:blip ou v:imagedata)."""
    body = doc.element.body
    A_BLIP = qn("a:blip")
    V_IMG = "{urn:schemas-microsoft-com:vml}imagedata"   # 'v' (VML) não está no nsmap do python-docx
    TXBX = qn("w:txbxContent")
    alvos = []
    for tag in ("w:drawing", "w:pict"):
        for el in body.findall(".//" + tag if False else ".//" + qn(tag)):
            tem_imagem = (el.find(".//" + A_BLIP) is not None) or (el.find(".//" + V_IMG) is not None)
            eh_caixa_texto = el.find(".//" + TXBX) is not None
            if eh_caixa_texto or not tem_imagem:      # caixa de texto (balão) OU forma sem imagem (retângulo)
                alvos.append(el)
    for el in alvos:
        run = el
        while run is not None and run.tag != qn("w:r"):
            run = run.getparent()
        alvo = run if run is not None else el
        pai = alvo.getparent()
        if pai is not None:
            pai.remove(alvo)


def garantir_template():
    """Reconstrói SEMPRE o template a partir do modelo (item 1: nunca usar um template em cache
    antigo). É rápido e garante que qualquer mudança no mapeamento de tokens já valha.
    Se o diretório padrão não for gravável (Electron empacotado), usa temp."""
    global TEMPLATE_SAIDA
    try:
        construir()
    except PermissionError:
        import tempfile
        TEMPLATE_SAIDA = Path(tempfile.gettempdir()) / "ct_template_proposta.docx"
        construir()
    return TEMPLATE_SAIDA


if __name__ == "__main__":
    caminho = construir()
    print("Template gerado:", caminho)
    d = Document(str(caminho))
    for i, p in enumerate(d.paragraphs):
        t = p.text.strip()
        if t:
            print(f"[{i:03d}] {t[:100]}")
