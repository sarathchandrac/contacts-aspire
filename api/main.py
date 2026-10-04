from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_databases()
    yield


app = FastAPI(title="Contacts API", lifespan=lifespan)


class Contact(BaseModel):
    id: int
    name: str
    phone: str
    email: str


@app.get("/")
def root():
    return {"service": "contacts-api", "endpoints": ["/contacts", "/users", "/analytics", "/health", "/docs"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/contacts", response_model=list[Contact])
def list_contacts():
    """Contacts live in MySQL."""
    with db.mysql_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, phone, email FROM contacts ORDER BY id")
        return cur.fetchall()


@app.get("/users")
def list_users():
    """Users live in PostgreSQL."""
    with db.pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id")
        return cur.fetchall()


@app.get("/analytics")
def analytics():
    """Aggregated analytics from PostgreSQL."""
    with db.pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM analytics_events")
        total = cur.fetchone()["total"]
        cur.execute("SELECT event_type, COUNT(*) AS count FROM analytics_events GROUP BY event_type ORDER BY count DESC")
        by_type = cur.fetchall()
        cur.execute("SELECT page, COUNT(*) AS count FROM analytics_events GROUP BY page ORDER BY count DESC")
        by_page = cur.fetchall()
        cur.execute(
            """SELECT u.username, COUNT(*) AS count FROM analytics_events e
               JOIN users u ON u.id = e.user_id GROUP BY u.username ORDER BY count DESC LIMIT 5"""
        )
        top_users = cur.fetchall()
    return {"total_events": total, "by_type": by_type, "by_page": by_page, "top_users": top_users}
