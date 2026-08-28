"""
Ahmed Ragab — Investigations backend
FastAPI + SQLite. Provides:
  - /api/investigations           GET  (public list)
  - /api/investigations/{slug}    GET  (public single)
  - /admin                        GET  (admin dashboard, basic-auth)
  - /admin/api/*                  CRUD (basic-auth)
  - /uploads/<file>               static image serving
"""

import os
import re
import json
import secrets
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import storage as gcs_storage

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "investigations.db"

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "change-me-in-env")
if ADMIN_PASS == "change-me-in-env":
    import warnings
    warnings.warn("ADMIN_PASS is using the insecure default. Set ADMIN_PASS in your environment.")

def _ensure_schema():
    """Create tables if missing, then seed if empty."""
    init_db()
    with db() as c:
        count = c.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
    if count == 0:
        # Seed only on truly empty DB
        try:
            import seed as _seed
            _seed.run()
            gcs_storage.upload_db_to_gcs()
        except Exception as e:
            print(f"[startup] seed skipped: {e}")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # On startup: pull DB from GCS if bucket configured
    gcs_storage.download_db_from_gcs()
    _ensure_schema()
    yield

app = FastAPI(title="Ahmed Ragab CMS", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok_u = secrets.compare_digest(credentials.username, ADMIN_USER)
    ok_p = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (ok_u and ok_p):
        raise HTTPException(401, "Unauthorized", {"WWW-Authenticate": "Basic"})
    return credentials.username

# ---------- DB ----------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            date TEXT,
            sort_order INTEGER DEFAULT 0,
            published INTEGER DEFAULT 1,

            title_ar TEXT NOT NULL,
            publication_ar TEXT,
            body_ar TEXT,

            title_en TEXT,
            publication_en TEXT,
            body_en TEXT,

            hero_image TEXT,
            source_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investigation_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            caption_ar TEXT,
            caption_en TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
        );
        """)

init_db()

# ---------- Helpers ----------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:80] or f"item-{int(datetime.now().timestamp())}"

def row_to_dict(row):
    d = dict(row)
    return d

def get_investigation_full(inv_id: int):
    with db() as c:
        inv = c.execute("SELECT * FROM investigations WHERE id = ?", (inv_id,)).fetchone()
        if not inv:
            return None
        gallery = c.execute(
            "SELECT id, url, caption_ar, caption_en, sort_order FROM gallery WHERE investigation_id = ? ORDER BY sort_order, id",
            (inv_id,),
        ).fetchall()
        d = row_to_dict(inv)
        d["gallery"] = [row_to_dict(g) for g in gallery]
        return d

# ---------- Public API ----------
@app.get("/api/investigations")
def list_investigations(lang: str = "ar", include_unpublished: bool = False):
    with db() as c:
        q = "SELECT * FROM investigations"
        if not include_unpublished:
            q += " WHERE published = 1"
        q += " ORDER BY sort_order DESC, year DESC, id DESC"
        rows = c.execute(q).fetchall()
        result = []
        for r in rows:
            d = row_to_dict(r)
            gallery = c.execute(
                "SELECT url, caption_ar, caption_en FROM gallery WHERE investigation_id = ? ORDER BY sort_order, id LIMIT 1",
                (d["id"],),
            ).fetchall()
            d["gallery"] = [row_to_dict(g) for g in gallery]
            result.append(d)
        return result

@app.get("/api/investigations/{slug}")
def get_investigation(slug: str):
    with db() as c:
        inv = c.execute("SELECT * FROM investigations WHERE slug = ? AND published = 1", (slug,)).fetchone()
        if not inv:
            raise HTTPException(404, "Not found")
        return get_investigation_full(inv["id"])

# ---------- Admin API ----------
@app.get("/admin/api/investigations")
def admin_list(user: str = Depends(require_admin)):
    with db() as c:
        rows = c.execute("SELECT * FROM investigations ORDER BY sort_order DESC, year DESC, id DESC").fetchall()
        return [row_to_dict(r) for r in rows]

@app.get("/admin/api/investigations/{inv_id}")
def admin_get(inv_id: int, user: str = Depends(require_admin)):
    inv = get_investigation_full(inv_id)
    if not inv:
        raise HTTPException(404, "Not found")
    return inv

@app.post("/admin/api/investigations")
async def admin_create(request: Request, user: str = Depends(require_admin)):
    data = await request.json()
    slug = data.get("slug") or slugify(data.get("title_en") or data.get("title_ar") or "item")
    with db() as c:
        # Ensure unique slug
        base_slug, i = slug, 1
        while c.execute("SELECT 1 FROM investigations WHERE slug = ?", (slug,)).fetchone():
            i += 1
            slug = f"{base_slug}-{i}"
        cur = c.execute("""
            INSERT INTO investigations (slug, year, date, sort_order, published,
                title_ar, publication_ar, body_ar,
                title_en, publication_en, body_en,
                hero_image, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slug,
            int(data.get("year") or 0),
            data.get("date"),
            int(data.get("sort_order") or 0),
            1 if data.get("published", True) else 0,
            data.get("title_ar", ""),
            data.get("publication_ar"),
            data.get("body_ar"),
            data.get("title_en"),
            data.get("publication_en"),
            data.get("body_en"),
            data.get("hero_image"),
            data.get("source_url"),
        ))
        inv_id = cur.lastrowid
        # Gallery
        for i, g in enumerate(data.get("gallery") or []):
            c.execute(
                "INSERT INTO gallery (investigation_id, url, caption_ar, caption_en, sort_order) VALUES (?, ?, ?, ?, ?)",
                (inv_id, g.get("url"), g.get("caption_ar"), g.get("caption_en"), i),
            )
        c.commit()
    gcs_storage.upload_db_to_gcs()
    return get_investigation_full(inv_id)

@app.put("/admin/api/investigations/{inv_id}")
async def admin_update(inv_id: int, request: Request, user: str = Depends(require_admin)):
    data = await request.json()
    with db() as c:
        existing = c.execute("SELECT * FROM investigations WHERE id = ?", (inv_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Not found")
        slug = data.get("slug") or existing["slug"]
        # Slug uniqueness (excluding self)
        if slug != existing["slug"]:
            base_slug, i = slug, 1
            while c.execute("SELECT 1 FROM investigations WHERE slug = ? AND id != ?", (slug, inv_id)).fetchone():
                i += 1
                slug = f"{base_slug}-{i}"
        c.execute("""
            UPDATE investigations SET
                slug=?, year=?, date=?, sort_order=?, published=?,
                title_ar=?, publication_ar=?, body_ar=?,
                title_en=?, publication_en=?, body_en=?,
                hero_image=?, source_url=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            slug,
            int(data.get("year") or existing["year"]),
            data.get("date"),
            int(data.get("sort_order") or 0),
            1 if data.get("published", True) else 0,
            data.get("title_ar", existing["title_ar"]),
            data.get("publication_ar"),
            data.get("body_ar"),
            data.get("title_en"),
            data.get("publication_en"),
            data.get("body_en"),
            data.get("hero_image"),
            data.get("source_url"),
            inv_id,
        ))
        # Replace gallery
        c.execute("DELETE FROM gallery WHERE investigation_id = ?", (inv_id,))
        for i, g in enumerate(data.get("gallery") or []):
            c.execute(
                "INSERT INTO gallery (investigation_id, url, caption_ar, caption_en, sort_order) VALUES (?, ?, ?, ?, ?)",
                (inv_id, g.get("url"), g.get("caption_ar"), g.get("caption_en"), i),
            )
        c.commit()
    gcs_storage.upload_db_to_gcs()
    return get_investigation_full(inv_id)

@app.delete("/admin/api/investigations/{inv_id}")
def admin_delete(inv_id: int, user: str = Depends(require_admin)):
    with db() as c:
        c.execute("DELETE FROM investigations WHERE id = ?", (inv_id,))
        c.commit()
    gcs_storage.upload_db_to_gcs()
    return {"ok": True}

@app.post("/admin/api/translate")
async def admin_translate(request: Request, user: str = Depends(require_admin)):
    """Translate Arabic fields to English using Claude (via llm-api:website preset)."""
    data = await request.json()
    title_ar = (data.get("title_ar") or "").strip()
    publication_ar = (data.get("publication_ar") or "").strip()
    body_ar = (data.get("body_ar") or "").strip()
    if not (title_ar or body_ar):
        raise HTTPException(400, "Nothing to translate")

    try:
        from anthropic import Anthropic
    except ImportError:
        raise HTTPException(500, "anthropic SDK not installed")

    system_prompt = (
        "You are a professional Arabic-to-English translator specializing in investigative journalism. "
        "Translate the provided Arabic fields to natural, publication-ready English. "
        "Preserve names, dates, place names, and quotations. Use standard newsroom English (AP style). "
        "Keep paragraph breaks as they are (blank line between paragraphs). "
        "Return ONLY a valid JSON object with keys: title_en, publication_en, body_en. "
        "No preamble, no code fences, no explanation \u2014 just the JSON."
    )
    user_payload = json.dumps({
        "title_ar": title_ar,
        "publication_ar": publication_ar,
        "body_ar": body_ar,
    }, ensure_ascii=False)

    try:
        client = Anthropic()
        msg = client.messages.create(
            model="claude_sonnet_4_6",
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_payload}],
        )
        content = msg.content[0].text.strip()
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {type(e).__name__}: {str(e)[:400]}")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise HTTPException(500, f"Translation returned non-JSON: {content[:300]}")
        parsed = json.loads(m.group(0))

    return {
        "title_en": parsed.get("title_en", ""),
        "publication_en": parsed.get("publication_en", ""),
        "body_en": parsed.get("body_en", ""),
    }


@app.post("/admin/api/upload")
async def admin_upload(file: UploadFile = File(...), user: str = Depends(require_admin)):
    ext = Path(file.filename).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(400, "Only jpg/png/webp/gif allowed")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rnd = secrets.token_hex(4)
    fname = f"{stamp}-{rnd}{ext}"
    dest = UPLOADS_DIR / fname
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # Upload to GCS if configured; falls back to local URL otherwise.
    url = gcs_storage.upload_image(str(dest), fname)
    return {"url": url, "filename": fname}

# ---------- Static ----------
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

@app.get("/admin", response_class=HTMLResponse)
def admin_page(user: str = Depends(require_admin)):
    return FileResponse(BASE_DIR / "static" / "admin.html")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Serve the site's static files (HTML/CSS/JS/images) from the repo root.
# STATIC_ROOT is set by the Dockerfile to /app; locally we default to the parent dir.
STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", str(BASE_DIR.parent)))
if STATIC_ROOT.exists():
    # `html=True` makes /some/path/ resolve to /some/path/index.html
    app.mount("/", StaticFiles(directory=str(STATIC_ROOT), html=True), name="site")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "admin": "/admin", "api": "/api/investigations"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8787))
    uvicorn.run(app, host="0.0.0.0", port=port)
