from typing import Literal
from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
from anthropic import Anthropic
import turso_serverless as turso
from imap_tools import MailBox
from pydantic import BaseModel, Field
from db import insert_expense, query_if_expense_exists

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

fetch_emails()