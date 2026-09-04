# -*- coding: utf-8 -*-
"""Configurações Sistema — lista somente-leitura de todo campo de preenchimento/inserção de
dados das Telas 1 a 7 (registro fixo em CampoSistema, ver backend/scripts/migrar_campos_sistema.py
e models.py). Nunca editável por aqui — é referência/consulta, e fonte pro vínculo campo↔árvore
de Ids Comerciais (Tela E) e pra exportação em Excel."""
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import openpyxl
from ..database import get_db
from .. import models as m
from ..utils import list_to_dict

router = APIRouter(prefix="/api/sistema", tags=["sistema"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ordenados(db: Session):
    # Reorganização SEMPRE automática (aprovado 2026-08-09): primeiro por Tela, segundo pelo
    # sequencial numérico do próprio campo_id ("T23" -> 23) -- nunca pela coluna `ordem` (ordem de
    # inserção do script de migração, que já tinha 3 violações reais de agrupamento por Tela).
    # campo_id é sempre "T" + dígitos (garantido por migrar_campos_sistema.py) -- fatiar
    # campo_id[1:] é seguro.
    campos = db.query(m.CampoSistema).all()
    return sorted(campos, key=lambda c: (c.tela, int(c.campo_id[1:])))


@router.get("/campos")
def listar_campos(db: Session = Depends(get_db)):
    return list_to_dict(_ordenados(db))


@router.get("/campos/exportar/excel")
def exportar_campos_excel(db: Session = Depends(get_db)):
    campos = _ordenados(db)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ids de Campo"
    ws.append(["Id", "Rótulo"])
    for c in ws[1]:
        c.font = openpyxl.styles.Font(bold=True)
    for campo in campos:
        ws.append([campo.campo_id, campo.rotulo])
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 55
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type=_XLSX,
                              headers={"Content-Disposition": "attachment; filename=Ids_Campos_Sistema.xlsx"})
