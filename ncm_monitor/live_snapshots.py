import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import normalize_ncm


@dataclass
class LiveSnapshotDiff:
    first_snapshot: bool
    new_events: list[dict[str, Any]]
    removed_events: list[dict[str, Any]]
    unchanged_count: int
    previous_count: int
    current_count: int
    latest_path: Path
    archive_path: Path


def _event_key(event: dict[str, Any]) -> str:
    url = str(event.get("url") or event.get("URL") or "").strip()
    if url:
        return url

    data = str(event.get("data_publicacao") or event.get("Data") or "").strip()
    tipo = str(event.get("tipo_alteracao") or event.get("Tipo") or "").strip()
    titulo = str(event.get("titulo") or event.get("Titulo") or "").strip()
    return f"{data}|{tipo}|{titulo}"


def _normalize_related_codes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "key": _event_key(event),
        "data_publicacao": str(event.get("data_publicacao") or event.get("Data") or "").strip(),
        "tipo_alteracao": str(event.get("tipo_alteracao") or event.get("Tipo") or "").strip(),
        "titulo": str(event.get("titulo") or event.get("Titulo") or "").strip(),
        "url": str(event.get("url") or event.get("URL") or "").strip(),
        "detalhe": str(event.get("detalhe") or event.get("O que alterou") or "").strip(),
        "resumo_objetivo": str(event.get("resumo_objetivo") or event.get("Resumo objetivo") or "").strip(),
        "acao_recomendada": str(event.get("acao_recomendada") or event.get("Acao recomendada") or "").strip(),
        "impacto_importacao": str(event.get("impacto_importacao") or event.get("Impacto importacao") or "").strip(),
        "acao_importacao": str(event.get("acao_importacao") or event.get("Acao importacao") or "").strip(),
        "ncms_relacionadas": _normalize_related_codes(
            event.get("ncms_relacionadas") or event.get("NCMs relacionadas") or []
        ),
    }
    return normalized


def _read_previous_events(latest_path: Path) -> list[dict[str, Any]]:
    if not latest_path.exists():
        return []
    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    events = payload.get("events", [])
    if not isinstance(events, list):
        return []
    normalized: list[dict[str, Any]] = []
    for event in events:
        if isinstance(event, dict):
            normalized.append(_normalize_event(event))
    return normalized


def _write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compare_and_save_live_snapshot(
    snapshots_dir: Path,
    ncm: str,
    events: list[dict[str, Any]],
) -> LiveSnapshotDiff:
    ncm_norm = normalize_ncm(ncm)
    live_dir = snapshots_dir / "live_ncm"
    latest_path = live_dir / f"{ncm_norm}_latest.json"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = live_dir / f"{ncm_norm}_{stamp}.json"

    current_events_raw = [_normalize_event(e) for e in events if isinstance(e, dict)]
    current_by_key: dict[str, dict[str, Any]] = {}
    current_events: list[dict[str, Any]] = []
    for event in current_events_raw:
        key = event.get("key", "")
        if not key or key in current_by_key:
            continue
        current_by_key[key] = event
        current_events.append(event)

    had_previous_file = latest_path.exists()
    previous_events = _read_previous_events(latest_path)
    previous_by_key = {e.get("key", ""): e for e in previous_events if e.get("key")}

    current_keys = set(current_by_key)
    previous_keys = set(previous_by_key)

    new_keys = current_keys - previous_keys
    removed_keys = previous_keys - current_keys
    unchanged_count = len(current_keys & previous_keys)

    new_events = [event for event in current_events if event.get("key") in new_keys]
    removed_events = [event for event in previous_events if event.get("key") in removed_keys]

    generated_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "ncm": ncm_norm,
        "generated_at": generated_at,
        "total_events": len(current_events),
        "events": current_events,
    }

    _write_snapshot(archive_path, payload)
    _write_snapshot(latest_path, payload)

    return LiveSnapshotDiff(
        first_snapshot=not had_previous_file,
        new_events=new_events,
        removed_events=removed_events,
        unchanged_count=unchanged_count,
        previous_count=len(previous_events),
        current_count=len(current_events),
        latest_path=latest_path,
        archive_path=archive_path,
    )
