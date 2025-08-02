#!/usr/bin/env python3
import sys
import os
import logging
from email import message_from_file
from email.policy import default
from uuid import uuid4
from dotenv import load_dotenv
from pathlib import Path

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
log_path = LOG_DIR / "queue_writer.log"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

QUEUE_DIR = Path(os.getenv("QUEUE_DIR"))
QUEUE_DIR.mkdir(exist_ok=True)

def save_to_queue(msg):
    msg_id = uuid4().hex
    queue_file = QUEUE_DIR / f"{msg_id}.eml"
    with open(queue_file, "w", encoding="utf-8") as f:
        f.write(msg.as_string())
    logging.info(f"Saved to queue To: {msg.get('To', '')} - {queue_file}")

def main():
    msg = message_from_file(sys.stdin, policy=default)
    save_to_queue(msg)

if __name__ == "__main__":
    main()

