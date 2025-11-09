from fastapi import FastAPI, Query
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row 
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="App Metrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"

    return psycopg.connect(dsn, prepare_threshold=None)

@app.get("/")
def root():
    return {"message": "API is running"}

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