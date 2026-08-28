# Ahmed Ragab — Investigative Journalist

الموقع الشخصي للصحفي الاستقصائي أحمد رجب. ثنائي اللغة (عربي / إنجليزي) مع لوحة تحكم لإدارة التحقيقات وترجمة تلقائية من العربي للإنجليزي.

Personal website for investigative journalist Ahmed Ragab. Bilingual (Arabic / English) with a CMS for managing investigations and auto-translation from Arabic to English.

## Features

- **Bilingual site** — Arabic (RTL) and English (LTR) versions
- **Static frontend** — HTML/CSS/JS, no build step
- **FastAPI backend** — SQLite-backed CMS
- **Admin panel** at `/admin` with basic auth
- **Auto-translate** Arabic → English via Anthropic Claude
- **Image uploads** for hero images and galleries

## Structure

```
├── index.html, about.html, ...   # Arabic pages (root)
├── en/                            # English pages
├── styles.css, site.js            # Shared assets
├── assets/                        # Images
└── backend/
    ├── app.py                     # FastAPI application
    ├── seed.py                    # Seed investigations metadata
    ├── static/admin.html          # Admin panel UI
    ├── investigations.db          # SQLite DB (gitignored)
    └── uploads/                   # User-uploaded images (gitignored)
```

## Run locally

```bash
# 1. Install dependencies
pip install fastapi 'uvicorn[standard]' python-multipart anthropic

# 2. Configure environment
cp .env.example .env
# edit .env and set ADMIN_USER, ADMIN_PASS, ANTHROPIC_API_KEY

# 3. Seed the database (first run only)
cd backend
python seed.py

# 4. Start the server
python app.py
# server runs on http://localhost:8787
```

Then open:
- **Frontend:** open `index.html` directly, or serve the root folder with any static server
- **Admin panel:** http://localhost:8787/admin

## Admin panel

Log in with the `ADMIN_USER` / `ADMIN_PASS` you set in `.env`.

For each investigation:
1. Paste the full Arabic body under the **العربية** tab (blank line between paragraphs)
2. Click the **English** tab, then **ترجم من العربي →** to auto-translate
3. Review and edit the translation, upload a hero image and gallery, then save

## Deployment notes

The current setup is designed for development. For production hosting you'll need:
- A persistent host for the FastAPI backend (Railway, Fly.io, Render)
- A persistent database (Postgres instead of SQLite)
- Static frontend can be hosted on Vercel/Netlify pointing API calls to the backend URL

## License

All content © Ahmed Ragab. Code is not licensed for reuse without permission.
