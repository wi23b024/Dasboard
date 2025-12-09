# CAUTION: This script will delete all existing rows in the tables listed in TABLES.
import os, random, math
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import psycopg

load_dotenv()

def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    return psycopg.connect(dsn, prepare_threshold=None)

def clamp(v, lo, hi): return max(lo, min(hi, v))

TABLES = (
    "login",
    "list",
    "tasks_create",
    "comment_create"
)

print("Connecting…")
with get_conn() as conn, conn.cursor() as cur:
    print("Connected!")

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    today_utc = datetime.now(timezone.utc).date()
    end = datetime.combine(today_utc, datetime.min.time(), tzinfo=timezone.utc)

    if end <= start:
        raise RuntimeError("End before or equal start; nothing to generate.")

    total_minutes = int((end - start).total_seconds() // 60)

    regions = ("EU","US","APAC")
    codes   = (200,201,400,404,500,504)

    BATCH = 10_000

    for table in TABLES:
        print(f"\n🧹 Deleting existing rows from {table}…")
        cur.execute(f"DELETE FROM {table};")
        conn.commit()

        sql = f"""
            INSERT INTO {table} (
                timestamp,
                response_time_ms,
                request_size_kb,
                response_size_kb,
                status_code,
                region
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        batch = []
        inserted = 0
        ts = start

        print(f"🚀 Generating data for table '{table}'…")

        for _ in range(total_minutes):
            # Normalverteilung via Box-Muller
            u1, u2 = random.random(), random.random()
            z = math.sqrt(-2*math.log(max(u1, 1e-12))) * math.cos(2*math.pi*u2)

            resp_ms = int(clamp(250 + 80*z, 50, 900))
            req_kb  = int(clamp(120 + 40*z, 10, 300))
            res_kb  = int(clamp(200 + 60*z, 20, 400))
            status  = random.choice(codes)
            region  = random.choice(regions)

            batch.append((ts, resp_ms, req_kb, res_kb, status, region))

            if len(batch) >= BATCH:
                cur.executemany(sql, batch)
                conn.commit()
                inserted += len(batch)
                print(f"[{table}] Inserted {inserted:,} / {total_minutes:,}")
                batch.clear()

            ts += timedelta(minutes=1)

        if batch:
            cur.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
            print(f"[{table}] Inserted {inserted:,} / {total_minutes:,}")

        # Check
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        (count_actual,) = cur.fetchone()
        if count_actual != total_minutes:
            raise RuntimeError(
                f"[{table}] Mismatch: expected {total_minutes:,} rows, got {count_actual:,}"
            )

        print(f"✅ Table '{table}' done.")

print("\n🎉 All tables done — one row per minute up to today's 00:00 UTC.")