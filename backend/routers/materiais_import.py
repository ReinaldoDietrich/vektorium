# -*- coding: utf-8 -*-
"""Importação de Materiais Mecânicos/Elétricos pra Composição de Preço — mesmo padrão de
upload -> prévia editável -> confirmação usado em Forçador/UC/Válvulas. Template simples
(Bloco/Centro de Custo/Fator/Descrição/Quantidade/Custo Unitário) porque, ao contrário dos
catálogos técnicos, aqui não há um catálogo de fabricante por trás — é lista de material livre."""
import io
from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import openpyxl
from ..database import get_db
from .. import models as m
from .. import composicao_preco as cp
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api/materiais-import", tags=["materiais-import"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_COLUNAS = ["Bloco", "Centro de Custo", "Fator", "Descrição", "Fabricante", "Quantidade", "Custo Unitário (R$)"]
_BLOCOS_IMPORTAVEIS = ["Materiais Mecânicos", "Materiais Elétricos"]


def _gerar_template() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Materiais"
    ws.append(_COLUNAS)
    for c in ws[1]:
        c.font = openpyxl.styles.Font(bold=True)
    ws.append(["Materiais Mecânicos", "2.1", "FT5", "Tubulação de cobre", "", 1, 0])
    ws.append(["Materiais Elétricos", "12.1", "FT5", "Materiais elétricos (infra e cabos)", "", 1, 0])
    dv = openpyxl.worksheet.datavalidation.DataValidation(
        type="list", formula1='"Materiais Mecânicos,Materiais Elétricos"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("A2:A1000")
    for i, w in enumerate([22, 16, 10, 45, 18, 12, 18], start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/template")
def baixar_template():
    return StreamingResponse(io.BytesIO(_gerar_template()), media_type=_XLSX,
                              headers={"Content-Disposition": "attachment; filename=Template_Materiais.xlsx"})


@router.post("/preview")
async def preview(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True)
    ws = wb.active
    fatores_validos = {f.codigo for f in db.query(m.FatorVenda).all()}
    itens = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or all(v is None for v in row):
            continue
        bloco, centro_custo, fator, descricao, fabricante, quantidade, custo_unit = (list(row) + [None] * 7)[:7]
        erros = []
        if bloco not in _BLOCOS_IMPORTAVEIS:
            erros.append(f'Bloco deve ser um de: {", ".join(_BLOCOS_IMPORTAVEIS)}')
        if not descricao:
            erros.append("Descrição obrigatória")
        if fator and fator not in fatores_validos:
            erros.append(f'Fator "{fator}" não cadastrado')
        itens.append({"bloco": bloco, "centro_custo": centro_custo, "fator": fator,
                      "descricao": descricao, "fabricante": fabricante, "quantidade": quantidade or 1,
                      "custo_unitario": custo_unit or 0, "erros": erros})
    return {"itens": itens}


@router.post("/confirmar")
def confirmar(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    itens = payload.get("itens", [])
    fatores = {f.codigo: f.id for f in db.query(m.FatorVenda).all()}
    ordem_por_bloco = {}
    criados = 0
    for it in itens:
        if it.get("erros"):
            continue
        bloco = it["bloco"]
        if bloco not in _BLOCOS_IMPORTAVEIS:
            continue
        centro = None
        if it.get("centro_custo"):
            centro = (db.query(m.CentroCusto)
                      .filter_by(codigo=str(it["centro_custo"])).first())
        ordem = ordem_por_bloco.get(bloco)
        if ordem is None:
            ordem = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id, bloco=bloco).count()
        db.add(m.ComposicaoPrecoItem(
            projeto_id=projeto_id, bloco=bloco, descricao=it["descricao"],
            fabricante=it.get("fabricante") or None,
            quantidade=it.get("quantidade") or 1, custo_unitario=it.get("custo_unitario") or 0,
            fator_id=fatores.get(it.get("fator")), centro_custo_id=centro.id if centro else None,
            origem="manual", ordem=ordem))
        ordem_por_bloco[bloco] = ordem + 1
        criados += 1
    db.commit()
    return {"itens_importados": criados}
