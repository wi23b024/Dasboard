from fastapi import FastAPI, Query
from datetime import datetime
import os
from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row 

load_dotenv()

app = FastAPI(title="App Metrics API")

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