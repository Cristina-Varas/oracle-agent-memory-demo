import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
CONNECT_STRING = os.getenv("CONNECT_STRING")

if not all([DB_USER, DB_PASSWORD, CONNECT_STRING]):
    raise ValueError("Missing DB_USER, DB_PASSWORD or CONNECT_STRING in .env")

is_descriptor = CONNECT_STRING.strip().lower().startswith("(description=")
is_easy_connect = "/" in CONNECT_STRING or ":" in CONNECT_STRING

if not is_descriptor and not is_easy_connect:
    raise ValueError(
        "CONNECT_STRING looks like a wallet alias. For TLS without wallet, use "
        "the full TLS connection string from Autonomous Database."
    )

pool = oracledb.create_pool(
    user=DB_USER,
    password=DB_PASSWORD,
    dsn=CONNECT_STRING,
    min=1,
    max=4,
    increment=1,
)

with pool.acquire() as conn:
    with conn.cursor() as cur:
        cur.execute("select sysdate from dual")
        print(cur.fetchone())

print("Database connection OK")
