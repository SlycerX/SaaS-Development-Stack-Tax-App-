import calendar
import re
from datetime import date, timedelta, timezone

from fastapi import HTTPException

from app.db import connect

KINDS = {"property", "share", "bitcoin"}
MONEY = re.compile(r"^\d+(\.\d{1,2})?$")


def parse_money(value: str) -> int:
    cleaned = value.strip()
    if not MONEY.fullmatch(cleaned):
        raise HTTPException(status_code=422, detail="Enter an amount in dollars and cents")
    whole, _, fraction = cleaned.partition(".")
    fraction = (fraction + "00")[:2]
    return int(whole) * 100 + int(fraction)


def format_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Enter a date as YYYY-MM-DD") from exc


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def income_year_bounds(ending_year: int) -> tuple[date, date]:
    return date(ending_year - 1, 7, 1), date(ending_year, 6, 30)


def _record_from_row(row) -> dict:
    return {
        "id": row[0],
        "kind": row[1],
        "description": row[2],
        "acquired_on": row[3].isoformat(),
        "disposed_on": row[4].isoformat() if row[4] else None,
        "cost_base_cents": row[5],
        "incidental_cents": row[6],
        "proceeds_cents": row[7],
        "quantity": row[8],
        "main_residence": row[9],
    }


def add_record(account_id: int, payload: dict) -> dict:
    kind = payload["kind"]
    if kind not in KINDS:
        raise HTTPException(status_code=422, detail="Choose property, share, or bitcoin")
    description = payload["description"].strip()
    if not description:
        raise HTTPException(status_code=422, detail="Describe the asset")
    acquired = parse_day(payload["acquired_on"])
    disposed = parse_day(payload["disposed_on"]) if payload.get("disposed_on") else None
    if disposed and disposed < acquired:
        raise HTTPException(status_code=422, detail="The sale date is before the purchase date")
    cost_base = parse_money(payload["cost_base"])
    incidental = parse_money(payload.get("incidental") or "0")
    proceeds = parse_money(payload["proceeds"]) if payload.get("proceeds") else None
    if disposed and proceeds is None:
        raise HTTPException(status_code=422, detail="A sale needs the amount you received")
    if proceeds is not None and disposed is None:
        raise HTTPException(status_code=422, detail="Proceeds need a sale date")
    quantity = (payload.get("quantity") or "").strip() or None
    main_residence = bool(payload.get("main_residence")) and kind == "property"
    with connect() as conn:
        row = conn.execute(
            """
            insert into ledger_records (
                account_id, kind, description, acquired_on, disposed_on,
                cost_base_cents, incidental_cents, proceeds_cents, quantity, main_residence
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning id, kind, description, acquired_on, disposed_on,
                      cost_base_cents, incidental_cents, proceeds_cents, quantity, main_residence
            """,
            (
                account_id,
                kind,
                description,
                acquired,
                disposed,
                cost_base,
                incidental,
                proceeds,
                quantity,
                main_residence,
            ),
        ).fetchone()
        record = _record_from_row(row)
        detail = _history_line(record)
        conn.execute(
            "insert into ledger_events (account_id, record_id, detail) values (%s, %s, %s)",
            (account_id, record["id"], detail),
        )
        conn.commit()
    return record


def _history_line(record: dict) -> str:
    cost = format_money(record["cost_base_cents"] + record["incidental_cents"])
    if record["disposed_on"]:
        return (
            f"Recorded a {record['kind']} disposal of {record['description']} "
            f"acquired {record['acquired_on']}, sold {record['disposed_on']} "
            f"for {format_money(record['proceeds_cents'])}. Cost base {cost}."
        )
    return (
        f"Recorded a {record['kind']} holding of {record['description']} "
        f"acquired {record['acquired_on']}. Cost base {cost}."
    )


def list_records(account_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            select id, kind, description, acquired_on, disposed_on,
                   cost_base_cents, incidental_cents, proceeds_cents, quantity, main_residence
            from ledger_records
            where account_id = %s
            order by acquired_on, id
            """,
            (account_id,),
        ).fetchall()
    return [_record_from_row(row) for row in rows]


def list_history(account_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            select id, detail, created_at
            from ledger_events
            where account_id = %s
            order by id desc
            """,
            (account_id,),
        ).fetchall()
    return [
        {"id": row[0], "detail": row[1], "created_at": row[2].astimezone(timezone.utc).isoformat()}
        for row in rows
    ]


def estimate(account: dict, records: list[dict] | None = None) -> dict:
    rows = records if records is not None else list_records(account["id"])
    start, end = income_year_bounds(account["income_year_ending"])
    other_gains: list[int] = []
    discount_gains: list[int] = []
    losses = 0
    events = []
    recommendations = []
    kinds_seen = {row["kind"] for row in rows}

    for record in rows:
        if record["disposed_on"] is None or record["proceeds_cents"] is None:
            continue
        disposed = date.fromisoformat(record["disposed_on"])
        if not start <= disposed <= end:
            continue
        acquired = date.fromisoformat(record["acquired_on"])
        gain = record["proceeds_cents"] - record["cost_base_cents"] - record["incidental_cents"]
        discount = (
            account["australian_resident"]
            and account["entity_type"] == "individual"
            and disposed >= add_months(acquired, 12)
            and not record["main_residence"]
        )
        if record["main_residence"] and record["kind"] == "property":
            gain = 0
            discount = False
        events.append(
            {
                "record_id": record["id"],
                "description": record["description"],
                "gain_cents": gain,
                "discount_eligible": discount and gain > 0,
            }
        )
        if gain < 0:
            losses += -gain
        elif discount:
            discount_gains.append(gain)
        elif gain > 0:
            other_gains.append(gain)
        if record["incidental_cents"] == 0 and gain != 0:
            recommendations.append(
                f"Add brokerage, stamp duty, or legal fees to {record['description']} if you paid them. They increase the cost base."
            )
        if gain > 0 and not discount and not record["main_residence"]:
            eligible_on = add_months(acquired, 12)
            if disposed < eligible_on <= disposed + timedelta(days=31):
                recommendations.append(
                    f"{record['description']} was sold just short of 12 months. The 50% CGT discount is available after {eligible_on.isoformat()} for a resident individual."
                )
        if record["kind"] == "property" and not record["main_residence"] and gain > 0:
            recommendations.append(
                f"If you lived in {record['description']} as your main residence, the main residence exemption may reduce this gain. Mark it only when that is true."
            )

    loss_pool = losses
    other_net = 0
    for gain in other_gains:
        used = min(loss_pool, gain)
        loss_pool -= used
        other_net += gain - used
    discount_net = 0
    for gain in discount_gains:
        used = min(loss_pool, gain)
        loss_pool -= used
        discount_net += gain - used
    taxable = other_net + discount_net // 2

    if loss_pool and not other_gains and not discount_gains:
        recommendations.append(
            f"You have {format_money(loss_pool)} of capital losses. They can offset a capital gain. They do not reduce salary or wages."
        )
    elif loss_pool:
        recommendations.append(
            f"{format_money(loss_pool)} of capital losses remains after this year's gains. Keep the record for a later capital gain."
        )
    for kind, label in (
        ("property", "property records"),
        ("share", "share trades"),
        ("bitcoin", "bitcoin disposals"),
    ):
        if kind not in kinds_seen:
            recommendations.append(f"No {label} are saved yet. Add them if you bought, sold, or swapped any.")

    return {
        "income_year_ending": account["income_year_ending"],
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "taxable_gain_cents": taxable,
        "remaining_loss_cents": loss_pool,
        "events": events,
        "recommendations": recommendations,
        "note": "This is an estimate from the records in this account, using the individual CGT discount and loss order that leaves the smaller taxable gain. It is not a tax-agent opinion.",
    }
