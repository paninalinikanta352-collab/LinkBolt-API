# LinkBolt API - Solo Backend Project

URL shortener with JWT ownership + click analytics. No frontend - Swagger /docs is the demo.

## Features
- Register / Login with hashed passwords + JWT (24h)
- Shorten any http(s) URL to 6-char code
- `GET /{code}` 307 redirect + clicks+1
- My links list (owner only)
- Per-link stats (owner only), owner-only delete
- Seeded demo links + demo user

## Run
```powershell
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```
Open: http://127.0.0.1:8002/docs

Demo: `admin@linkbolt.test` / `admin123`
Try: open http://127.0.0.1:8002/ytlink -> redirects to YouTube, clicks goes up.

## API
- `GET /api/health`
- `POST /api/auth/register` | `POST /api/auth/login`
- `POST /api/shorten` (auth)
- `GET /{code}` (public redirect)
- `GET /api/links` (auth)
- `GET /api/links/{code}/stats` (owner)
- `DELETE /api/links/{code}` (owner)

## How it works
1. Shorten -> random 6-char code from 62 letters, retry on collision
2. Visit -> DB lookup code -> UPDATE clicks -> 307 redirect
3. Stats prove it: clicks counter in DB, not memory

Built solo by Backend Lead.
