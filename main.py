from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import hashlib
import json
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

app = FastAPI()

# Load from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = list(map(int, os.getenv("CHAT_IDS", "").split(",")))
FETCH_URL = os.getenv("FETCH_URL")

DATA_FILE = "hash_store.json"


def load_hash():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return data.get("jsonHashStore")


def save_hash(hash_val):
    with open(DATA_FILE, "w") as f:
        json.dump({"jsonHashStore": hash_val}, f)


def fetch_ipo_data():
    response = requests.get(FETCH_URL)
    response.raise_for_status()
    return response.json()


def generate_message(data, changed: bool):
    sorted_data = sorted(data["content"], key=lambda x: x["category"].lower())
    if changed:
        message = (
            "🔴<b>IPO data changed!</b>🔴\n"
            'Visit <a href="https://www.cse.lk/pages/primary-issues/primary-issues.component.html">this link</a> for more info.\n\n'
        )
    else:
        message = (
            "🟢<b>IPO data has not changed</b>🟢\n"
            'Visit <a href="https://www.cse.lk/pages/primary-issues/primary-issues.component.html">this link</a> for more info.\n\n'
        )

    for ipo in sorted_data:
        if ipo["category"] == "Equity IPO":
            message += f"<b>{ipo['category']}</b> - <ins>{ipo['title']}</ins>\n"
        else:
            message += f"{ipo['category']} - {ipo['title']}\n"

    return message


def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()


def ipo_check_job():
    try:
        ipo_data = fetch_ipo_data()
        json_string = json.dumps(ipo_data, sort_keys=True)
        current_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()

        previous_hash = load_hash()
        changed = current_hash != previous_hash

        message = generate_message(ipo_data, changed)

        for chat_id in CHAT_IDS:
            send_telegram_message(chat_id, message)

        if changed:
            save_hash(current_hash)

        print("IPO check completed.")

    except Exception as e:
        print(f"Error during IPO check: {e}")


# Scheduler to run job daily at specific time
# scheduler = BackgroundScheduler()
# scheduler.add_job(ipo_check_job, "cron", hour=7, minute=0)  # Run daily at 7:00 AM
# scheduler.start()


@app.get("/")
def read_root():
    return {"message": "IPO Monitor Running"}

@app.get("/run-check")
def run_check():
    ipo_check_job()
    return {"status": "Job manually triggered"}

