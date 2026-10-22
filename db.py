import turso_serverless as turso
import os
from dotenv import load_dotenv

load_dotenv()
DB_NAME = os.getenv("TURSO_DB_NAME")


def create_db():
    db = turso.connect(url=os.getenv("TURSO_URL"), auth_token=os.getenv("TURSO_AUTH_TOKEN"))
    try:
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT,
                amount REAL,
                currency TEXT,
                date TEXT,
                message_id TEXT UNIQUE,
                used_tokens INTEGER
            )
        """)
        db.commit()
    finally:
        db.close()

def insert_expense(concept, amount, currency, date, message_id, used_tokens):
    db = turso.connect(url=os.getenv("TURSO_URL"), auth_token=os.getenv("TURSO_AUTH_TOKEN"))
    try:
        db.execute(
            f"""
            INSERT INTO {DB_NAME} (concept, amount, currency, date, message_id, used_tokens)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (concept, amount, currency, date, message_id, used_tokens),
        )
        db.commit()
        print("Inserted.")
    finally:
        db.close()

def query_if_expense_exists(message_id):
    db = turso.connect(url=os.getenv("TURSO_URL"), auth_token=os.getenv("TURSO_AUTH_TOKEN"))
    try:
        result = db.execute(
            f"""
            SELECT 1 FROM {DB_NAME}
            WHERE message_id = ?
            """,
            (message_id,),
        )
        return result.fetchone() is not None
    finally:
        db.close()

if __name__ == "__main__":
    create_db()