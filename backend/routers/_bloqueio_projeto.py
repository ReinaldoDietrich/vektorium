# -*- coding: utf-8 -*-
"""Projeto "Fechado" — trava reversível de edição (Tela 1, aprovado 2026-08-12). Um único ponto
de verificação, chamado no início de todo endpoint de escrita (POST/PUT/DELETE/PATCH) de todo
router do app — nunca em leitura (GET). `Projeto.fechado=True` bloqueia qualquer alteração; o
próprio botão "Reabrir Projeto" (Tela 1) volta a liberar.

Metodologia usada pra aplicar isso nos ~147 endpoints de escrita (21 arquivos) sem esquecer
nenhum, ver checklist em Documentos de Criação — resumo:
  1. `verificar_projeto_aberto(db, projeto_id)` — endpoint que já recebe `projeto_id` direto
     (query/path) chama isso como PRIMEIRA linha do corpo.
  2. `verificar_projeto_da(db, objeto)` — endpoint que recebe o id de um filho (câmara, sistema,
     item, etc.) busca o objeto primeiro (like sempre já fazia, pro 404), então chama isso logo
     em seguida, ANTES de qualquer `setattr`/`db.add`/`db.delete`. Sobe a cadeia de relações já
     existente no próprio model (`.sistema.projeto`, `.projeto`, `.camara.sistema.projeto` etc.)
     — nunca duplica dado, só navega o que o SQLAlchemy já resolve.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .. import models as m


def verificar_projeto_aberto(db: Session, projeto_id: int | None):
    """Bloqueia a escrita se o projeto (buscado direto pelo id) estiver Fechado. `projeto_id`
    None é no-op (endpoint que não pertence a projeto nenhum, ex.: cadastro de catálogo global)."""
    if projeto_id is None:
        return
    projeto = db.get(m.Projeto, projeto_id)
    if projeto and projeto.fechado:
        raise HTTPException(423, "Projeto fechado — reabra o projeto na Tela 1 antes de editar.")


def _achar_projeto(objeto, profundidade=4):
    """Sobe a cadeia de relações já existente no próprio model até achar o Projeto — tenta, nessa
    ordem, `.projeto` e `.sistema` (SistemaRefrigeracao sempre tem `.projeto`), recursivamente
    (cobre objeto -> câmara -> sistema -> projeto, por exemplo). `profundidade` evita loop
    infinito em relação mal configurada; nunca deveria realmente precisar de mais de 3 saltos
    neste schema."""
    if objeto is None or profundidade <= 0:
        return None
    if isinstance(objeto, m.Projeto):
        return objeto
    projeto = getattr(objeto, "projeto", None)
    if isinstance(projeto, m.Projeto):
        return projeto
    proximo = getattr(objeto, "sistema", None)
    if proximo is not None:
        return _achar_projeto(proximo, profundidade - 1)
    return None


def verificar_projeto_da(objeto):
    """Bloqueia a escrita se o Projeto do objeto (já buscado pelo endpoint) estiver Fechado —
    sobe a cadeia de relações já existente no model (`.sistema.projeto`, `.projeto`, etc., ver
    `_achar_projeto`) até achar o Projeto. Se o objeto não tem caminho direto até o Projeto
    (ex.: item filho de câmara, como Porta/Equipamento/Forçador, que só guarda `camara_id`), o
    endpoint precisa buscar a Câmara primeiro (ele já faz isso pro 404) e passar ELA aqui, não o
    item filho."""
    projeto = _achar_projeto(objeto)
    if projeto and projeto.fechado:
        raise HTTPException(423, "Projeto fechado — reabra o projeto na Tela 1 antes de editar.")
