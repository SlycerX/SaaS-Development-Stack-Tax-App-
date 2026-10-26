import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response

from app.db import connect

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SESSION_DAYS = 14
PBKDF2_ROUNDS = 600_000


def current_income_year_ending(today: datetime | None = None) -> int:
    moment = today or datetime.now(timezone.utc)
    return moment.year + 1 if moment.month >= 7 else moment.year


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$", 1)
    candidate = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, f"{salt_hex}${digest_hex}")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not EMAIL.fullmatch(cleaned):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return cleaned


def _clean_password(password: str) -> str:
    if len(password) < 12:
        raise HTTPException(status_code=422, detail="Use at least 12 characters")
    return password


def _public_account(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2],
        "australian_resident": row[3],
        "income_year_ending": row[4],
        "entity_type": row[5],
    }


def register_account(email: str, password: str, display_name: str) -> dict:
    cleaned = _clean_email(email)
    _clean_password(password)
    name = display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Enter your name")
    year = current_income_year_ending()
    with connect() as conn:
        exists = conn.execute("select 1 from accounts where email = %s", (cleaned,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        row = conn.execute(
            """
            insert into accounts (email, password_hash, display_name, income_year_ending)
            values (%s, %s, %s, %s)
            returning id, email, display_name, australian_resident, income_year_ending, entity_type
            """,
            (cleaned, _hash_password(password), name, year),
        ).fetchone()
        conn.commit()
    return _public_account(row)


def authenticate(email: str, password: str) -> dict:
    cleaned = email.strip().lower()
    with connect() as conn:
        row = conn.execute(
            """
            select id, email, display_name, australian_resident, income_year_ending, entity_type, password_hash
            from accounts where email = %s
            """,
            (cleaned,),
        ).fetchone()
    if row is None or not _verify_password(password, row[6]):
        raise HTTPException(status_code=401, detail="Email or password is wrong")
    return _public_account(row)


def start_session(account_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute(
            "insert into sessions (token_hash, account_id, expires_at) values (%s, %s, %s)",
            (_hash_token(token), account_id, expires),
        )
        conn.commit()
    return token


def account_for_token(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Sign in")
    with connect() as conn:
        row = conn.execute(
            """
            select a.id, a.email, a.display_name, a.australian_resident, a.income_year_ending, a.entity_type
            from sessions s
            join accounts a on a.id = s.account_id
            where s.token_hash = %s and s.expires_at > now()
            """,
            (_hash_token(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Sign in")
    return _public_account(row)


def end_session(token: str | None) -> None:
    if not token:
        return
    with connect() as conn:
        conn.execute("delete from sessions where token_hash = %s", (_hash_token(token),))
        conn.commit()


def update_account(account_id: int, display_name: str, australian_resident: bool, income_year_ending: int) -> dict:
    name = display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Enter your name")
    if not 2000 <= income_year_ending <= 2100:
        raise HTTPException(status_code=422, detail="Choose an income year")
    with connect() as conn:
        row = conn.execute(
            """
            update accounts
            set display_name = %s, australian_resident = %s, income_year_ending = %s
            where id = %s
            returning id, email, display_name, australian_resident, income_year_ending, entity_type
            """,
            (name, australian_resident, income_year_ending, account_id),
        ).fetchone()
        conn.commit()
    return _public_account(row)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SESSION_COOKIE_SECURE", "").lower() == "true",
        path="/",
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie("session", path="/")
