---
trigger: always_on
---

# Project Overview & Context
- **Project Name**: Anything App
- **Description**: High-performance asynchronous REST API dan Real-time WebSocket service.
- **Primary Tech Stack**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), PostgreSQL.

## Architecture & Folder Structure
- `src/to_do_list_fast_api/main.py` : Entry point aplikasi FastAPI (CORS middleware, lifespan context, route inclusion).
- `src/to_do_list_fast_api/routers/` : Endpoint routers (routing per domain resource).
- `src/to_do_list_fast_api/schemas.py` : Pydantic models/schemas (Request validation, Response models, Data transfer objects).
- `src/to_do_list_fast_api/models.py` : Definisi tabel database ORM (SQLAlchemy declarative base).
- `src/to_do_list_fast_api/dependencies.py` : Common FastAPI dependencies.

## Coding & Style Conventions
- Terapkan standar **PEP 8** dan selalu sertakan **Type Hints** penuh di setiap argumen fungsi dan return value.
- Gunakan endpoint `async def` secara default untuk operasi I/O-bound (database, third-party HTTP call, Redis).
- Selalu tentukan `response_model` atau return type annotation pada setiap path operation decorator.
- Gunakan `FastAPI.HTTPException` dengan status code bawaan dari `starlette.status` (`status.HTTP_404_NOT_FOUND`, dll.).

## Database Migrations Protocol (Alembic)
- Selalu tinjau kode auto-generated migration sebelum dieksekusi untuk memastikan deteksi foreign key dan index sesuai.

## Hard Guardrails (Dilarang Keras)
1. **DILARANG** mengubah file `.env`, kredensial koneksi, atau token rahasia secara langsung.
2. **DILARANG** mengeksekusi migration destruktif (drop column, drop table, reset database) tanpa konfirmasi eksplisit.
3. **DILARANG** menambahkan library baru ke `requirements.txt`, `Pipfile`, atau `pyproject.toml` tanpa konfirmasi.
4. **DILARANG** melakukan blocking synchronous call (misalnya `time.sleep` atau library sync seperti `requests`) di dalam fungsi `async def`; gunakan async alternative (`asyncio.sleep`, `httpx.AsyncClient`).
5. **DILARANG** melakukan git commit atau push ke remote repository secara mandiri.