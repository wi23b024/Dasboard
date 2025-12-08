from fastapi import FastAPI, Query, HTTPException, Response, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

import psycopg
from psycopg.rows import dict_row 
from passlib.context import CryptContext
import secrets

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = FastAPI(title="App Metrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))

def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"

    return psycopg.connect(dsn, prepare_threshold=None)

# ---------- SCHEMAS ----------
class RegisterIn(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

# ---------- HELPERS ----------
def set_session_cookie(resp: Response, session_id: str):
    # Frontend ≠ Backend → Cross-Site-Cookie nötig
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )

def clear_session_cookie(resp: Response):
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/")

def create_session(conn, user_id: str) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    with conn.cursor() as cur:
        cur.execute(
            "insert into sessions (session_id, user_id, expires_at) values (%s, %s, %s);",
            (session_id, user_id, expires_at),
        )
    return session_id

def get_user_by_session(conn, session_id: str):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            select u.id, u.first_name, u.last_name, u.email, u.created_at
            from sessions s
            join users u on u.id = s.user_id
            where s.session_id = %s and s.expires_at > now();
        """, (session_id,))
        return cur.fetchone()

@app.get("/")
def root():
    return {"message": "API is running"}

@app.post("/registrieren")
def registrieren(body: RegisterIn):
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select 1 from users where email=%s;", (body.email.lower(),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="E-Mail bereits registriert.")
        pw_hash = pwd_ctx.hash(body.password)
        cur.execute("""
            insert into users (first_name, last_name, email, password_hash)
            values (%s,%s,%s,%s)
            returning id, first_name, last_name, email, created_at;
        """, (body.firstName.strip(), body.lastName.strip(), body.email.lower(), pw_hash))
        user = cur.fetchone()
    return {"ok": True, "message": "Registrierung erfolgreich.", "user": user}

@app.post("/login")
def login(body: LoginIn, response: Response):
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select id, password_hash from users where email=%s;", (body.email.lower(),))
        row = cur.fetchone()
        if not row or not pwd_ctx.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch.")
        session_id = create_session(conn, row["id"])
        conn.commit()
    set_session_cookie(response, session_id)
    return {"ok": True, "message": "Login erfolgreich."}

# --- Metrics Endpoint ---
@app.get("/metrics")
def get_metrics(
    start: datetime = Query(..., description="Startzeitpunkt (YYYY-MM-DDTHH:MM:SSZ)"),
    end:   datetime = Query(..., description="Endzeitpunkt (YYYY-MM-DDTHH:MM:SSZ)")
):
    """
    Liefert alle Zeilen aus der Tabelle 'login' zwischen start und end.
    Beispiel:
    /metrics?start=2025-10-07T00:00:00Z&end=2025-10-10T00:00:00Z
    """
    try:
        sql = """
            SELECT id, "timestamp", response_time_ms, request_size_kb,
                   response_size_kb, status_code, region
            FROM login
            WHERE "timestamp" BETWEEN %s AND %s
            ORDER BY "timestamp" ASC;
        """

        with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (start, end))
            rows = cur.fetchall()

        return {
            "ok": True,
            "count": len(rows),
            "start": start,
            "end": end,
            "data": rows
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/cron_fill")
def cron_fill():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return {"ok": False, "error": "DATABASE_URL not set"}
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"

    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end   = datetime.combine(today,                   datetime.min.time(), tzinfo=timezone.utc)

    try:
        with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM login WHERE timestamp >= %s AND timestamp < %s;", (start, end))
            cur.execute("""
                INSERT INTO login (timestamp, response_time_ms, request_size_kb, response_size_kb, status_code, region)
                SELECT
                  ts,
                  (50  + round(850*random()))::int,
                  (10  + round(290*random()))::int,
                  (20  + round(380*random()))::int,
                  (ARRAY[200,201,400,404,500,504])[1 + floor(random()*6)]::int,
                  (ARRAY['EU','US','APAC'])[1 + floor(random()*3)]::text
                FROM generate_series(%s, %s - interval '1 minute', interval '1 minute') AS ts;
            """, (start, end))
        return {"ok": True, "start": start.isoformat(), "end": end.isoformat()}
    except Exception as e:
        return {"ok": False, "error": str(e)}