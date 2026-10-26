import os
import time
from urllib.parse import quote_plus

import psycopg


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = quote_plus(os.environ["DB_USER"])
    password = quote_plus(os.environ["DB_PASSWORD"])
    host = os.environ["DB_HOST"]
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "saas")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def connect():
    return psycopg.connect(database_url())


def init_db(attempts: int = 20, delay_seconds: float = 1.0) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with connect() as conn:
                conn.execute(
                    """
                    create table if not exists items (
                        id serial primary key,
                        name text not null
                    )
                    """
                )
                conn.execute(
                    """
                    insert into items (name)
                    select 'example'
                    where not exists (select 1 from items)
                    """
                )
                conn.execute(
                    """
                    create table if not exists accounts (
                        id bigserial primary key,
                        email text not null unique,
                        password_hash text not null,
                        display_name text not null,
                        australian_resident boolean not null default true,
                        income_year_ending integer not null,
                        entity_type text not null default 'individual',
                        created_at timestamptz not null default now()
                    )
                    """
                )
                conn.execute(
                    """
                    create table if not exists sessions (
                        token_hash text primary key,
                        account_id bigint not null references accounts(id),
                        expires_at timestamptz not null
                    )
                    """
                )
                conn.execute(
                    """
                    create table if not exists ledger_records (
                        id bigserial primary key,
                        account_id bigint not null references accounts(id),
                        kind text not null,
                        description text not null,
                        acquired_on date not null,
                        disposed_on date,
                        cost_base_cents bigint not null,
                        incidental_cents bigint not null,
                        proceeds_cents bigint,
                        quantity text,
                        main_residence boolean not null default false,
                        created_at timestamptz not null default now()
                    )
                    """
                )
                conn.execute(
                    """
                    create table if not exists ledger_events (
                        id bigserial primary key,
                        account_id bigint not null references accounts(id),
                        record_id bigint,
                        detail text not null,
                        created_at timestamptz not null default now()
                    )
                    """
                )
                conn.commit()
                return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError("Database did not become ready") from last_error


def list_items() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("select id, name from items order by id").fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]


def add_item(name: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "insert into items (name) values (%s) returning id, name",
            (name,),
        ).fetchone()
        conn.commit()
    return {"id": row[0], "name": row[1]}
