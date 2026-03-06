from pathlib import Path

import pandas as pd
import streamlit as st

from ncm_monitor.live_sites import buscar_alteracoes_ncm_online
from ncm_monitor.settings import Settings
from ncm_monitor.utils import normalize_ncm


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

        with st.spinner("Consultando DOU dia a dia (ordem decrescente)..."):
            result = buscar_alteracoes_ncm_online(
                settings=settings,
                ncm=ncm,
                target_events=int(target_events),
                max_days=int(max_days),
                max_pages_per_day=int(max_pages_day),
            )

        st.success(
            f"Consulta concluida. Dias varridos: {result.dias_varridos} | "
            f"Atos analisados: {result.atos_analisados} | "
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

