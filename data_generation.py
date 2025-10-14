import psycopg2
import os
import random
from datetime import datetime, timedelta
import numpy as np
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    user=os.getenv("user"),
    password=os.getenv("password"),
    host=os.getenv("host"),
    port=os.getenv("port"),
    dbname=os.getenv("dbname")
)

cur = conn.cursor()

print("Connected!")

# Parameter
regions = ["EU", "US", "APAC"]
status_codes = [200, 201, 400, 404, 500, 504]
start_time = datetime.utcnow() - timedelta(days=7)
total_minutes = 7 * 24 * 60  # 7 days; every minute

sql = """
INSERT INTO login (timestamp, response_time_ms, request_size_kb, response_size_kb, status_code, region)
VALUES (%s, %s, %s, %s, %s, %s);
"""

for i in range(total_minutes):
    ts = start_time + timedelta(minutes=i)

    response_time = int(np.clip(np.random.normal(250, 80), 50, 900))
    request_size = int(np.clip(np.random.normal(120, 40), 10, 300))
    response_size = int(np.clip(np.random.normal(200, 60), 20, 400))
    status = random.choice(status_codes)
    region = random.choice(regions)

    cur.execute(sql, (ts, response_time, request_size, response_size, status, region))

    if i % 500 == 0:
        conn.commit()
        print(f"Inserted {i} / {total_minutes}...")

conn.commit()
cur.close()
conn.close()
print("✅ Done, all rows inserted.")