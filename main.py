from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
import sqlite3
from auth import db, init, now, hash_pw, check_pw, make_token, read_token, new_code


class Register(BaseModel):
    name: str
    email: str
    password: str


class Login(BaseModel):
    email: str
    password: str


class ShortIn(BaseModel):
    url: str


bearer = HTTPBearer(auto_error=False)


def me(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not cred:
        raise HTTPException(401, "Login first: click Authorize, paste token")
    data = read_token(cred.credentials)
    if not data:
        raise HTTPException(401, "Token bad or expired")
    row = db().execute("SELECT * FROM users WHERE email=?", (data["sub"],)).fetchone()
    if not row:
        raise HTTPException(401, "User deleted")
    return dict(row)


@asynccontextmanager
async def life(app: FastAPI):
    init()
    yield


app = FastAPI(title="LinkBolt API", lifespan=life)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "LinkBolt"}


@app.post("/api/auth/register", status_code=201)
def register(b: Register):
    if len(b.password) < 4:
        raise HTTPException(400, "Password min 4 chars")
    try:
        c = db()
        c.execute("INSERT INTO users(name,email,pw) VALUES(?,?,?)",
                  (b.name, b.email, hash_pw(b.password, b.email)))
        c.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Email already used")
    return {"name": b.name, "email": b.email}


@app.post("/api/auth/login")
def login(b: Login):
    r = db().execute("SELECT * FROM users WHERE email=?", (b.email,)).fetchone()
    if not r or not check_pw(b.password, b.email, r["pw"]):
        raise HTTPException(401, "Wrong email or password")
    return {"access_token": make_token(r["email"]), "token_type": "bearer"}


@app.post("/api/shorten", status_code=201)
def shorten(b: ShortIn, u: dict = Depends(me)):
    url = b.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(400, "URL must start with http:// or https://")
    c = db()
    for _ in range(5):
        code = new_code()
        try:
            c.execute("INSERT INTO links VALUES(?,?,?,?,?)",
                      (code, url, u["email"], 0, now()))
            c.commit()
            return {"code": code, "short": f"/{code}", "url": url}
        except sqlite3.IntegrityError:
            continue
    raise HTTPException(500, "Retry, code collision")


@app.get("/{code}")
def go(code: str):
    c = db()
    r = c.execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
    if not r:
        raise HTTPException(404, "Short link not found")
    c.execute("UPDATE links SET clicks=clicks+1 WHERE code=?", (code,))
    c.commit()
    return RedirectResponse(url=r["url"], status_code=307)


@app.get("/api/links")
def my_links(u: dict = Depends(me)):
    rows = db().execute("SELECT * FROM links WHERE owner=? ORDER BY created DESC",
                        (u["email"],)).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/links/{code}/stats")
def link_stats(code: str, u: dict = Depends(me)):
    r = db().execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    if r["owner"] != u["email"]:
        raise HTTPException(403, "Only owner sees stats")
    return dict(r)


@app.delete("/api/links/{code}")
def delete(code: str, u: dict = Depends(me)):
    c = db()
    r = c.execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    if r["owner"] != u["email"]:
        raise HTTPException(403, "Only owner can delete")
    c.execute("DELETE FROM links WHERE code=?", (code,))
    c.commit()
    return {"deleted": code}
