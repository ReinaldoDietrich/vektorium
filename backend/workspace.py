# -*- coding: utf-8 -*-
"""SE-052 — Gerenciador de workspace: arquivos .vek individuais por projeto.

Estratégia "virtual database": ao abrir um .vek, os dados são importados no banco principal
(usando _importar_projeto de cloud_projetos.py). Ao salvar, são serializados de volta.
Ao fechar, são removidos do banco. Assim, NENHUM router existente precisa ser alterado.
"""

import json
import logging
import os
import re
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import engine
from . import models as m

_log = logging.getLogger(__name__)

TABELAS_PROJETO = [
    "margem_negociacao_projeto",
    "comissao_vendedor_projeto",
    "condicao_pagamento_parcela",
    "condicao_pagamento_projeto",
    "composicao_preco_item",
    "portas_frigorificas",
    "paineis_termicos",
    "equipamento_valor_tela10",
    "material_tela10",
    "camara_completo_valvulas",
    "camara_completo_forcadores",
    "camara_completo_equipamentos",
    "camara_completo_portas",
    "camaras_completo",
    "camara_simples_valvulas",
    "camara_simples_forcadores",
    "camaras_simples",
    "expositor_modulos",
    "expositores",
    "compressor_rack",
    "material_rack",
    "rack_condensador_selecao",
    "rack_paralelo",
    "uc_selecao_sistema",
    "sistemas_refrigeracao",
    "projetos",
]


def migrar_projetos_legado():
    """SE-060: migra projetos do banco SQLite para .vek antes da limpeza do startup."""
    from .routers.cloud_projetos import _serializar_projeto

    with Session(engine) as db:
        projetos = db.query(m.Projeto).order_by(m.Projeto.id).all()
        if not projetos:
            return 0

        _log.info("Migração automática: %d projeto(s) encontrado(s) no banco.", len(projetos))

        grupos: dict[str, list] = {}
        for p in projetos:
            chave = p.codigo_base or p.codigo_projeto or f"__id_{p.id}"
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append(p)

        docs = str(Path.home() / "Documents")
        fallback = str(Path(os.environ.get("APPDATA", str(Path.home()))) / "Vektorium" / "migrados")

        criados = 0
        for chave, grupo in grupos.items():
            grupo.sort(key=lambda p: p.revisao or 0)

            pasta_destino = None
            for p in grupo:
                if p.pasta_salvamento and os.path.isdir(p.pasta_salvamento):
                    pasta_destino = p.pasta_salvamento
                    break

            if not pasta_destino:
                pasta_orig = grupo[0].pasta_salvamento or "(não definida)"
                if os.path.isdir(docs):
                    pasta_destino = docs
                    _log.warning(
                        "Projeto '%s': pasta '%s' não existe. Salvando em Documentos: %s",
                        chave, pasta_orig, docs,
                    )
                else:
                    os.makedirs(fallback, exist_ok=True)
                    pasta_destino = fallback
                    _log.warning(
                        "Projeto '%s': pasta '%s' não existe. Salvando em: %s",
                        chave, pasta_orig, fallback,
                    )

            projetos_serializados = []
            for p in grupo:
                try:
                    data = _serializar_projeto(db, p)
                    data["_original_id"] = p.id
                    projetos_serializados.append(data)
                except Exception as e:
                    _log.error("Erro ao serializar projeto %d (%s): %s", p.id, p.codigo_projeto, e)

            if not projetos_serializados:
                continue

            nome_arq = re.sub(r'[\\/:*?"<>|]', "-", chave)
            path_vek = os.path.join(pasta_destino, f"{nome_arq}.vek")

            if os.path.exists(path_vek):
                base, ext = os.path.splitext(path_vek)
                i = 1
                while os.path.exists(f"{base}_{i}{ext}"):
                    i += 1
                path_vek = f"{base}_{i}{ext}"

            vek_data = {
                "vek_version": 1,
                "codigo_base": chave,
                "criado_em": datetime.now(timezone.utc).isoformat(),
                "atualizado_em": datetime.now(timezone.utc).isoformat(),
                "projetos": projetos_serializados,
            }

            try:
                os.makedirs(os.path.dirname(os.path.abspath(path_vek)), exist_ok=True)
                with open(path_vek, "w", encoding="utf-8") as f:
                    json.dump(vek_data, f, default=str, ensure_ascii=False, indent=2)
                ids_proj = [p.id for p in grupo]
                _log.info("Migrado: %s (projetos: %s)", path_vek, ids_proj)
                criados += 1
            except Exception as e:
                _log.error("Erro ao gravar %s: %s", path_vek, e)

        _log.info("Migração concluída: %d arquivo(s) .vek criado(s).", criados)
        return criados


def limpar_tabelas_projeto():
    """Remove TODOS os dados de projeto do banco (startup safety)."""
    with Session(engine) as db:
        for tabela in TABELAS_PROJETO:
            try:
                db.execute(text(f"DELETE FROM {tabela}"))
            except Exception:
                pass
        db.commit()


_FK_DIRETA_PROJETO = [
    "margem_negociacao_projeto", "comissao_vendedor_projeto",
    "condicao_pagamento_parcela", "condicao_pagamento_projeto",
    "composicao_preco_item", "portas_frigorificas", "paineis_termicos",
    "equipamento_valor_tela10", "material_tela10",
]


def _limpar_projetos_por_ids(db: Session, ids: set):
    """Remove projetos órfãos (sem entry no workspace) do banco."""
    for pid in ids:
        for tabela in _FK_DIRETA_PROJETO:
            try:
                db.execute(text(
                    f"DELETE FROM {tabela} WHERE projeto_id = :pid"
                ), {"pid": pid})
            except Exception:
                pass
        db.execute(text(
            "DELETE FROM uc_selecao_sistema WHERE sistema_id IN "
            "(SELECT id FROM sistemas_refrigeracao WHERE projeto_id = :pid)"
        ), {"pid": pid})
        proj = db.get(m.Projeto, pid)
        if proj:
            db.delete(proj)
    db.commit()


def _serializar_para_vek(db: Session, projeto: m.Projeto) -> dict:
    from .routers.cloud_projetos import _serializar_projeto
    data = _serializar_projeto(db, projeto)
    data["_original_id"] = projeto.id
    return data


def _importar_de_vek(db: Session, data: dict) -> int:
    from .routers.cloud_projetos import _importar_projeto
    return _importar_projeto(db, data)


class WorkspaceEntry:
    def __init__(self, path_vek: str, projeto_ids: list[int], codigo_base: str):
        self.path_vek = path_vek
        self.projeto_ids = projeto_ids
        self.codigo_base = codigo_base
        self.lock_path = path_vek + ".lock"
        self.modificado = False


class WorkspaceManager:
    def __init__(self):
        self._abertos: dict[str, WorkspaceEntry] = {}

    def _norm(self, p: str) -> str:
        return str(Path(p).resolve())

    # ---- Lock ----

    def _criar_lock(self, path_vek: str):
        lock_path = path_vek + ".lock"
        lock_data = {
            "user": os.environ.get("USERNAME", os.environ.get("USER", "unknown")),
            "machine": socket.gethostname(),
            "pid": os.getpid(),
            "since": datetime.now(timezone.utc).isoformat(),
        }
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False)

    def _verificar_lock(self, path_vek: str) -> dict | None:
        lock_path = path_vek + ".lock"
        if not os.path.exists(lock_path):
            return None
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                lock = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if lock.get("machine") == socket.gethostname():
            pid = lock.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)
                except OSError:
                    try:
                        os.remove(lock_path)
                    except OSError:
                        pass
                    return None
        return lock

    def _remover_lock(self, path_vek: str):
        lock_path = path_vek + ".lock"
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except OSError:
            pass

    # ---- Core ----

    def abrir_arquivo(self, path_vek: str) -> dict:
        norm = self._norm(path_vek)
        if norm in self._abertos:
            entry = self._abertos[norm]
            return {"ok": True, "ja_aberto": True, "projeto_ids": list(entry.projeto_ids)}

        lock = self._verificar_lock(path_vek)
        if lock:
            return {"ok": False, "erro": "locked", "lock": lock}

        try:
            with open(path_vek, "r", encoding="utf-8") as f:
                vek = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"ok": False, "erro": f"Arquivo .vek corrompido: {e}"}

        codigo_base = vek.get("codigo_base", "")
        projetos_data = vek.get("projetos", [])
        if not projetos_data:
            return {"ok": False, "erro": "Arquivo .vek sem projetos."}

        projetos_data.sort(key=lambda d: d.get("projeto", {}).get("revisao", 0))

        ids_em_uso = set()
        for entry in self._abertos.values():
            ids_em_uso.update(entry.projeto_ids)

        projeto_ids = []
        id_map = {}
        try:
            with Session(engine) as db:
                existentes = {p.id for p in db.query(m.Projeto).all()}
                orfaos = existentes - ids_em_uso
                if orfaos:
                    _limpar_projetos_por_ids(db, orfaos)

                for proj_data in projetos_data:
                    original_id = proj_data.get("_original_id")
                    pid = _importar_de_vek(db, proj_data)
                    projeto_ids.append(pid)
                    if original_id is not None:
                        id_map[original_id] = pid

                for pid in projeto_ids:
                    proj = db.get(m.Projeto, pid)
                    if proj and proj.revisao_de and proj.revisao_de in id_map:
                        proj.revisao_de = id_map[proj.revisao_de]
                db.commit()
        except Exception as e:
            return {"ok": False, "erro": f"Erro ao importar dados do .vek: {e}"}

        self._criar_lock(path_vek)
        entry = WorkspaceEntry(path_vek, projeto_ids, codigo_base)
        self._abertos[norm] = entry
        return {"ok": True, "projeto_ids": list(projeto_ids), "codigo_base": codigo_base}

    def salvar_arquivo(self, path_vek: str) -> dict:
        norm = self._norm(path_vek)
        entry = self._abertos.get(norm)
        if not entry:
            return {"ok": False, "erro": "Arquivo não está aberto no workspace."}

        projetos_serializados = []
        with Session(engine) as db:
            for pid in entry.projeto_ids:
                projeto = db.get(m.Projeto, pid)
                if projeto:
                    projetos_serializados.append(_serializar_para_vek(db, projeto))

        criado_em = None
        try:
            with open(path_vek, "r", encoding="utf-8") as f:
                existing = json.load(f)
            criado_em = existing.get("criado_em")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        vek_data = {
            "vek_version": 1,
            "codigo_base": entry.codigo_base,
            "criado_em": criado_em or datetime.now(timezone.utc).isoformat(),
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
            "projetos": projetos_serializados,
        }

        dir_vek = os.path.dirname(os.path.abspath(path_vek))
        os.makedirs(dir_vek, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(suffix=".vek.tmp", dir=dir_vek)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(vek_data, tmp, default=str, ensure_ascii=False, indent=2)

            bak_path = path_vek + ".bak"
            if os.path.exists(path_vek):
                try:
                    if os.path.exists(bak_path):
                        os.remove(bak_path)
                    os.rename(path_vek, bak_path)
                except OSError:
                    pass

            os.replace(tmp_path, path_vek)
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

        entry.modificado = False
        return {"ok": True, "salvo_em": path_vek, "projetos": len(projetos_serializados)}

    def fechar_arquivo(self, path_vek: str, salvar: bool = True) -> dict:
        norm = self._norm(path_vek)
        entry = self._abertos.get(norm)
        if not entry:
            return {"ok": False, "erro": "Arquivo não está aberto no workspace."}

        erro_save = None
        if salvar:
            result = self.salvar_arquivo(path_vek)
            if not result.get("ok"):
                erro_save = result.get("erro", "Erro ao salvar")

        _TABELAS_FK_DIRETA = [
            "margem_negociacao_projeto", "comissao_vendedor_projeto",
            "condicao_pagamento_parcela", "condicao_pagamento_projeto",
            "composicao_preco_item", "portas_frigorificas", "paineis_termicos",
            "equipamento_valor_tela10", "material_tela10",
        ]
        with Session(engine) as db:
            for pid in entry.projeto_ids:
                for tabela in _TABELAS_FK_DIRETA:
                    db.execute(text(
                        f"DELETE FROM {tabela} WHERE projeto_id = :pid"
                    ), {"pid": pid})
                db.execute(text(
                    "DELETE FROM uc_selecao_sistema WHERE sistema_id IN "
                    "(SELECT id FROM sistemas_refrigeracao WHERE projeto_id = :pid)"
                ), {"pid": pid})
                projeto = db.get(m.Projeto, pid)
                if projeto:
                    db.delete(projeto)
            db.commit()

        self._remover_lock(path_vek)
        del self._abertos[norm]
        if erro_save:
            return {"ok": True, "aviso": f"Arquivo fechado, mas houve erro ao salvar: {erro_save}"}
        return {"ok": True}

    def salvar_todos(self) -> dict:
        resultados = []
        erros = 0
        for entry in list(self._abertos.values()):
            try:
                r = self.salvar_arquivo(entry.path_vek)
                resultados.append({"path": entry.path_vek, **r})
                if not r.get("ok"):
                    erros += 1
            except Exception as e:
                erros += 1
                resultados.append({"path": entry.path_vek, "ok": False, "erro": str(e)})
        return {"ok": erros == 0, "resultados": resultados, "erros": erros}

    def fechar_todos(self) -> dict:
        resultados = []
        erros = 0
        for entry in list(self._abertos.values()):
            try:
                r = self.fechar_arquivo(entry.path_vek, salvar=True)
                resultados.append({"path": entry.path_vek, **r})
                if not r.get("ok"):
                    erros += 1
            except Exception as e:
                erros += 1
                resultados.append({"path": entry.path_vek, "ok": False, "erro": str(e)})
        return {"ok": erros == 0, "resultados": resultados}

    def listar_abertos(self) -> list[dict]:
        return [
            {
                "path": e.path_vek,
                "codigo_base": e.codigo_base,
                "projeto_ids": list(e.projeto_ids),
                "modificado": e.modificado,
            }
            for e in self._abertos.values()
        ]

    def projeto_pertence_a(self, projeto_id: int) -> str | None:
        for entry in self._abertos.values():
            if projeto_id in entry.projeto_ids:
                return entry.path_vek
        return None

    def registrar_projeto_novo(self, projeto_id: int, path_vek: str, codigo_base: str):
        norm = self._norm(path_vek)
        if norm in self._abertos:
            entry = self._abertos[norm]
            if projeto_id not in entry.projeto_ids:
                entry.projeto_ids.append(projeto_id)
            entry.modificado = True
        else:
            entry = WorkspaceEntry(path_vek, [projeto_id], codigo_base)
            entry.modificado = True
            self._abertos[norm] = entry
            self._criar_lock(path_vek)

    def desregistrar_projeto(self, projeto_id: int):
        for entry in self._abertos.values():
            if projeto_id in entry.projeto_ids:
                entry.projeto_ids.remove(projeto_id)
                entry.modificado = True
                return

    def marcar_modificado(self, projeto_id: int):
        for entry in self._abertos.values():
            if projeto_id in entry.projeto_ids:
                entry.modificado = True
                return

    def registrar_revisao(self, projeto_id_novo: int, projeto_id_original: int):
        for entry in self._abertos.values():
            if projeto_id_original in entry.projeto_ids:
                if projeto_id_novo not in entry.projeto_ids:
                    entry.projeto_ids.append(projeto_id_novo)
                entry.modificado = True
                return


workspace = WorkspaceManager()
