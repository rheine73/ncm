import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import Database, HistoricoItem
from .settings import Settings
from .structural import load_monitoradas
from .utils import build_ncm_pattern


def _session(settings: Settings) -> requests.Session:
    session = requests.Session()
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
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _extract_total_resultados(html: str) -> int | None:
    m = re.search(r"([0-9][0-9\.,]*)\s+resultado[s]?\s+para", html, flags=re.IGNORECASE)
    if not m:
        return None
    txt = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(txt)
    except ValueError:
        return None


def _extract_total_pages(html: str) -> int:
    m = re.search(r"totalPages\s*:\s*(\d+)", html)
    if not m:
        return 1
    return max(1, int(m.group(1)))


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


@dataclass
class TermStat:
    termo: str
    resultados: int | None = None
    total_pages: int = 1
    atos_coletados: int = 0


@dataclass
class DOUResult:
    novos_atos: int = 0
    novos_eventos: int = 0
    termos: list[TermStat] = field(default_factory=list)
    mensagens_alerta: list[str] = field(default_factory=list)


def _fetch_first_page(
    session: requests.Session,
    settings: Settings,
    termo: str,
    data_ref: str,
) -> tuple[str, str]:
    params = {
        "q": termo,
        "s": "todos",
        "exactDate": "personalizado",
        "publishFrom": data_ref,
        "publishTo": data_ref,
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
    return r.text, r.url


def _fetch_next_page(
    session: requests.Session,
    settings: Settings,
    termo: str,
    data_ref: str,
    current_page: int,
    next_page: int,
    pivot_item: dict,
) -> str:
    params = {
        "q": termo,
        "s": "todos",
        "exactDate": "personalizado",
        "publishFrom": data_ref,
        "publishTo": data_ref,
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


def run_dou_monitor(settings: Settings, db: Database, data_ref: str) -> DOUResult:
    session = _session(settings)
    monitoradas = load_monitoradas(settings.ncms_monitoradas_path)
    patterns = {ncm: build_ncm_pattern(ncm) for ncm in monitoradas}

    result = DOUResult()
    seen_urls: set[str] = set()

    for termo in settings.dou_terms:
        stat = TermStat(termo=termo)
        try:
            first_html, _ = _fetch_first_page(session, settings, termo, data_ref)
        except Exception:
            result.termos.append(stat)
            continue

        stat.resultados = _extract_total_resultados(first_html)
        total_pages = _extract_total_pages(first_html)
        stat.total_pages = min(total_pages, settings.dou_max_pages)

        page_html = first_html
        page_items = _extract_atos(page_html)

        all_items: list[dict] = []
        for page in range(1, stat.total_pages + 1):
            if page > 1:
                if not page_items:
                    break
                pivot = page_items[-1]
                try:
                    page_html = _fetch_next_page(session, settings, termo, data_ref, page - 1, page, pivot)
                except Exception:
                    break
                page_items = _extract_atos(page_html)

            if not page_items:
                break

            all_items.extend(page_items)

        stat.atos_coletados = len(all_items)
        result.termos.append(stat)

        for ato in all_items:
            url_title = (ato.get("urlTitle") or "").strip()
            if not url_title:
                continue
            url = _build_ato_url(settings.dou_ato_base_url, url_title)
            if url in seen_urls or db.ato_processado(url):
                continue
            seen_urls.add(url)

            try:
                ato_response = session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    timeout=settings.http_timeout,
                )
                ato_response.raise_for_status()
            except Exception:
                continue

            text = BeautifulSoup(ato_response.text, "html.parser").get_text(" ", strip=True)
            matched = [ncm for ncm, pattern in patterns.items() if pattern.search(text)]

            db.save_ato_processado(
                url=url,
                url_title=url_title,
                titulo=(ato.get("title") or "").strip(),
                data_publicacao=(ato.get("pubDate") or "").strip(),
                termo_origem=termo,
                possui_ncm=bool(matched),
            )
            result.novos_atos += 1

            for ncm in matched:
                detalhe = f"Ato DOU ({termo}) {url}"
                if db.add_historico(
                    HistoricoItem("DOU", ncm, "PUBLICACAO_DOU", "ALTO", detalhe),
                    dedupe_daily=False,
                ):
                    msg = f"[ALERTA] DOU NCM {ncm} termo={termo} url={url}"
                    result.mensagens_alerta.append(msg)
                    result.novos_eventos += 1

    return result

