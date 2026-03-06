import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from time import monotonic
from typing import Callable

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .settings import Settings
from .utils import build_ncm_pattern, normalize_ncm


def _session(settings: Settings) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=settings.http_retry_total,
        connect=settings.http_retry_total,
        read=settings.http_retry_total,
        backoff_factor=settings.http_retry_backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _extract_total_pages(html: str) -> int:
    m = re.search(r"totalPages\s*:\s*(\d+)", html)
    return max(1, int(m.group(1))) if m else 1


def _extract_atos(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"id": "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"})
    if not script:
        return []
    try:
        payload = json.loads(script.get_text(strip=True))
    except (ValueError, TypeError):
        return []
    arr = payload.get("jsonArray", [])
    return arr if isinstance(arr, list) else []


def _build_ato_url(base_url: str, url_title: str) -> str:
    return f"{base_url.rstrip('/')}/{url_title.lstrip('/')}"


def _format_ncm(ncm: str) -> str:
    n = normalize_ncm(ncm)
    if len(n) != 8:
        return n
    return f"{n[:4]}.{n[4:6]}.{n[6:]}"


def _ncm_variants(ncm: str) -> list[str]:
    n = normalize_ncm(ncm)
    if len(n) != 8:
        return [n]
    v1 = f"{n[:4]}.{n[4:6]}.{n[6:]}"
    return [n, v1]


def _normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def _extract_ncm_codes(text: str) -> list[str]:
    found: set[str] = set()

    for m in re.finditer(r"(?<!\d)(\d{4}\.\d{2}\.\d{2})(?!\d)", text):
        n = normalize_ncm(m.group(1))
        if len(n) == 8:
            found.add(n)

    for m in re.finditer(r"(?<!\d)(\d{2}\.\d{2}\.\d{2}\.\d{2})(?!\d)", text):
        n = normalize_ncm(m.group(1))
        if len(n) == 8:
            found.add(n)

    for m in re.finditer(r"(?i)\bncm\b[\s:\-]*(\d{8})\b", text):
        n = normalize_ncm(m.group(1))
        if len(n) == 8:
            found.add(n)

    return sorted(found)


def _extract_effective_date(plain_text: str) -> str | None:
    m = re.search(
        r"(a partir de|desde|vigencia em)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        plain_text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    return m.group(2).replace("-", "/")


def _extract_regulatory_notes(plain_text: str) -> list[str]:
    notes: list[str] = []
    if "licenciamento" in plain_text:
        if "ministerio da defesa" in plain_text:
            notes.append("Pode haver licenciamento do Ministerio da Defesa.")
        else:
            notes.append("Pode haver exigencia de licenciamento especifico.")
    if "importacao" in plain_text or "exportacao" in plain_text:
        notes.append("Revise requisitos administrativos de importacao/exportacao.")
    if "aliquota" in plain_text:
        if "sem alter" in plain_text or "nao houve" in plain_text or "mantid" in plain_text:
            notes.append("O ato sugere manutencao de aliquota (sem mudanca automatica).")
        else:
            notes.append("Revise possiveis impactos de aliquota.")
    return notes


def _build_objective_impact(
    target_ncm: str,
    tipo: str,
    full_text: str,
) -> tuple[str, str, list[str]]:
    plain = _normalize_text(full_text)
    target = normalize_ncm(target_ncm)
    target_fmt = _format_ncm(target)

    all_codes = _extract_ncm_codes(full_text)
    related = [c for c in all_codes if c != target and c[:6] == target[:6]]
    if not related:
        related = [c for c in all_codes if c != target and c[:4] == target[:4]]
    related = sorted(set(related))
    related_fmt = ", ".join(_format_ncm(c) for c in related)

    split_markers = [
        "desdobr",
        "desmembr",
        "deixa de existir",
        "extint",
        "substitu",
        "passa a ser",
    ]
    split_detected = bool(related) and any(marker in plain for marker in split_markers)
    effective_date = _extract_effective_date(plain)

    if split_detected:
        resumo = f"NCM {target_fmt} foi desdobrada/substituida em: {related_fmt}."
        if effective_date:
            resumo += f" Vigencia a partir de {effective_date}."
        acao = (
            f"Nao use mais a NCM {target_fmt} em novas operacoes. "
            f"Passe a classificar/vender nas NCMs: {related_fmt}."
        )
    elif tipo == "REVOGACAO":
        resumo = f"Regra vinculada a NCM {target_fmt} foi revogada."
        acao = "Revalidar imediatamente a classificacao fiscal e beneficios vinculados."
    elif tipo == "INCLUSAO":
        resumo = f"Houve inclusao normativa para a NCM {target_fmt}."
        acao = "Revisar exigencias novas e atualizar cadastro/regras fiscais."
    elif tipo == "EXCLUSAO":
        resumo = f"Houve exclusao normativa para a NCM {target_fmt}."
        acao = "Validar codigo substituto e interromper uso da regra excluida."
    elif tipo == "PRORROGACAO":
        resumo = f"Houve prorrogacao de regra/prazo para a NCM {target_fmt}."
        acao = "Atualizar vigencias internas e validar continuidade de tratamento."
    else:
        resumo = f"Houve alteracao normativa envolvendo a NCM {target_fmt}."
        acao = "Revisar o ato e atualizar classificacao/regra fiscal aplicavel."

    notes = _extract_regulatory_notes(plain)
    if notes:
        resumo = f"{resumo} " + " ".join(notes)

    return resumo, acao, related


def _find_change_type(text: str) -> tuple[str | None, str]:
    plain = _normalize_text(text)
    rules = [
        ("REVOGACAO", [r"\brevog\w*"]),
        ("ALTERACAO", [r"\balter\w*"]),
        ("INCLUSAO", [r"\binclu\w*", r"\bacrescent\w*"]),
        ("EXCLUSAO", [r"\bexclu\w*", r"\bretir\w*"]),
        ("PRORROGACAO", [r"\bprorrog\w*"]),
    ]
    for tipo, patterns in rules:
        for p in patterns:
            m = re.search(p, plain, flags=re.IGNORECASE)
            if m:
                start = max(0, m.start() - 120)
                end = min(len(text), m.end() + 120)
                snippet = (text[start:end] or "").replace("\n", " ").strip()
                return tipo, snippet
    return None, ""


def _fetch_first_page(
    session: requests.Session,
    settings: Settings,
    query: str,
    day_str: str,
) -> str:
    params = {
        "q": query,
        "s": "todos",
        "exactDate": "personalizado",
        "publishFrom": day_str,
        "publishTo": day_str,
        "sortType": "0",
        "delta": "20",
    }
    r = session.get(
        settings.dou_search_url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=settings.http_timeout,
    )
    r.raise_for_status()
    return r.text


def _fetch_next_page(
    session: requests.Session,
    settings: Settings,
    query: str,
    day_str: str,
    current_page: int,
    next_page: int,
    pivot_item: dict,
) -> str:
    params = {
        "q": query,
        "s": "todos",
        "exactDate": "personalizado",
        "publishFrom": day_str,
        "publishTo": day_str,
        "sortType": "0",
        "delta": "20",
        "currentPage": str(current_page),
        "newPage": str(next_page),
        "score": str(pivot_item.get("score", 0)),
        "id": str(pivot_item.get("classPK", "")),
        "displayDate": str(pivot_item.get("displayDateSortable", "")),
    }
    r = session.get(
        settings.dou_search_url,
        params=params,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=settings.http_timeout,
    )
    r.raise_for_status()
    return r.text


@dataclass
class LiveEvent:
    data_publicacao: str
    fonte: str
    tipo_alteracao: str
    titulo: str
    detalhe: str
    resumo_objetivo: str
    acao_recomendada: str
    ncms_relacionadas: list[str]
    url: str


@dataclass
class LiveScanResult:
    eventos: list[LiveEvent]
    dias_varridos: int
    atos_analisados: int
    elapsed_seconds: float


def buscar_alteracoes_ncm_online(
    settings: Settings,
    ncm: str,
    target_events: int = 5,
    max_days: int = 3650,
    max_pages_per_day: int = 3,
    progress_callback: Callable[[dict], None] | None = None,
) -> LiveScanResult:
    ncm_norm = normalize_ncm(ncm)
    if len(ncm_norm) != 8:
        return LiveScanResult(eventos=[], dias_varridos=0, atos_analisados=0, elapsed_seconds=0.0)

    session = _session(settings)
    ncm_pattern = build_ncm_pattern(ncm_norm)
    queries = _ncm_variants(ncm_norm)

    eventos: list[LiveEvent] = []
    seen_urls: set[str] = set()
    atos_analisados = 0
    dias_varridos = 0
    started = monotonic()

    for offset in range(max_days):
        day = date.today() - timedelta(days=offset)
        day_str = day.strftime("%d/%m/%Y")
        dias_varridos += 1

        if len(eventos) >= target_events:
            break

        day_candidates: dict[str, dict] = {}
        for query in queries:
            try:
                first_html = _fetch_first_page(session, settings, query, day_str)
            except Exception:
                continue

            total_pages = min(_extract_total_pages(first_html), max_pages_per_day)
            page_html = first_html
            items = _extract_atos(page_html)

            for page in range(1, total_pages + 1):
                if page > 1:
                    if not items:
                        break
                    pivot = items[-1]
                    try:
                        page_html = _fetch_next_page(session, settings, query, day_str, page - 1, page, pivot)
                    except Exception:
                        break
                    items = _extract_atos(page_html)

                if not items:
                    break
                for ato in items:
                    url_title = (ato.get("urlTitle") or "").strip()
                    if not url_title:
                        continue
                    url = _build_ato_url(settings.dou_ato_base_url, url_title)
                    if url not in day_candidates:
                        day_candidates[url] = ato

        for url, ato in day_candidates.items():
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                r = session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    timeout=settings.http_timeout,
                )
                r.raise_for_status()
            except Exception:
                continue

            text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
            atos_analisados += 1

            if not ncm_pattern.search(text):
                continue

            tipo, detalhe = _find_change_type(text)
            if not tipo:
                continue

            resumo_objetivo, acao_recomendada, ncms_relacionadas = _build_objective_impact(
                target_ncm=ncm_norm,
                tipo=tipo,
                full_text=text,
            )

            eventos.append(
                LiveEvent(
                    data_publicacao=(ato.get("pubDate") or day_str),
                    fonte="DOU",
                    tipo_alteracao=tipo,
                    titulo=(ato.get("title") or "").strip(),
                    detalhe=detalhe or "Termo de alteracao identificado no texto do ato.",
                    resumo_objetivo=resumo_objetivo,
                    acao_recomendada=acao_recomendada,
                    ncms_relacionadas=ncms_relacionadas,
                    url=url,
                )
            )

            if len(eventos) >= target_events:
                break

        if len(eventos) >= target_events:
            break

        if progress_callback:
            elapsed = monotonic() - started
            avg_day = elapsed / dias_varridos if dias_varridos else 0.0
            eta_limit = avg_day * max(max_days - dias_varridos, 0)

            eta_target = None
            if len(eventos) > 0:
                events_per_day = len(eventos) / dias_varridos
                remaining_events = max(target_events - len(eventos), 0)
                if events_per_day > 0:
                    eta_target = avg_day * (remaining_events / events_per_day)

            eta_candidates = [eta_limit]
            if eta_target is not None:
                eta_candidates.append(eta_target)
            eta_seconds = min(eta_candidates) if eta_candidates else 0.0

            progress_callback(
                {
                    "progress": min(dias_varridos / max_days, 1.0),
                    "days_scanned": dias_varridos,
                    "max_days": max_days,
                    "current_date": day_str,
                    "events_found": len(eventos),
                    "target_events": target_events,
                    "acts_analyzed": atos_analisados,
                    "elapsed_seconds": elapsed,
                    "eta_seconds": max(eta_seconds, 0.0),
                    "done": False,
                }
            )

    eventos.sort(key=lambda e: e.data_publicacao, reverse=True)
    elapsed = monotonic() - started
    if progress_callback:
        progress_callback(
            {
                "progress": 1.0,
                "days_scanned": dias_varridos,
                "max_days": max_days,
                "current_date": None,
                "events_found": len(eventos[:target_events]),
                "target_events": target_events,
                "acts_analyzed": atos_analisados,
                "elapsed_seconds": elapsed,
                "eta_seconds": 0.0,
                "done": True,
            }
        )

    return LiveScanResult(
        eventos=eventos[:target_events],
        dias_varridos=dias_varridos,
        atos_analisados=atos_analisados,
        elapsed_seconds=elapsed,
    )
