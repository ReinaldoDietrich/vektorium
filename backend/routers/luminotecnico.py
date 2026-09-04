# -*- coding: utf-8 -*-
"""Estudo Luminotécnico (Tela 11) — aprovado 2026-08-08.
- CRUD de "Tela 11 - Cadastro Lâmpadas" (com cascata do campo Modelo na árvore de Ids Comerciais).
- Endpoint agregado, somente leitura, que reúne toda câmara (Completo/Simples) do projeto com
  Tipo Ambiente + Modelo Luminária preenchidos, recalculando ao vivo — igual ao padrão de
  Resumo de Painéis/Portas (nunca editado/excluído direto aqui, sempre reflexo do lançamento nas
  Telas 2/3)."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, chave_ordem_camara, resposta_excel_projeto
from ..exportacao.luminotecnico_export import gerar_excel_luminotecnico
from .. import id_comercial as idc
from ..calculos.luminotecnico import calcular_luminotecnico
from .camaras_completo import _codigo as _codigo_completo
from .camaras_simples import _codigo as _codigo_simples

router = APIRouter(prefix="/api/luminotecnico", tags=["luminotecnico"])

ANCORA_LAMPADAS = "1.4.1"

NOTAS = [
    "Para o desenvolvimento do projeto luminotécnico foram adotadas refletâncias de 80% para o "
    "teto e 75% para as paredes, considerando a utilização de painéis isotérmicos metálicos com "
    "acabamento na cor RAL 9003 (Branco Sinal). Para o piso foi considerada refletância de 20% "
    "(ou o valor correspondente ao acabamento especificado). Esses parâmetros foram utilizados na "
    "determinação do coeficiente de utilização da luminária e na simulação luminotécnica, "
    "permitindo representar adequadamente as características ópticas do ambiente e garantir maior "
    "precisão na estimativa dos níveis de iluminância.",
    "Na ausência da curva fotométrica definitiva da luminária, foi adotado um coeficiente de "
    "utilização (CU) igual a 0,80, compatível com ambientes frigorificados constituídos por "
    "painéis isotérmicos de alta refletância (RAL 9003), luminárias LED de distribuição ampla e "
    "montagem no teto. Na fase executiva, recomenda-se a validação do projeto por meio de "
    "simulação luminotécnica utilizando os arquivos fotométricos (IES/LDT) do fabricante das "
    "luminárias especificadas.",
]


@router.get("/lampadas")
def listar_lampadas(db: Session = Depends(get_db)):
    return [model_to_dict(l) for l in db.query(m.LookupLampada).order_by(m.LookupLampada.ordem, m.LookupLampada.id).all()]


@router.post("/lampadas")
def criar_lampada(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.LookupLampada(**{k: v for k, v in payload.items() if hasattr(m.LookupLampada, k) and k != "id"})
    if obj.modelo:
        obj.id_comercial = idc.resolver_no_modelo(db, ANCORA_LAMPADAS, obj.modelo)
        db.flush()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/lampadas/{item_id}")
def atualizar_lampada(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.LookupLampada, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    modelo_antes = obj.modelo
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    if obj.modelo and obj.modelo != modelo_antes:
        obj.id_comercial = idc.resolver_no_modelo(db, ANCORA_LAMPADAS, obj.modelo)
        db.flush()
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.delete("/lampadas/{item_id}")
def excluir_lampada(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.LookupLampada, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


def _extrair_potencia_w(texto):
    """Extrai o número de watts do texto exato do nó da árvore (ex.: "36W" -> 36.0)."""
    import re
    if not texto:
        return None
    match = re.search(r"[\d.,]+", texto)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _linha_camara(db, camara, sistema, tipo_camara):
    if not (camara.tipo_ambiente_lumino_id and camara.potencia_luminaria_texto):
        return None
    ambiente = camara.tipo_ambiente_lumino
    potencia_w = _extrair_potencia_w(camara.potencia_luminaria_texto)
    if potencia_w is None:
        return None
    lampada = db.query(m.LookupLampada).filter_by(potencia_w=potencia_w).first()
    if not lampada:
        return None
    largura = getattr(camara, "largura", None)
    comprimento = getattr(camara, "comprimento", None)
    altura = camara.pedireito
    calc = calcular_luminotecnico(largura, comprimento, altura, camara.qtd_luminarias or 0,
                                   ambiente.lux_recomendado, lampada.potencia_w, lampada.fluxo_lumens)
    # Nomenclatura completa (sistema+sucção+elétrica), igual à Compilação de Linhas — aprovado
    # 2026-08-10 (antes mostrava só camara.linha_succao cru). `_succao_ordem` guarda o valor cru
    # só pra ordenação (chave_ordem_camara), sem mudar o critério de ordem existente.
    codigo_completo = (_codigo_completo(camara) if tipo_camara == "Completo" else _codigo_simples(camara))
    return {
        "camara_id": camara.id, "tipo_camara": tipo_camara,
        "sistema_nome": sistema.nome if sistema else None,
        "linha_succao": codigo_completo, "_succao_ordem": camara.linha_succao,
        "linha_eletrica": camara.linha_eletrica,
        "ambiente": camara.nome,
        "largura": largura, "comprimento": comprimento, "altura": altura,
        "plano_calculo": 0,
        "qtd_luminarias": camara.qtd_luminarias, "modelo_luminaria": camara.modelo_luminaria_texto,
        "potencia_w": lampada.potencia_w, "fluxo_lumens": lampada.fluxo_lumens, "ip": lampada.ip,
        "temperatura_cor_k": lampada.temperatura_cor_k, "tensao": lampada.tensao,
        "tipo_ambiente": ambiente.nome,
        **calc,
    }


def montar_estudo(db: Session, projeto_id: int) -> dict:
    """Lógica do estudo luminotécnico, isolada da rota pra ser reaproveitada por
    composicao_preco.sincronizar_luminarias (mesmo padrão de calc_paineis_portas.montar_resumo)."""
    sistemas = db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all()
    linhas = []
    for sistema in sistemas:
        for camara in sistema.camaras_completo:
            linha = _linha_camara(db, camara, sistema, "Completo")
            if linha:
                linhas.append(linha)
        for camara in sistema.camaras_simples:
            linha = _linha_camara(db, camara, sistema, "Simples")
            if linha:
                linhas.append(linha)

    linhas.sort(key=lambda l: chave_ordem_camara(l["sistema_nome"], l["_succao_ordem"], l["linha_eletrica"]))
    for i, linha in enumerate(linhas, start=1):
        linha["seq"] = i
        linha.pop("_succao_ordem", None)

    # Resumo somatório de materiais: agrupa por MODELO (o que se compra de fato), não por
    # potência — aprovado 2026-08-10 ("não compro lâmpada por potência e sim modelo"). Fabricante
    # vem de LookupLampada casado pelo MODELO (não pela potência — lampada em _linha_camara é
    # casada só por potencia_w, pode ser um modelo diferente do escolhido na câmara).
    resumo = {}
    for linha in linhas:
        modelo = linha["modelo_luminaria"]
        if not modelo:
            continue
        resumo[modelo] = resumo.get(modelo, 0) + (linha["qtd_luminarias"] or 0)
    resumo_lista = []
    for modelo, qtd in sorted(resumo.items()):
        lampada_modelo = db.query(m.LookupLampada).filter_by(modelo=modelo).first()
        resumo_lista.append({"modelo_luminaria": modelo, "qtd_total": qtd,
                              "fabricante": lampada_modelo.fabricante if lampada_modelo else None})

    return {"linhas": linhas, "resumo_por_modelo": resumo_lista, "notas": NOTAS}


@router.get("/estudo")
def estudo_luminotecnico(projeto_id: int, db: Session = Depends(get_db)):
    return montar_estudo(db, projeto_id)


@router.get("/exportar/excel")
def exportar_luminotecnico_excel(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    dados = montar_estudo(db, projeto_id)
    conteudo = gerar_excel_luminotecnico(projeto, dados)
    return resposta_excel_projeto(conteudo, f"estudo_luminotecnico_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)
