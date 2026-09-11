# -*- coding: utf-8 -*-
"""Sincronização de catálogos: exporta dados do banco local e recebe/upsert no banco remoto
(Fly.io → Supabase). Mesmo router roda nos dois lados; o frontend orquestra: lê o export
do local, envia pro receber do Fly.io."""
import logging, os, base64, json, mimetypes
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from fastapi import APIRouter, Body, Depends
from fastapi.requests import Request as FastAPIRequest
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models as m
from ..utils import model_to_dict

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/catalogo-sync", tags=["catalogo-sync"])


def _d(obj, exclude=None):
    if obj is None:
        return None
    return model_to_dict(obj, exclude=exclude)


def _ld(objs, exclude=None):
    return [_d(o, exclude) for o in objs]


# ── EXPORTAR ──────────────────────────────────────────────────────────────────

def _exportar_forcadores(db: Session):
    fabricantes = _ld(db.query(m.Fabricante).all())
    linhas = []
    for ln in db.query(m.LinhaForcador).all():
        d = _d(ln)
        d["fabricante_nome"] = ln.fabricante.nome if ln.fabricante else None
        modelos = []
        for mod in ln.modelos:
            dm = _d(mod)
            dm["capacidades"] = _ld(mod.capacidades, exclude={"id"})
            dm["eletricas"] = _ld(mod.eletricas, exclude={"id"})
            dm["fisicos"] = _d(mod.fisicos, exclude={"id"})
            dm["dimensionais"] = _d(mod.dimensionais, exclude={"id"})
            modelos.append(dm)
        d["modelos"] = modelos
        fatores = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=ln.id).all()
        d["fatores_gas"] = _ld(fatores, exclude={"id"})
        campos = db.query(m.CampoCatalogo).filter_by(tipo_catalogo="Forcador", catalogo_id=ln.id).order_by(m.CampoCatalogo.ordem).all()
        d["campos"] = []
        for c in campos:
            dc = _d(c, exclude={"id"})
            dc["opcoes"] = _ld(c.opcoes, exclude={"id"})
            d["campos"].append(dc)
        linhas.append(d)
    return {"tipo": "forcadores", "fabricantes": fabricantes, "linhas": linhas}


def _exportar_uc(db: Session):
    catalogos = []
    for cat in db.query(m.CatalogoUC).all():
        d = _d(cat)
        unidades = []
        for u in cat.unidades:
            du = _d(u)
            du["capacidades"] = _ld(u.capacidades, exclude={"id"})
            du["eletricas"] = _ld(u.eletricas, exclude={"id"})
            unidades.append(du)
        d["unidades"] = unidades
        campos = db.query(m.CampoCatalogo).filter_by(tipo_catalogo="UC", catalogo_id=cat.id).order_by(m.CampoCatalogo.ordem).all()
        d["campos"] = []
        for c in campos:
            dc = _d(c, exclude={"id"})
            dc["opcoes"] = _ld(c.opcoes, exclude={"id"})
            d["campos"].append(dc)
        catalogos.append(d)
    return {"tipo": "uc", "catalogos": catalogos}


def _exportar_condensadores(db: Session):
    fabricantes = _ld(db.query(m.Fabricante).all())
    linhas = []
    for ln in db.query(m.LinhaCondensadorRemoto).all():
        d = _d(ln)
        d["fabricante_nome"] = ln.fabricante.nome if ln.fabricante else None
        d["modelos"] = _ld(ln.modelos, exclude={"id"})
        d["fatores"] = _ld(ln.fatores, exclude={"id"})
        campos = db.query(m.CampoCatalogo).filter_by(tipo_catalogo="CondensadorRemoto", catalogo_id=ln.id).order_by(m.CampoCatalogo.ordem).all()
        d["campos"] = []
        for c in campos:
            dc = _d(c, exclude={"id"})
            dc["opcoes"] = _ld(c.opcoes, exclude={"id"})
            d["campos"].append(dc)
        linhas.append(d)
    return {"tipo": "condensadores", "fabricantes": fabricantes, "linhas": linhas}


def _exportar_comercial(db: Session):
    return {"tipo": "comercial", "itens": _ld(db.query(m.CatalogoComercial).all())}


_EXPORTADORES = {
    "forcadores": _exportar_forcadores,
    "uc": _exportar_uc,
    "condensadores": _exportar_condensadores,
    "comercial": _exportar_comercial,
}


@router.get("/exportar")
def exportar(tipo: str, db: Session = Depends(get_db)):
    fn = _EXPORTADORES.get(tipo)
    if not fn:
        return {"erro": f"Tipo desconhecido: {tipo}"}
    return fn(db)


# ── RECEBER (upsert) ─────────────────────────────────────────────────────────

def _garantir_fabricante(db: Session, nome: str) -> int:
    fab = db.query(m.Fabricante).filter_by(nome=nome).first()
    if fab:
        return fab.id
    fab = m.Fabricante(nome=nome)
    db.add(fab)
    db.flush()
    return fab.id


def _upsert_campos(db: Session, tipo_catalogo: str, catalogo_id: int, campos_payload: list):
    existentes = {c.nome_campo: c for c in
                  db.query(m.CampoCatalogo).filter_by(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id).all()}
    for cp in campos_payload:
        nome = cp["nome_campo"]
        opcoes_payload = cp.pop("opcoes", [])
        cp.pop("tipo_catalogo", None)
        cp.pop("catalogo_id", None)
        if nome in existentes:
            campo = existentes.pop(nome)
            for k, v in cp.items():
                if hasattr(campo, k) and k not in ("id",):
                    setattr(campo, k, v)
        else:
            campo = m.CampoCatalogo(tipo_catalogo=tipo_catalogo, catalogo_id=catalogo_id, **{k: v for k, v in cp.items() if hasattr(m.CampoCatalogo, k) and k not in ("id",)})
            db.add(campo)
            db.flush()
        opc_exist = {o.valor: o for o in campo.opcoes}
        for op in opcoes_payload:
            valor = op.get("valor")
            if valor in opc_exist:
                opc = opc_exist.pop(valor)
                opc.codigo = op.get("codigo", opc.codigo)
                opc.ordem = op.get("ordem", opc.ordem)
            else:
                db.add(m.CampoCatalogoOpcao(campo_id=campo.id, valor=valor, codigo=op.get("codigo", ""), ordem=op.get("ordem", 0)))


def _receber_forcadores(db: Session, payload: dict):
    for fp in payload.get("fabricantes", []):
        _garantir_fabricante(db, fp["nome"])
    criados, atualizados = 0, 0
    for lp in payload.get("linhas", []):
        fab_nome = lp.pop("fabricante_nome", None)
        modelos_p = lp.pop("modelos", [])
        fatores_p = lp.pop("fatores_gas", [])
        campos_p = lp.pop("campos", [])
        fab_id = _garantir_fabricante(db, fab_nome) if fab_nome else lp.get("fabricante_id")
        ln = db.query(m.LinhaForcador).filter_by(fabricante_id=fab_id, nome=lp["nome"],
                                                   versao_catalogo=lp.get("versao_catalogo")).first()
        if ln:
            for k, v in lp.items():
                if hasattr(ln, k) and k not in ("id", "fabricante_id"):
                    setattr(ln, k, v)
            atualizados += 1
        else:
            ln = m.LinhaForcador(fabricante_id=fab_id, **{k: v for k, v in lp.items() if hasattr(m.LinhaForcador, k) and k not in ("id", "fabricante_id")})
            db.add(ln)
            db.flush()
            criados += 1
        for mp in modelos_p:
            caps_p = mp.pop("capacidades", [])
            elet_p = mp.pop("eletricas", [])
            fis_p = mp.pop("fisicos", None)
            dim_p = mp.pop("dimensionais", None)
            mod = db.query(m.ModeloForcador).filter_by(linha_id=ln.id, modelo=mp["modelo"]).first()
            if mod:
                for k, v in mp.items():
                    if hasattr(mod, k) and k not in ("id", "linha_id"):
                        setattr(mod, k, v)
            else:
                mod = m.ModeloForcador(linha_id=ln.id, **{k: v for k, v in mp.items() if hasattr(m.ModeloForcador, k) and k not in ("id", "linha_id")})
                db.add(mod)
                db.flush()
            db.query(m.CapacidadeForcador).filter_by(modelo_id=mod.id).delete()
            for cp in caps_p:
                db.add(m.CapacidadeForcador(modelo_id=mod.id, temp_evaporacao_c=cp["temp_evaporacao_c"], capacidade_kcal_h=cp["capacidade_kcal_h"]))
            db.query(m.DadosEletricosForcador).filter_by(modelo_id=mod.id).delete()
            for ep in elet_p:
                db.add(m.DadosEletricosForcador(modelo_id=mod.id, **{k: v for k, v in ep.items() if hasattr(m.DadosEletricosForcador, k) and k not in ("id", "modelo_id")}))
            if fis_p:
                existing = db.query(m.DadosFisicosForcador).filter_by(modelo_id=mod.id).first()
                if existing:
                    for k, v in fis_p.items():
                        if hasattr(existing, k) and k not in ("id", "modelo_id"):
                            setattr(existing, k, v)
                else:
                    db.add(m.DadosFisicosForcador(modelo_id=mod.id, **{k: v for k, v in fis_p.items() if hasattr(m.DadosFisicosForcador, k) and k not in ("id", "modelo_id")}))
            if dim_p:
                existing = db.query(m.DadosDimensionaisForcador).filter_by(modelo_id=mod.id).first()
                if existing:
                    for k, v in dim_p.items():
                        if hasattr(existing, k) and k not in ("id", "modelo_id"):
                            setattr(existing, k, v)
                else:
                    db.add(m.DadosDimensionaisForcador(modelo_id=mod.id, **{k: v for k, v in dim_p.items() if hasattr(m.DadosDimensionaisForcador, k) and k not in ("id", "modelo_id")}))
        for fp in fatores_p:
            existing = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=ln.id, gas=fp["gas"]).first()
            if existing:
                existing.fator = fp.get("fator")
            else:
                db.add(m.FatorCorrecaoGasForcador(linha_id=ln.id, gas=fp["gas"], fator=fp.get("fator")))
        _upsert_campos(db, "Forcador", ln.id, campos_p)
    db.commit()
    return {"criados": criados, "atualizados": atualizados}


def _receber_uc(db: Session, payload: dict):
    criados, atualizados = 0, 0
    for cp in payload.get("catalogos", []):
        unidades_p = cp.pop("unidades", [])
        campos_p = cp.pop("campos", [])
        cat = db.query(m.CatalogoUC).filter_by(fabricante_uc=cp["fabricante_uc"], nome=cp["nome"],
                                                 versao_catalogo=cp.get("versao_catalogo")).first()
        if cat:
            for k, v in cp.items():
                if hasattr(cat, k) and k not in ("id",):
                    setattr(cat, k, v)
            atualizados += 1
        else:
            cat = m.CatalogoUC(**{k: v for k, v in cp.items() if hasattr(m.CatalogoUC, k) and k not in ("id",)})
            db.add(cat)
            db.flush()
            criados += 1
        for up in unidades_p:
            caps_p = up.pop("capacidades", [])
            elet_p = up.pop("eletricas", [])
            u = db.query(m.UnidadeCondensadora).filter_by(catalogo_id=cat.id, modelo=up["modelo"],
                                                            gas=up.get("gas")).first()
            if u:
                for k, v in up.items():
                    if hasattr(u, k) and k not in ("id", "catalogo_id"):
                        setattr(u, k, v)
            else:
                u = m.UnidadeCondensadora(catalogo_id=cat.id, **{k: v for k, v in up.items() if hasattr(m.UnidadeCondensadora, k) and k not in ("id", "catalogo_id")})
                db.add(u)
                db.flush()
            db.query(m.CapacidadeUC).filter_by(unidade_id=u.id).delete()
            for capd in caps_p:
                db.add(m.CapacidadeUC(unidade_id=u.id, **{k: v for k, v in capd.items() if hasattr(m.CapacidadeUC, k) and k not in ("id", "unidade_id")}))
            db.query(m.EletricaUC).filter_by(unidade_id=u.id).delete()
            for ed in elet_p:
                db.add(m.EletricaUC(unidade_id=u.id, **{k: v for k, v in ed.items() if hasattr(m.EletricaUC, k) and k not in ("id", "unidade_id")}))
        _upsert_campos(db, "UC", cat.id, campos_p)
    db.commit()
    return {"criados": criados, "atualizados": atualizados}


def _receber_condensadores(db: Session, payload: dict):
    for fp in payload.get("fabricantes", []):
        _garantir_fabricante(db, fp["nome"])
    criados, atualizados = 0, 0
    for lp in payload.get("linhas", []):
        fab_nome = lp.pop("fabricante_nome", None)
        modelos_p = lp.pop("modelos", [])
        fatores_p = lp.pop("fatores", [])
        campos_p = lp.pop("campos", [])
        fab_id = _garantir_fabricante(db, fab_nome) if fab_nome else lp.get("fabricante_id")
        ln = db.query(m.LinhaCondensadorRemoto).filter_by(
            fabricante_id=fab_id, nome=lp["nome"], versao_catalogo=lp.get("versao_catalogo"),
            tipo_estrutura=lp.get("tipo_estrutura")).first()
        if ln:
            for k, v in lp.items():
                if hasattr(ln, k) and k not in ("id", "fabricante_id"):
                    setattr(ln, k, v)
            atualizados += 1
        else:
            ln = m.LinhaCondensadorRemoto(fabricante_id=fab_id, **{k: v for k, v in lp.items() if hasattr(m.LinhaCondensadorRemoto, k) and k not in ("id", "fabricante_id")})
            db.add(ln)
            db.flush()
            criados += 1
        existing_modelos = {mod.modelo: mod for mod in ln.modelos}
        for mp in modelos_p:
            modelo_nome = mp.get("modelo")
            if modelo_nome in existing_modelos:
                mod = existing_modelos[modelo_nome]
                for k, v in mp.items():
                    if hasattr(mod, k) and k not in ("id", "linha_id"):
                        setattr(mod, k, v)
            else:
                db.add(m.ModeloCondensadorRemoto(linha_id=ln.id, **{k: v for k, v in mp.items() if hasattr(m.ModeloCondensadorRemoto, k) and k not in ("id", "linha_id")}))
        for fp in fatores_p:
            existing = db.query(m.FatorCorrecaoCondensador).filter_by(linha_id=ln.id, tipo=fp["tipo"], chave=fp["chave"]).first()
            if existing:
                existing.fator = fp.get("fator")
            else:
                db.add(m.FatorCorrecaoCondensador(linha_id=ln.id, tipo=fp["tipo"], chave=fp["chave"], fator=fp.get("fator")))
        _upsert_campos(db, "CondensadorRemoto", ln.id, campos_p)
    db.commit()
    return {"criados": criados, "atualizados": atualizados}


def _receber_comercial(db: Session, payload: dict):
    criados, atualizados = 0, 0
    for ip in payload.get("itens", []):
        existing = db.query(m.CatalogoComercial).filter_by(id_cadastro=ip.get("id_cadastro")).first() if ip.get("id_cadastro") else None
        if not existing and ip.get("categoria") and ip.get("nome"):
            existing = db.query(m.CatalogoComercial).filter_by(categoria=ip["categoria"], nome=ip["nome"]).first()
        if existing:
            for k, v in ip.items():
                if hasattr(existing, k) and k not in ("id",):
                    setattr(existing, k, v)
            atualizados += 1
        else:
            db.add(m.CatalogoComercial(**{k: v for k, v in ip.items() if hasattr(m.CatalogoComercial, k) and k not in ("id",)}))
            criados += 1
    db.commit()
    return {"criados": criados, "atualizados": atualizados}


_RECEBEDORES = {
    "forcadores": _receber_forcadores,
    "uc": _receber_uc,
    "condensadores": _receber_condensadores,
    "comercial": _receber_comercial,
}


@router.post("/receber")
def receber(payload: dict = Body(...), db: Session = Depends(get_db)):
    tipo = payload.get("tipo")
    fn = _RECEBEDORES.get(tipo)
    if not fn:
        return {"erro": f"Tipo desconhecido: {tipo}"}
    try:
        resultado = fn(db, payload)
        log.info("Sync %s: %s", tipo, resultado)
        return {"ok": True, **resultado}
    except Exception as e:
        log.exception("Erro no sync %s", tipo)
        db.rollback()
        return {"ok": False, "erro": str(e)}


def _resolver_uploads_dir():
    appdata = os.environ.get("VEKTORIUM_APPDATA")
    if appdata:
        return Path(appdata) / "uploads"
    return Path(__file__).resolve().parent.parent.parent / "uploads"


def _converter_path_para_base64(caminho_relativo: str, uploads_dir: Path):
    nome_arquivo = caminho_relativo.replace("/uploads/", "")
    arquivo = uploads_dir / nome_arquivo
    if not arquivo.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(arquivo))
    if not mime:
        ext = arquivo.suffix.lower()
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp"}.get(ext.lstrip("."), "application/octet-stream")
    conteudo = arquivo.read_bytes()
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


@router.post("/converter-fotos")
def converter_fotos(db: Session = Depends(get_db)):
    uploads_dir = _resolver_uploads_dir()
    convertidos = 0
    erros = []
    tabelas = [
        (m.LinhaForcador, "LinhaForcador"),
        (m.CatalogoUC, "CatalogoUC"),
        (m.LinhaCondensadorRemoto, "LinhaCondensadorRemoto"),
        (m.CatalogoComercial, "CatalogoComercial"),
    ]
    for modelo, nome in tabelas:
        for obj in db.query(modelo).all():
            img = getattr(obj, "imagem_path", None)
            if not img or not img.startswith("/uploads/"):
                continue
            b64 = _converter_path_para_base64(img, uploads_dir)
            if b64:
                obj.imagem_path = b64
                convertidos += 1
            else:
                erros.append(f"{nome}: arquivo não encontrado para {img}")
    db.commit()
    log.info("Converter-fotos: %d convertidos, %d erros", convertidos, len(erros))
    return {"ok": True, "convertidos": convertidos, "erros": erros}


# ── SYNC ON BOOT (F4.3) ─────────────────────────────────────────────────────

_GRUPOS_TABELAS = {
    "forcadores": ["cat_fabricantes", "forcador_linhas", "forcador_modelos",
                    "forcador_capacidades", "forcador_eletricos", "forcador_fisicos",
                    "forcador_dimensionais", "forcador_fatores_gas"],
    "uc": ["uc_catalogos", "uc_unidades", "uc_eletricas", "uc_capacidades"],
    "condensadores": ["condensador_linhas", "condensador_modelos",
                      "condensador_fatores"],
    "comercial": ["catalogo_comercial"],
}


@router.post("/sync-boot")
def sync_boot(request: FastAPIRequest, db: Session = Depends(get_db)):
    """Sincroniza catálogos na inicialização: compara versões locais vs remotas,
    baixa grupos desatualizados do Fly.io."""
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not token:
        return {"ok": False, "motivo": "sem_token"}

    remote_url = os.environ.get("VEKTORIUM_API_URL", "https://vektorium-calc.fly.dev")

    try:
        req = Request(f"{remote_url}/api/catalogos/versoes",
                      headers={"Authorization": f"Bearer {token}"})
        resp = urlopen(req, timeout=10)
        versoes_remotas = json.loads(resp.read())
    except Exception as e:
        log.warning("Sync boot: não consultou versões remotas: %s", e)
        return {"ok": False, "motivo": "sem_rede", "erro": str(e)}

    versoes_locais = {v.tabela: v.versao for v in db.query(m.CatalogoVersao).all()}

    grupos_stale = set()
    for grupo, tabelas in _GRUPOS_TABELAS.items():
        for t in tabelas:
            remota = versoes_remotas.get(t, {})
            v_remota = remota.get("versao", 0) if isinstance(remota, dict) else 0
            if v_remota > versoes_locais.get(t, 0):
                grupos_stale.add(grupo)
                break

    if not grupos_stale:
        return {"ok": True, "atualizados": []}

    for grupo in grupos_stale:
        try:
            req = Request(f"{remote_url}/api/catalogo-sync/exportar?tipo={grupo}",
                          headers={"Authorization": f"Bearer {token}"})
            resp = urlopen(req, timeout=60)
            dados = json.loads(resp.read())
            fn = _RECEBEDORES.get(grupo)
            if fn:
                fn(db, dados)
                log.info("Sync boot: grupo '%s' atualizado", grupo)
        except Exception as e:
            log.warning("Sync boot: falha no grupo '%s': %s", grupo, e)

    for tabela, info in versoes_remotas.items():
        v_remota = info.get("versao", 0) if isinstance(info, dict) else 0
        atualizado = info.get("atualizado_em") if isinstance(info, dict) else None
        v = db.query(m.CatalogoVersao).filter_by(tabela=tabela).first()
        if v:
            v.versao = v_remota
            v.atualizado_em = atualizado
        else:
            db.add(m.CatalogoVersao(tabela=tabela, versao=v_remota, atualizado_em=atualizado))
    db.commit()

    return {"ok": True, "atualizados": list(grupos_stale)}


@router.post("/push-para-remoto")
def push_para_remoto(request: FastAPIRequest, db: Session = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return {"ok": False, "erro": "Token JWT não fornecido"}
    token = auth_header[7:]
    remote_url = os.environ.get("VEKTORIUM_API_URL", "https://vektorium-calc.fly.dev")
    resultados = {}
    for tipo in ("forcadores", "uc", "condensadores", "comercial"):
        fn = _EXPORTADORES.get(tipo)
        dados = fn(db)
        payload_bytes = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        req = Request(
            f"{remote_url}/api/catalogo-sync/receber",
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            resp = urlopen(req, timeout=120)
            body = json.loads(resp.read().decode("utf-8"))
            resultados[tipo] = body
            log.info("Push %s → remoto: %s", tipo, body)
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            resultados[tipo] = {"ok": False, "erro": f"HTTP {e.code}: {body[:200]}"}
            log.error("Push %s falhou: %s %s", tipo, e.code, body[:200])
        except (URLError, Exception) as e:
            resultados[tipo] = {"ok": False, "erro": str(e)}
            log.error("Push %s falhou: %s", tipo, e)
    return {"ok": True, "resultados": resultados}
