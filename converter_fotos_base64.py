# -*- coding: utf-8 -*-
"""Converte imagem_path de caminhos de arquivo (/uploads/xxx.png) para data URIs base64
no banco local, usando apenas os endpoints existentes (catalogo-sync/exportar e receber).
Não requer reinicialização do servidor."""
import os, sys, base64, mimetypes, json

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
LOCAL = "http://localhost:8842"

try:
    import requests
except ImportError:
    print("ERRO: módulo 'requests' não encontrado.")
    print("Execute: pip install requests")
    sys.exit(1)


def converter_path_para_base64(caminho_relativo):
    nome = caminho_relativo.replace("/uploads/", "")
    arquivo = os.path.join(UPLOADS_DIR, nome)
    if not os.path.isfile(arquivo):
        return None
    mime, _ = mimetypes.guess_type(arquivo)
    if not mime:
        ext = os.path.splitext(arquivo)[1].lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp"}.get(ext, "application/octet-stream")
    with open(arquivo, "rb") as f:
        conteudo = f.read()
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


def processar_tipo(tipo):
    print(f"\n{'='*60}")
    print(f"Processando: {tipo}")
    print(f"{'='*60}")

    r = requests.get(f"{LOCAL}/api/catalogo-sync/exportar", params={"tipo": tipo}, timeout=30)
    r.raise_for_status()
    dados = r.json()

    convertidos = 0

    if tipo == "forcadores":
        for ln in dados.get("linhas", []):
            img = ln.get("imagem_path")
            if img and img.startswith("/uploads/"):
                b64 = converter_path_para_base64(img)
                if b64:
                    ln["imagem_path"] = b64
                    convertidos += 1
                    print(f"  OK: {ln.get('nome', '?')}")
                else:
                    print(f"  ERRO: arquivo não encontrado para {img}")

    elif tipo == "uc":
        for cat in dados.get("catalogos", []):
            img = cat.get("imagem_path")
            if img and img.startswith("/uploads/"):
                b64 = converter_path_para_base64(img)
                if b64:
                    cat["imagem_path"] = b64
                    convertidos += 1
                    print(f"  OK: {cat.get('nome', '?')}")
                else:
                    print(f"  ERRO: arquivo não encontrado para {img}")

    elif tipo == "condensadores":
        for ln in dados.get("linhas", []):
            img = ln.get("imagem_path")
            if img and img.startswith("/uploads/"):
                b64 = converter_path_para_base64(img)
                if b64:
                    ln["imagem_path"] = b64
                    convertidos += 1
                    print(f"  OK: {ln.get('nome', '?')}")
                else:
                    print(f"  ERRO: arquivo não encontrado para {img}")

    elif tipo == "comercial":
        for item in dados.get("itens", []):
            img = item.get("imagem_path")
            if img and img.startswith("/uploads/"):
                b64 = converter_path_para_base64(img)
                if b64:
                    item["imagem_path"] = b64
                    convertidos += 1
                    print(f"  OK: {item.get('nome', '?')}")
                else:
                    print(f"  ERRO: arquivo não encontrado para {img}")

    if convertidos == 0:
        print("  Nenhuma conversão necessária")
        return 0

    print(f"\n  Enviando {convertidos} fotos convertidas para o banco local...")
    r2 = requests.post(f"{LOCAL}/api/catalogo-sync/receber", json=dados, timeout=120)
    r2.raise_for_status()
    resultado = r2.json()
    print(f"  Resultado: {resultado}")
    return convertidos


def main():
    print("=" * 60)
    print("CONVERSÃO DE FOTOS: caminho de arquivo → base64")
    print("=" * 60)

    if not os.path.isdir(UPLOADS_DIR):
        print(f"ERRO: pasta uploads não encontrada: {UPLOADS_DIR}")
        sys.exit(1)

    total = 0
    for tipo in ("forcadores", "uc", "condensadores", "comercial"):
        try:
            total += processar_tipo(tipo)
        except Exception as e:
            print(f"  ERRO em {tipo}: {e}")

    print(f"\n{'='*60}")
    print(f"CONCLUÍDO — {total} fotos convertidas para base64 no banco local")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
