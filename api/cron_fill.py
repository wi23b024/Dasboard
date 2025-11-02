import os
from datetime import datetime, timedelta, timezone
import psycopg

def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    return psycopg.connect(dsn, autocommit=True)

def handler(request):
    try:
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        end   = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

        with get_conn() as conn, conn.cursor() as cur:
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

        return (200, {"Content-Type": "application/json"}, b'{"ok":true}')
    except Exception as e:
        msg = str(e).replace('"', "'")
        return (500, {"Content-Type": "application/json"}, f'{{"ok":false,"error":"{msg}"}}'.encode())