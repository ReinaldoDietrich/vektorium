"""SE-032 FASE D — Sincronização automática de projetos na nuvem (Supabase Storage)."""

import json
import uuid
import socket
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import engine
from ..models import (
    Projeto, SistemaRefrigeracao,
    CamaraCompleto, PortaCamara, EquipamentoCamaraCompleto,
    ForcadorSelecaoCompleto, ValvulaSelecaoCompleto,
    CamaraSimples, ForcadorSelecaoSimples, ValvulaSelecaoSimples,
    Expositor, ModuloExpositor,
    RackParalelo, RackCondensadorSelecao, CompressorRack, MaterialRack,
    UnidadeSelecaoSistema,
    PainelTermico, PortaFrigorifica,
    ComposicaoPrecoItem, CondicaoPagamentoProjeto, CondicaoPagamentoParcela,
    ComissaoVendedorProjeto, MargemNegociacaoProjeto,
    Vendedor,
)

router = APIRouter(prefix="/api/cloud", tags=["cloud"])

SUPABASE_URL = "https://luzvgsgxutggnbyrhswg.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_BreZGIXnU6_rdBi8n3bF5w_N3HZ56-S"
BUCKET = "vektorium-projetos"
LOCK_TTL_SECONDS = 90  # 90s — renovado por heartbeat a cada 30s (SE-063)


# ---- Schemas ----

class LockRequest(BaseModel):
    user_id: str
    token: str


class SyncRequest(BaseModel):
    user_id: str
    token: str


# ---- Helpers de Storage ----

def _headers(token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
    }


def _storage_upload(token: str, path: str, data: bytes) -> bool:
    r = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
        content=data,
        headers={
            **_headers(token),
            "Content-Type": "application/json",
            "x-upsert": "true",
        },
        timeout=30,
    )
    return r.status_code in (200, 201)


def _storage_download(token: str, path: str) -> Optional[bytes]:
    r = httpx.get(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
        headers=_headers(token),
        timeout=30,
    )
    if r.status_code == 200:
        return r.content
    return None


def _storage_list(token: str, prefix: str) -> list:
    r = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
        json={"prefix": prefix, "limit": 1000, "offset": 0},
        headers={**_headers(token), "Content-Type": "application/json"},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    return []


def _storage_delete(token: str, path: str) -> bool:
    r = httpx.delete(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
        json={"prefixes": [path]},
        headers={**_headers(token), "Content-Type": "application/json"},
        timeout=10,
    )
    return r.status_code in (200, 204)


# ---- Endpoints de Session Lock ----

@router.post("/check-lock")
def check_lock(req: LockRequest):
    """Verifica se existe lock ativo. Retorna locked=True se houver sessão ativa não-vencida."""
    lock_path = f"{req.user_id}/.session_lock"
    raw = _storage_download(req.token, lock_path)
    if raw is None:
        return {"locked": False}
    try:
        lock = json.loads(raw)
        expires_at = datetime.fromisoformat(lock["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now >= expires_at:
            return {"locked": False, "stale": True}
        return {"locked": True, "hostname": lock.get("hostname", "")}
    except Exception:
        return {"locked": False}


@router.post("/create-lock")
def create_lock(req: LockRequest):
    """Cria o session lock para este terminal."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=LOCK_TTL_SECONDS)
    lock = {
        "ts": now.isoformat(),
        "expires_at": expires.isoformat(),
        "hostname": socket.gethostname(),
    }
    lock_path = f"{req.user_id}/.session_lock"
    ok = _storage_upload(req.token, lock_path, json.dumps(lock).encode())
    return {"ok": ok}


@router.post("/delete-lock")
def delete_lock(req: LockRequest):
    """Remove o session lock (chamado no Sair)."""
    lock_path = f"{req.user_id}/.session_lock"
    try:
        ok = _storage_delete(req.token, lock_path)
    except Exception:
        ok = False
    return {"ok": ok}


# ---- Serialização de Projeto ----

def _row_cols(cls) -> set:
    return {col.name for col in cls.__table__.columns}


def _to_dict(obj, exclude: tuple) -> dict:
    return {
        col.name: getattr(obj, col.name)
        for col in obj.__table__.columns
        if col.name not in exclude
    }


def _filtrar(cls, data: dict, exclude: tuple = ()) -> dict:
    valid = _row_cols(cls)
    return {k: v for k, v in data.items() if k in valid and k not in exclude}


def _serializar_projeto(db: Session, projeto: Projeto) -> dict:
    data: dict = {
        "v": 1,
        "cloud_id": projeto.cloud_id,
        "serializado_em": datetime.now(timezone.utc).isoformat(),
        "projeto": _to_dict(projeto, ("id",)),
        "sistemas": [],
        "paineis": [],
        "portas": [],
        "composicao": [],
        "condicao_pagamento": None,
        "comissoes": [],
        "margem": None,
    }

    for sistema in db.query(SistemaRefrigeracao).filter_by(projeto_id=projeto.id).all():
        s = _to_dict(sistema, ("id", "projeto_id"))
        s["_old_id"] = sistema.id
        s["camaras_completo"] = []
        s["camaras_simples"] = []
        s["expositores"] = []
        s["racks"] = []
        s["uc_selecao"] = []

        for cc in db.query(CamaraCompleto).filter_by(sistema_id=sistema.id).all():
            c = _to_dict(cc, ("id", "sistema_id"))
            c["_old_id"] = cc.id
            c["portas"] = [_to_dict(p, ("id", "camara_id")) for p in db.query(PortaCamara).filter_by(camara_id=cc.id).all()]
            c["equipamentos"] = [_to_dict(e, ("id", "camara_id")) for e in db.query(EquipamentoCamaraCompleto).filter_by(camara_id=cc.id).all()]
            c["forcadores"] = []
            for f in db.query(ForcadorSelecaoCompleto).filter_by(camara_id=cc.id).order_by(ForcadorSelecaoCompleto.id).all():
                fd = _to_dict(f, ("id", "camara_id"))
                fd["_old_id"] = f.id
                fd["valvulas"] = [_to_dict(v, ("id", "forcador_selecao_id")) for v in db.query(ValvulaSelecaoCompleto).filter_by(forcador_selecao_id=f.id).all()]
                c["forcadores"].append(fd)
            s["camaras_completo"].append(c)

        for cs in db.query(CamaraSimples).filter_by(sistema_id=sistema.id).all():
            c = _to_dict(cs, ("id", "sistema_id"))
            c["_old_id"] = cs.id
            c["forcadores"] = []
            for f in db.query(ForcadorSelecaoSimples).filter_by(camara_id=cs.id).order_by(ForcadorSelecaoSimples.id).all():
                fd = _to_dict(f, ("id", "camara_id"))
                fd["_old_id"] = f.id
                fd["valvulas"] = [_to_dict(v, ("id", "forcador_selecao_id")) for v in db.query(ValvulaSelecaoSimples).filter_by(forcador_selecao_id=f.id).all()]
                c["forcadores"].append(fd)
            s["camaras_simples"].append(c)

        for ex in db.query(Expositor).filter_by(sistema_id=sistema.id).all():
            e = _to_dict(ex, ("id", "sistema_id"))
            e["_old_id"] = ex.id
            e["modulos"] = [_to_dict(m, ("id", "expositor_id")) for m in db.query(ModuloExpositor).filter_by(expositor_id=ex.id).all()]
            s["expositores"].append(e)

        for rack in db.query(RackParalelo).filter_by(sistema_id=sistema.id).order_by(RackParalelo.id).all():
            r = _to_dict(rack, ("id", "sistema_id"))
            r["_old_id"] = rack.id
            r["compressores"] = [_to_dict(c, ("id", "rack_id")) for c in db.query(CompressorRack).filter_by(rack_id=rack.id).order_by(CompressorRack.posicao).all()]
            r["materiais"] = [_to_dict(m, ("id", "rack_id")) for m in db.query(MaterialRack).filter_by(rack_id=rack.id).order_by(MaterialRack.ordem).all()]
            r["condensadores"] = [_to_dict(cond, ("id", "rack_id")) for cond in db.query(RackCondensadorSelecao).filter_by(rack_id=rack.id).order_by(RackCondensadorSelecao.id).all()]
            s["racks"].append(r)

        s["uc_selecao"] = [_to_dict(uc, ("id", "sistema_id")) for uc in db.query(UnidadeSelecaoSistema).filter_by(sistema_id=sistema.id).all()]
        data["sistemas"].append(s)

    data["paineis"] = [_to_dict(p, ("id", "projeto_id")) for p in db.query(PainelTermico).filter_by(projeto_id=projeto.id).all()]
    data["portas"] = [_to_dict(p, ("id", "projeto_id")) for p in db.query(PortaFrigorifica).filter_by(projeto_id=projeto.id).all()]
    data["composicao"] = [_to_dict(c, ("id", "projeto_id")) for c in db.query(ComposicaoPrecoItem).filter_by(projeto_id=projeto.id).all()]

    cond = db.query(CondicaoPagamentoProjeto).filter_by(projeto_id=projeto.id).first()
    if cond:
        cd = _to_dict(cond, ("id", "projeto_id"))
        cd["parcelas"] = [_to_dict(p, ("id", "projeto_id")) for p in db.query(CondicaoPagamentoParcela).filter_by(projeto_id=projeto.id).order_by(CondicaoPagamentoParcela.ordem).all()]
        data["condicao_pagamento"] = cd

    for cm in db.query(ComissaoVendedorProjeto).filter_by(projeto_id=projeto.id).all():
        cd2 = _to_dict(cm, ("id", "projeto_id"))
        vend = db.query(Vendedor).filter_by(id=cm.vendedor_id).first()
        cd2["_vendedor_nome"] = vend.nome if vend else None
        data["comissoes"].append(cd2)

    marg = db.query(MargemNegociacaoProjeto).filter_by(projeto_id=projeto.id).first()
    if marg:
        data["margem"] = _to_dict(marg, ("projeto_id",))

    return data


# ---- Importação de Projeto ----

def _importar_projeto(db: Session, data: dict) -> int:
    """Insere projeto serializado no banco local. Retorna novo projeto_id."""
    cloud_id = data["cloud_id"]

    # Projeto
    proj_data = _filtrar(Projeto, data["projeto"], ("id",))
    proj_data["cloud_id"] = cloud_id
    novo_proj = Projeto(**proj_data)
    db.add(novo_proj)
    db.flush()
    novo_pid = novo_proj.id

    id_cc: dict = {}  # old_cc_id -> new_cc_id
    id_cs: dict = {}  # old_cs_id -> new_cs_id

    for s_raw in data.get("sistemas", []):
        old_sid = s_raw.get("_old_id")
        s_data = _filtrar(SistemaRefrigeracao, s_raw, ("id", "projeto_id"))
        novo_sis = SistemaRefrigeracao(**s_data, projeto_id=novo_pid)
        db.add(novo_sis)
        db.flush()
        novo_sid = novo_sis.id

        for cc_raw in s_raw.get("camaras_completo", []):
            old_ccid = cc_raw.get("_old_id")
            cc_data = _filtrar(CamaraCompleto, cc_raw, ("id", "sistema_id"))
            nova_cc = CamaraCompleto(**cc_data, sistema_id=novo_sid)
            db.add(nova_cc)
            db.flush()
            novo_ccid = nova_cc.id
            if old_ccid is not None:
                id_cc[old_ccid] = novo_ccid

            for p in cc_raw.get("portas", []):
                db.add(PortaCamara(**_filtrar(PortaCamara, p, ("id", "camara_id")), camara_id=novo_ccid))

            for e in cc_raw.get("equipamentos", []):
                db.add(EquipamentoCamaraCompleto(**_filtrar(EquipamentoCamaraCompleto, e, ("id", "camara_id")), camara_id=novo_ccid))

            for f_raw in cc_raw.get("forcadores", []):
                old_fid = f_raw.get("_old_id")
                f_data = _filtrar(ForcadorSelecaoCompleto, f_raw, ("id", "camara_id"))
                novo_f = ForcadorSelecaoCompleto(**f_data, camara_id=novo_ccid)
                db.add(novo_f)
                db.flush()
                for v in f_raw.get("valvulas", []):
                    db.add(ValvulaSelecaoCompleto(**_filtrar(ValvulaSelecaoCompleto, v, ("id", "forcador_selecao_id")), forcador_selecao_id=novo_f.id))

        for cs_raw in s_raw.get("camaras_simples", []):
            old_csid = cs_raw.get("_old_id")
            cs_data = _filtrar(CamaraSimples, cs_raw, ("id", "sistema_id"))
            nova_cs = CamaraSimples(**cs_data, sistema_id=novo_sid)
            db.add(nova_cs)
            db.flush()
            novo_csid = nova_cs.id
            if old_csid is not None:
                id_cs[old_csid] = novo_csid

            for f_raw in cs_raw.get("forcadores", []):
                f_data = _filtrar(ForcadorSelecaoSimples, f_raw, ("id", "camara_id"))
                novo_f = ForcadorSelecaoSimples(**f_data, camara_id=novo_csid)
                db.add(novo_f)
                db.flush()
                for v in f_raw.get("valvulas", []):
                    db.add(ValvulaSelecaoSimples(**_filtrar(ValvulaSelecaoSimples, v, ("id", "forcador_selecao_id")), forcador_selecao_id=novo_f.id))

        for ex_raw in s_raw.get("expositores", []):
            old_eid = ex_raw.get("_old_id")
            e_data = _filtrar(Expositor, ex_raw, ("id", "sistema_id"))
            novo_ex = Expositor(**e_data, sistema_id=novo_sid)
            db.add(novo_ex)
            db.flush()
            for m in ex_raw.get("modulos", []):
                db.add(ModuloExpositor(**_filtrar(ModuloExpositor, m, ("id", "expositor_id")), expositor_id=novo_ex.id))

        for rack_raw in s_raw.get("racks", []):
            r_data = _filtrar(RackParalelo, rack_raw, ("id", "sistema_id"))
            novo_rack = RackParalelo(**r_data, sistema_id=novo_sid)
            db.add(novo_rack)
            db.flush()
            for c in rack_raw.get("compressores", []):
                db.add(CompressorRack(**_filtrar(CompressorRack, c, ("id", "rack_id")), rack_id=novo_rack.id))
            for m in rack_raw.get("materiais", []):
                db.add(MaterialRack(**_filtrar(MaterialRack, m, ("id", "rack_id")), rack_id=novo_rack.id))
            for cond in rack_raw.get("condensadores", []):
                db.add(RackCondensadorSelecao(**_filtrar(RackCondensadorSelecao, cond, ("id", "rack_id")), rack_id=novo_rack.id))

        for uc in s_raw.get("uc_selecao", []):
            db.add(UnidadeSelecaoSistema(**_filtrar(UnidadeSelecaoSistema, uc, ("id", "sistema_id")), sistema_id=novo_sid))

    for p in data.get("paineis", []):
        p2 = _filtrar(PainelTermico, p, ("id", "projeto_id"))
        old_cc = p.get("camara_completo_id")
        old_cs = p.get("camara_simples_id")
        p2["camara_completo_id"] = id_cc.get(old_cc) if old_cc else None
        p2["camara_simples_id"] = id_cs.get(old_cs) if old_cs else None
        db.add(PainelTermico(**p2, projeto_id=novo_pid))

    for p in data.get("portas", []):
        p2 = _filtrar(PortaFrigorifica, p, ("id", "projeto_id"))
        old_cc = p.get("camara_completo_id")
        old_cs = p.get("camara_simples_id")
        p2["camara_completo_id"] = id_cc.get(old_cc) if old_cc else None
        p2["camara_simples_id"] = id_cs.get(old_cs) if old_cs else None
        db.add(PortaFrigorifica(**p2, projeto_id=novo_pid))

    for c in data.get("composicao", []):
        db.add(ComposicaoPrecoItem(**_filtrar(ComposicaoPrecoItem, c, ("id", "projeto_id")), projeto_id=novo_pid))

    cond_pag = data.get("condicao_pagamento")
    if cond_pag:
        parcelas = cond_pag.get("parcelas", [])
        cp_data = _filtrar(CondicaoPagamentoProjeto, cond_pag, ("id", "projeto_id"))
        db.add(CondicaoPagamentoProjeto(**cp_data, projeto_id=novo_pid))
        for par in parcelas:
            db.add(CondicaoPagamentoParcela(**_filtrar(CondicaoPagamentoParcela, par, ("id", "projeto_id")), projeto_id=novo_pid))

    for cm in data.get("comissoes", []):
        vend_nome = cm.get("_vendedor_nome")
        if vend_nome:
            vend = db.query(Vendedor).filter_by(nome=vend_nome).first()
            if vend:
                cm2 = _filtrar(ComissaoVendedorProjeto, cm, ("id", "projeto_id"))
                cm2["vendedor_id"] = vend.id
                db.add(ComissaoVendedorProjeto(**cm2, projeto_id=novo_pid))

    marg = data.get("margem")
    if marg:
        db.add(MargemNegociacaoProjeto(**_filtrar(MargemNegociacaoProjeto, marg, ("projeto_id",)), projeto_id=novo_pid))

    db.flush()
    return novo_pid


# ---- Endpoints de Sincronização ----

@router.post("/push-todos")
def push_todos(req: SyncRequest):
    """Faz upload de todos os projetos locais para o Supabase Storage."""
    enviados = 0
    erros = 0
    with Session(engine) as db:
        projetos = db.query(Projeto).all()
        for projeto in projetos:
            if not projeto.cloud_id:
                projeto.cloud_id = str(uuid.uuid4())
                db.flush()
            try:
                payload = _serializar_projeto(db, projeto)
                raw = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
                path = f"{req.user_id}/{projeto.cloud_id}.json"
                if _storage_upload(req.token, path, raw):
                    enviados += 1
                else:
                    erros += 1
            except Exception:
                erros += 1
        db.commit()
    return {"ok": True, "enviados": enviados, "erros": erros}


@router.post("/pull-novos")
def pull_novos(req: SyncRequest):
    """Baixa da nuvem projetos que ainda não existem localmente (por cloud_id)."""
    importados = 0
    erros = 0

    with Session(engine) as db:
        # Cloud IDs já existentes localmente
        cloud_ids_locais: set = {
            row[0] for row in db.query(Projeto.cloud_id).filter(Projeto.cloud_id.isnot(None)).all()
        }

        # Listar arquivos na nuvem (excluindo o lock)
        arquivos = _storage_list(req.token, f"{req.user_id}/")
        for arq in arquivos:
            nome: str = arq.get("name", "")
            if not nome.endswith(".json") or nome == ".session_lock":
                continue
            cloud_id = nome.replace(".json", "").split("/")[-1]
            if cloud_id in cloud_ids_locais:
                continue  # já existe localmente

            path = f"{req.user_id}/{cloud_id}.json"
            raw = _storage_download(req.token, path)
            if raw is None:
                erros += 1
                continue
            try:
                data = json.loads(raw)
                _importar_projeto(db, data)
                importados += 1
            except Exception:
                erros += 1
                db.rollback()
                continue
        db.commit()

    return {"ok": True, "importados": importados, "erros": erros}
