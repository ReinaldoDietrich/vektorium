# -*- coding: utf-8 -*-
"""Importação de catálogo de Condensadores Remotos via planilha Excel — mesmo rito da importação
de Forçadores (excel_import.py), adaptado às diferenças do produto: modelo ACHATADO (sem tabelas
aninhadas de capacidade/elétrica/físico/dimensional — tudo numa linha só), capacidade é VALOR
ÚNICO, e a correção usa 5 tipos de fator (condensador_fatores). Tipo Estrutura (Plano/V) faz parte
da identidade da linha: um mesmo catálogo com os dois tipos vira duas linhas separadas."""
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models as m
from .. import campo_catalogo as cc
from .. import id_comercial

ABA_MODELOS = "Modelos"
ABA_FATORES = "Fatores"
ABA_CAMPOS = "Campos"

# coluna Excel -> campo escalar do ModeloCondensadorRemoto
MAPA_MODELO = {
    "FPI": "fpi", "Qtd_Ventiladores": "qtd_ventiladores",
    "Diametro_Ventilador_mm": "diametro_ventilador_mm",  # em branco se o catálogo não publicar
    "Vazao_Ar_m3h": "vazao_ar_m3h",
    "Polos_ou_RPM": "polos_ou_rpm", "Tipo_Motor": "tipo_motor", "Num_Fileiras": "num_fileiras",
    "Capacidade_kcal_h": "capacidade_kcal_h", "Potencia_kW": "potencia_kw",
    "Corrente_220V": "corrente_220v", "Corrente_380V": "corrente_380v", "Corrente_460V": "corrente_460v",
    "Ruido_dB": "ruido_db", "Carga_Refrigerante_kg": "carga_refrigerante_kg",
    "Coletor_Entrada_pol": "coletor_entrada_pol", "Coletor_Saida_pol": "coletor_saida_pol",
    "Peso_Liquido_kg": "peso_liquido_kg", "Peso_Bruto_kg": "peso_bruto_kg",
    "Comprimento_mm": "comprimento_mm", "Largura_mm": "largura_mm", "Altura_mm": "altura_mm",
    "Num_Fixacoes": "num_fixacoes",
}
COLUNAS_MODELOS = ["Fabricante", "Linha", "Versao_Catalogo", "Tipo_Estrutura", "DT_Catalogo_C",
                   "Modelo"] + list(MAPA_MODELO.keys()) + ["Descricao_Comercial"]
COLUNAS_FATORES = ["Fabricante", "Linha", "Tipo_Estrutura", "Tipo_Fator", "Chave", "Fator"]
COLUNAS_CAMPOS_CONDENSADOR = ["Fabricante", "Linha", "Tipo_Estrutura"] + cc.COLUNAS_CAMPOS

# Delta de condensação NÃO é fator de tabela — é razão linear (delta projeto / DT de Catálogo),
# igual ao forçador de ar; o DT de Catálogo vem na própria aba Modelos (coluna DT_Catalogo_C).
TIPOS_FATOR = ["gas", "aleta", "altitude", "temp_entrada_ar"]
# campos comparados para decidir se uma reimportação é idêntica (mesma regra do Forçador)
CAMPOS_COMPARAVEIS = list(MAPA_MODELO.values())


def gerar_template() -> bytes:
    """Gera o .xlsx modelo (cabeçalhos + 1 linha de exemplo por aba) para download."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    exemplos = {
        ABA_MODELOS: (COLUNAS_MODELOS, [["Elgin", "ACC", "2026", "Plano (Fluxo Vertical)", 10,
                                          "ACC040", 10, 6, 300, 4150, "6", "AC", 4, 4150, 2.5, 7.58, 4.66,
                                          4.73, 44, 2.1, '1.5/8"', '1.5/8"', 120, 135, 2000, 1000, 900,
                                          8, None]]),
        ABA_FATORES: (COLUNAS_FATORES, [
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", "gas", "R-404A", 1.0],
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", "aleta", "Padrão", 1.0],
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", "altitude", "600", 1.0],
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", "temp_entrada_ar", "35", 0.97],
        ]),
        ABA_CAMPOS: (COLUNAS_CAMPOS_CONDENSADOR, [
            # "Modelo Pesquisa": card especial, no máximo 1 por linha — valor = o próprio texto da
            # coluna Modelo (aba Modelos), não editável depois; só a POSIÇÃO na nomenclatura é livre
            # (arrastável em Configurações/Tela C). Padrão único do sistema, mesmo do Forçador/UC —
            # nunca criar Campo "prefixo fixo" tentando simular isso (ver montar_codigo).
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", 0, "Modelo Pesquisa", "modelo_pesquisa", None, 0, None, None, None],
            ["Elgin", "ACC", "Plano (Fluxo Vertical)", 1, "Tensão", "manual", None, 0, None, "220V", "B"],
        ]),
    }
    for nome_aba, (colunas, linhas_exemplo) in exemplos.items():
        ws = wb.create_sheet(nome_aba)
        for c, titulo in enumerate(colunas, start=1):
            cell = ws.cell(row=1, column=c, value=titulo)
            cell.fill = PatternFill("solid", fgColor="111827")
            cell.font = Font(bold=True, color="FFFFFF")
        for r, linha in enumerate(linhas_exemplo, start=2):
            for c, valor in enumerate(linha, start=1):
                ws.cell(row=r, column=c, value=valor)
        for c, _ in enumerate(colunas, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 18
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _ler_aba(wb, nome_aba, colunas_esperadas):
    if nome_aba not in wb.sheetnames:
        return []
    ws = wb[nome_aba]
    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        return []
    cabecalho = [str(c).strip() if c else "" for c in linhas[0]]
    indices = {col: cabecalho.index(col) for col in colunas_esperadas if col in cabecalho}
    registros = []
    for linha in linhas[1:]:
        if not linha or all(v is None for v in linha):
            continue
        reg = {col: (linha[indices[col]] if col in indices and indices[col] < len(linha) else None)
               for col in colunas_esperadas}
        registros.append(reg)
    return registros


def _valores_iguais(a, b, tolerancia=0.1):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) < tolerancia
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def _modelo_identico(existente: m.ModeloCondensadorRemoto, novo: dict) -> bool:
    for campo in CAMPOS_COMPARAVEIS:
        valor_novo = novo.get(campo)
        if valor_novo is not None and not _valores_iguais(getattr(existente, campo), valor_novo):
            return False
    return True


def ler_grupos(conteudo: bytes) -> tuple:
    """Lê o .xlsx e devolve (grupos, fatores_por_linha, campos_por_linha) sem tocar no banco.
    grupos: {(fabricante, linha, versao, tipo_estrutura): {"dt_catalogo_c":..., "modelos":[...]}}"""
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    modelos_raw = _ler_aba(wb, ABA_MODELOS, COLUNAS_MODELOS)
    fatores_raw = _ler_aba(wb, ABA_FATORES, COLUNAS_FATORES)
    campos_raw = _ler_aba(wb, ABA_CAMPOS, COLUNAS_CAMPOS_CONDENSADOR)

    if not modelos_raw:
        return {}, {}, {}

    grupos = {}
    for mr in modelos_raw:
        chave = (mr["Fabricante"], mr["Linha"],
                 str(mr["Versao_Catalogo"]) if mr["Versao_Catalogo"] else None,
                 mr["Tipo_Estrutura"])
        item = {"modelo": mr["Modelo"], "descricao_comercial": mr.get("Descricao_Comercial")}
        for col_excel, campo in MAPA_MODELO.items():
            item[campo] = mr[col_excel]
        g = grupos.setdefault(chave, {"dt_catalogo_c": mr.get("DT_Catalogo_C"), "modelos": []})
        g["modelos"].append(item)

    fatores_por_linha = {}
    for fr in fatores_raw:
        if not fr["Fabricante"] or not fr["Linha"] or not fr["Tipo_Fator"] or fr["Chave"] in (None, ""):
            continue
        chave = (fr["Fabricante"], fr["Linha"], fr["Tipo_Estrutura"])
        fatores_por_linha.setdefault(chave, []).append(
            {"tipo": fr["Tipo_Fator"], "chave": str(fr["Chave"]), "fator": fr["Fator"]})

    campos_raw_por_linha = {}
    for cr in campos_raw:
        if not cr.get("Fabricante") or not cr.get("Linha") or not cr.get("Nome_Campo"):
            continue
        campos_raw_por_linha.setdefault((cr["Fabricante"], cr["Linha"], cr["Tipo_Estrutura"]), []).append(cr)
    campos_por_linha = {k: cc.campos_de_linhas_planilha(v) for k, v in campos_raw_por_linha.items()}

    return grupos, fatores_por_linha, campos_por_linha


def montar_preview(db: Session, conteudo: bytes) -> dict:
    """Lê o Excel e devolve, para cada linha detectada, os modelos prontos para revisão no
    front-end (sem gravar nada), já com o status de versionamento calculado."""
    grupos, fatores_por_linha, campos_por_linha = ler_grupos(conteudo)
    if not grupos:
        return {"erro": f"Aba '{ABA_MODELOS}' não encontrada ou vazia. Use o template para gerar a planilha."}

    resultado = {"linhas": []}
    for (nome_fab, nome_linha, versao, tipo_estrutura), grupo in grupos.items():
        if not nome_fab or not nome_linha:
            resultado["linhas"].append({"linha": nome_linha, "erro": "Fabricante ou Linha em branco — pulado."})
            continue
        versao = versao or datetime.now().strftime("%Y-%m-%d")
        modelos = grupo["modelos"]

        fabricante = db.query(m.Fabricante).filter(func.lower(m.Fabricante.nome) == nome_fab.strip().lower()).first()
        status, observacao, linha_anterior = "nova_linha", None, None
        if fabricante:
            linha_anterior = (db.query(m.LinhaCondensadorRemoto)
                              .filter_by(fabricante_id=fabricante.id, nome=nome_linha, tipo_estrutura=tipo_estrutura)
                              .filter(m.LinhaCondensadorRemoto.versao_catalogo != versao)
                              .order_by(m.LinhaCondensadorRemoto.id.desc()).first())
            mesma_versao = (db.query(m.LinhaCondensadorRemoto)
                            .filter_by(fabricante_id=fabricante.id, nome=nome_linha,
                                       versao_catalogo=versao, tipo_estrutura=tipo_estrutura).first())
            if mesma_versao:
                status = "atualizar_versao_existente"
            elif linha_anterior:
                todos_identicos = all(
                    (existente := next((md for md in linha_anterior.modelos if md.modelo == mp["modelo"]), None))
                    and _modelo_identico(existente, mp) for mp in modelos)
                if todos_identicos:
                    status = "sem_alteracoes"
                    observacao = f"Dados idênticos à versão {linha_anterior.versao_catalogo} — nenhuma alteração."
                else:
                    status = "nova_versao"
                    observacao = f"Substitui a versão anterior: {linha_anterior.versao_catalogo}."

        resultado["linhas"].append({
            "status": status, "observacao": observacao,
            "fabricante": nome_fab, "linha": nome_linha, "versao_catalogo": versao,
            "tipo_estrutura": tipo_estrutura, "dt_catalogo_c": grupo["dt_catalogo_c"],
            "modelos": modelos,
            "fatores": fatores_por_linha.get((nome_fab, nome_linha, tipo_estrutura), []),
            "campos": campos_por_linha.get((nome_fab, nome_linha, tipo_estrutura), []),
            "linha_anterior_id": linha_anterior.id if linha_anterior else None,
        })
    return resultado


def salvar_grupo(db: Session, fabricante: str, linha_nome: str, versao_catalogo: str, tipo_estrutura: str,
                  modelos: list, dt_catalogo_c=None, nome_arquivo: str = None, fatores: list = None,
                  payload_completo: bool = False, campos: list = None,
                  id_pai: str | None = None) -> dict:
    """Cria/atualiza uma linha de condensador (chaveada por fabricante+nome+versão+tipo_estrutura)
    com seus modelos achatados. payload_completo=True (edição manual da grade) aplica todos os
    campos inclusive None; False (importação Excel) nunca sobrescreve com None."""
    if not fabricante or not linha_nome:
        return {"erro": "Fabricante ou Linha em branco."}
    versao_catalogo = versao_catalogo or datetime.now().strftime("%Y-%m-%d")

    fabricante_obj = db.query(m.Fabricante).filter(func.lower(m.Fabricante.nome) == fabricante.strip().lower()).first()
    if not fabricante_obj:
        fabricante_obj = m.Fabricante(nome=fabricante.strip())
        db.add(fabricante_obj)
        db.commit()
        db.refresh(fabricante_obj)

    linha_anterior = (db.query(m.LinhaCondensadorRemoto)
                      .filter_by(fabricante_id=fabricante_obj.id, nome=linha_nome, tipo_estrutura=tipo_estrutura)
                      .filter(m.LinhaCondensadorRemoto.versao_catalogo != versao_catalogo)
                      .order_by(m.LinhaCondensadorRemoto.id.desc()).first())

    linha = (db.query(m.LinhaCondensadorRemoto)
             .filter_by(fabricante_id=fabricante_obj.id, nome=linha_nome,
                        versao_catalogo=versao_catalogo, tipo_estrutura=tipo_estrutura).first())
    if not linha:
        linha = m.LinhaCondensadorRemoto(fabricante_id=fabricante_obj.id, nome=linha_nome,
                                          versao_catalogo=versao_catalogo, tipo_estrutura=tipo_estrutura,
                                          dt_catalogo_c=dt_catalogo_c,
                                          linha_anterior_id=linha_anterior.id if linha_anterior else None)
        db.add(linha)
        db.commit()
        db.refresh(linha)
        if id_pai:
            linha.id_comercial = id_comercial.proximo_sequencial_sob(
                db, m.LinhaCondensadorRemoto, id_pai, nome_item=linha_nome)
        else:
            linha.id_comercial = id_comercial.gerar_proximo_id_catalogo(
                db, m.LinhaCondensadorRemoto, "fabricante_id", fabricante_obj.id, fabricante_obj.nome,
                id_comercial.ancora_condensador(tipo_estrutura), nome_item=linha_nome)
        db.commit()
    if dt_catalogo_c is not None:
        linha.dt_catalogo_c = dt_catalogo_c

    # descricao_comercial é campo da LINHA (catálogo inteiro), nunca por modelo — não entra em
    # campos_escalares pra não ser resetado a cada salvamento da Matriz -- aprovado 2026-08-11.
    campos_escalares = list(MAPA_MODELO.values()) + ["nomenclatura_compra"]
    modelos_mantidos = set()
    for mp in modelos:
        obj = None
        if mp.get("id"):
            obj = db.get(m.ModeloCondensadorRemoto, mp["id"])
        if not obj:
            obj = db.query(m.ModeloCondensadorRemoto).filter_by(linha_id=linha.id, modelo=mp["modelo"]).first()
        if not obj:
            iniciais = {k: v for k, v in mp.items() if k in campos_escalares and v is not None}
            obj = m.ModeloCondensadorRemoto(linha_id=linha.id, modelo=mp["modelo"], **iniciais)
            db.add(obj)
        else:
            obj.modelo = mp["modelo"]
            if payload_completo:
                for k in campos_escalares:
                    setattr(obj, k, mp.get(k))
            else:
                for k, v in mp.items():
                    if k in campos_escalares and v is not None:
                        setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        modelos_mantidos.add(obj.id)

    for obj in list(linha.modelos):
        if obj.id not in modelos_mantidos:
            db.delete(obj)
    db.commit()

    # Descrição comercial é da LINHA (por tipo de estrutura), não por modelo — usa a primeira não vazia.
    descricao = next((mp.get("descricao_comercial") for mp in modelos if mp.get("descricao_comercial")), None)
    if descricao:
        linha.descricao_comercial = descricao
        db.commit()

    if campos:
        cc.salvar_campos(db, "CondensadorRemoto", linha.id, campos)

    if fatores:
        for f in fatores:
            if f.get("fator") is None or not f.get("tipo") or f.get("chave") in (None, ""):
                continue
            existente = db.query(m.FatorCorrecaoCondensador).filter_by(
                linha_id=linha.id, tipo=f["tipo"], chave=str(f["chave"])).first()
            if existente:
                existente.fator = f["fator"]
            else:
                db.add(m.FatorCorrecaoCondensador(linha_id=linha.id, tipo=f["tipo"],
                                                  chave=str(f["chave"]), fator=f["fator"]))
        db.commit()

    db.add(m.ImportacaoCondensador(linha_id=linha.id, nome_arquivo=nome_arquivo,
                                   tipo_arquivo="excel" if nome_arquivo else "edicao_manual",
                                   confirmado_pelo_usuario=True,
                                   observacao=f"{'Importação' if nome_arquivo else 'Edição'} — {len(modelos)} modelo(s)."))
    db.commit()
    return {"linha": linha_nome, "fabricante": fabricante, "tipo_estrutura": tipo_estrutura,
            "acao": "importado", "linha_id": linha.id, "qtd_modelos": len(modelos)}
