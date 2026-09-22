import io
import re
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import inspect

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def resposta_excel_projeto(conteudo: bytes, nome_arquivo: str, projeto):
    """Devolve a exportação Excel de uma tela do PROJETO sempre salvando em disco
    (usa pasta_salvamento do projeto ou ~/Downloads como fallback). Compatível com Electron."""
    return resposta_arquivo_projeto(conteudo, nome_arquivo, projeto, _XLSX_MIME)


def resposta_arquivo_projeto(conteudo: bytes, nome_arquivo: str, projeto, mime: str):
    """Salva um arquivo do projeto (ex.: a Proposta .docx) na 'Pasta de Salvamento' do projeto
    (Tela 1); se não houver, salva na pasta Downloads do Windows do usuário. Sempre grava em disco
    e devolve {salvo_em: caminho} — o front mostra onde salvou (via api.baixarOuSalvar)."""
    nome_arquivo = re.sub(r'[\\/:*?"<>|]', "-", nome_arquivo)
    pasta = getattr(projeto, "pasta_salvamento", None) if projeto else None
    destino = Path(pasta) if pasta else (Path.home() / "Downloads")
    try:
        destino.mkdir(parents=True, exist_ok=True)
        caminho = destino / nome_arquivo
        caminho.write_bytes(conteudo)
    except OSError as e:
        # Fallback final: se a pasta configurada falhar, tenta o Downloads.
        try:
            alt = Path.home() / "Downloads"
            alt.mkdir(parents=True, exist_ok=True)
            caminho = alt / nome_arquivo
            caminho.write_bytes(conteudo)
        except OSError:
            raise HTTPException(400, f'Não foi possível salvar em "{destino}": {e}')
    return {"salvo_em": str(caminho)}


def _natural(s):
    """Pedaços texto/número para ordenação natural ('1,2,10' e não '1,10,2')."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s or ""))]


def chave_ordem_camara(sistema_nome, linha_succao, linha_eletrica):
    """Chave de ordenação canônica de tudo no app: Sistema › Linha de Sucção › Linha Elétrica,
    com ordenação natural em cada nível."""
    return (_natural(sistema_nome), _natural(linha_succao), _natural(linha_eletrica))


def model_to_dict(obj, exclude=None):
    if obj is None:
        return None
    exclude = exclude or set()
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs if c.key not in exclude}


def list_to_dict(objs, exclude=None):
    return [model_to_dict(o, exclude) for o in objs]
