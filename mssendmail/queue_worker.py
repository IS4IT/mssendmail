#!/usr/bin/env python3
import os
import atexit
import signal
import json
import time
import sys
import requests
import msal
import tempfile
import logging
from pathlib import Path
from email import message_from_file
from email.policy import default
from dotenv import load_dotenv

# prefer config from /etc/mssendmail
env_paths = [
    Path("/etc/mssendmail/.env"),
    Path(__file__).resolve().parent.parent / ".env"
]
for path in env_paths:
    if path.exists():
        load_dotenv(path)
        break

LOG_DIR = Path(os.getenv("LOG_DIR"))

# Logging konfigurieren
log_path = LOG_DIR / "queue_worker.log"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Goal: Single instance - Pattern: PID-File-locking 
PID_FILE = Path("/tmp/mail_worker.pid")

def already_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)  # Nur prüfen, nicht beenden
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    return False

if already_running():
    logging.warning("Mail-Worker läuft bereits – aktueller Start wird abgebrochen.")
    sys.exit(0)

with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))
atexit.register(lambda: os.path.exists(PID_FILE) and os.remove(PID_FILE))

def cleanup(*args):
    logging.info("Stopping the worker")
    os.remove(PID_FILE)
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Script
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SENDER = os.getenv("SENDER")
CACHE_PATH = Path(tempfile.gettempdir()) / "msal_token_cache.json"
QUEUE_DIR = Path(os.getenv("QUEUE_DIR"))


def get_access_token():
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache
    )
    result = app.acquire_token_silent(["https://graph.microsoft.com/.default"], account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description"))
    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize())
    return result["access_token"]


def send_mail(token, msg):
    subject = msg.get("Subject", "")
    to = msg.get("To", "")
    content_type = "Text"
    content = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                content_type = "HTML"
                content = part.get_payload(decode=True).decode(part.get_content_charset("utf-8"))
                break
            elif part.get_content_type() == "text/plain" and not content:
                content = part.get_payload(decode=True).decode(part.get_content_charset("utf-8"))
    else:
        content = msg.get_payload(decode=True).decode(msg.get_content_charset("utf-8"))

    payload = {
        "message": {
            "subject": subject,
            "body": { "contentType": content_type, "content": content },
            "toRecipients": [ { "emailAddress": { "address": to } } ]
        }
    }

    response = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{SENDER}/sendMail",
        headers={ "Authorization": f"Bearer {token}", "Content-Type": "application/json" },
        json=payload
    )
    response.raise_for_status()


# Work is an endless loop!
def work():
    failed_cnt = 0
    while True:
        token = get_access_token()
        for mailfile in sorted(QUEUE_DIR.glob("*.eml")):
            try:
                with open(mailfile, "r", encoding="utf-8") as f:
                    msg = message_from_file(f, policy=default)
                send_mail(token, msg)
                mailfile.unlink()
                logging.info(f"Mail aus Queue gesendet: {mailfile.name}")
            except Exception as e:
                failed_cnt += 1
                logging.error(f"Fehler beim Senden {mailfile.name}: {e}")
        time.sleep(10)

if __name__ == "__main__":
    work()

