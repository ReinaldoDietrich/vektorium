# -*- coding: utf-8 -*-
"""Catálogo Comercial — texto + foto unificados por categoria (Painel Térmico, Porta
Frigorífica, Válvula de Expansão, Supervisório e outras que surgirem). Cadastro manual, sem
importação — insumo para os relatórios de memorial/proposta gerados depois. Forçadores e
Unidades Condensadoras continuam com seu próprio cadastro comercial (LinhaForcador/CatalogoUC),
por já carregarem dado técnico tabular junto."""
import base64
import os
from pathlib import Path
from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from .. import id_comercial
from ..database import get_db
from ..utils import model_to_dict, list_to_dict

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}

router = APIRouter(prefix="/api/catalogo-comercial", tags=["catalogo-comercial"])
_BASE = Path(__file__).resolve().parent.parent.parent
_AD = os.environ.get("VEKTORIUM_APPDATA")
_UPLOADS_DIR = Path(_AD) / "uploads" if _AD else _BASE / "uploads"

@router.get("")
def listar(categoria: str = None, db: Session = Depends(get_db)):
    # Ordena por posicao real na arvore de Id Comercial (nao alfabetico por nome -- um cadastro
    # novo caia no meio dos demais e o usuario tinha que cacar onde entrou). Item sem Id Comercial
    # ainda (recem-criado, em preenchimento) vai pro final da categoria, na ordem de cadastro --
    # assim que ganha um Id valido e e salvo, reordena para a posicao certa.
    q = db.query(m.CatalogoComercial)
    if categoria:
        q = q.filter_by(categoria=categoria)
    itens = q.all()

    def _chave(c):
        cat = c.categoria or ""   # categoria pode ser None (itens novos não usam mais categoria) — evita TypeError ao ordenar
        if c.id_comercial:
            return (cat, 0, id_comercial.chave_codigo(c.id_comercial), c.id)
        return (cat, 1, (), c.id)

    itens.sort(key=_chave)
    return list_to_dict(itens)


@router.post("")
def criar(payload: dict = Body(...), db: Session = Depends(get_db)):
    id_com = payload.get("id_comercial") or None
    if not id_com:
        raise HTTPException(400, "Escolha o Id Comercial — ele define a categoria do cadastro.")
    modelo = payload.get("modelo") or None
    # Com Modelo preenchido, o cadastro nasce apontando pro nó-filho específico do Modelo, não
    # pro nó de categoria/fabricante escolhido no seletor (ver id_comercial.resolver_no_modelo).
    if id_com and modelo:
        id_com = id_comercial.resolver_no_modelo(db, id_com, modelo)
        db.flush()  # sessão é autoflush=False — sem isso, o nó recém-criado não aparece na
                    # consulta seguinte (bug real reportado 2026-08-06: Id Cadastro saía None)
    existe_na_arvore = id_com and db.query(m.IdComercial).filter_by(codigo=id_com).first()
    # Categoria = nome do nó-RAIZ do Id (mesmo nível do agrupamento da Tela D, por Id-raiz) — deriva
    # do Id, satisfaz o NOT NULL com valor real, sem placeholder (aprovado 2026-08-14).
    raiz = str(id_com).split(".")[0]
    categoria = id_comercial.nome_por_codigo(db, raiz) or raiz
    obj = m.CatalogoComercial(categoria=categoria, fabricante=payload.get("fabricante"),
                               modelo=modelo,
                               nome=payload["nome"], descricao_comercial=payload.get("descricao_comercial"),
                               id_comercial=id_com,
                               id_cadastro=id_comercial.gerar_id_cadastro(db, id_com) if existe_na_arvore else None)
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.get("/arvore-ids")
def listar_arvore_ids(db: Session = Depends(get_db)):
    """Árvore de Ids comerciais (ver id_comercial.py) — usada pelo seletor em cascata desta tela,
    pra o usuário escolher Categoria > Subcategoria > Item em vez de digitar o código na mão."""
    return list_to_dict(id_comercial.listar_arvore(db))


@router.get("/memorial-teste")
def memorial_teste(projeto_id: int, db: Session = Depends(get_db)):
    """Página teste (item 1.1 do escopo) — busca cruzada: junta os Ids referenciados pelas
    seleções de todos os Sistemas do projeto (avulsos + catálogo) e devolve só os itens de
    CatalogoComercial (Tela D) que realmente têm foto/texto cadastrado nesse Id, sem repetir."""
    return id_comercial.montar_memorial_projeto(db, projeto_id)


@router.put("/{item_id}")
def atualizar(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.CatalogoComercial, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")

    id_comercial_antes = obj.id_comercial
    modelo_antes = obj.modelo

    for k, v in payload.items():
        if hasattr(obj, k) and k not in ("id", "id_cadastro"):
            setattr(obj, k, v)

    # Com Modelo preenchido, o Id Comercial salvo aponta pro nó-filho específico do Modelo, não
    # pro nó de categoria/fabricante escolhido no seletor (ver id_comercial.resolver_no_modelo) —
    # sem isso, vários produtos diferentes cadastrados sob o mesmo Id de categoria/fabricante
    # deixavam o Memorial sem saber qual dos N puxar (aprovado 2026-08-06). Se o usuário trocou a
    # categoria no seletor, resolve embaixo da NOVA categoria; se só o texto do Modelo mudou
    # (categoria igual), resolve embaixo do PAI do nó atual — senão ficaria aninhando nó dentro de
    # nó a cada correção de texto. Sem mudança nenhuma (Salvar sem editar), reaproveita o mesmo nó.
    if obj.modelo and obj.id_comercial:
        mudou_categoria = obj.id_comercial != id_comercial_antes
        mudou_modelo = obj.modelo != modelo_antes
        if mudou_categoria:
            obj.id_comercial = id_comercial.resolver_no_modelo(db, obj.id_comercial, obj.modelo)
            db.flush()
        elif mudou_modelo and id_comercial_antes:
            pai = id_comercial_antes.rsplit(".", 1)[0]
            obj.id_comercial = id_comercial.resolver_no_modelo(db, pai, obj.modelo)
            db.flush()

    # Id Cadastro é gerado, nunca digitado. Regenerado sempre que o Id Comercial salvo for
    # diferente do que gerou o Id Cadastro atual — cobre criação, correção de um Id Comercial
    # errado (bug real reportado 2026-08-06: usuário salvou com Id errado e não tinha como
    # corrigir, porque antes o Id Cadastro ficava fixo pra sempre) e revisão de cadastros antigos
    # com id_comercial órfão. Sem chave de busca em nenhuma outra tabela (só rótulo/sequencial
    # visual), então regenerar não quebra nenhuma referência do sistema. Sem Id Comercial, some.
    if obj.id_comercial:
        prefixo_atual = f"{obj.id_comercial}-"
        if not (obj.id_cadastro and obj.id_cadastro.startswith(prefixo_atual)):
            existe_na_arvore = db.query(m.IdComercial).filter_by(codigo=obj.id_comercial).first()
            if existe_na_arvore:
                obj.id_cadastro = id_comercial.gerar_id_cadastro(db, obj.id_comercial)
    else:
        obj.id_cadastro = None
    db.commit()
    return model_to_dict(obj)


@router.delete("/{item_id}")
def excluir(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CatalogoComercial, item_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}


@router.post("/{item_id}/foto")
async def enviar_foto(item_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    obj = db.get(m.CatalogoComercial, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    conteudo = await arquivo.read()
    ext = (Path(arquivo.filename or "").suffix or ".jpg").lower()
    mime = _MIME.get(ext, "image/jpeg")
    obj.imagem_path = f"data:{mime};base64,{base64.b64encode(conteudo).decode('ascii')}"
    db.commit()
    return {"imagem_path": obj.imagem_path}
