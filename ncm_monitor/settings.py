import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    base_dir: Path
    db_path: Path
    logs_dir: Path
    snapshots_dir: Path
    tabela_ncm_path: Path
    ncms_monitoradas_path: Path
    dou_search_url: str
    dou_ato_base_url: str
    dou_terms: list[str]
    dou_max_pages: int
    http_retry_total: int
    http_retry_backoff: float
    http_timeout: int
    telegram_token: str
    telegram_chat_id: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_to: str
    enable_alerts: bool

    @classmethod
    def load(cls, base_dir: Path) -> "Settings":
        _load_dotenv(base_dir / ".env")

        def env(key: str, default: str = "") -> str:
            return os.getenv(key, default).strip()

        terms_raw = env("DOU_TERMS", "Convenio ICMS,Protocolo ICMS,Ajuste SINIEF")
        terms = [t.strip() for t in terms_raw.split(",") if t.strip()]

        return cls(
            base_dir=base_dir,
            db_path=base_dir / env("DB_NAME", "database.db"),
            logs_dir=base_dir / env("LOGS_DIR", "logs"),
            snapshots_dir=base_dir / env("SNAPSHOTS_DIR", "snapshots"),
            tabela_ncm_path=base_dir / env("NCM_ATUAL_FILE", "tabela_ncm_atual.csv"),
            ncms_monitoradas_path=base_dir / env("NCM_MONITORADAS_FILE", "ncms.csv"),
            dou_search_url=env("DOU_SEARCH_URL", "https://www.in.gov.br/consulta/-/buscar/dou"),
            dou_ato_base_url=env("DOU_ATO_BASE_URL", "https://www.in.gov.br/web/dou/-/"),
            dou_terms=terms,
            dou_max_pages=max(1, int(env("DOU_MAX_PAGES", "3"))),
            http_retry_total=max(0, int(env("HTTP_RETRY_TOTAL", "5"))),
            http_retry_backoff=float(env("HTTP_RETRY_BACKOFF", "2")),
            http_timeout=max(5, int(env("HTTP_TIMEOUT_SECONDS", "60"))),
            telegram_token=env("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env("TELEGRAM_CHAT_ID"),
            smtp_host=env("SMTP_HOST"),
            smtp_port=int(env("SMTP_PORT", "587")),
            smtp_user=env("SMTP_USER"),
            smtp_password=env("SMTP_PASSWORD"),
            smtp_from=env("SMTP_FROM"),
            smtp_to=env("SMTP_TO"),
            enable_alerts=env("ENABLE_ALERTS", "true").lower() in {"1", "true", "yes"},
        )

