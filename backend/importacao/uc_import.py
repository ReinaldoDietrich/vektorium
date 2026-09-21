# -*- coding: utf-8 -*-
"""Importação de Unidades Condensadoras via planilha Excel (Tela B). Estrutura de 5 abas:
Unidades, Eletricas, Capacidades, Nomenclatura, Fatores_Gas (esta última opcional). Lê célula por
célula pelo nome da coluna no cabeçalho — coluna ausente vira None, nunca dá erro (orientação:
colunas faltantes permanecem em branco no cadastro).

Aba Eletricas: uma linha por (Modelo × Tensão × Modelo de Compressor) — confirmado no catálogo real
que o mesmo Modelo+Tensão pode ter mais de uma opção de compressor, cada uma com corrente própria.
Físico/Dimensional NÃO varia por tensão, fica na aba Unidades (escalar)."""
import io
from datetime import datetime
import openpyxl
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models as m
from .. import campo_catalogo as cc
from .. import id_comercial

def _normalizar_sistema(valor):
    if not valor:
        return valor
    v = valor.strip().lower()
    if "alta" in v and "média" in v or "alta" in v and "media" in v:
        return "Alta e Média"
    if "média" in v and "baixa" in v or "media" in v and "baixa" in v:
        return "Média e Baixa"
    if "baixa" in v:
        return "Baixa"
    if "média" in v or "media" in v:
        return "Média"
    if "alta" in v:
        return "Alta"
    return valor

ABA_UNIDADES = "Unidades"
ABA_ELETRICAS = "Eletricas"
ABA_CAPACIDADES = "Capacidades"
ABA_CAMPOS = "Campos"

COLUNAS_UNIDADES = [
    "Fabricante_UC", "Nome_Catalogo", "Modelo", "Versao_Catalogo", "Sistema", "Gas", "Tipo_Compressor",
    "Fabricante_Compressor", "Numero_Compressores", "HP", "Vent_Qtd", "Conexao_Liquido", "Conexao_Succao",
    "Tanque_Liquido_L", "Nivel_Ruido_dB", "Ventilador_Diametro_mm", "Comprimento_mm",
    "Largura_mm", "Altura_mm", "Peso_Liquido_kg", "Peso_Bruto_kg", "Descricao_Comercial",
]
# Fabricante_UC + Nome_Catalogo + Versao_Catalogo identificam o CatalogoUC (find-or-create) — nome
# é obrigatório e PRÓPRIO do documento (a dupla Fabricante+Versão sozinha não diferencia catálogos
# distintos publicados na mesma data). Foto do catálogo é editada na tela, não faz parte da
# planilha (não há caminho de imagem pela planilha) — Descrição Comercial ENTRA na planilha
# (mesmo princípio do Forçador: coluna repetida por linha só por praticidade de preenchimento,
# o texto vale pro catálogo inteiro, usa a primeira não vazia — ver salvar_unidades).
COLUNAS_ELETRICAS = [
    "Modelo", "Fabricante_Compressor", "Tensao", "Fases", "Frequencia", "Modelo_Compressor", "MCC_A", "RLA_A", "LRA_A",
    "Vent_Tensao", "Vent_Fases", "Vent_Frequencia", "Vent_Corrente_A",
]
# Fabricante_Compressor é opcional aqui — só necessário quando o MESMO código de Modelo aparece sob
# mais de uma marca de compressor no catálogo (ex.: U*HMB4120 tanto sob Bitzer quanto sob Dorin, com
# elétrica/capacidade diferentes cada). Em branco = aplica a todas as unidades com esse Modelo.
# Gas TAMBÉM é obrigatório aqui — o mesmo código mecânico frequentemente cobre 2+ gases (ex.:
# R-404A/R-507 numa faixa de colunas do catálogo, R-134a ou R-448A/R-449A noutra) com faixas de
# Temp_Evaporacao_C que SE SOBREPÕEM mas capacidades DIFERENTES na mesma (Temp_Ambiente,
# Temp_Evaporacao) — sem Gas aqui pra desambiguar, a linha de um gás pode ser atribuída à unidade
# do gás errado (bug real, encontrado em produção: 644 de 1020 combinações conflitantes no catálogo
# US 10-66HP por essa causa). Em branco = aplica a todas as unidades com esse Modelo+Fabricante,
# só pra compatibilidade com planilhas antigas onde o catálogo não tinha essa sobreposição.
COLUNAS_CAPACIDADES = ["Modelo", "Fabricante_Compressor", "Gas", "Temp_Ambiente_C", "Temp_Evaporacao_C", "Capacidade_kcal_h", "Potencia_kW"]

# Mapa coluna Excel -> atributo do modelo UnidadeCondensadora (Fabricante_UC/Nome_Catalogo/
# Versao_Catalogo NÃO entram aqui — resolvem o CatalogoUC via find-or-create, ver salvar_unidades)
_MAP_UNIDADE = {
    "Modelo": "modelo", "Sistema": "sistema", "Gas": "gas", "Tipo_Compressor": "tipo_compressor",
    "Fabricante_Compressor": "fabricante_compressor",
    "Numero_Compressores": "numero_compressores",
    "HP": "hp", "Vent_Qtd": "vent_qtd",
    "Conexao_Liquido": "conexao_liquido", "Conexao_Succao": "conexao_succao",
    "Tanque_Liquido_L": "tanque_liquido_l", "Nivel_Ruido_dB": "nivel_ruido_db",
    "Ventilador_Diametro_mm": "ventilador_diametro_mm", "Comprimento_mm": "comprimento_mm",
    "Largura_mm": "largura_mm", "Altura_mm": "altura_mm", "Peso_Liquido_kg": "peso_liquido_kg",
    "Peso_Bruto_kg": "peso_bruto_kg",
}

# Mapa coluna Excel -> atributo do modelo EletricaUC
_MAP_ELETRICA = {
    "Tensao": "tensao", "Fases": "fases", "Frequencia": "frequencia", "Modelo_Compressor": "modelo_compressor",
    "MCC_A": "mcc_a", "RLA_A": "rla_a", "LRA_A": "lra_a", "Vent_Tensao": "vent_tensao",
    "Vent_Fases": "vent_fases", "Vent_Frequencia": "vent_frequencia", "Vent_Corrente_A": "vent_corrente_a",
}


def gerar_template_uc() -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(ABA_UNIDADES)
    ws.append(COLUNAS_UNIDADES)
    ws.append(["Elgin", "US 10 a 66HP - 2 e 3 Compressores", "U*HMB4250", "01/2024", "Média e Baixa", "R-404a",
               "Semi-Hermético", "Dorin", 2, 25, 3, "1.1/8", "2.1/8", 70, 78, 630, 2965, 1485, 1512, 757, 973,
               "Unidade condensadora comercial de alta eficiência, com compressores Dorin semi-herméticos."])
    ws1b = wb.create_sheet(ABA_ELETRICAS)
    ws1b.append(COLUNAS_ELETRICAS)
    ws1b.append(["U*HMB4250", "Dorin", "380V", 3, "60Hz", "H2201CC", 54, 34.62, 244, "380V", 3, "60/50", 5.7])
    ws1b.append(["U*HMB4250", "Dorin", "220V", 3, "60Hz", "H2201CC", 90, 57.69, 393, "220V", 3, "60/50", 9.9])
    ws2 = wb.create_sheet(ABA_CAPACIDADES)
    ws2.append(COLUNAS_CAPACIDADES)
    ws2.append(["U*HMB4250", "Dorin", "R-404a", 32, 5, 46476, 18.69])
    ws2.append(["U*HMB4250", "Dorin", "R-404a", 32, 0, 38694, 17.03])
    ws2.append(["U*HMB4250", "Dorin", "R-404a", 35, 5, 44129, 19.19])
    ws3 = wb.create_sheet(ABA_CAMPOS)
    ws3.append(cc.COLUNAS_CAMPOS)
    # "Modelo Pesquisa": card especial, no máximo 1 por catálogo — valor = o próprio texto da
    # coluna Modelo (aba Unidades, ex.: "U*HMB4250"), não editável depois; só a POSIÇÃO na
    # nomenclatura é livre (arrastável em Configurações/Tela B). Padrão único do sistema, mesmo do
    # Forçador/Condensador — nunca criar Campo "prefixo fixo" tentando simular isso.
    ws3.append([0, "Modelo Pesquisa", "modelo_pesquisa", None, 0, None, None, None])
    ws3.append([1, "Sistema", "manual", None, 0, None, "Média e Baixa", "4"])
    ws3.append([1, "Sistema", "manual", None, 0, None, "Alta", "2"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _ler_aba(wb, nome_aba, colunas):
    if nome_aba not in wb.sheetnames:
        return []
    ws = wb[nome_aba]
    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        return []
    cab = [str(c).strip() if c is not None else "" for c in linhas[0]]
    idx = {col: cab.index(col) for col in colunas if col in cab}
    out = []
    for linha in linhas[1:]:
        if not linha or all(v is None for v in linha):
            continue
        reg = {col: (linha[idx[col]] if col in idx and idx[col] < len(linha) else None) for col in colunas}
        out.append(reg)
    return out


def ler_planilha_uc(conteudo: bytes):
    """Devolve (unidades, eletricas_por_modelo, capacidades_por_modelo, campos) a partir do Excel.
    eletricas_por_modelo é chaveado por (Modelo, Fabricante_Compressor) — necessário porque o MESMO
    código de Modelo pode aparecer sob mais de uma marca de compressor no catálogo, cada uma com
    dados diferentes (regra 1). capacidades_por_modelo é chaveado por (Modelo, Fabricante_Compressor,
    Gas) — Gas entra na chave porque o mesmo Modelo cobre gases diferentes com faixas de evaporação
    que se sobrepõem mas capacidades diferentes (ver nota em COLUNAS_CAPACIDADES)."""
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    unidades = _ler_aba(wb, ABA_UNIDADES, COLUNAS_UNIDADES)
    eletricas = _ler_aba(wb, ABA_ELETRICAS, COLUNAS_ELETRICAS)
    caps = _ler_aba(wb, ABA_CAPACIDADES, COLUNAS_CAPACIDADES)
    # Aba 'Campos' (estrutura do código comercial, emitida já pronta pelo script de extração do
    # fabricante) — importação automática INCLUSIVE da nomenclatura, sem cadastro manual depois.
    campos = cc.campos_de_linhas_planilha(_ler_aba(wb, ABA_CAMPOS, cc.COLUNAS_CAMPOS))
    caps_por_modelo = {}
    for c in caps:
        caps_por_modelo.setdefault((c["Modelo"], c["Fabricante_Compressor"], c["Gas"]), []).append(c)
    eletricas_por_modelo = {}
    for e in eletricas:
        eletricas_por_modelo.setdefault((e["Modelo"], e["Fabricante_Compressor"]), []).append(e)
    return unidades, eletricas_por_modelo, caps_por_modelo, campos


def _buscar_por_modelo(dic_por_modelo, modelo, fabricante_compressor):
    """Busca em dic_por_modelo (chave (Modelo, Fabricante_Compressor)): tenta a chave exata da
    unidade primeiro; se a planilha não distinguiu por marca (linhas com Fabricante_Compressor em
    branco), cai pro bucket (Modelo, None) — aplica a todas as unidades daquele Modelo."""
    exata = dic_por_modelo.get((modelo, fabricante_compressor))
    if exata:
        return exata
    return dic_por_modelo.get((modelo, None), [])


def _buscar_capacidades(caps_por_modelo, modelo, fabricante_compressor, gas):
    """Busca em caps_por_modelo (chave (Modelo, Fabricante_Compressor, Gas)) — SEMPRE inclui Gas na
    busca pra não misturar capacidade de gases diferentes que compartilham faixa de evaporação (bug
    real corrigido: ver nota em COLUNAS_CAPACIDADES). Faz fallback progressivo só pra compatibilidade
    com planilhas antigas/parciais que não preencheram Fabricante_Compressor e/ou Gas na aba
    Capacidades — nessa ordem: (modelo,fab,gas) exata > (modelo,fab,None) > (modelo,None,gas) >
    (modelo,None,None)."""
    for chave in ((modelo, fabricante_compressor, gas), (modelo, fabricante_compressor, None),
                  (modelo, None, gas), (modelo, None, None)):
        achado = caps_por_modelo.get(chave)
        if achado:
            return achado
    return []


def montar_preview_uc(conteudo: bytes) -> dict:
    unidades, eletricas_por_modelo, caps_por_modelo, campos = ler_planilha_uc(conteudo)
    if not unidades:
        return {"erro": "Aba 'Unidades' não encontrada ou vazia. Use o template."}
    itens = []
    for u in unidades:
        caps = _buscar_capacidades(caps_por_modelo, u["Modelo"], u["Fabricante_Compressor"], u["Gas"])
        itens.append({
            "unidade": u,
            "eletricas": _buscar_por_modelo(eletricas_por_modelo, u["Modelo"], u["Fabricante_Compressor"]),
            "capacidades": caps,
            "temps_ambiente": sorted({c["Temp_Ambiente_C"] for c in caps if c["Temp_Ambiente_C"] is not None}),
            "temps_evaporacao": sorted({c["Temp_Evaporacao_C"] for c in caps if c["Temp_Evaporacao_C"] is not None}),
        })
    return {"unidades": itens, "campos": campos}


def montar_matriz_catalogo(db: Session, catalogo_id: int) -> dict:
    """Mesmo formato de saída de montar_preview_uc (pra reaproveitar a mesma matriz de conferência
    da tela), mas lendo direto do banco em vez de reler um Excel — permite reabrir um catálogo já
    confirmado antes pra corrigir em lote (mecânica, elétrica, nomenclatura), sem precisar ter o
    arquivo .xlsx original em mãos. As chaves dos dicts usam o nome de coluna do Excel (mesmo
    padrão de _MAP_UNIDADE/_MAP_ELETRICA), porque /confirmar-editado espera esse formato de volta."""
    catalogo = db.get(m.CatalogoUC, catalogo_id)
    if not catalogo:
        return {"erro": "Catálogo não encontrado."}
    itens = []
    for u in catalogo.unidades:
        unidade_dict = {"Fabricante_UC": catalogo.fabricante_uc, "Nome_Catalogo": catalogo.nome,
                         "Versao_Catalogo": catalogo.versao_catalogo,
                         "Descricao_Comercial": catalogo.descricao_comercial}
        for col, attr in _MAP_UNIDADE.items():
            unidade_dict[col] = getattr(u, attr)
        eletricas = []
        for e in u.eletricas:
            ed = {"Modelo": u.modelo, "Fabricante_Compressor": u.fabricante_compressor}
            for col, attr in _MAP_ELETRICA.items():
                ed[col] = getattr(e, attr)
            eletricas.append(ed)
        capacidades = [{"Modelo": u.modelo, "Fabricante_Compressor": u.fabricante_compressor, "Gas": u.gas,
                         "Temp_Ambiente_C": c.temp_ambiente_c, "Temp_Evaporacao_C": c.temp_evaporacao_c,
                         "Capacidade_kcal_h": c.capacidade_kcal_h, "Potencia_kW": c.potencia_kw}
                        for c in u.capacidades]
        itens.append({
            "unidade": unidade_dict, "eletricas": eletricas, "capacidades": capacidades,
            "temps_ambiente": sorted({c["Temp_Ambiente_C"] for c in capacidades if c["Temp_Ambiente_C"] is not None}),
            "temps_evaporacao": sorted({c["Temp_Evaporacao_C"] for c in capacidades if c["Temp_Evaporacao_C"] is not None}),
        })
    campos = cc.campos_para_dict(cc.listar_campos(db, "UC", catalogo_id))
    return {"unidades": itens, "campos": campos}


def salvar_unidades(db: Session, unidades, eletricas_por_modelo, caps_por_modelo, campos_codigo=None,
                     id_pai: str | None = None) -> dict:
    """Núcleo da gravação — usado tanto pela importação direta do Excel quanto pela confirmação
    da prévia editada (matriz de conferência, item 11). campos_codigo (lista de Campos do código
    comercial, ver campo_catalogo.py) é persistido no catálogo quando informado — importação
    automática INCLUSIVE da nomenclatura."""
    if not unidades:
        return {"erro": "Nenhuma unidade para gravar."}
    criadas, atualizadas = 0, 0
    catalogos_cache = {}
    for u in unidades:
        chave_cat = (u["Fabricante_UC"], u["Nome_Catalogo"], u["Versao_Catalogo"])
        catalogo = catalogos_cache.get(chave_cat)
        if not catalogo:
            catalogo = (db.query(m.CatalogoUC)
                        .filter(func.lower(m.CatalogoUC.fabricante_uc) == u["Fabricante_UC"].strip().lower(),
                                m.CatalogoUC.nome == u["Nome_Catalogo"],
                                m.CatalogoUC.versao_catalogo == u["Versao_Catalogo"]).first())
            if not catalogo:
                catalogo = m.CatalogoUC(fabricante_uc=u["Fabricante_UC"].strip(), nome=u["Nome_Catalogo"],
                                        versao_catalogo=u["Versao_Catalogo"])
                db.add(catalogo)
                db.flush()
                # Id comercial (4.1.1 = Unidade Comercial) — auto-gerado uma vez na criação, fixo
                # depois (ver id_comercial.py).
                if id_pai:
                    catalogo.id_comercial = id_comercial.proximo_sequencial_sob(
                        db, m.CatalogoUC, id_pai, nome_item=catalogo.nome)
                else:
                    catalogo.id_comercial = id_comercial.gerar_proximo_id_catalogo(
                        db, m.CatalogoUC, "fabricante_uc", catalogo.fabricante_uc, catalogo.fabricante_uc,
                        id_comercial.ANCORA_UC, nome_item=catalogo.nome)
            catalogos_cache[chave_cat] = catalogo

        # chave: catálogo + modelo + gás + fabricante_compressor — modelo+gás nunca se funde (mesmo
        # código mecânico pode cobrir 2 gases com capacidades diferentes) e fabricante_compressor
        # evita colisão quando 2 marcas de compressor usam o mesmo código (não precisa mais "sujar"
        # o campo Modelo com o nome da marca por extenso).
        obj = (db.query(m.UnidadeCondensadora)
               .filter_by(catalogo_id=catalogo.id, modelo=u["Modelo"], gas=u["Gas"],
                          fabricante_compressor=u["Fabricante_Compressor"]).first())
        if obj:
            atualizadas += 1
        else:
            obj = m.UnidadeCondensadora(catalogo_id=catalogo.id)
            db.add(obj)
            criadas += 1
        for col, attr in _MAP_UNIDADE.items():
            val = u.get(col)
            if attr == "sistema":
                val = _normalizar_sistema(val)
            setattr(obj, attr, val)
        db.flush()
        # recria capacidades do zero
        db.query(m.CapacidadeUC).filter_by(unidade_id=obj.id).delete()
        for c in _buscar_capacidades(caps_por_modelo, u["Modelo"], u["Fabricante_Compressor"], u["Gas"]):
            db.add(m.CapacidadeUC(
                unidade_id=obj.id, temp_ambiente_c=c["Temp_Ambiente_C"],
                temp_evaporacao_c=c["Temp_Evaporacao_C"], capacidade_kcal_h=c["Capacidade_kcal_h"],
                potencia_kw=c["Potencia_kW"]))
        # recria elétricas do zero (uma linha por Tensão × Modelo de Compressor)
        db.query(m.EletricaUC).filter_by(unidade_id=obj.id).delete()
        for e in _buscar_por_modelo(eletricas_por_modelo, u["Modelo"], u["Fabricante_Compressor"]):
            campos = {attr: e.get(col) for col, attr in _MAP_ELETRICA.items()}
            db.add(m.EletricaUC(unidade_id=obj.id, **campos))
    # Descrição comercial é do CATÁLOGO (não por unidade) — a planilha traz uma coluna repetida por
    # linha só por praticidade de preenchimento, mesmo texto pro catálogo todo; usa a primeira não
    # vazia encontrada por catálogo. Nunca apaga uma descrição já cadastrada (mesma regra do
    # Forçador, ver excel_import.py:salvar_grupo).
    for chave_cat, catalogo in catalogos_cache.items():
        descricao = next((u.get("Descricao_Comercial") for u in unidades
                           if (u["Fabricante_UC"], u["Nome_Catalogo"], u["Versao_Catalogo"]) == chave_cat
                           and u.get("Descricao_Comercial")), None)
        if descricao:
            catalogo.descricao_comercial = descricao

    # Campos do código comercial (estrutura Automático/Fixo/Manual) — substitui a lista inteira do
    # catálogo. É o único mecanismo de nomenclatura vigente (a antiga NomenclaturaUC/categoria foi
    # removida por não ter nenhum consumidor real — ver auditoria de 2026-07-15).
    catalogo_id_nomencl = next(iter(catalogos_cache.values())).id if catalogos_cache else None
    if campos_codigo and catalogo_id_nomencl:
        cc.salvar_campos(db, "UC", catalogo_id_nomencl, campos_codigo)
    db.commit()
    return {"ok": True, "criadas": criadas, "atualizadas": atualizadas}


def salvar_planilha_uc(db: Session, conteudo: bytes) -> dict:
    unidades, eletricas_por_modelo, caps_por_modelo, campos = ler_planilha_uc(conteudo)
    if not unidades:
        return {"erro": "Aba 'Unidades' não encontrada ou vazia."}
    return salvar_unidades(db, unidades, eletricas_por_modelo, caps_por_modelo, campos)
