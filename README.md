# Tracker de gastos por IMAP

Script local que lee un inbox de Gmail, usa Claude para detectar si un mail es un gasto, y guarda concepto, monto, moneda y fecha en TursoDB.

Si el `message_id` ya existe, lo salta entonces Claude no procesa nunca dos veces el mismo email, ni se guarda un duplicado. No tiene UI (aún, proximamente si).

## Setup

```bash
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Llenar `.env` con Turso, Anthropic y el Gmail (app password).

```bash
python db.py
python app.py
```

## Proximos pasos

Dashboard web para ver y filtrar gastos, y poder desplegarlo como web app personal.
