from fastapi import FastAPI, Query
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
from typing import Optional

# --- Lade Umgebungsvariablen (.env) ---
load_dotenv()

# --- DB-Konfiguration ---
DB_CONFIG = {
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "dbname": os.getenv("dbname")
}

# --- API-Instanz ---
app = FastAPI(title="App Metrics API")

# --- Hilfsfunktion für DB-Abfragen ---
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# --- Root (Test) ---
@app.get("/")
def root():
    return {"message": "API is running 🚀"}


# --- Endpoint: hole alle Werte für bestimmten Zeitraum ---
@app.get("/metrics")
def get_metrics(
    start: datetime = Query(..., description="Startzeitpunkt (YYYY-MM-DDTHH:MM:SSZ)"),
    end: datetime = Query(..., description="Endzeitpunkt (YYYY-MM-DDTHH:MM:SSZ)")
):
    """
    Liefert alle Zeilen aus login zwischen start und end.
    Beispielaufruf:
    http://127.0.0.1:8000/metrics?start=2025-10-07T00:00:00Z&end=2025-10-10T00:00:00Z
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT id, timestamp, response_time_ms, request_size_kb, 
                   response_size_kb, status_code, region
            FROM login
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp ASC;
        """
        cur.execute(query, (start, end))
        rows = cur.fetchall()

        # Spaltennamen holen (für JSON-Schlüssel)
        colnames = [desc[0] for desc in cur.description]

        # Daten in JSON-kompatibles Format bringen
        results = [dict(zip(colnames, row)) for row in rows]

        cur.close()
        conn.close()

        return {
            "count": len(results),
            "start": start,
            "end": end,
            "data": results
        }

    except Exception as e:
        return {"error": str(e)}