# -*- coding: utf-8 -*-
"""Gera o "Documento de Importação" (.docx) do Catálogo de Condensadores Remotos — mesmo rito do
documento de Forçadores (docx_template.py), adaptado ao produto: 5 tabelas de fator de correção,
sem tabela elétrica separada, e Excel de saída com 3 abas (Modelos achatada, Fatores, Campos)."""
import io
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

CABECALHO_CAMPOS = [
    "Fabricante", "Linha", "Versão/Ano do Catálogo",
    "Tipo Estrutura (Plano - Fluxo Vertical / V - Fluxo Horizontal)", "DT de Catálogo (°C)",
    "Coluna Dimensional = Comprimento", "Coluna Dimensional = Largura", "Coluna Dimensional = Altura",
]

# As 5 tabelas de fator de correção do condensador (tipo -> lista de chaves pré-preenchidas). Os
# valores dos fatores ficam em branco no documento — o usuário consulta o catálogo e preenche.
FATORES = [
    ("Gás Refrigerante", "gas", ["R-134a", "R-22", "R-404A", "R-407A", "R-407C", "R-407F",
                                  "R-410A", "R-448A", "R-449A", "R-452A", "R-507"]),
    ("Material de Aletas", "aleta", ["Padrão", "Protegida"]),
    ("Altitude (Até, em metros)", "altitude", ["50", "600", "800", "1000", "1500", "2000"]),
    ("Temp. Entrada do Ar (Até, °C)", "temp_entrada_ar", ["15", "20", "25", "30", "35", "40", "45", "50"]),
]

SECOES_TABELAS = [
    ("1. Tabela Mecânica (Capacidades e Elétrica)",
     "Cole abaixo o(s) print(s) da tabela de capacidades (kcal/h), quantidade de ventiladores, "
     "diâmetro do ventilador (mm) — se o catálogo publicar, deixe em branco se não —, vazão de ar, "
     "nº de polos (AC) ou rotação (EC), nº de fileiras, potência, correntes (220/380/460V), nível "
     "de ruído e carga de refrigerante. No condensador NÃO há tabela elétrica separada — esses "
     "dados já vêm junto da mecânica."),
    ("2. Dados Físicos",
     "Cole abaixo o print da tabela de dados físicos (coletor de entrada/saída, peso líquido, "
     "peso bruto). Pode colar mais de uma imagem se o catálogo quebrar essas informações."),
    ("3. Dados Dimensionais",
     "Cole abaixo o print da tabela de dimensões. As colunas costumam vir com letras genéricas "
     "(A, B, C...) — preencha no cabeçalho acima qual letra corresponde a Comprimento/Largura/"
     "Altura. Se uma medida for FIXA para todos os modelos, digite o número direto no cabeçalho. "
     "Inclua também o número de fixações, se houver."),
    ("4. Nomenclatura do Código de Compra",
     "Cole abaixo o print da tabela que decompõe o código de compra do fabricante em campos "
     "(ex.: \"FLA-B-4-017\" onde B = tensão, 4 = aletas). Se o catálogo não tiver, deixe em branco."),
    ("5. Informações Gerais (opcional, para proposta comercial)",
     "Escreva abaixo um texto curto de descrição comercial por Tipo de Estrutura (o que aparecerá "
     "numa proposta ao cliente). A foto do equipamento NÃO vai por aqui — suba direto na Tela C do "
     "catálogo já criado, depois da importação."),
]

INSTRUCOES_IA = """Instruções para quem for processar este documento (IA ou humano, sem precisar de contexto prévio):

Objetivo: ler o cabeçalho preenchido (incluindo as 5 tabelas de Fator de Correção) e as imagens/textos das seções abaixo, e gerar um arquivo .xlsx com exatamente esta estrutura (3 abas):

Aba "Modelos" (achatada — UMA linha por modelo, todos os dados técnicos juntos): Fabricante, Linha, Versao_Catalogo, Tipo_Estrutura, DT_Catalogo_C, Modelo, FPI, Qtd_Ventiladores, Diametro_Ventilador_mm (em branco se o catálogo não publicar), Vazao_Ar_m3h, Polos_ou_RPM, Tipo_Motor, Num_Fileiras, Capacidade_kcal_h, Potencia_kW, Corrente_220V, Corrente_380V, Corrente_460V, Ruido_dB, Carga_Refrigerante_kg, Coletor_Entrada_pol, Coletor_Saida_pol, Peso_Liquido_kg, Peso_Bruto_kg, Comprimento_mm, Largura_mm, Altura_mm, Num_Fixacoes, Descricao_Comercial
Aba "Fatores": Fabricante, Linha, Tipo_Estrutura, Tipo_Fator, Chave, Fator — uma linha por chave de cada uma das 4 tabelas de fator do cabeçalho. Tipo_Fator deve ser exatamente um destes: gas, aleta, altitude, temp_entrada_ar. Chave é o rótulo da linha da tabela (ex.: "R-404A", "Padrão", "600", "35"). Se o usuário deixou um fator em branco, não inclua a linha. NÃO existe fator de delta de condensação — ver abaixo.
Aba "Campos": Fabricante, Linha, Tipo_Estrutura, Ordem, Nome_Campo, Modo, Campo_Busca_Sistema, Substitui_Coringa, Codigo_Fixo, Valor, Codigo — estrutura do código comercial (motor genérico do app, mesmo do Forçador/UC). Uma linha POR OPÇÃO de cada campo. REGRA OBRIGATÓRIA: todo campo entra com Modo = "manual" (Campo_Busca_Sistema e Codigo_Fixo em branco), só Valor/Codigo preenchidos com o que está literalmente na tabela de nomenclatura. Nunca decidir "automatico"/"fixo"/"ignorar" por conta própria — isso é decisão do usuário, feita depois na própria Tela C.

DIFERENÇAS IMPORTANTES DO CONDENSADOR (em relação ao Forçador):
- Capacidade é um VALOR ÚNICO por modelo (não uma tabela por temperatura de evaporação). A correção de capacidade é feita depois pelo app: primeiro a proporção de delta de condensação (capacidade de catálogo ÷ DT_Catalogo_C × delta de condensação do projeto — mesmo princípio do ΔT do forçador de ar), depois multiplicando os 4 fatores de tabela (gás, aleta, altitude, temp. entrada do ar).
- DT_Catalogo_C é OBRIGATÓRIO: sem ele o app não consegue corrigir o delta de condensação. É o delta de condensação em que as capacidades do catálogo foram medidas.
- NÃO existe aba Elétrica separada — motor/corrente/potência ficam na própria aba "Modelos".
- Tipo Estrutura (Plano/V) faz parte da IDENTIDADE do catálogo: se o mesmo catálogo físico traz os dois tipos, gere DUAS linhas na aba Modelos com Tipo_Estrutura diferente — o app trata cada uma como um catálogo separado (texto/foto comerciais próprios).
- Polos_ou_RPM: se o motor é AC, preencha o número de polos; se é EC, a rotação em RPM. Tipo_Motor = "AC" ou "EC".
- Campos que constam em alguns fabricantes e em outros não: mantenha a coluna padrão, apenas deixe a célula em branco.
- As informações faltantes de um modelo devem ser buscadas em TODAS as imagens coladas (o catálogo costuma quebrar os dados em várias tabelas) — dificilmente algo fica de fora.

SEM AUTONOMIA: quem processa este documento não tem autonomia para nenhuma decisão de mapeamento, valor ou estrutura além do que está literalmente escrito. Qualquer ambiguidade ou dado faltante deve ser perguntado ao usuário — nunca resolvido por conta própria. Sempre mostre os dados extraídos em tabela, para revisão e confirmação, antes de gerar o .xlsx.

CAMINHO OBRIGATÓRIO DE SALVAMENTO: o .xlsx final deve ser salvo em "B:\\Documentos Programas\\App Carga Térmica\\Documentos de Criação\\A - Catálogos\\4 - Condensadores\\", nome "Importacao_{Fabricante}_{Linha}.xlsx" — nunca em pasta temporária."""


def _titulo(doc, texto, tamanho=16, cor=RGBColor(0x11, 0x18, 0x27)):
    p = doc.add_paragraph()
    run = p.add_run(texto)
    run.bold = True
    run.font.size = Pt(tamanho)
    run.font.color.rgb = cor
    return p


def _placeholder(doc):
    tabela = doc.add_table(rows=1, cols=1)
    tabela.style = "Table Grid"
    celula = tabela.cell(0, 0)
    celula.text = "[Cole a imagem aqui]"
    for paragrafo in celula.paragraphs:
        paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragrafo.runs:
            run.italic = True
            run.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)
    tabela.rows[0].height = Inches(2.2)
    doc.add_paragraph()


def gerar_documento_condensador() -> bytes:
    doc = Document()

    _titulo(doc, "Documento de Importação — Catálogo de Condensadores Remotos a Ar", 18)
    intro = doc.add_paragraph(
        "Preencha o cabeçalho abaixo e cole as imagens (prints) de cada tabela do catálogo nas "
        "seções indicadas. Depois, envie este arquivo numa conversa com o Claude pedindo para "
        "gerar a planilha Excel de importação do sistema Carga Térmica — não é preciso explicar "
        "nada além disso, as instruções já estão neste documento.")
    intro.runs[0].font.size = Pt(11)
    doc.add_paragraph()

    _titulo(doc, "Cabeçalho", 13)
    tabela_cab = doc.add_table(rows=len(CABECALHO_CAMPOS), cols=2)
    tabela_cab.style = "Table Grid"
    for i, campo in enumerate(CABECALHO_CAMPOS):
        cel = tabela_cab.cell(i, 0)
        cel.text = campo
        cel.paragraphs[0].runs[0].bold = True
        tabela_cab.cell(i, 1).text = ""
    doc.add_paragraph()

    _titulo(doc, "Fatores de Correção de Capacidade", 13)
    doc.add_paragraph(
        "Cada fabricante publica seus próprios fatores — consulte o catálogo e preencha um valor "
        "por linha (deixe em branco o que não constar). ATENÇÃO: o delta de condensação NÃO entra "
        "aqui — ele é corrigido por proporção direta (capacidade de catálogo ÷ DT de Catálogo × "
        "delta do projeto), então basta preencher o campo \"DT de Catálogo (°C)\" no cabeçalho acima.")
    for nome_fator, _tipo, chaves in FATORES:
        p = doc.add_paragraph()
        p.add_run(nome_fator).bold = True
        tabela = doc.add_table(rows=len(chaves) + 1, cols=2)
        tabela.style = "Table Grid"
        tabela.cell(0, 0).paragraphs[0].add_run("Chave").bold = True
        tabela.cell(0, 1).paragraphs[0].add_run("Fator").bold = True
        for i, chave in enumerate(chaves, start=1):
            tabela.cell(i, 0).text = chave
            tabela.cell(i, 1).text = ""
        doc.add_paragraph()

    for titulo_secao, instrucao in SECOES_TABELAS:
        _titulo(doc, titulo_secao, 13)
        doc.add_paragraph(instrucao)
        if titulo_secao.startswith("5."):
            p = doc.add_paragraph()
            p.add_run("Descrição comercial: ").bold = True
            doc.add_paragraph("_" * 90)
        else:
            _placeholder(doc)

    doc.add_page_break()
    _titulo(doc, "Instruções para quem for processar este documento", 13, RGBColor(0xB4, 0x53, 0x09))
    for linha in INSTRUCOES_IA.split("\n"):
        p = doc.add_paragraph(linha or " ")
        p.runs[0].font.size = Pt(9)
        p.runs[0].font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
