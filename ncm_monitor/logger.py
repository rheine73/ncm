import json
import logging
from datetime import datetime
from pathlib import Path


def build_logger(logs_dir: Path) -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ncm_monitor")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    text_log_path = logs_dir / f"log_{datetime.now():%Y-%m-%d}.txt"
    text_handler = logging.FileHandler(text_log_path, encoding="utf-8")
    text_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(text_handler)
    logger.addHandler(console_handler)
    return logger


def append_json_event(logs_dir: Path, payload: dict) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    json_log_path = logs_dir / f"log_{datetime.now():%Y-%m-%d}.jsonl"
    with json_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

