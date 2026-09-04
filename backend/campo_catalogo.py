# -*- coding: utf-8 -*-
"""Motor genérico de código comercial por catálogo — usado por Unidades Condensadoras e (depois)
Forçadores. Cada catálogo define sua PRÓPRIA lista ordenada de Campos (ver models.CampoCatalogo),
em vez de uma ordem fixa no código-fonte, porque fabricantes diferentes têm estruturas de código
diferentes."""
import re
from sqlalchemy.orm import Session
from . import models as m

_RE_TENSAO_V = re.compile(r"(\d+)\s*V", re.I)
_RE_TENSAO_F = re.compile(r"(\d+)\s*F", re.I)
_RE_TENSAO_HZ = re.compile(r"(\d+)\s*Hz", re.I)


def _normalizar_tensao(texto):
    """Extrai (volts, fases, freq) de qualquer formato de tensão usado no app ou digitado num
    catálogo (ex.: '220V/1F/60Hz' do projeto, '220V-1F 50-60Hz' de um catálogo Elgin, '380V/3F/50Hz'
    de um catálogo Mipal que lista 50Hz e 60Hz como opções SEPARADAS pra mesma Volts+Fases — por
    isso a frequência agora entra na comparação (antes era ignorada assumindo "Brasil só usa 60Hz",
    o que quebrava exatamente esse caso: 380V/3F/50Hz e 380V/3F/60Hz "empatavam" e o sistema pegava
    sempre o primeiro da lista, errado).
    freq: None quando o texto não define uma frequência única (nenhum Hz encontrado, ou combinado
    tipo "50-60Hz"/"50/60Hz") — funciona como coringa na comparação, pra não quebrar catálogos como
    o Elgin que não separam por Hz.
    Devolve (None, None, None) se não achar Volts+Fases, pra nunca "quase-casar" por acidente."""
    if not texto:
        return None, None, None
    mv = _RE_TENSAO_V.search(texto)
    mf = _RE_TENSAO_F.search(texto)
    if not mv or not mf:
        return None, None, None
    freqs = {int(h) for h in _RE_TENSAO_HZ.findall(texto)}
    freq = freqs.pop() if len(freqs) == 1 else None
    return int(mv.group(1)), int(mf.group(1)), freq


def _tensao_compativel(alvo, opcao):
    """Compara (volts, fases, freq) com coringa em freq=None de qualquer um dos dois lados."""
    av, af, ahz = alvo
    ov, of, ohz = opcao
    if av is None or ov is None or av != ov or af != of:
        return False
    return ahz is None or ohz is None or ahz == ohz

# Colunas da aba "Campos" da planilha de importação — o script de extração (que é POR FABRICANTE)
# emite a estrutura do código comercial já pronta aqui, e o importador só persiste (sem nenhuma
# suposição fixa de ordem/estrutura no importador genérico). Uma linha por OPÇÃO; os campos de nível
# Campo (Modo/Busca/Coringa/Codigo_Fixo) repetem em todas as linhas do mesmo Nome_Campo.
COLUNAS_CAMPOS = ["Ordem", "Nome_Campo", "Modo", "Campo_Busca_Sistema", "Substitui_Coringa",
                  "Codigo_Fixo", "Valor", "Codigo"]


def _verdadeiro(v):
    return str(v).strip().lower() in ("1", "true", "sim", "x", "s", "verdadeiro")


# Mapeamento categoria da Nomenclatura -> Campo do código comercial, no padrão Elgin (os 3 catálogos
# UC extraídos hoje são todos Elgin). (categoria, nome_campo, modo, campo_busca_sistema, coringa).
# categoria=None => campo sem tabela de código (Nº Compressores: opções 1/2/3 idênticas). Outro
# fabricante definiria o SEU mapa (cada fabricante tem sua estrutura de código).
MAPA_CAMPOS_ELGIN_UC = [
    ("Fluxo de Ar", "Fluxo de Ar", "manual", None, True),
    ("Tensão", "Tensão", "automatico", "tensao", False),
    ("Linha de Líquido", "Linha de Líquido", "manual", None, False),
    ("Fabricante Compressor", "Fabricante Compressor", "automatico", "fabricante_compressor", False),
    (None, "Nº Compressores", "automatico", "numero_compressores", False),
    ("Versão", "Versão", "manual", None, False),
    ("Opcional Mecânico", "Opcional Mecânico", "manual", None, False),
    ("Opcional Elétrico", "Opcional Elétrico", "manual", None, False),
]


def campos_de_nomenclatura(nomencl, mapa):
    """Constrói a estrutura de Campos a partir de uma lista de nomenclatura (tuplas
    (categoria, valor, codigo)) e um mapa fabricante-específico. Usado pelos scripts de extração pra
    emitir a aba 'Campos' já pronta na planilha de importação."""
    por_cat = {}
    for categoria, valor, codigo in nomencl:
        por_cat.setdefault(categoria, []).append((valor, codigo))
    campos = []
    for categoria, nome, modo, busca, coringa in mapa:
        if categoria is None:
            opcoes = [{"valor": "1", "codigo": "1"}, {"valor": "2", "codigo": "2"}, {"valor": "3", "codigo": "3"}]
        else:
            opcoes = [{"valor": v, "codigo": c} for v, c in por_cat.get(categoria, [])]
        campos.append({"nome_campo": nome, "modo": modo, "campo_busca_sistema": busca,
                       "codigo_fixo": None, "substitui_coringa_modelo": coringa, "opcoes": opcoes})
    return campos


def campos_de_linhas_planilha(linhas):
    """Converte as linhas da aba 'Campos' (lista de dicts com COLUNAS_CAMPOS) na estrutura de Campos
    aceita por salvar_campos. Agrupa por Nome_Campo preservando a ordem de aparição."""
    por_campo = {}
    ordem_campos = []
    for r in linhas:
        nome = (r.get("Nome_Campo") or "").strip()
        if not nome:
            continue
        if nome not in por_campo:
            ordem_campos.append(nome)
            por_campo[nome] = {
                "nome_campo": nome,
                "modo": (r.get("Modo") or "manual").strip().lower(),
                "campo_busca_sistema": (r.get("Campo_Busca_Sistema") or None) or None,
                "codigo_fixo": (r.get("Codigo_Fixo") or None) or None,
                "substitui_coringa_modelo": _verdadeiro(r.get("Substitui_Coringa")),
                "opcoes": [],
            }
        valor = r.get("Valor")
        if valor is not None and str(valor).strip() != "":
            por_campo[nome]["opcoes"].append({"valor": str(valor).strip(),
                                              "codigo": ("" if r.get("Codigo") is None else str(r.get("Codigo")).strip())})
    return [por_campo[n] for n in ordem_campos]


def campos_para_linhas_planilha(campos):
    """Inverso: transforma a estrutura de Campos em linhas pra escrever na aba 'Campos' (exportação/
    template). Uma linha por opção; campos sem opção viram uma linha só com metadados."""
    out = []
    for i, c in enumerate(campos):
        base = {"Ordem": i, "Nome_Campo": c.get("nome_campo"), "Modo": c.get("modo", "manual"),
                "Campo_Busca_Sistema": c.get("campo_busca_sistema") or "",
                "Substitui_Coringa": 1 if c.get("substitui_coringa_modelo") else 0,
                "Codigo_Fixo": c.get("codigo_fixo") or ""}
        opcoes = c.get("opcoes") or []
        if not opcoes:
            out.append({**base, "Valor": "", "Codigo": ""})
        for o in opcoes:
            out.append({**base, "Valor": o.get("valor", ""), "Codigo": o.get("codigo", "")})
    return out


def listar_campos(db: Session, tipo_catalogo: str, catalogo_id: int):
    return (db.query(m.CampoCatalogo)
            .filter_by(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id)
            .order_by(m.CampoCatalogo.ordem).all())


def opcoes_automatico(db: Session, tipo_catalogo: str, catalogo_id: int, campo_busca_sistema: str):
    """Lista de Valor das opções de um campo Automático específico do catálogo (ex.: os tipos de
    degelo que a NOMENCLATURA comercial desse catálogo realmente tem cadastrado) — fonte mais
    confiável que o campo técnico genérico da matriz (modelo.tipo_degelo), que é texto livre do
    fabricante e pode ser genérico/impreciso pra uma linha inteira. None se o catálogo não tiver
    esse campo configurado (não dá pra afirmar nada, então quem chama não deve alertar)."""
    campo = (db.query(m.CampoCatalogo)
             .filter_by(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id, modo="automatico",
                        campo_busca_sistema=campo_busca_sistema).first())
    if not campo:
        return None
    return [o.valor for o in campo.opcoes]


def campos_para_dict(campos):
    return [{
        "id": c.id, "ordem": c.ordem, "nome_campo": c.nome_campo, "modo": c.modo,
        "campo_busca_sistema": c.campo_busca_sistema, "codigo_fixo": c.codigo_fixo,
        "substitui_coringa_modelo": c.substitui_coringa_modelo,
        "opcoes": [{"id": o.id, "valor": o.valor, "codigo": o.codigo, "ordem": o.ordem} for o in c.opcoes],
    } for c in campos]


def salvar_campos(db: Session, tipo_catalogo: str, catalogo_id: int, campos_payload: list):
    """Substitui a lista inteira de Campos do catálogo (mesmo padrão de salvar_nomenclatura do
    Forçador: reconstrói do zero a cada salvamento, mais simples que diff)."""
    ids_antigos = [c.id for c in db.query(m.CampoCatalogo.id)
                   .filter_by(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id).all()]
    if ids_antigos:
        # Bulk delete() do SQLAlchemy NÃO aciona cascade="all, delete-orphan" (isso só funciona pra
        # delete via sessão, objeto a objeto) — sem isso, as Opções filhas ficavam órfãs no banco e,
        # como os IDs são reaproveitados pelo SQLite, "religavam" em Campos novos de OUTRO catálogo
        # (bug real: editar um catálogo parecia afetar outro, e duplicidades voltavam depois de salvar).
        db.query(m.CampoCatalogoOpcao).filter(m.CampoCatalogoOpcao.campo_id.in_(ids_antigos)).delete(synchronize_session=False)
        db.query(m.CampoCatalogo).filter_by(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id).delete()
    db.flush()
    for i, c in enumerate(campos_payload):
        campo = m.CampoCatalogo(
            tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id, ordem=i,
            nome_campo=c["nome_campo"], modo=c.get("modo", "manual"),
            campo_busca_sistema=c.get("campo_busca_sistema") or None,
            codigo_fixo=c.get("codigo_fixo") or None,
            substitui_coringa_modelo=bool(c.get("substitui_coringa_modelo")))
        db.add(campo)
        db.flush()
        for j, o in enumerate(c.get("opcoes") or []):
            if not o.get("valor"):
                continue
            db.add(m.CampoCatalogoOpcao(campo_id=campo.id, valor=o["valor"], codigo=o.get("codigo") or "", ordem=j))
    db.commit()
    return campos_para_dict(listar_campos(db, tipo_catalogo, catalogo_id))


def _codigo_do_campo(campo, contexto, selecoes_manuais, modelo_base=""):
    if campo.modo == "modelo_pesquisa":
        # Card especial: valor = o próprio modelo técnico (ex.: "0062", "FL*017"), não editável
        # pelo usuário — só a POSIÇÃO dele na nomenclatura é livre (arrasta como qualquer card).
        return modelo_base
    if campo.modo == "fixo":
        return campo.codigo_fixo or ""
    if campo.modo == "automatico":
        # "tensao" é chave legada (catálogos importados antes do desdobro Comando/Equipamentos) —
        # trata como Comando, com fallback pra Equipamentos, pra não quebrar código já cadastrado.
        busca = campo.campo_busca_sistema
        if busca == "tensao":
            valor = contexto.get("tensao_comando") or contexto.get("tensao_equipamentos")
        else:
            valor = contexto.get(busca)
        if valor is None:
            return ""
        if busca in ("tensao", "tensao_comando", "tensao_equipamentos"):
            # Tensão pode vir em formatos diferentes (ex.: "220V/1F/60Hz" do projeto vs
            # "220V-1F 50-60Hz" digitado no catálogo importado) — compara por Volts+Fases (+Hz
            # quando as duas frequências existem separadas no catálogo, ver _tensao_compativel).
            alvo = _normalizar_tensao(valor)
            candidatas = [o for o in campo.opcoes if alvo[0] is not None and _tensao_compativel(alvo, _normalizar_tensao(o.valor))]
            # Entre as compatíveis, prioriza a que também bate a frequência exata (evita pegar uma
            # opção 50Hz por acidente quando existe a 60Hz certa, ambas "compatíveis" por coringa).
            opcao = next((o for o in candidatas if _normalizar_tensao(o.valor)[2] == alvo[2]), candidatas[0] if candidatas else None)
        else:
            opcao = next((o for o in campo.opcoes if o.valor == valor), None)
        return opcao.codigo if opcao else ""
    if campo.modo == "manual":
        valor = selecoes_manuais.get(campo.nome_campo)
        opcao = next((o for o in campo.opcoes if o.valor == valor), None) if valor else None
        # Sem seleção ainda: "*" no lugar (não pula o campo em silêncio) — sinaliza visualmente
        # no código que falta escolher essa peça.
        return opcao.codigo if opcao else "*"
    if campo.modo == "ignorar":
        # Campo existe na nomenclatura (aparece na Tela 2/3, não editável) mas não entra no
        # código comercial — não concatena nada, passa pro próximo campo.
        return ""
    return ""


def montar_codigo(db: Session, tipo_catalogo: str, catalogo_id: int, modelo_base: str = "",
                   contexto: dict = None, selecoes_manuais: dict = None) -> str:
    """Monta o código comercial a partir da lista de Campos do catálogo, na ordem cadastrada.
    PADRÃO ÚNICO DO SISTEMA (nunca resolver isso por fabricante/linha) — o modelo técnico não é
    mais um prefixo fixo hardcoded: é só mais um Campo (modo="modelo_pesquisa") que participa da
    MESMA lista ordenada dos demais, na posição em que o usuário arrastou (ver models.CampoCatalogo).
    modelo_base: código-base do modelo (pode ter um '*' coringa, ex.: "FL*017", ou não, ex.: "0062")
      — é o valor do card "Modelo Pesquisa", onde quer que ele esteja na ordem.
    contexto: valores já conhecidos do sistema/unidade (ex.: {"tensao": "380V/3F", "gas": "R-404A"}),
      usado nos campos em modo automático.
    selecoes_manuais: {nome_campo: valor_escolhido}, usado nos campos em modo manual."""
    contexto = contexto or {}
    selecoes_manuais = selecoes_manuais or {}
    partes = []
    coringa_codigo = None
    for campo in listar_campos(db, tipo_catalogo, catalogo_id):
        valor_codigo = _codigo_do_campo(campo, contexto, selecoes_manuais, modelo_base)
        if not valor_codigo:
            continue
        if campo.substitui_coringa_modelo:
            # Campo que ocupa o coringa '*' do "Modelo Pesquisa" — guardado à parte, aplicado
            # DEPOIS de montar a sequência inteira, pra achar o '*' onde quer que ele tenha caído.
            coringa_codigo = valor_codigo
        else:
            partes.append(valor_codigo)
    codigo = "".join(partes)
    if coringa_codigo is not None:
        if "*" in codigo:
            codigo = codigo.replace("*", coringa_codigo, 1)
        else:
            # sem coringa no meio da sequência: nunca some em silêncio (bug real anterior) — entra
            # no início como prefixo.
            codigo = coringa_codigo + codigo
    return codigo
