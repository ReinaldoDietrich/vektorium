"""Router de administração — roda SOMENTE no Fly.io (main_calc.py).
Endpoints protegidos por JWT + verificação de papel=master no Postgres.
Usa SQL direto (text()) porque as tabelas de gestão (usuarios, assinaturas, dispositivos,
permissoes_por_papel, logs_admin) existem apenas no Postgres, não no SQLite local.
CRUD de usuários via Supabase Auth Admin API (service_role key)."""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth_supabase import exigir_usuario, exigir_jwt, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _uid(payload: dict) -> str:
    return payload.get("sub", "")


def _exigir_master(payload: dict = Depends(exigir_usuario), db: Session = Depends(get_db)) -> dict:
    uid = _uid(payload)
    row = db.execute(text(
        "SELECT p.is_admin FROM usuarios u "
        "JOIN papeis p ON p.nome = u.papel "
        "WHERE u.id = :uid"
    ), {"uid": uid}).fetchone()
    if not row or not row[0]:
        raise HTTPException(403, "Acesso restrito a administradores")
    return payload


def _log_admin(db: Session, master_uid: str, acao: str, detalhes: str = ""):
    try:
        db.execute(text(
            "INSERT INTO logs_admin (usuario_id, acao, detalhes) VALUES (:uid, :acao, :det)"
        ), {"uid": master_uid, "acao": acao, "det": detalhes})
        db.commit()
    except Exception:
        pass


def _admin_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# LICENÇA — qualquer usuário autenticado consulta o status da própria assinatura
# ---------------------------------------------------------------------------

@router.get("/licenca/status")
def licenca_status(payload: dict = Depends(exigir_jwt), db: Session = Depends(get_db)):
    uid = _uid(payload)
    row = db.execute(text(
        "SELECT status, plano, vence_em FROM assinaturas WHERE usuario_id = :uid LIMIT 1"
    ), {"uid": uid}).fetchone()
    if not row:
        return {"ativa": False, "plano": None, "vence_em": None, "motivo": "sem_assinatura"}
    ativa = row[0] in ("active",)
    return {"ativa": ativa, "plano": row[1],
            "vence_em": str(row[2]) if row[2] else None,
            "motivo": None if ativa else row[0]}


# ---------------------------------------------------------------------------
# MEU PERFIL — qualquer usuário autenticado
# ---------------------------------------------------------------------------

@router.get("/meu-perfil")
def meu_perfil(payload: dict = Depends(exigir_usuario), db: Session = Depends(get_db)):
    uid = _uid(payload)
    u = db.execute(text(
        "SELECT id, email, nome, papel, criado_em FROM usuarios WHERE id = :uid"
    ), {"uid": uid}).fetchone()
    if not u:
        raise HTTPException(404, "Usuário não encontrado na tabela de gestão")
    a = db.execute(text(
        "SELECT id, status, plano, iugu_subscription_id, vence_em, criado_em, atualizado_em "
        "FROM assinaturas WHERE usuario_id = :uid ORDER BY id DESC LIMIT 1"
    ), {"uid": uid}).fetchone()
    return {
        "usuario": {"id": str(u[0]), "email": u[1], "nome": u[2], "papel": u[3],
                     "criado_em": str(u[4]) if u[4] else None},
        "assinatura": {
            "id": a[0], "status": a[1], "plano": a[2], "iugu_subscription_id": a[3],
            "vence_em": str(a[4]) if a[4] else None,
            "criado_em": str(a[5]) if a[5] else None,
            "atualizado_em": str(a[6]) if a[6] else None,
        } if a else None,
    }


# ---------------------------------------------------------------------------
# PERMISSÕES DO USUÁRIO LOGADO — usado pelo frontend para filtrar telas
# ---------------------------------------------------------------------------

@router.get("/minhas-permissoes")
def minhas_permissoes(payload: dict = Depends(exigir_jwt), db: Session = Depends(get_db)):
    uid = _uid(payload)
    u = db.execute(text("SELECT papel FROM usuarios WHERE id = :uid"), {"uid": uid}).fetchone()
    if not u:
        return {"permissoes": [], "is_admin": False}
    papel = u[0]
    is_admin_row = db.execute(text(
        "SELECT is_admin FROM papeis WHERE nome = :nome"
    ), {"nome": papel}).fetchone()
    is_admin = bool(is_admin_row and is_admin_row[0])
    rows = db.execute(text(
        "SELECT modulo, ver, editar FROM permissoes_por_papel WHERE papel = :papel"
    ), {"papel": papel}).fetchall()
    return {
        "papel": papel,
        "is_admin": is_admin,
        "permissoes": [{"modulo": r[0], "ver": r[1], "editar": r[2]} for r in rows],
    }


# ---------------------------------------------------------------------------
# USUÁRIOS — master only (CRUD via Supabase Admin API)
# ---------------------------------------------------------------------------

@router.get("/usuarios")
def listar_usuarios(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT u.id, u.email, u.nome, u.papel, u.criado_em, "
        "a.status, a.plano, a.vence_em "
        "FROM usuarios u LEFT JOIN assinaturas a ON a.usuario_id = u.id "
        "ORDER BY u.criado_em DESC"
    )).fetchall()
    return [{"id": str(r[0]), "email": r[1], "nome": r[2], "papel": r[3],
             "criado_em": str(r[4]) if r[4] else None,
             "assinatura_status": r[5], "assinatura_plano": r[6],
             "assinatura_vence_em": str(r[7]) if r[7] else None} for r in rows]


@router.post("/usuarios")
def criar_usuario(payload_body: dict = Body(...),
                  payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    email = payload_body.get("email", "").strip().lower()
    senha = payload_body.get("senha", "").strip()
    nome = payload_body.get("nome", "").strip()
    papel = payload_body.get("papel", "usuario").strip()
    if not email or not senha:
        raise HTTPException(400, "Email e senha são obrigatórios")
    if len(senha) < 6:
        raise HTTPException(400, "Senha deve ter no mínimo 6 caracteres")
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(500, "SUPABASE_SERVICE_ROLE_KEY não configurada no servidor")
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        json={"email": email, "password": senha, "email_confirm": True},
        headers=_admin_headers(),
        timeout=15,
    )
    if r.status_code not in (200, 201):
        detail = r.json().get("msg", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise HTTPException(r.status_code, f"Erro Supabase Auth: {detail}")
    auth_user = r.json()
    uid = auth_user.get("id")
    db.execute(text(
        "INSERT INTO usuarios (id, email, nome, papel) VALUES (:id, :email, :nome, :papel) "
        "ON CONFLICT (id) DO UPDATE SET email=EXCLUDED.email, nome=EXCLUDED.nome, papel=EXCLUDED.papel"
    ), {"id": uid, "email": email, "nome": nome, "papel": papel})
    db.execute(text(
        "INSERT INTO assinaturas (usuario_id, status, plano) VALUES (:uid, 'active', 'vitalicio') "
        "ON CONFLICT (usuario_id) DO NOTHING"
    ), {"uid": uid})
    db.commit()
    _log_admin(db, _uid(payload), "criar_usuario", f"{email} (papel={papel})")
    return {"ok": True, "id": uid, "email": email}


@router.put("/usuarios/{uid}")
def editar_usuario(uid: str, payload_body: dict = Body(...),
                   payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    nome = payload_body.get("nome")
    papel = payload_body.get("papel")
    updates = []
    params = {"uid": uid}
    if nome is not None:
        updates.append("nome = :nome")
        params["nome"] = nome.strip()
    if papel is not None:
        papel = papel.strip()
        existe = db.execute(text("SELECT 1 FROM papeis WHERE nome = :nome"), {"nome": papel}).fetchone()
        if not existe:
            raise HTTPException(400, f"Tipo '{papel}' não existe")
        updates.append("papel = :papel")
        params["papel"] = papel
    if not updates:
        raise HTTPException(400, "Nenhum campo para atualizar")
    result = db.execute(text(f"UPDATE usuarios SET {', '.join(updates)} WHERE id = :uid"), params)
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Usuário não encontrado")
    _log_admin(db, _uid(payload), "editar_usuario", f"uid={uid} {', '.join(updates)}")
    return {"ok": True, "uid": uid}


@router.delete("/usuarios/{uid}")
def excluir_usuario(uid: str, payload: dict = Depends(_exigir_master),
                    db: Session = Depends(get_db)):
    master_uid = _uid(payload)
    if uid == master_uid:
        raise HTTPException(400, "Não é possível excluir a si mesmo")
    u = db.execute(text("SELECT email FROM usuarios WHERE id = :uid"), {"uid": uid}).fetchone()
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    email = u[0]
    if SUPABASE_SERVICE_ROLE_KEY:
        r = httpx.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{uid}",
            headers=_admin_headers(),
            timeout=15,
        )
        if r.status_code not in (200, 204):
            raise HTTPException(r.status_code, f"Erro ao excluir do Auth: {r.text}")
    db.execute(text("DELETE FROM assinaturas WHERE usuario_id = :uid"), {"uid": uid})
    db.execute(text("DELETE FROM dispositivos WHERE usuario_id = :uid"), {"uid": uid})
    db.execute(text("DELETE FROM usuarios WHERE id = :uid"), {"uid": uid})
    db.commit()
    _log_admin(db, master_uid, "excluir_usuario", email)
    return {"ok": True, "excluido": email}


@router.put("/usuarios/{uid}/papel")
def alterar_papel(uid: str, payload_body: dict = Body(...),
                  payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    novo_papel = payload_body.get("papel", "").strip()
    existe = db.execute(text("SELECT 1 FROM papeis WHERE nome = :nome"), {"nome": novo_papel}).fetchone()
    if not existe:
        raise HTTPException(400, f"Tipo '{novo_papel}' não existe")
    result = db.execute(text("UPDATE usuarios SET papel = :papel WHERE id = :uid"),
                        {"papel": novo_papel, "uid": uid})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Usuário não encontrado")
    _log_admin(db, _uid(payload), "alterar_papel", f"uid={uid} -> {novo_papel}")
    return {"ok": True, "uid": uid, "papel": novo_papel}


# ---------------------------------------------------------------------------
# ASSINATURAS — master only
# ---------------------------------------------------------------------------

@router.get("/assinaturas")
def listar_assinaturas(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT a.id, a.usuario_id, u.email, u.nome, a.status, a.plano, "
        "a.iugu_subscription_id, a.vence_em, a.criado_em, a.atualizado_em "
        "FROM assinaturas a JOIN usuarios u ON u.id = a.usuario_id "
        "ORDER BY a.atualizado_em DESC"
    )).fetchall()
    return [{"id": r[0], "usuario_id": str(r[1]), "email": r[2], "nome": r[3],
             "status": r[4], "plano": r[5], "iugu_subscription_id": r[6],
             "vence_em": str(r[7]) if r[7] else None,
             "criado_em": str(r[8]) if r[8] else None,
             "atualizado_em": str(r[9]) if r[9] else None} for r in rows]


@router.post("/assinaturas/{uid}/conceder-vitalicia")
def conceder_vitalicia(uid: str, payload: dict = Depends(_exigir_master),
                       db: Session = Depends(get_db)):
    check = db.execute(text("SELECT id FROM usuarios WHERE id = :uid"), {"uid": uid}).fetchone()
    if not check:
        raise HTTPException(404, "Usuário não encontrado")
    existing = db.execute(text(
        "SELECT id FROM assinaturas WHERE usuario_id = :uid"), {"uid": uid}).fetchone()
    if existing:
        db.execute(text(
            "UPDATE assinaturas SET status='active', plano='vitalicio', vence_em=NULL, "
            "atualizado_em=NOW() WHERE usuario_id = :uid"), {"uid": uid})
    else:
        db.execute(text(
            "INSERT INTO assinaturas (usuario_id, status, plano, vence_em) "
            "VALUES (:uid, 'active', 'vitalicio', NULL)"), {"uid": uid})
    db.commit()
    _log_admin(db, _uid(payload), "conceder_vitalicia", f"uid={uid}")
    return {"ok": True, "uid": uid, "plano": "vitalicio"}


@router.post("/assinaturas/{uid}/revogar")
def revogar_assinatura(uid: str, payload: dict = Depends(_exigir_master),
                       db: Session = Depends(get_db)):
    result = db.execute(text(
        "UPDATE assinaturas SET status='canceled', atualizado_em=NOW() "
        "WHERE usuario_id = :uid"), {"uid": uid})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Assinatura não encontrada")
    _log_admin(db, _uid(payload), "revogar_assinatura", f"uid={uid}")
    return {"ok": True, "uid": uid, "status": "canceled"}


# ---------------------------------------------------------------------------
# DISPOSITIVOS — master only
# ---------------------------------------------------------------------------

@router.get("/dispositivos")
def listar_dispositivos(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT d.id, d.usuario_id, u.email, d.fingerprint, d.ultimo_acesso, d.ativo "
        "FROM dispositivos d JOIN usuarios u ON u.id = d.usuario_id "
        "ORDER BY d.ultimo_acesso DESC"
    )).fetchall()
    return [{"id": r[0], "usuario_id": str(r[1]), "email": r[2], "fingerprint": r[3],
             "ultimo_acesso": str(r[4]) if r[4] else None, "ativo": r[5]} for r in rows]


@router.put("/dispositivos/{did}/ativar")
def ativar_dispositivo(did: int, payload: dict = Depends(_exigir_master),
                       db: Session = Depends(get_db)):
    result = db.execute(text("UPDATE dispositivos SET ativo=TRUE WHERE id = :did"), {"did": did})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Dispositivo não encontrado")
    _log_admin(db, _uid(payload), "ativar_dispositivo", f"id={did}")
    return {"ok": True, "id": did, "ativo": True}


@router.put("/dispositivos/{did}/desativar")
def desativar_dispositivo(did: int, payload: dict = Depends(_exigir_master),
                          db: Session = Depends(get_db)):
    result = db.execute(text("UPDATE dispositivos SET ativo=FALSE WHERE id = :did"), {"did": did})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Dispositivo não encontrado")
    _log_admin(db, _uid(payload), "desativar_dispositivo", f"id={did}")
    return {"ok": True, "id": did, "ativo": False}


# ---------------------------------------------------------------------------
# PERMISSÕES — master only
# ---------------------------------------------------------------------------

@router.get("/permissoes")
def listar_permissoes(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT papel, modulo, ver, editar FROM permissoes_por_papel ORDER BY papel, modulo"
    )).fetchall()
    return [{"papel": r[0], "modulo": r[1], "ver": r[2], "editar": r[3]} for r in rows]


@router.put("/permissoes")
def atualizar_permissoes(payload_body: dict = Body(...),
                         payload: dict = Depends(_exigir_master),
                         db: Session = Depends(get_db)):
    itens = payload_body.get("permissoes", [])
    for item in itens:
        papel = item.get("papel", "").strip()
        modulo = item.get("modulo", "").strip()
        if not papel or not modulo:
            continue
        db.execute(text(
            "INSERT INTO permissoes_por_papel (papel, modulo, ver, editar) "
            "VALUES (:papel, :modulo, :ver, :editar) "
            "ON CONFLICT (papel, modulo) DO UPDATE SET ver=EXCLUDED.ver, editar=EXCLUDED.editar"
        ), {"papel": papel, "modulo": modulo,
            "ver": bool(item.get("ver", False)), "editar": bool(item.get("editar", False))})
    db.commit()
    _log_admin(db, _uid(payload), "atualizar_permissoes", f"{len(itens)} regras")
    return listar_permissoes(payload=payload, db=db)


# ---------------------------------------------------------------------------
# PAPÉIS — CRUD de tipos de usuário (master only)
# ---------------------------------------------------------------------------

@router.get("/papeis")
def listar_papeis(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT id, nome, descricao, is_admin, criado_em FROM papeis ORDER BY id"
    )).fetchall()
    return [{"id": r[0], "nome": r[1], "descricao": r[2] or "",
             "is_admin": r[3], "criado_em": str(r[4]) if r[4] else None} for r in rows]


@router.post("/papeis")
def criar_papel(payload_body: dict = Body(...),
                payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    nome = payload_body.get("nome", "").strip().lower()
    descricao = payload_body.get("descricao", "").strip()
    is_admin = bool(payload_body.get("is_admin", False))
    if not nome:
        raise HTTPException(400, "Nome do tipo é obrigatório")
    existe = db.execute(text("SELECT 1 FROM papeis WHERE nome = :nome"), {"nome": nome}).fetchone()
    if existe:
        raise HTTPException(409, f"Tipo '{nome}' já existe")
    db.execute(text(
        "INSERT INTO papeis (nome, descricao, is_admin) VALUES (:nome, :descricao, :is_admin)"
    ), {"nome": nome, "descricao": descricao, "is_admin": is_admin})
    db.commit()
    row = db.execute(text("SELECT id, nome, descricao, is_admin, criado_em FROM papeis WHERE nome = :nome"),
                     {"nome": nome}).fetchone()
    _log_admin(db, _uid(payload), "criar_papel", nome)
    return {"id": row[0], "nome": row[1], "descricao": row[2] or "",
            "is_admin": row[3], "criado_em": str(row[4]) if row[4] else None}


@router.put("/papeis/{papel_id}")
def editar_papel(papel_id: int, payload_body: dict = Body(...),
                 payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    nome = payload_body.get("nome", "").strip().lower()
    descricao = payload_body.get("descricao", "").strip()
    is_admin = bool(payload_body.get("is_admin", False))
    if not nome:
        raise HTTPException(400, "Nome do tipo é obrigatório")
    atual = db.execute(text("SELECT nome FROM papeis WHERE id = :id"), {"id": papel_id}).fetchone()
    if not atual:
        raise HTTPException(404, "Tipo não encontrado")
    conflito = db.execute(text("SELECT 1 FROM papeis WHERE nome = :nome AND id != :id"),
                          {"nome": nome, "id": papel_id}).fetchone()
    if conflito:
        raise HTTPException(409, f"Tipo '{nome}' já existe")
    nome_antigo = atual[0]
    db.execute(text(
        "UPDATE papeis SET nome = :nome, descricao = :descricao, is_admin = :is_admin WHERE id = :id"
    ), {"nome": nome, "descricao": descricao, "is_admin": is_admin, "id": papel_id})
    if nome != nome_antigo:
        db.execute(text("UPDATE usuarios SET papel = :novo WHERE papel = :antigo"),
                   {"novo": nome, "antigo": nome_antigo})
        db.execute(text("UPDATE permissoes_por_papel SET papel = :novo WHERE papel = :antigo"),
                   {"novo": nome, "antigo": nome_antigo})
    db.commit()
    _log_admin(db, _uid(payload), "editar_papel", f"{nome_antigo} -> {nome}")
    return {"ok": True, "id": papel_id, "nome": nome}


@router.delete("/papeis/{papel_id}")
def excluir_papel(papel_id: int, payload: dict = Depends(_exigir_master),
                  db: Session = Depends(get_db)):
    row = db.execute(text("SELECT nome FROM papeis WHERE id = :id"), {"id": papel_id}).fetchone()
    if not row:
        raise HTTPException(404, "Tipo não encontrado")
    nome = row[0]
    if nome == "master":
        raise HTTPException(400, "O tipo 'master' não pode ser excluído")
    em_uso = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE papel = :nome"), {"nome": nome}).fetchone()
    if em_uso and em_uso[0] > 0:
        raise HTTPException(409, f"Tipo '{nome}' possui {em_uso[0]} usuário(s) atribuído(s). Reatribua-os primeiro.")
    db.execute(text("DELETE FROM permissoes_por_papel WHERE papel = :nome"), {"nome": nome})
    db.execute(text("DELETE FROM papeis WHERE id = :id"), {"id": papel_id})
    db.commit()
    _log_admin(db, _uid(payload), "excluir_papel", nome)
    return {"ok": True, "excluido": nome}


# ---------------------------------------------------------------------------
# LOGS — master only
# ---------------------------------------------------------------------------

@router.get("/logs")
def listar_logs(payload: dict = Depends(_exigir_master), db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT l.id, l.usuario_id, u.email, l.acao, l.detalhes, l.criado_em "
        "FROM logs_admin l LEFT JOIN usuarios u ON u.id = l.usuario_id "
        "ORDER BY l.criado_em DESC LIMIT 200"
    )).fetchall()
    return [{"id": r[0], "usuario_id": str(r[1]) if r[1] else None,
             "email": r[2] or "—", "acao": r[3], "detalhes": r[4] or "",
             "criado_em": str(r[5]) if r[5] else None} for r in rows]


# ---------------------------------------------------------------------------
# WEBHOOK IUGU — placeholder (F1.6)
# ---------------------------------------------------------------------------

@router.post("/iugu/webhook")
def iugu_webhook(payload_body: dict = Body(...), db: Session = Depends(get_db)):
    evento = payload_body.get("event", "")
    iugu_sub_id = payload_body.get("data", {}).get("id", "")
    if not iugu_sub_id:
        return {"ok": False, "motivo": "sem subscription id"}
    row = db.execute(text(
        "SELECT a.id, a.usuario_id FROM assinaturas a "
        "WHERE a.iugu_subscription_id = :iugu_id"
    ), {"iugu_id": iugu_sub_id}).fetchone()
    if not row:
        return {"ok": False, "motivo": "assinatura não encontrada para iugu_id=" + iugu_sub_id}

    if evento in ("subscription.activated", "subscription.renewed"):
        db.execute(text(
            "UPDATE assinaturas SET status='active', atualizado_em=NOW() WHERE id = :aid"
        ), {"aid": row[0]})
    elif evento in ("subscription.suspended", "subscription.expired"):
        db.execute(text(
            "UPDATE assinaturas SET status='past_due', atualizado_em=NOW() WHERE id = :aid"
        ), {"aid": row[0]})
    elif evento == "subscription.canceled":
        db.execute(text(
            "UPDATE assinaturas SET status='canceled', atualizado_em=NOW() WHERE id = :aid"
        ), {"aid": row[0]})
    db.commit()
    return {"ok": True, "evento": evento, "assinatura_id": row[0]}
