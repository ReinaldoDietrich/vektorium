# -*- coding: utf-8 -*-
"""Importação de seleção de Válvulas de Expansão (Excel gerado a partir do relatório de
dimensionamento do fabricante — ver valvula_docx_template.py). Mesmo padrão de
upload -> prévia editável -> confirmação usado em Forçador/UC."""
import io
from fastapi import APIRouter, Body, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..importacao.valvula_import import gerar_template_valvulas, montar_preview_valvulas, salvar_valvulas
from ..importacao.valvula_docx_template import gerar_documento_importacao_valvulas

router = APIRouter(prefix="/api/valvulas-import", tags=["valvulas-import"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/template")
def baixar_template():
    return StreamingResponse(io.BytesIO(gerar_template_valvulas()), media_type=_XLSX,
                              headers={"Content-Disposition": "attachment; filename=Template_Valvulas.xlsx"})


@router.get("/documento")
def baixar_documento():
    return StreamingResponse(io.BytesIO(gerar_documento_importacao_valvulas()), media_type=_DOCX,
                              headers={"Content-Disposition": "attachment; filename=Documento_Importacao_Valvulas.docx"})


@router.post("/preview")
async def preview(projeto_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    return montar_preview_valvulas(db, projeto_id, conteudo)


@router.post("/confirmar")
def confirmar(payload: dict = Body(...), db: Session = Depends(get_db)):
    # sobrepor=False (escolha do usuário na reimportação): mantém válvulas já preenchidas.
    return salvar_valvulas(db, payload.get("itens", []), payload.get("sobrepor", True))
