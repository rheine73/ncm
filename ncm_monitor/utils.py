import hashlib
import re
from datetime import datetime


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def date_dou() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def normalize_ncm(ncm: str) -> str:
    return re.sub(r"\D", "", ncm or "")


def hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def build_ncm_pattern(ncm: str) -> re.Pattern:
    groups = [re.escape(ncm[i:i + 2]) for i in range(0, len(ncm), 2)]
    sep = r"(?:[.\-/\s])?"
    return re.compile(rf"(?<!\d){sep.join(groups)}(?!\d)")

