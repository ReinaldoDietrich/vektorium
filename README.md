# Vektorium — App Carga Térmica

Sistema de dimensionamento térmico e elétrico para instalações
frigoríficas. Aplicativo desktop (Electron + backend Python/FastAPI)
com catálogo e cálculo hospedados em servidor remoto (Fly.io + Supabase).

## Arquitetura

- **Frontend:** HTML/JS puro (`frontend/`)
- **Backend local:** FastAPI, expõe endpoints para dados de projeto,
  em SQLite local; iniciado pelo Electron (`electron/main.js`)
- **Backend remoto:** mesmo código Python, rodando no Fly.io contra
  Postgres/Supabase, responsável por CATÁLOGO e CÁLCULO
- **Instalador:** `electron-builder` (Windows NSIS)

## Documentação

Plano de revisão técnica e roadmap: [docs/PLANO_REVISAO_v2_2026-09-04.md](docs/PLANO_REVISAO_v2_2026-09-04.md)

## Regras invariantes

1. SQLite local ≡ Postgres remoto para **catálogo** (sincronia obrigatória)
2. Cálculo e catálogo são **obrigatoriamente online** (nunca calcular local)
3. Dados de PROJETO ficam locais no SQLite do usuário
