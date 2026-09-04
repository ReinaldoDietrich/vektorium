# Fase 3 — imagem do app REMOTO (catálogo + cálculo), hospedado no Fly.io.
# Empacota só backend/main_calc.py — NUNCA backend/main.py (esse é o app local, com os
# projetos, roda no computador do usuário, nunca é publicado).
FROM python:3.12-slim

WORKDIR /app

COPY requirements-calc.txt .
RUN pip install --no-cache-dir -r requirements-calc.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/main_calc.py backend/main_calc.py
COPY backend/database.py backend/database.py
COPY backend/models.py backend/models.py
COPY backend/auth_supabase.py backend/auth_supabase.py
COPY backend/calc_service.py backend/calc_service.py
COPY backend/calc_puro_uc_rack.py backend/calc_puro_uc_rack.py
COPY backend/campo_catalogo.py backend/campo_catalogo.py
COPY backend/id_comercial.py backend/id_comercial.py
COPY backend/calc_polinomio_compressor.py backend/calc_polinomio_compressor.py
COPY backend/calc_paineis_portas.py backend/calc_paineis_portas.py
COPY backend/calc_remoto_client.py backend/calc_remoto_client.py
COPY backend/composicao_preco.py backend/composicao_preco.py
COPY backend/calculos backend/calculos
COPY backend/exportacao backend/exportacao
COPY backend/importacao backend/importacao
COPY backend/routers backend/routers
COPY backend/utils.py backend/utils.py

EXPOSE 8080
CMD ["uvicorn", "backend.main_calc:app", "--host", "0.0.0.0", "--port", "8080"]
