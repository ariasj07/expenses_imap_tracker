import turso_serverless as turso
import os
from dotenv import load_dotenv

load_dotenv()
DB_NAME = os.getenv("TURSO_DB_NAME")

DEFAULT_LIMIT = 10
TABLE_LIMITS = (10, 25, 50)
TABLE_LIMIT_OPTIONS = ("10", "25", "50", "todos")


def _connect():
    return turso.connect(url=os.getenv("TURSO_URL"), auth_token=os.getenv("TURSO_AUTH_TOKEN"))


def create_db():
    db = _connect()
    try:
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT,
                amount REAL,
                currency TEXT,
                date TEXT,
                message_id TEXT UNIQUE,
                used_tokens INTEGER,
                is_valid INTEGER
            )
        """)
        db.commit()
    finally:
        db.close()


def insert_expense(concept, amount, currency, date, message_id, used_tokens, is_valid):
    db = _connect()
    try:
        db.execute(
            f"""
            INSERT INTO {DB_NAME} (concept, amount, currency, date, message_id, used_tokens, is_valid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (concept, amount, currency, date, message_id, used_tokens, int(is_valid)),
        )
        db.commit()
        print("Inserted.")
    finally:
        db.close()


def query_if_expense_exists(message_id):
    db = _connect()
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


def _rows_as_dicts(result):
    rows = result.fetchall()
    cols = [col[0] for col in result.description] if result.description else []
    return [dict(zip(cols, row)) for row in rows]


def get_expenses(limit=None):
    db = _connect()
    try:
        if limit is None:
            sql = f"SELECT * FROM {DB_NAME} WHERE is_valid = 1 ORDER BY date DESC"
        else:
            limit = int(limit)
            if limit not in TABLE_LIMITS:
                limit = DEFAULT_LIMIT
            sql = f"SELECT * FROM {DB_NAME} WHERE is_valid = 1 ORDER BY date DESC LIMIT {limit}"
        return _rows_as_dicts(db.execute(sql))
    finally:
        db.close()


def get_kpi_rows():
    db = _connect()
    try:
        result = db.execute(
            f"""
            SELECT amount, currency, date
            FROM {DB_NAME}
            WHERE is_valid = 1
            """
        )
        return _rows_as_dicts(result)
    finally:
        db.close()


if __name__ == "__main__":
    create_db()
