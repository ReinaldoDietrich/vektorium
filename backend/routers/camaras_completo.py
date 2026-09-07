import json
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict, chave_ordem_camara
from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo
from .. import id_comercial as idc
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf

router = APIRouter(prefix="/api/camaras-completo", tags=["camaras-completo"])

CAMPOS_BASICOS = {
    "sistema_id", "nome", "linha_succao", "linha_eletrica", "temp_interna", "largura", "comprimento",
    "pedireito", "utilizar_valv_reg_pressao", "dt_evaporacao_desejado",
    "produto_id", "qtd_estocada", "mov_diaria", "tempo_processo", "temp_entrada", "temp_saida",
    "tipo_embalagem_id", "massa_embalagem", "isolamento_parede_id", "isolamento_teto_id", "isolamento_piso_id",
    "num_portas", "porta_largura", "porta_altura", "freq_abertura_min_h", "protecao_porta",
    "fonte_ar", "temp_adjacente", "umidade_adjacente",
    "num_pessoas", "tempo_pessoas", "qtd_luminarias", "potencia_luminaria", "horas_iluminacao_carga",
    "tipo_ambiente_lumino_id", "modelo_luminaria_id", "potencia_luminaria_texto", "modelo_luminaria_texto",
    "fator_seguranca", "tempo_func_compressores",
}


def _codigo(camara: m.CamaraCompleto) -> str:
    prefixo = (camara.sistema.nome[:3].upper() if camara.sistema and camara.sistema.nome else "???")
    return f"{prefixo}{camara.linha_succao or '?'}{camara.linha_eletrica or '?'}"


@router.get("")
def listar(sistema_id: int = None, projeto_id: int = None, db: Session = Depends(get_db)):
    q = db.query(m.CamaraCompleto)
    if sistema_id:
        q = q.filter_by(sistema_id=sistema_id)
    if projeto_id:
        q = q.join(m.SistemaRefrigeracao).filter(m.SistemaRefrigeracao.projeto_id == projeto_id)
    camaras = sorted(q.all(), key=lambda c: chave_ordem_camara(
        c.sistema.nome if c.sistema else "", c.linha_succao, c.linha_eletrica))
    out = []
    for c in camaras:
        calculo = calcular_camara_completo(db, c)
        out.append({**model_to_dict(c), "codigo": _codigo(c), "calculo": calculo})
    return out


@router.post("")
def criar(payload: dict = Body(...), db: Session = Depends(get_db)):
    dados = {k: v for k, v in payload.items() if k in CAMPOS_BASICOS}
    if dados.get("sistema_id"):
        bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, dados["sistema_id"]))
    obj = m.CamaraCompleto(**dados)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.get("/{camara_id}")
def obter(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraCompleto, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    def _equip_dict(e):
        t = e.tipo_equipamento
        fu = t.fator_calor_rejeitado if t.fator_calor_rejeitado is not None else 1.0
        fs = t.fator_simultaneidade if t.fator_simultaneidade is not None else 1.0
        calor_w = (t.potencia_tipica_w or 0) * fu * fs
        return {**model_to_dict(e), "tipo_nome": t.nome, "calor_unitario_kcal_h": round(calor_w * 0.86, 1)}

    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calcular_camara_completo(db, obj),
            "equipamentos": [_equip_dict(e) for e in obj.equipamentos],
            "portas": list_to_dict(obj.portas)}


@router.put("/{camara_id}")
def atualizar(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.CamaraCompleto, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    bf.verificar_entidade_aberta(obj)
    for k, v in payload.items():
        if k in CAMPOS_BASICOS:
            setattr(obj, k, v)
    # Salvar uma câmara vinculada é o sinal de que o usuário revisou os lançamentos dessa câmara
    # à luz da configuração atual do sistema — limpa o alerta "revisar lançamentos" (Tela 1).
    if obj.sistema and obj.sistema.precisa_revisar:
        obj.sistema.precisa_revisar = False
    db.commit()
    db.refresh(obj)
    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calcular_camara_completo(db, obj)}


@router.delete("/{camara_id}")
def excluir(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraCompleto, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    bf.verificar_entidade_aberta(obj)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/{camara_id}/editar")
def abrir_edicao(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraCompleto, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    bf.editar_entidade(db, obj)
    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calcular_camara_completo(db, obj)}


@router.post("/{camara_id}/salvar")
def fechar_entidade(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraCompleto, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    calculo = calcular_camara_completo(db, obj)
    bf.salvar_entidade(db, obj, snapshot=calculo, nome_model="CamaraCompleto")
    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calculo}


@router.post("/{camara_id}/duplicar")
def duplicar(camara_id: int, db: Session = Depends(get_db)):
    """Copia só os dados de dimensionamento (campos básicos + equipamentos + portas) — Forçadores e
    Válvulas NÃO entram, a câmara nova nasce sem forçador selecionado (orientação explícita do
    usuário: isso é seleção de equipamento, não dado de dimensionamento)."""
    orig = db.get(m.CamaraCompleto, camara_id)
    if not orig:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(orig)
    dados = {campo: getattr(orig, campo) for campo in CAMPOS_BASICOS}
    dados["nome"] = f"{orig.nome} (cópia)" if orig.nome else "(cópia)"
    nova = m.CamaraCompleto(**dados)
    db.add(nova)
    db.flush()
    for e in orig.equipamentos:
        db.add(m.EquipamentoCamaraCompleto(camara_id=nova.id, tipo_equipamento_id=e.tipo_equipamento_id,
                                            qtd=e.qtd, tempo=e.tempo))
    for p in orig.portas:
        db.add(m.PortaCamara(camara_id=nova.id, quantidade=p.quantidade, largura=p.largura, altura=p.altura,
                              freq_abertura_min_h=p.freq_abertura_min_h, protecao=p.protecao,
                              fonte_ar=p.fonte_ar, temp_adjacente=p.temp_adjacente,
                              umidade_adjacente=p.umidade_adjacente, ordem=p.ordem))
    db.commit()
    db.refresh(nova)
    return {**model_to_dict(nova), "codigo": _codigo(nova)}


# ---------- Equipamentos (Seção 7) ----------

@router.post("/{camara_id}/equipamentos")
def add_equipamento(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    camara = db.get(m.CamaraCompleto, camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    obj = m.EquipamentoCamaraCompleto(camara_id=camara_id, tipo_equipamento_id=payload["tipo_equipamento_id"],
                                       qtd=payload.get("qtd", 1), tempo=payload.get("tempo", 0))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/{camara_id}/equipamentos/{item_id}")
def upd_equipamento(camara_id: int, item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.EquipamentoCamaraCompleto, item_id)
    if not obj:
        raise HTTPException(404, "Equipamento não encontrado")
    camara = db.get(m.CamaraCompleto, camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    if "tipo_equipamento_id" in payload:
        obj.tipo_equipamento_id = payload["tipo_equipamento_id"]
    if "qtd" in payload:
        obj.qtd = payload["qtd"] or 1
    if "tempo" in payload:
        obj.tempo = payload["tempo"] or 0
    db.commit()
    return {"ok": True}


@router.delete("/{camara_id}/equipamentos/{item_id}")
def remove_equipamento(camara_id: int, item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.EquipamentoCamaraCompleto, item_id)
    if obj:
        camara = db.get(m.CamaraCompleto, camara_id)
        bp.verificar_projeto_da(camara)
        bf.verificar_entidade_aberta(camara)
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------- Portas (Seção 4 — infiltração; uma câmara pode ter várias portas) ----------

CAMPOS_PORTA = {"quantidade", "largura", "altura", "freq_abertura_min_h", "protecao",
                "fonte_ar", "temp_adjacente", "umidade_adjacente", "ordem"}


@router.post("/{camara_id}/portas")
def add_porta(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    camara = db.get(m.CamaraCompleto, camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    ordem = db.query(m.PortaCamara).filter_by(camara_id=camara_id).count()
    dados = {k: v for k, v in payload.items() if k in CAMPOS_PORTA}
    obj = m.PortaCamara(camara_id=camara_id, ordem=ordem, **dados)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/portas/{porta_id}")
def upd_porta(porta_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.PortaCamara, porta_id)
    if not obj:
        raise HTTPException(404, "Porta não encontrada")
    camara = db.get(m.CamaraCompleto, obj.camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    for k, v in payload.items():
        if k in CAMPOS_PORTA:
            setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/portas/{porta_id}")
def del_porta(porta_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PortaCamara, porta_id)
    if obj:
        camara = db.get(m.CamaraCompleto, obj.camara_id)
        bp.verificar_projeto_da(camara)
        bf.verificar_entidade_aberta(camara)
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------- Forçadores (Seção 8) ----------

def _provisionar_valvula(db: Session, camara: m.CamaraCompleto, forcador: m.ForcadorSelecaoCompleto):
    """Toda linha de forçador ganha 1 válvula própria — Fabricante e Tipo de Expansão vêm do
    Sistema (Tela 1: Fabricante Válvula / Válvula de Expansão), não são perguntados de novo aqui.
    Os campos de resultado (Modelo/Carga%/Conexões) ficam em branco até importação ou edição manual."""
    sistema = camara.sistema
    tipo_expansao_nome = (idc.nome_por_codigo(db, sistema.tipo_expansao) if sistema and sistema.tipo_expansao else None)
    db.add(m.ValvulaSelecaoCompleto(
        forcador_selecao_id=forcador.id, considerado=True,
        fabricante=(sistema.fabricante_valvula if sistema else None) or "—",
        tipo_expansao=tipo_expansao_nome or "Eletrônica",
    ))


@router.post("/{camara_id}/forcadores")
def add_forcador(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    camara = db.get(m.CamaraCompleto, camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    existentes = db.query(m.ForcadorSelecaoCompleto).filter_by(camara_id=camara_id).count()
    if existentes >= 5:
        raise HTTPException(400, "Máximo de 5 linhas de comparação")
    obj = m.ForcadorSelecaoCompleto(camara_id=camara_id, fabricante_id=payload["fabricante_id"],
                                     linha_id=payload["linha_id"], folga_desejada=payload.get("folga_desejada", 10),
                                     quantidade=payload.get("quantidade", 1), tipo_degelo=payload.get("tipo_degelo"),
                                     considerado=existentes == 0, codigo_curto=f"F{existentes + 1}")
    db.add(obj)
    db.flush()
    camara = db.get(m.CamaraCompleto, camara_id)
    _provisionar_valvula(db, camara, obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/{camara_id}/forcadores/{item_id}")
def upd_forcador(camara_id: int, item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ForcadorSelecaoCompleto, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    camara = db.get(m.CamaraCompleto, camara_id)
    bp.verificar_projeto_da(camara)
    bf.verificar_entidade_aberta(camara)
    if "folga_desejada" in payload:
        obj.folga_desejada = payload["folga_desejada"]
    if "quantidade" in payload:
        obj.quantidade = payload["quantidade"] or 1
    if "tipo_degelo" in payload:
        obj.tipo_degelo = payload["tipo_degelo"]
    if "nomenclatura_selecionada" in payload:
        obj.nomenclatura_selecionada = json.dumps(payload["nomenclatura_selecionada"] or {})
    if payload.get("considerado"):
        for row in db.query(m.ForcadorSelecaoCompleto).filter_by(camara_id=camara_id).all():
            row.considerado = (row.id == item_id)
    db.commit()
    return {"ok": True}


@router.delete("/{camara_id}/forcadores/{item_id}")
def remove_forcador(camara_id: int, item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ForcadorSelecaoCompleto, item_id)
    if obj:
        camara = db.get(m.CamaraCompleto, camara_id)
        bp.verificar_projeto_da(camara)
        bf.verificar_entidade_aberta(camara)
        era_considerado = obj.considerado
        db.delete(obj)
        db.commit()
        if era_considerado:
            sobrou = db.query(m.ForcadorSelecaoCompleto).filter_by(camara_id=camara_id).first()
            if sobrou:
                sobrou.considerado = True
                db.commit()
    return {"ok": True}


# ---------- Válvulas (Seção 8.1) — 1 por forçador, provisionada junto com ele; só edição dos
# campos de resultado (Fabricante/Tipo vêm do Sistema, não são recriáveis/excluíveis aqui) ----------

@router.put("/valvulas/{item_id}")
def upd_valvula(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ValvulaSelecaoCompleto, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    forcador = db.get(m.ForcadorSelecaoCompleto, obj.forcador_selecao_id)
    camara = db.get(m.CamaraCompleto, forcador.camara_id) if forcador else None
    bp.verificar_projeto_da(camara)
    if camara:
        bf.verificar_entidade_aberta(camara)
    for campo in ("modelo_selecao", "carga_abertura_pct", "conexao_entrada", "conexao_saida",
                  "capacidade_unit_kcal_h", "orificio", "tensao", "tipo_motor", "controlador"):
        if campo in payload:
            setattr(obj, campo, payload[campo])
    db.commit()
    return {"ok": True}
