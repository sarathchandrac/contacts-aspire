import os
import random
import time
from datetime import datetime, timedelta, timezone

import psycopg
import pymysql
from psycopg.rows import dict_row
from pymysql.cursors import DictCursor

NAMES = [
    "Olivia Carter", "Liam Johnson", "Emma Williams", "Noah Brown", "Ava Davis",
    "Elijah Miller", "Sophia Wilson", "James Moore", "Isabella Taylor", "Benjamin Anderson",
    "Mia Thomas", "Lucas Jackson", "Charlotte White", "Henry Harris", "Amelia Martin",
    "Alexander Thompson", "Harper Garcia", "Daniel Martinez", "Evelyn Robinson", "Michael Clark",
]
ROLES = ["admin", "editor", "viewer"]
EVENT_TYPES = ["page_view", "click", "search", "signup", "purchase"]
PAGES = ["/home", "/contacts", "/users", "/reports", "/settings"]


def mysql_conn():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        cursorclass=DictCursor,
        autocommit=True,
    )


def pg_conn():
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DATABASE"],
        row_factory=dict_row,
        autocommit=True,
    )


def _retry(fn, attempts=15, delay=2):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(delay)


def seed_mysql():
    with mysql_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS contacts (
                   id INT PRIMARY KEY AUTO_INCREMENT,
                   name VARCHAR(100) NOT NULL,
                   phone VARCHAR(30) NOT NULL,
                   email VARCHAR(150) NOT NULL)"""
        )
        cur.execute("SELECT COUNT(*) AS n FROM contacts")
        if cur.fetchone()["n"] == 0:
            rows = [
                (n, f"+1-555-01{i:02d}", f"{n.lower().replace(' ', '.')}@example.com")
                for i, n in enumerate(NAMES, start=1)
            ]
            cur.executemany("INSERT INTO contacts (name, phone, email) VALUES (%s, %s, %s)", rows)


def seed_postgres():
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id SERIAL PRIMARY KEY,
                   username TEXT NOT NULL,
                   email TEXT NOT NULL,
                   role TEXT NOT NULL,
                   created_at TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS analytics_events (
                   id SERIAL PRIMARY KEY,
                   user_id INT REFERENCES users(id),
                   event_type TEXT NOT NULL,
                   page TEXT NOT NULL,
                   occurred_at TIMESTAMPTZ NOT NULL)"""
        )
        cur.execute("SELECT COUNT(*) AS n FROM users")
        if cur.fetchone()["n"] == 0:
            rng = random.Random(42)
            now = datetime.now(timezone.utc)
            for i, n in enumerate(NAMES[:10], start=1):
                cur.execute(
                    "INSERT INTO users (username, email, role, created_at) VALUES (%s, %s, %s, %s)",
                    (n.split()[0].lower() + str(i), f"{n.lower().replace(' ', '.')}@example.com",
                     ROLES[i % 3], now - timedelta(days=rng.randint(10, 365))),
                )
            for _ in range(200):
                cur.execute(
                    "INSERT INTO analytics_events (user_id, event_type, page, occurred_at) VALUES (%s, %s, %s, %s)",
                    (rng.randint(1, 10), rng.choice(EVENT_TYPES), rng.choice(PAGES),
                     now - timedelta(hours=rng.randint(0, 24 * 30))),
                )


def init_databases():
    _retry(seed_mysql)
    _retry(seed_postgres)
