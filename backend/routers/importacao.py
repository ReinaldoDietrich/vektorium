"""Importação de catálogo de forçadores (Etapa 3) — duas formas:
1) Planilha Excel (.xlsx, template fixo) — determinístico, sem nenhuma adivinhação de texto.
2) Documento Word (.docx) de preparação — cabeçalho preenchível + espaços para colar as imagens
   do catálogo; o usuário leva esse arquivo para uma conversa com o Claude (esta ou outra,
   sem precisar de contexto prévio) para gerar o Excel, e depois importa o Excel aqui."""
import io
from fastapi import APIRouter, Body, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict
from ..importacao.excel_import import gerar_template, montar_preview, salvar_grupo, anexar_complementares
from ..importacao.matriz import matriz_para_modelos
from ..importacao.docx_template import gerar_documento_importacao

router = APIRouter(prefix="/api/importacao", tags=["importacao"])


@router.get("/template")
def baixar_template(pasta: str = None):
    from ..utils import resposta_excel_catalogo
    conteudo = gerar_template()
    return resposta_excel_catalogo(conteudo, "template_catalogo_forcadores.xlsx", pasta=pasta)


@router.get("/documento")
def baixar_documento_importacao(pasta: str = None):
    from ..utils import resposta_arquivo_catalogo
    conteudo = gerar_documento_importacao()
    return resposta_arquivo_catalogo(conteudo, "documento_importacao_forcadores.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", pasta=pasta)


@router.post("/excel-preview")
def preview_excel(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Lê o Excel e devolve a matriz de cada linha para revisão no app — nada é gravado ainda."""
    conteudo = arquivo.file.read()
    resultado = montar_preview(db, conteudo)
    if "erro" not in resultado:
        resultado["nome_arquivo"] = arquivo.filename
    return resultado


@router.post("/excel-confirmar")
def confirmar_excel(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Grava as linhas revisadas/corrigidas pelo usuário na grade de preview."""
    nome_arquivo = payload.get("nome_arquivo")
    resultado = {"linhas": []}
    for item in payload.get("linhas", []):
        matriz = item["matriz"]
        modelos = matriz_para_modelos(matriz)
        if item.get("status") == "sem_alteracoes" and not item.get("forcar_gravacao"):
            fatores_gas = item.get("fatores_gas")
            campos = item.get("campos")
            tem_descricao = any(md.get("descricao_comercial") for md in modelos)
            linha_anterior_id = item.get("linha_anterior_id")
            if linha_anterior_id and (tem_descricao or fatores_gas or campos):
                r = anexar_complementares(db, linha_anterior_id, modelos, nome_arquivo, fatores_gas, campos)
            else:
                r = {"linha": matriz["linha"], "fabricante": matriz["fabricante"],
                     "acao": "sem_alteracoes", "observacao": item.get("observacao")}
            resultado["linhas"].append(r)
            continue
        r = salvar_grupo(db, matriz["fabricante"], matriz["linha"], matriz["versao_catalogo"], modelos, nome_arquivo,
                          fatores_gas=item.get("fatores_gas"), campos=item.get("campos"),
                          id_pai=item.get("id_pai"))
        resultado["linhas"].append(r)
    return resultado


@router.get("/historico")
def historico(linha_id: int = None, db: Session = Depends(get_db)):
    q = db.query(m.ImportacaoCatalogo)
    if linha_id:
        q = q.filter_by(linha_id=linha_id)
    return [model_to_dict(i) for i in q.order_by(m.ImportacaoCatalogo.id.desc()).all()]
