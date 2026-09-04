"""Importação de catálogo de forçadores via planilha Excel — substitui colar texto / PDF / imagem
por ser 100% determinístico (lê célula por célula, sem nenhuma adivinhação de texto/formato).
Estrutura fixa de 5 abas, espelhando exatamente as tabelas do banco (padrão FBA-6 fechado com
o usuário)."""
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill
from sqlalchemy.orm import Session
from .. import models as m
from .matriz import modelos_para_matriz
from .. import campo_catalogo as cc
from .. import id_comercial

ABA_MODELOS = "Modelos"
ABA_CAPACIDADES = "Capacidades"
ABA_ELETRICA = "Eletrica"
ABA_FISICOS = "Fisicos"
ABA_DIMENSIONAIS = "Dimensionais"
ABA_FATORES_GAS = "Fatores_Gas"
ABA_CAMPOS = "Campos"

COLUNAS_MODELOS = ["Fabricante", "Linha", "Versao_Catalogo", "Modelo", "FPI", "Num_Ventiladores",
                    "Diametro_Ventilador_mm", "Tipo_Degelo", "Carga_Gas_kg", "Pot_Resistencia_Degelo_W",
                    "Vazao_Ar_m3h", "DT_Referencia_C", "PDL_Referencia_m", "Flecha_Ar_m", "Coletores_Por_Forcador",
                    "Descricao_Comercial"]
COLUNAS_CAPACIDADES = ["Modelo", "Temp_Evaporacao_C", "Capacidade_kcal_h"]
COLUNAS_ELETRICA = ["Modelo", "Tensao", "Degelo_W", "Degelo_A", "Motores_W", "Motores_A"]
COLUNAS_FISICOS = ["Modelo", "Linha_Liquido", "Linha_Succao", "Equalizador", "Dreno", "Peso_Liquido_kg",
                    "Carga_Refrigerante_kg"]
COLUNAS_DIMENSIONAIS = ["Modelo", "Comprimento_mm", "Largura_mm", "Altura_mm", "Num_Fixacoes"]
# Estrutura do código comercial (Automático/Fixo/Manual/Ignorar, ver campo_catalogo.py) —
# Fabricante/Linha identificam a qual linha cada bloco de Campo pertence (um xlsx pode trazer
# mais de uma linha).
COLUNAS_CAMPOS_FORCADOR = ["Fabricante", "Linha"] + cc.COLUNAS_CAMPOS
# Fator de correção de capacidade por gás refrigerante — cada fabricante publica o seu, por linha.
COLUNAS_FATORES_GAS = ["Fabricante", "Linha", "Gas", "Fator"]

CAMPOS_COMPARAVEIS_MODELO = ["fpi", "num_ventiladores", "diametro_ventilador_mm", "tipo_degelo",
                              "carga_gas_kg", "pot_resistencia_degelo_w", "vazao_ar_m3h",
                              "dt_referencia_c", "pdl_referencia_m", "flecha_ar_m", "coletores_por_forcador"]


def gerar_template() -> bytes:
    """Gera o arquivo .xlsx modelo (vazio, só cabeçalhos + 1 linha de exemplo) para download."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    exemplos = {
        ABA_MODELOS: (COLUNAS_MODELOS, [["Heatcraft", "FLA", "2026", "FLA022", 4, 1, 400, "Ar forçado",
                                          1.5, 3100, 2895, 6, 4.0, 9, 2, None]]),
        ABA_CAPACIDADES: (COLUNAS_CAPACIDADES, [["FLA022", 10, 14800], ["FLA022", 0, 13000], ["FLA022", -30, 6700]]),
        ABA_ELETRICA: (COLUNAS_ELETRICA, [["FLA022", "220V/1F/60Hz", 3100, 24.3, 813, 3.69]]),
        ABA_FISICOS: (COLUNAS_FISICOS, [["FLA022", "3/8", "7/8", "1/4", "1 BSP", 44, 2.4]]),
        ABA_DIMENSIONAIS: (COLUNAS_DIMENSIONAIS, [["FLA022", 1558, 721, 840, None]]),
        ABA_FATORES_GAS: (COLUNAS_FATORES_GAS, [["Heatcraft", "FLA", "R-404A", 1.0], ["Heatcraft", "FLA", "R-134a", 0.95]]),
        ABA_CAMPOS: (COLUNAS_CAMPOS_FORCADOR, [
            # "Modelo Pesquisa": card especial, no máximo 1 por linha — valor = o próprio texto da
            # coluna Modelo (aba Modelos) do modelo técnico, ex.: "022" ou "FLA*022" se o fabricante
            # já usa coringa '*' dentro do código do modelo. NÃO editável pelo usuário depois — só a
            # POSIÇÃO na nomenclatura é livre (ordem cadastrada aqui é só o ponto de partida, o
            # usuário pode arrastar em Configurações/Tela A). Padrão único do sistema — nunca criar
            # um Campo "prefixo fixo" tentando simular isso, ver montar_codigo em campo_catalogo.py.
            ["Heatcraft", "FLA", 0, "Modelo Pesquisa", "modelo_pesquisa", None, 0, None, None, None],
            ["Heatcraft", "FLA", 1, "Tensão", "manual", None, 0, None, "220V/1F", "B"],
            ["Heatcraft", "FLA", 1, "Tensão", "manual", None, 0, None, "220V/3F", "C"],
        ]),
    }
    for nome_aba, (colunas, linhas_exemplo) in exemplos.items():
        ws = wb.create_sheet(nome_aba)
        for c, titulo in enumerate(colunas, start=1):
            cell = ws.cell(row=1, column=c, value=titulo)
            cell.font = Font(bold=True)
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
        reg = {}
        for col in colunas_esperadas:
            if col in indices and indices[col] < len(linha):
                reg[col] = linha[indices[col]]
            else:
                reg[col] = None
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


def _modelo_completo_identico(existente: m.ModeloForcador, novo: dict) -> bool:
    # campo em branco na planilha reimportada = "não informado", não "mudou para vazio" — não
    # conta como alteração (evita falso positivo de nova versão por causa de default de coluna).
    for campo in CAMPOS_COMPARAVEIS_MODELO:
        valor_novo = novo.get(campo)
        if valor_novo is not None and not _valores_iguais(getattr(existente, campo), valor_novo):
            return False
    caps_existentes = {c.temp_evaporacao_c: c.capacidade_kcal_h for c in existente.capacidades}
    caps_novas = {c["temp_evaporacao_c"]: c["capacidade_kcal_h"] for c in novo.get("capacidades", [])}
    if set(caps_existentes) != set(caps_novas):
        return False
    if not all(_valores_iguais(caps_existentes[t], caps_novas[t]) for t in caps_existentes):
        return False
    elet_existentes = {e.tensao: e for e in existente.eletricas}
    elet_novas = {e["tensao"]: e for e in novo.get("eletricas", [])}
    if set(elet_existentes) != set(elet_novas):
        return False
    for tensao, e_novo in elet_novas.items():
        e_velho = elet_existentes[tensao]
        for campo in ["degelo_w", "degelo_a", "motores_w", "motores_a"]:
            valor_novo = e_novo.get(campo)
            if valor_novo is not None and not _valores_iguais(getattr(e_velho, campo), valor_novo):
                return False
    fis_novo = novo.get("fisicos")
    if fis_novo:
        fis_velho = existente.fisicos
        if not fis_velho:
            return False
        for campo in ["linha_liquido", "linha_succao", "equalizador", "dreno", "peso_liquido_kg", "carga_refrigerante_kg"]:
            valor_novo = fis_novo.get(campo)
            if valor_novo is not None and not _valores_iguais(getattr(fis_velho, campo), valor_novo):
                return False
    dim_novo = novo.get("dimensionais")
    if dim_novo:
        dim_velho = existente.dimensionais
        if not dim_velho:
            return False
        for campo in ["comprimento_mm", "largura_mm", "altura_mm", "num_fixacoes"]:
            valor_novo = dim_novo.get(campo)
            if valor_novo is not None and not _valores_iguais(getattr(dim_velho, campo), valor_novo):
                return False
    return True


def ler_grupos(conteudo: bytes) -> tuple:
    """Lê o .xlsx e devolve (grupos, fatores_gas_por_linha, campos_por_linha) sem tocar no banco.
    grupos: {(fabricante, linha, versao): [item, ...]}
    campos_por_linha: {(fabricante, linha): [Campo, ...]} — estrutura do código comercial (ver
      campo_catalogo.py), importação automática, sem cadastro manual depois (cada fabricante tem
      sua própria estrutura)."""
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    modelos_raw = _ler_aba(wb, ABA_MODELOS, COLUNAS_MODELOS)
    capacidades_raw = _ler_aba(wb, ABA_CAPACIDADES, COLUNAS_CAPACIDADES)
    eletrica_raw = _ler_aba(wb, ABA_ELETRICA, COLUNAS_ELETRICA)
    fisicos_raw = _ler_aba(wb, ABA_FISICOS, COLUNAS_FISICOS)
    dimensionais_raw = _ler_aba(wb, ABA_DIMENSIONAIS, COLUNAS_DIMENSIONAIS)
    fatores_gas_raw = _ler_aba(wb, ABA_FATORES_GAS, COLUNAS_FATORES_GAS)
    campos_raw = _ler_aba(wb, ABA_CAMPOS, COLUNAS_CAMPOS_FORCADOR)

    if not modelos_raw:
        return {}, {}, {}

    por_modelo_cap, por_modelo_elet, por_modelo_fis, por_modelo_dim = {}, {}, {}, {}
    for c in capacidades_raw:
        por_modelo_cap.setdefault(c["Modelo"], []).append(
            {"temp_evaporacao_c": c["Temp_Evaporacao_C"], "capacidade_kcal_h": c["Capacidade_kcal_h"]})
    for e in eletrica_raw:
        por_modelo_elet.setdefault(e["Modelo"], []).append(
            {"tensao": e["Tensao"], "degelo_w": e["Degelo_W"], "degelo_a": e["Degelo_A"],
             "motores_w": e["Motores_W"], "motores_a": e["Motores_A"]})
    for f in fisicos_raw:
        por_modelo_fis[f["Modelo"]] = {"linha_liquido": f["Linha_Liquido"], "linha_succao": f["Linha_Succao"],
                                        "equalizador": f["Equalizador"], "dreno": f["Dreno"],
                                        "peso_liquido_kg": f["Peso_Liquido_kg"],
                                        "carga_refrigerante_kg": f["Carga_Refrigerante_kg"]}
    for d in dimensionais_raw:
        por_modelo_dim[d["Modelo"]] = {"comprimento_mm": d["Comprimento_mm"], "largura_mm": d["Largura_mm"],
                                        "altura_mm": d["Altura_mm"], "num_fixacoes": d["Num_Fixacoes"]}

    grupos = {}
    for mr in modelos_raw:
        chave = (mr["Fabricante"], mr["Linha"], str(mr["Versao_Catalogo"]) if mr["Versao_Catalogo"] else None)
        nome_modelo = mr["Modelo"]
        item = {
            "modelo": nome_modelo, "fpi": mr["FPI"], "num_ventiladores": mr["Num_Ventiladores"],
            "diametro_ventilador_mm": mr["Diametro_Ventilador_mm"], "tipo_degelo": mr["Tipo_Degelo"],
            "carga_gas_kg": mr["Carga_Gas_kg"], "pot_resistencia_degelo_w": mr["Pot_Resistencia_Degelo_W"],
            "vazao_ar_m3h": mr["Vazao_Ar_m3h"], "dt_referencia_c": mr["DT_Referencia_C"],
            "pdl_referencia_m": mr["PDL_Referencia_m"], "flecha_ar_m": mr["Flecha_Ar_m"],
            "coletores_por_forcador": mr["Coletores_Por_Forcador"],
            "descricao_comercial": mr.get("Descricao_Comercial"),
            "capacidades": por_modelo_cap.get(nome_modelo, []),
            "eletricas": por_modelo_elet.get(nome_modelo, []),
            "fisicos": por_modelo_fis.get(nome_modelo),
            "dimensionais": por_modelo_dim.get(nome_modelo),
        }
        grupos.setdefault(chave, []).append(item)

    fatores_gas_por_linha = {}
    for gr in fatores_gas_raw:
        if not gr["Fabricante"] or not gr["Linha"] or not gr["Gas"]:
            continue
        chave_gas = (gr["Fabricante"], gr["Linha"])
        fatores_gas_por_linha.setdefault(chave_gas, []).append({"gas": gr["Gas"], "fator": gr["Fator"]})

    campos_raw_por_linha = {}
    for cr in campos_raw:
        if not cr.get("Fabricante") or not cr.get("Linha") or not cr.get("Nome_Campo"):
            continue
        campos_raw_por_linha.setdefault((cr["Fabricante"], cr["Linha"]), []).append(cr)
    campos_por_linha = {chave: cc.campos_de_linhas_planilha(linhas) for chave, linhas in campos_raw_por_linha.items()}

    return grupos, fatores_gas_por_linha, campos_por_linha


def montar_preview(db: Session, conteudo: bytes) -> dict:
    """Lê o Excel e devolve, para cada linha detectada, a matriz pronta para revisão no front-end
    (sem gravar nada no banco). Cada grupo já vem com o status de versionamento calculado."""
    grupos, fatores_gas_por_linha, campos_por_linha = ler_grupos(conteudo)
    if not grupos:
        return {"erro": f"Aba '{ABA_MODELOS}' não encontrada ou vazia. Use o template para gerar a planilha."}

    resultado = {"linhas": []}
    for (nome_fabricante, nome_linha, versao_catalogo), modelos in grupos.items():
        if not nome_fabricante or not nome_linha:
            resultado["linhas"].append({"linha": nome_linha, "erro": "Fabricante ou Linha em branco — pulado."})
            continue
        versao_catalogo = versao_catalogo or datetime.now().strftime("%Y-%m-%d")

        fabricante = db.query(m.Fabricante).filter_by(nome=nome_fabricante).first()
        linha_anterior = None
        status, observacao = "nova_linha", None
        if fabricante:
            linha_anterior = (db.query(m.LinhaForcador)
                              .filter_by(fabricante_id=fabricante.id, nome=nome_linha)
                              .filter(m.LinhaForcador.versao_catalogo != versao_catalogo)
                              .order_by(m.LinhaForcador.id.desc()).first())
            linha_mesma_versao = (db.query(m.LinhaForcador)
                                  .filter_by(fabricante_id=fabricante.id, nome=nome_linha,
                                             versao_catalogo=versao_catalogo).first())
            if linha_mesma_versao:
                status = "atualizar_versao_existente"
            elif linha_anterior:
                todos_identicos = all(
                    (existente := next((md for md in linha_anterior.modelos if md.modelo == mp["modelo"]), None))
                    and _modelo_completo_identico(existente, mp)
                    for mp in modelos
                )
                if todos_identicos:
                    status = "sem_alteracoes"
                    observacao = (f"Dados idênticos à versão {linha_anterior.versao_catalogo} — "
                                   f"nenhuma alteração de catálogo.")
                else:
                    status = "nova_versao"
                    observacao = f"Substitui a versão anterior: {linha_anterior.versao_catalogo}."

        matriz = modelos_para_matriz(nome_fabricante, nome_linha, versao_catalogo, modelos)
        fatores_gas = fatores_gas_por_linha.get((nome_fabricante, nome_linha), [])
        campos = campos_por_linha.get((nome_fabricante, nome_linha), [])
        resultado["linhas"].append({"status": status, "observacao": observacao, "matriz": matriz,
                                     "fatores_gas": fatores_gas, "campos": campos,
                                     "linha_anterior_id": linha_anterior.id if linha_anterior else None})
    return resultado


def salvar_grupo(db: Session, fabricante: str, linha_nome: str, versao_catalogo: str, modelos: list,
                  nome_arquivo: str = None, fatores_gas: list = None,
                  payload_completo: bool = False, campos: list = None,
                  id_pai: str | None = None) -> dict:
    """Grava (cria ou atualiza) uma linha inteira com seus modelos/capacidades/elétrica/físicos/
    dimensionais. Usado tanto pela confirmação de importação Excel quanto pela edição manual da
    matriz de uma linha já existente.

    payload_completo=True (só na edição manual da matriz, onde a tela envia TODOS os campos de
    TODOS os modelos) permite limpar um campo pra None — sem isso, None era sempre ignorado, então
    apagar um texto (ex.: Descrição Comercial) e salvar nunca realmente limpava o banco.
    payload_completo=False (importação por Excel, que traz só um subconjunto de campos por vez)
    mantém o comportamento antigo: nunca sobrescreve com None, pra não apagar Descrição Comercial
    já anexada por uma importação anterior."""
    if not fabricante or not linha_nome:
        return {"erro": "Fabricante ou Linha em branco."}
    versao_catalogo = versao_catalogo or datetime.now().strftime("%Y-%m-%d")

    fabricante_obj = db.query(m.Fabricante).filter_by(nome=fabricante).first()
    if not fabricante_obj:
        fabricante_obj = m.Fabricante(nome=fabricante)
        db.add(fabricante_obj)
        db.commit()
        db.refresh(fabricante_obj)

    linha_anterior = (db.query(m.LinhaForcador)
                      .filter_by(fabricante_id=fabricante_obj.id, nome=linha_nome)
                      .filter(m.LinhaForcador.versao_catalogo != versao_catalogo)
                      .order_by(m.LinhaForcador.id.desc()).first())

    linha = (db.query(m.LinhaForcador)
            .filter_by(fabricante_id=fabricante_obj.id, nome=linha_nome, versao_catalogo=versao_catalogo).first())
    if not linha:
        linha = m.LinhaForcador(fabricante_id=fabricante_obj.id, nome=linha_nome, versao_catalogo=versao_catalogo,
                                 linha_anterior_id=linha_anterior.id if linha_anterior else None)
        db.add(linha)
        db.commit()
        db.refresh(linha)
        # Id comercial (4.2 = Forçadores de Ar) — auto-gerado uma vez na criação, fixo depois (ver
        # id_comercial.py). Marca já cadastrada na árvore reaproveita seu código; marca nova entra
        # num galho numerado na ordem de cadastro.
        if id_pai:
            linha.id_comercial = id_comercial.proximo_sequencial_sob(
                db, m.LinhaForcador, id_pai, nome_item=linha_nome)
        else:
            linha.id_comercial = id_comercial.gerar_proximo_id_catalogo(
                db, m.LinhaForcador, "fabricante_id", fabricante_obj.id, fabricante_obj.nome,
                id_comercial.ANCORA_FORCADOR, nome_item=linha_nome)
        db.commit()

    modelos_mantidos_ids = set()
    for mp in modelos:
        modelo_obj = None
        if mp.get("id"):
            modelo_obj = db.get(m.ModeloForcador, mp["id"])
        if not modelo_obj:
            modelo_obj = db.query(m.ModeloForcador).filter_by(linha_id=linha.id, modelo=mp["modelo"]).first()
        # descricao_comercial é campo da LINHA (catálogo inteiro), nunca por modelo — não entra em
        # campos_possiveis pra não ser resetado a cada salvamento da Matriz (a grade de edição não
        # coleta esse campo por modelo desde que virou campo de linha) -- aprovado 2026-08-11.
        campos_possiveis = CAMPOS_COMPARAVEIS_MODELO + ["nomenclatura_compra", "altura_max_instalacao_m"]
        if not modelo_obj:
            # criação nova: só usa os campos que vieram preenchidos (None vira default da coluna)
            campos_escalares = {k: v for k, v in mp.items() if k in campos_possiveis and v is not None}
            modelo_obj = m.ModeloForcador(linha_id=linha.id, modelo=mp["modelo"], **campos_escalares)
            db.add(modelo_obj)
        else:
            modelo_obj.modelo = mp["modelo"]
            if payload_completo:
                # edição manual da matriz: aplica TODOS os campos, inclusive None — permite limpar
                # um valor que o usuário apagou na tela.
                for k in campos_possiveis:
                    setattr(modelo_obj, k, mp.get(k))
            else:
                for k, v in mp.items():
                    if k in campos_possiveis and v is not None:
                        setattr(modelo_obj, k, v)
        db.commit()
        db.refresh(modelo_obj)
        modelos_mantidos_ids.add(modelo_obj.id)

        db.query(m.CapacidadeForcador).filter_by(modelo_id=modelo_obj.id).delete()
        for c in mp.get("capacidades", []):
            if c["temp_evaporacao_c"] is not None and c["capacidade_kcal_h"] is not None:
                db.add(m.CapacidadeForcador(modelo_id=modelo_obj.id, temp_evaporacao_c=c["temp_evaporacao_c"],
                                             capacidade_kcal_h=c["capacidade_kcal_h"]))
        db.query(m.DadosEletricosForcador).filter_by(modelo_id=modelo_obj.id).delete()
        for e in mp.get("eletricas", []):
            if e["tensao"]:
                db.add(m.DadosEletricosForcador(modelo_id=modelo_obj.id, tensao=e["tensao"],
                                                  degelo_w=e.get("degelo_w"), degelo_a=e.get("degelo_a"),
                                                  motores_w=e.get("motores_w"), motores_a=e.get("motores_a")))
        db.query(m.DadosFisicosForcador).filter_by(modelo_id=modelo_obj.id).delete()
        if mp.get("fisicos"):
            f = mp["fisicos"]
            db.add(m.DadosFisicosForcador(modelo_id=modelo_obj.id, linha_liquido=f.get("linha_liquido"),
                                           linha_succao=f.get("linha_succao"), equalizador=f.get("equalizador"),
                                           dreno=f.get("dreno"), peso_liquido_kg=f.get("peso_liquido_kg"),
                                           carga_refrigerante_kg=f.get("carga_refrigerante_kg")))
        db.query(m.DadosDimensionaisForcador).filter_by(modelo_id=modelo_obj.id).delete()
        if mp.get("dimensionais"):
            d = mp["dimensionais"]
            db.add(m.DadosDimensionaisForcador(modelo_id=modelo_obj.id, comprimento_mm=d.get("comprimento_mm"),
                                                largura_mm=d.get("largura_mm"), altura_mm=d.get("altura_mm"),
                                                num_fixacoes=d.get("num_fixacoes")))
        db.commit()

    # remove da linha os modelos que não vieram mais na matriz editada (edição é da linha inteira)
    for modelo_obj in list(linha.modelos):
        if modelo_obj.id not in modelos_mantidos_ids:
            db.delete(modelo_obj)

    # Descrição comercial é da LINHA (catálogo inteiro), não por modelo — a Excel traz uma coluna
    # por modelo só por praticidade de preenchimento, mas o texto é o mesmo pro catálogo todo; usa
    # a primeira não vazia encontrada. Nunca apaga uma descrição já cadastrada (mesma regra de não
    # sobrescrever com None que vale pro resto da importação por Excel).
    descricao_linha = next((mp.get("descricao_comercial") for mp in modelos if mp.get("descricao_comercial")), None)
    if descricao_linha:
        linha.descricao_comercial = descricao_linha
    db.commit()

    if campos:
        cc.salvar_campos(db, "Forcador", linha.id, campos)

    if fatores_gas:
        for item_gas in fatores_gas:
            if item_gas.get("fator") is None:
                continue
            existente = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=linha.id, gas=item_gas["gas"]).first()
            if existente:
                existente.fator = item_gas["fator"]
            else:
                db.add(m.FatorCorrecaoGasForcador(linha_id=linha.id, gas=item_gas["gas"], fator=item_gas["fator"]))
        db.commit()

    db.add(m.ImportacaoCatalogo(linha_id=linha.id, nome_arquivo=nome_arquivo, tipo_arquivo="excel" if nome_arquivo else "edicao_manual",
                                 confirmado_pelo_usuario=True,
                                 observacao=f"{'Importação' if nome_arquivo else 'Edição'} — {len(modelos)} modelo(s)."))
    db.commit()
    return {"linha": linha_nome, "fabricante": fabricante, "acao": "importado", "linha_id": linha.id,
            "qtd_modelos": len(modelos)}


def anexar_complementares(db: Session, linha_id: int, modelos: list,
                           nome_arquivo: str = None, fatores_gas: list = None, campos: list = None) -> dict:
    """Usado quando a reimportação é 'sem alterações' nos dados técnicos (capacidade/elétrica/
    físicos/dimensionais) mas traz Campos e/ou Descrição_Comercial novas — anexa só isso à
    linha já existente, sem criar uma versão nova nem tocar nos dados técnicos."""
    linha = db.get(m.LinhaForcador, linha_id)
    if not linha:
        return {"erro": "Linha de referência não encontrada."}

    # Descrição comercial é da LINHA (catálogo inteiro), não por modelo — ver mesma nota em salvar_grupo.
    descricao_linha = next((mp.get("descricao_comercial") for mp in modelos if mp.get("descricao_comercial")), None)
    qtd_atualizados = 1 if descricao_linha else 0
    if descricao_linha:
        linha.descricao_comercial = descricao_linha
    db.commit()

    if campos:
        cc.salvar_campos(db, "Forcador", linha.id, campos)

    if fatores_gas:
        for item_gas in fatores_gas:
            if item_gas.get("fator") is None:
                continue
            existente = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=linha.id, gas=item_gas["gas"]).first()
            if existente:
                existente.fator = item_gas["fator"]
            else:
                db.add(m.FatorCorrecaoGasForcador(linha_id=linha.id, gas=item_gas["gas"], fator=item_gas["fator"]))
        db.commit()

    db.add(m.ImportacaoCatalogo(linha_id=linha.id, nome_arquivo=nome_arquivo, tipo_arquivo="excel",
                                 confirmado_pelo_usuario=True,
                                 observacao=f"Sem alteração técnica — anexados: "
                                            f"{'nomenclatura (campos)' if campos else ''}"
                                            f"{' e ' if campos and qtd_atualizados else ''}"
                                            f"{f'descrição comercial ({qtd_atualizados} modelo(s))' if qtd_atualizados else ''}"
                                            f"{' e fatores de gás' if fatores_gas else ''}."))
    db.commit()
    return {"linha": linha.nome, "fabricante": linha.fabricante.nome, "acao": "complementos_anexados",
            "linha_id": linha.id, "qtd_descricoes": qtd_atualizados, "qtd_campos": len(campos or [])}


