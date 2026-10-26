import os
from contextlib import asynccontextmanager

from fastapi import Cookie, FastAPI, Header, Response
from pydantic import BaseModel, Field

from app.accounts import (
    account_for_token,
    authenticate,
    clear_session_cookie,
    end_session,
    register_account,
    set_session_cookie,
    start_session,
    update_account,
)
from app.auth import require_user
from app.db import add_item, init_db, list_items
from app.ledger import add_record, estimate, list_history, list_records


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=os.getenv("PRODUCT_NAME", "example"), version="0.1.0", lifespan=lifespan)


def _configure_telemetry() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "api")})
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, send_default_pii=False)


_configure_telemetry()


class ItemIn(BaseModel):
    name: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/items")
def get_items() -> dict:
    return {"items": list_items()}


@app.post("/items", status_code=201)
def post_item(body: ItemIn, authorization: str | None = Header(default=None)) -> dict:
    require_user(authorization)
    return add_item(body.name)


class RegisterIn(BaseModel):
    email: str
    password: str
    display_name: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: str
    password: str


class AccountUpdate(BaseModel):
    display_name: str
    australian_resident: bool
    income_year_ending: int


class LedgerIn(BaseModel):
    kind: str
    description: str
    acquired_on: str
    disposed_on: str | None = None
    cost_base: str
    incidental: str = "0"
    proceeds: str | None = None
    quantity: str | None = None
    main_residence: bool = False


@app.post("/auth/register", status_code=201)
def register(body: RegisterIn, response: Response) -> dict:
    account = register_account(body.email, body.password, body.display_name)
    set_session_cookie(response, start_session(account["id"]))
    return account


@app.post("/auth/login")
def login(body: LoginIn, response: Response) -> dict:
    account = authenticate(body.email, body.password)
    set_session_cookie(response, start_session(account["id"]))
    return account


@app.post("/auth/logout")
def logout(response: Response, session: str | None = Cookie(default=None)) -> dict:
    end_session(session)
    clear_session_cookie(response)
    return {"status": "signed_out"}


@app.get("/auth/me")
def me(session: str | None = Cookie(default=None)) -> dict:
    return account_for_token(session)


@app.patch("/auth/me")
def patch_me(body: AccountUpdate, session: str | None = Cookie(default=None)) -> dict:
    account = account_for_token(session)
    return update_account(
        account["id"],
        body.display_name,
        body.australian_resident,
        body.income_year_ending,
    )


@app.get("/ledger/records")
def get_ledger(session: str | None = Cookie(default=None)) -> dict:
    account = account_for_token(session)
    return {"records": list_records(account["id"])}


@app.post("/ledger/records", status_code=201)
def post_ledger(body: LedgerIn, session: str | None = Cookie(default=None)) -> dict:
    account = account_for_token(session)
    return add_record(account["id"], body.model_dump())


@app.get("/ledger/history")
def get_history(session: str | None = Cookie(default=None)) -> dict:
    account = account_for_token(session)
    return {"events": list_history(account["id"])}


@app.get("/ledger/estimate")
def get_estimate(session: str | None = Cookie(default=None)) -> dict:
    account = account_for_token(session)
    return estimate(account)
