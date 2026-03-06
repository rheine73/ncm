from pathlib import Path

import pandas as pd
import streamlit as st

from ncm_monitor.db import Database
from ncm_monitor.reports import export_history_csv, export_history_pdf, export_history_txt
from ncm_monitor.settings import Settings


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    settings = Settings.load(base_dir)
    db = Database(settings.db_path)
    db.init_schema()

    st.set_page_config(page_title="Monitor Fiscal NCM", layout="wide")
    st.title("Monitor Fiscal NCM")

    rows = db.fetch_recent_historico(limit=5000)
    df = pd.DataFrame(rows, columns=["data_execucao", "origem", "ncm", "tipo_alteracao", "risco", "detalhe"])

    if df.empty:
        st.info("Nenhum evento no historico.")
        return

    c1, c2, c3 = st.columns(3)
    origens = c1.multiselect("Origem", sorted(df["origem"].dropna().unique()), default=sorted(df["origem"].dropna().unique()))
    tipos = c2.multiselect(
        "Tipo alteracao",
        sorted(df["tipo_alteracao"].dropna().unique()),
        default=sorted(df["tipo_alteracao"].dropna().unique()),
    )
    riscos = c3.multiselect("Risco", sorted(df["risco"].dropna().unique()), default=sorted(df["risco"].dropna().unique()))

    ncm_filter = st.text_input("Filtrar NCM")

    f = df[df["origem"].isin(origens) & df["tipo_alteracao"].isin(tipos) & df["risco"].isin(riscos)]
    if ncm_filter.strip():
        f = f[f["ncm"].astype(str).str.contains(ncm_filter.strip(), regex=False)]

    st.metric("Eventos filtrados", len(f))
    st.dataframe(f, use_container_width=True, hide_index=True)

    out_dir = base_dir / "exports"
    out_dir.mkdir(exist_ok=True)

    csv_path = export_history_csv(db, out_dir / "historico_alteracoes.csv", limit=5000)
    txt_path = export_history_txt(db, out_dir / "historico_alteracoes.txt", limit=5000)
    pdf_path = export_history_pdf(db, out_dir / "historico_alteracoes.pdf", limit=300)

    st.download_button("Baixar CSV", data=csv_path.read_bytes(), file_name=csv_path.name, mime="text/csv")
    st.download_button("Baixar TXT", data=txt_path.read_bytes(), file_name=txt_path.name, mime="text/plain")
    if pdf_path and pdf_path.exists():
        st.download_button("Baixar PDF", data=pdf_path.read_bytes(), file_name=pdf_path.name, mime="application/pdf")
    else:
        st.caption("PDF indisponivel: instale reportlab para habilitar exportacao PDF.")


if __name__ == "__main__":
    main()

