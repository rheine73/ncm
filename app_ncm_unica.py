import os
import re
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from ncm_monitor.live_sites import buscar_alteracoes_ncm_online
from ncm_monitor.settings import Settings
from ncm_monitor.utils import normalize_ncm


def _fmt_seconds(seconds: float) -> str:
    total = max(int(seconds), 0)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _parse_ncms(raw: str) -> tuple[list[str], list[str]]:
    tokens = [t.strip() for t in re.split(r"[,;\n]+", raw or "") if t.strip()]
    valid: list[str] = []
    invalid: list[str] = []

    for t in tokens:
        n = normalize_ncm(t)
        if len(n) == 8:
            if n not in valid:
                valid.append(n)
        else:
            invalid.append(t)

    return valid, invalid


def _read_app_version(base_dir: Path) -> str:
    env_version = os.getenv("APP_VERSION", "").strip()
    if env_version:
        return env_version

    version_file = base_dir / "VERSION"
    if version_file.exists():
        content = version_file.read_text(encoding="utf-8").strip()
        if content:
            return content

    return "dev"


def _read_app_revision(base_dir: Path) -> str:
    for var in ("GITHUB_SHA", "GIT_COMMIT", "COMMIT_SHA"):
        value = os.getenv(var, "").strip()
        if value:
            return value[:7]

    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(base_dir),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        if output:
            return output
    except Exception:
        pass

    return "local"


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    settings = Settings.load(base_dir)
    app_version = _read_app_version(base_dir)
    app_revision = _read_app_revision(base_dir)

    st.set_page_config(page_title="Consulta Online NCM", layout="wide")
    st.title("Consulta Online de Alteracoes de NCM")
    st.caption("Busca direta no DOU (sem usar historico do banco) em ordem decrescente de dias.")
    st.caption(f"Build: versao `{app_version}` | revisao `{app_revision}`")
    st.sidebar.caption(f"Build: {app_version} ({app_revision})")

    ncm_input = st.text_input(
        "NCMs (8 digitos, separadas por virgula; ex.: 65061000, 40115000)",
        value="",
    )
    ncms, invalid_ncms = _parse_ncms(ncm_input)

    c1, c2, c3 = st.columns(3)
    target_events = c1.number_input("Qtde de alteracoes", min_value=1, max_value=20, value=5, step=1)
    max_days = c2.number_input("Max dias retroativos", min_value=30, max_value=3650, value=3650, step=30)
    max_pages_day = c3.number_input("Max paginas por dia", min_value=1, max_value=10, value=3, step=1)

    if st.button("Consultar sites agora", use_container_width=True):
        if not ncms:
            st.error("Informe pelo menos uma NCM valida (8 digitos).")
            return
        if invalid_ncms:
            st.warning(f"NCM(s) ignorada(s): {', '.join(invalid_ncms)}")

        progress_bar = st.progress(0.0)
        progress_text = st.empty()
        all_events = []
        total_days = 0
        total_acts = 0
        total_elapsed = 0.0
        total_ncms = len(ncms)

        with st.spinner("Consultando DOU dia a dia (ordem decrescente)..."):
            for idx, ncm in enumerate(ncms):
                def _on_progress(p: dict, current_idx: int = idx, current_ncm: str = ncm) -> None:
                    ncm_progress = float(p.get("progress", 0.0))
                    global_progress = (current_idx + ncm_progress) / total_ncms
                    progress_bar.progress(min(max(global_progress, 0.0), 1.0))

                    if p.get("done"):
                        progress_text.info(
                            f"NCM {current_ncm}: finalizada | dias {p['days_scanned']} | "
                            f"atos {p['acts_analyzed']} | tempo {_fmt_seconds(p['elapsed_seconds'])}"
                        )
                        return

                    progress_text.info(
                        f"NCM {current_ncm} | dia {p['days_scanned']}/{p['max_days']} ({p['current_date']}) | "
                        f"eventos {p['events_found']}/{p['target_events']} | "
                        f"atos {p['acts_analyzed']} | "
                        f"tempo {_fmt_seconds(p['elapsed_seconds'])} | "
                        f"ETA {_fmt_seconds(p['eta_seconds'])}"
                    )

                try:
                    result = buscar_alteracoes_ncm_online(
                        settings=settings,
                        ncm=ncm,
                        target_events=int(target_events),
                        max_days=int(max_days),
                        max_pages_per_day=int(max_pages_day),
                        progress_callback=_on_progress,
                    )
                except TypeError as exc:
                    # Compatibilidade com runtime antigo sem suporte a progress_callback.
                    if "progress_callback" not in str(exc):
                        raise
                    progress_text.warning(
                        f"NCM {ncm}: runtime sem suporte a barra em tempo real; executando em modo compatibilidade."
                    )
                    result = buscar_alteracoes_ncm_online(
                        settings=settings,
                        ncm=ncm,
                        target_events=int(target_events),
                        max_days=int(max_days),
                        max_pages_per_day=int(max_pages_day),
                    )
                    progress_bar.progress((idx + 1) / total_ncms)

                total_days += result.dias_varridos
                total_acts += result.atos_analisados
                total_elapsed += result.elapsed_seconds

                for e in result.eventos:
                    all_events.append(
                        {
                            "NCM consultada": ncm,
                            "Data": e.data_publicacao,
                            "Fonte": e.fonte,
                            "Tipo": e.tipo_alteracao,
                            "Titulo": e.titulo,
                            "Resumo objetivo": e.resumo_objetivo,
                            "Acao recomendada": e.acao_recomendada,
                            "NCMs relacionadas": ", ".join(e.ncms_relacionadas) if e.ncms_relacionadas else "",
                            "O que alterou": e.detalhe,
                            "URL": e.url,
                        }
                    )

            progress_bar.progress(1.0)

        st.success(
            f"Consulta concluida para {total_ncms} NCM(s). Dias varridos: {total_days} | "
            f"Atos analisados: {total_acts} | Tempo total: {_fmt_seconds(total_elapsed)} | "
            f"Alteracoes encontradas: {len(all_events)}"
        )

        if not all_events:
            st.warning(
                "Nenhuma alteracao encontrada nesse intervalo. "
                "Tente aumentar 'Max dias retroativos' ou revisar os codigos de NCM."
            )
            return

        df = pd.DataFrame(all_events)
        try:
            df["_ord_data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
            df = df.sort_values(by=["NCM consultada", "_ord_data"], ascending=[True, False]).drop(columns=["_ord_data"])
        except Exception:
            pass

        st.subheader(f"Alteracoes encontradas ({len(df)} registros)")
        st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
