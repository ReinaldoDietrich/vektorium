# -*- coding: utf-8 -*-
"""Importação de Rack Paralelo (Tela 6) via planilha Excel (1 aba, "Rack") — fonte é o relatório
de dimensionamento de compressores do fabricante (Bitzer BITZER Software ou Copeland Select),
transcrito por uma IA a partir do documento de instruções (ver rack_docx_template.py). Cada linha
casa com UM SISTEMA do projeto pelo nome exato (Tela 1) — diferente de Válvulas (que casa por
forçador), aqui é 1 registro por sistema (RackParalelo é 1:1 com o sistema)."""
import io
import openpyxl
from sqlalchemy.orm import Session
from .. import models as m

ABA_RACK = "Rack"

COLUNAS_RACK = [
    "Sistema", "Quantidade_Compressores", "Tensao", "Linha_Compressor",
    "Fabricante_Compressor", "Modelo_Compressor", "COP_Compressor", "Capacidade_Compressor_Kcal_H",
    "Carga_Total_Fornecida_Kcal_H", "Calor_Total_Rejeitado_Kcal_H", "Potencia_Total_W",
    "Corrente_Nominal_A", "Corrente_Maxima_Trabalho_A", "Vazao_Massica_Kg_H", "Carga_Oleo_L",
    "Conexao_Descarga", "Conexao_Succao", "HP_Total", "Tanque_Liquido_L", "Carga_Gas_Estimada_Kg",
]

# Mapa coluna da planilha -> campo do modelo RackParalelo (mesmo nome, só minúsculo)
_CAMPO_MODELO = {col: col.lower() for col in COLUNAS_RACK if col != "Sistema"}


def gerar_template_rack() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ABA_RACK
    ws.append(COLUNAS_RACK)
    ws.append(["HTA", 4, "380V-3-60Hz", "Semi-hermetic Reciprocating", "Bitzer", "4PES-12Y",
                4.17, "Não informado", 150800, 195400, 36100, 65.9, 28.8, 3650, "Não informado",
                "28mm - 1.1/8\"", "35mm - 1.3/8\"", "Não informado", 160.0, 176.5])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _ler_aba(wb):
    if ABA_RACK not in wb.sheetnames:
        return []
    ws = wb[ABA_RACK]
    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        return []
    cab = [str(c).strip() if c is not None else "" for c in linhas[0]]
    idx = {col: cab.index(col) for col in COLUNAS_RACK if col in cab}
    out = []
    for linha in linhas[1:]:
        if not linha or all(v is None for v in linha):
            continue
        reg = {col: (linha[idx[col]] if col in idx and idx[col] < len(linha) else None) for col in COLUNAS_RACK}
        out.append(reg)
    return out


def ler_planilha_rack(conteudo: bytes) -> list:
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    return _ler_aba(wb)


def _num_ou_none(v):
    """'Não informado' (ou vazio) -> None; número -> float."""
    if v is None or (isinstance(v, str) and v.strip().lower() in ("não informado", "nao informado", "")):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


_CAMPOS_NUMERICOS = {
    "quantidade_compressores", "cop_compressor", "capacidade_compressor_kcal_h",
    "carga_total_fornecida_kcal_h", "calor_total_rejeitado_kcal_h", "potencia_total_w",
    "corrente_nominal_a", "corrente_maxima_trabalho_a", "vazao_massica_kg_h", "carga_oleo_l",
    "hp_total", "tanque_liquido_l", "carga_gas_estimada_kg",
}


def montar_preview_rack(db: Session, projeto_id: int, conteudo: bytes) -> dict:
    linhas = ler_planilha_rack(conteudo)
    if not linhas:
        return {"erro": "Aba 'Rack' não encontrada ou vazia. Use o template."}
    sistemas = {s.nome: s for s in db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all()}

    itens = []
    for linha in linhas:
        nome_sistema = (linha.get("Sistema") or "").strip()
        sistema = sistemas.get(nome_sistema)
        item = {"sistema_nome": nome_sistema, "encontrado": sistema is not None,
                "sistema_id": sistema.id if sistema else None,
                "tipo_compressao": sistema.tipo_compressao if sistema else None}
        for col in COLUNAS_RACK:
            if col == "Sistema":
                continue
            campo = _CAMPO_MODELO[col]
            valor = linha.get(col)
            item[campo] = _num_ou_none(valor) if campo in _CAMPOS_NUMERICOS else (
                None if (valor is None or str(valor).strip().lower() in ("não informado", "nao informado")) else valor)
        itens.append(item)
    return {"itens": itens}


def salvar_rack(db: Session, itens: list) -> dict:
    from ..routers.rack_paralelo import _get_or_create
    criadas = atualizadas = ignoradas = 0
    for it in itens:
        if not it.get("sistema_id"):
            ignoradas += 1
            continue
        rack = _get_or_create(db, it["sistema_id"])
        era_nova = rack.quantidade_compressores is None
        for campo in _CAMPO_MODELO.values():
            if campo in it:
                setattr(rack, campo, it[campo])
        if era_nova:
            criadas += 1
        else:
            atualizadas += 1
    db.commit()
    return {"ok": True, "criadas": criadas, "atualizadas": atualizadas, "ignoradas": ignoradas}
