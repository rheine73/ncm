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


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    settings = Settings.load(base_dir)

    st.set_page_config(page_title="Consulta Online NCM", layout="wide")
    st.title("Consulta Online de Alteracoes de NCM")
    st.caption("Busca direta no DOU (sem usar historico do banco) em ordem decrescente de dias.")

    ncm_input = st.text_input("NCM (8 digitos, com ou sem pontuacao)", value="")
    ncm = normalize_ncm(ncm_input)

    c1, c2, c3 = st.columns(3)
    target_events = c1.number_input("Qtde de alteracoes", min_value=1, max_value=20, value=5, step=1)
    max_days = c2.number_input("Max dias retroativos", min_value=30, max_value=3650, value=3650, step=30)
    max_pages_day = c3.number_input("Max paginas por dia", min_value=1, max_value=10, value=3, step=1)

    if st.button("Consultar sites agora", use_container_width=True):
        if len(ncm) != 8:
            st.error("Informe uma NCM valida com 8 digitos.")
            return

        progress_bar = st.progress(0.0)
        progress_text = st.empty()

        def _on_progress(p: dict) -> None:
            progress_bar.progress(float(p.get("progress", 0.0)))
            if p.get("done"):
                progress_text.info(
                    f"Consulta finalizada | dias varridos: {p['days_scanned']} | "
                    f"atos analisados: {p['acts_analyzed']} | "
                    f"tempo total: {_fmt_seconds(p['elapsed_seconds'])}"
                )
                return

            progress_text.info(
                f"Varrendo dia {p['days_scanned']}/{p['max_days']} ({p['current_date']}) | "
                f"eventos {p['events_found']}/{p['target_events']} | "
                f"atos {p['acts_analyzed']} | "
                f"tempo {_fmt_seconds(p['elapsed_seconds'])} | "
                f"ETA {_fmt_seconds(p['eta_seconds'])}"
            )

        with st.spinner("Consultando DOU dia a dia (ordem decrescente)..."):
            result = buscar_alteracoes_ncm_online(
                settings=settings,
                ncm=ncm,
                target_events=int(target_events),
                max_days=int(max_days),
                max_pages_per_day=int(max_pages_day),
                progress_callback=_on_progress,
            )

        st.success(
            f"Consulta concluida. Dias varridos: {result.dias_varridos} | "
            f"Atos analisados: {result.atos_analisados} | "
            f"Tempo total: {_fmt_seconds(result.elapsed_seconds)} | "
            f"Alteracoes encontradas: {len(result.eventos)}"
        )

        if not result.eventos:
            st.warning(
                "Nenhuma alteracao encontrada nesse intervalo. "
                "Tente aumentar 'Max dias retroativos' ou revisar o codigo da NCM."
            )
            return

        df = pd.DataFrame(
            [
                {
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
                for e in result.eventos
            ]
        )
        st.subheader(f"Ultimas {len(df)} alteracoes encontradas")
        st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
