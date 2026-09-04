# -*- coding: utf-8 -*-
"""Importação de Rack Paralelo (Excel gerado a partir do relatório de seleção de compressores —
Bitzer ou Copeland, ver rack_docx_template.py). Mesmo padrão upload -> prévia editável ->
confirmação usado em Válvulas/Forçador/UC."""
import io
from fastapi import APIRouter, Body, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..importacao.rack_import import gerar_template_rack, montar_preview_rack, salvar_rack
from ..importacao.rack_docx_template import gerar_documento_importacao_rack_bitzer, gerar_documento_importacao_rack_copeland

router = APIRouter(prefix="/api/rack-import", tags=["rack-import"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/template")
def baixar_template():
    return StreamingResponse(io.BytesIO(gerar_template_rack()), media_type=_XLSX,
                              headers={"Content-Disposition": "attachment; filename=Template_Rack.xlsx"})


@router.get("/documento/bitzer")
def baixar_documento_bitzer():
    return StreamingResponse(io.BytesIO(gerar_documento_importacao_rack_bitzer()), media_type=_DOCX,
                              headers={"Content-Disposition": "attachment; filename=Documento_Importacao_Rack_Bitzer.docx"})


@router.get("/documento/copeland")
def baixar_documento_copeland():
    return StreamingResponse(io.BytesIO(gerar_documento_importacao_rack_copeland()), media_type=_DOCX,
                              headers={"Content-Disposition": "attachment; filename=Documento_Importacao_Rack_Copeland.docx"})


@router.post("/preview")
async def preview(projeto_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    return montar_preview_rack(db, projeto_id, conteudo)


@router.post("/confirmar")
def confirmar(payload: dict = Body(...), db: Session = Depends(get_db)):
    return salvar_rack(db, payload.get("itens", []))
