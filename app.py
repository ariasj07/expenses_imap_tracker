from datetime import datetime, timedelta
from io import BytesIO
from typing import Literal

from flask import Flask, render_template, request, redirect, send_file
from dotenv import load_dotenv
import os
from anthropic import Anthropic
from imap_tools import MailBox
from pydantic import BaseModel, Field
import pandas as pd

from db import (
    insert_expense,
    query_if_expense_exists,
    get_expenses,
    get_kpi_rows,
    DEFAULT_LIMIT,
    TABLE_LIMITS,
    TABLE_LIMIT_OPTIONS,
)

load_dotenv()


class ExpectedResponse(BaseModel):
    is_valid: bool = Field(description="Whether the email is a valid expense email or normal email")
    concept: str = Field(description="The concept of the expense described in the email")
    amount: float = Field(description="The amount of the expense described in the email")
    currency: Literal["USD", "EUR", "CRC"] = Field(description="The currency of the expense described in the email")


RECEIVER_EMAIL_GMAIL = os.getenv("RECEIVER_EMAIL_GMAIL")

app = Flask(__name__)


def fetch_emails():
    with MailBox("imap.gmail.com").login(RECEIVER_EMAIL_GMAIL, os.getenv("RECEIVER_EMAIL_APP_PASSWORD")) as mailbox:
        for msg in mailbox.fetch(criteria="ALL", reverse=True):
            message_id = msg.headers.get("message-id")[0]
            if query_if_expense_exists(message_id):
                print("Expense already exists.")
                continue

            date = msg.date.isoformat()
            response, used_tokens = process_email(msg.text)
            if response.is_valid:
                print(response.concept)
                insert_expense(
                    concept=response.concept,
                    amount=response.amount,
                    currency=response.currency,
                    date=date,
                    message_id=message_id,
                    used_tokens=used_tokens
                )
            else:
                print("Invalid expense.")


def process_email(msg_body):
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.parse(
        max_tokens=2000,
        model="claude-haiku-5-5",
        messages=[
            {
                "content": f"Email: {msg_body}",
                "role": "user"
            }
        ],
        system="You are a helpful assistant that extracts the concept, amount, and currency of an expense from the given email.",
        output_format=ExpectedResponse,
    )
    response = message.parsed_output
    print(response)
    return response, message.usage.input_tokens + message.usage.output_tokens


def load_df(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    return df


def suma(df, currency, start=None, end=None):
    if df.empty:
        return 0.0
    s = df[df["currency"] == currency]
    if start is not None:
        s = s[s["date"].dt.date >= start]
    if end is not None:
        s = s[s["date"].dt.date < end]
    return float(s["amount"].sum())


def pct(current, previous):
    if previous == 0:
        return 100.0 if current else 0.0
    return (current - previous) / previous * 100


def compute_kpis(df):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    today_crc = suma(df, "CRC", today, today + timedelta(days=1))
    week_crc = suma(df, "CRC", week_start)
    month_crc = suma(df, "CRC", month_start)

    return {
        "today": {
            "crc": today_crc,
            "usd": suma(df, "USD", today, today + timedelta(days=1)),
            "change": pct(today_crc, suma(df, "CRC", yesterday, today)),
            "compare": "ayer",
        },
        "week": {
            "crc": week_crc,
            "usd": suma(df, "USD", week_start),
            "change": pct(week_crc, suma(df, "CRC", last_week_start, week_start)),
            "compare": "la semana pasada",
        },
        "month": {
            "crc": month_crc,
            "usd": suma(df, "USD", month_start),
            "change": pct(month_crc, suma(df, "CRC", last_month_start, month_start)),
            "compare": "el mes pasado",
        },
    }


def parse_limit(raw_limit):
    if raw_limit == "todos":
        return None, "todos"
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    if limit not in TABLE_LIMITS:
        limit = DEFAULT_LIMIT
    return limit, str(limit)


@app.route("/")
def index():
    query_limit, selected_limit = parse_limit(request.args.get("limit", str(DEFAULT_LIMIT)))
    table = load_df(get_expenses(limit=query_limit))
    if table.empty:
        expenses = []
    else:
        table["date_label"] = table["date"].dt.strftime("%d %b %Y")
        table["amount_label"] = table["amount"].map("{:,.2f}".format)
        expenses = table.to_dict("records")

    return render_template(
        "index.html",
        kpis=compute_kpis(load_df(get_kpi_rows())),
        expenses=expenses,
        limit=selected_limit,
        limit_options=TABLE_LIMIT_OPTIONS,
        export_limit_options=TABLE_LIMIT_OPTIONS,
    )


@app.route("/sincronizar", methods=["POST"])
def sincronizar():
    fetch_emails()
    return redirect("/")


@app.route("/exportar")
def exportar():
    query_limit, _ = parse_limit(request.args.get("limit", str(DEFAULT_LIMIT)))
    fmt = request.args.get("format", "csv")
    if fmt not in ("csv", "xlsx"):
        fmt = "csv"

    df = pd.DataFrame(get_expenses(limit=query_limit))
    if fmt == "xlsx":
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="gastos.xlsx")

    buffer = BytesIO(df.to_csv(index=False).encode("utf-8"))
    return send_file(buffer, as_attachment=True, download_name="gastos.csv", mimetype="text/csv")


if __name__ == "__main__":
    app.run(debug=True)
