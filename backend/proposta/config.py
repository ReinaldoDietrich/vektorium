# -*- coding: utf-8 -*-
"""Defaults/config da Proposta Comercial em arquivo JSON — NÃO usa banco de dados (regra do
projeto: proibido gravar no banco). Guarda o "default por usuário" (após o 1º preenchimento vira
padrão) dos campos manuais + caminhos dos arquivos base (papel de carta, logomarca)."""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_APPDATA = os.environ.get("VEKTORIUM_APPDATA")
_USER_DIR = Path(_APPDATA) if _APPDATA else BASE_DIR
DADOS_DIR = _USER_DIR / "dados"
CONFIG_PATH = DADOS_DIR / "proposta_defaults.json"

# Pasta onde ficam os arquivos base enviados pelo usuário (papel de carta, logomarca, imagens).
UPLOADS_PROPOSTA = _USER_DIR / "uploads" / "proposta"

# Template padrão de proposta (já vem com papel de carta no rodapé + margens). É a base do docxtpl.
TEMPLATE_PADRAO = Path(__file__).resolve().parent / "template_proposta.docx"

DEFAULTS_INICIAIS = {
    "titulo_fornecimento": "FORNECIMENTO DE EQUIPAMENTOS E MÃO DE OBRA DE INSTALAÇÃO",
    "empresa_contratada": "",          # nome da empresa do usuário (substitui todo [EMPRESA USUÁRIO])
    "dias_proposta": "15",
    "meses_garantia": "12",
    "embarque_equipamentos": "45",
    "embarque_isopainel": "30",
    "tipo_painel": "",
    "vendedor_nome": "",
    "vendedor_cargo": "",
    "vendedor_telefone": "",
    "vendedor_email": "",
    # Dados de Faturamento — dados do usuário (empresa contratada) para RECEBER o pagamento.
    "fat_razao_social": "",
    "fat_cnpj": "",
    "fat_insc_municipal": "",
    "fat_insc_estadual": "",
    "fat_endereco": "",
    "fat_cidade_uf": "",
    "fat_banco": "",
    "fat_agencia": "",
    "fat_conta": "",
    "fat_pix": "",
    # Caminhos relativos (dentro de uploads/proposta) — None = usar o do template padrão.
    "papel_carta_path": None,
    "logo_path": None,
}


def _garantir_dirs():
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_PROPOSTA.mkdir(parents=True, exist_ok=True)


def carregar_defaults() -> dict:
    """Lê o JSON de defaults; se não existir, devolve os iniciais (sem gravar)."""
    _garantir_dirs()
    dados = dict(DEFAULTS_INICIAIS)
    if CONFIG_PATH.exists():
        try:
            salvos = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(salvos, dict):
                dados.update({k: v for k, v in salvos.items() if k in DEFAULTS_INICIAIS})
        except (json.JSONDecodeError, OSError):
            pass  # arquivo corrompido — cai nos iniciais, não derruba a geração
    return dados


def salvar_defaults(novos: dict) -> dict:
    """Grava só as chaves conhecidas (merge sobre o que já existe). Retorna o estado final."""
    _garantir_dirs()
    atual = carregar_defaults()
    for k, v in (novos or {}).items():
        if k in DEFAULTS_INICIAIS:
            atual[k] = v
    CONFIG_PATH.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
    return atual
