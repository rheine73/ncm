import csv
from pathlib import Path

from .db import Database


HEADER = ["data_execucao", "origem", "ncm", "tipo_alteracao", "risco", "detalhe"]


def export_history_csv(db: Database, out_path: Path, limit: int = 5000) -> Path:
    rows = db.fetch_recent_historico(limit=limit)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(HEADER)
        for row in rows:
            w.writerow(row)
    return out_path


def export_history_txt(db: Database, out_path: Path, limit: int = 5000) -> Path:
    rows = db.fetch_recent_historico(limit=limit)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(";".join(HEADER) + "\n")
        for row in rows:
            f.write(";".join(str(x).replace(";", ",") for x in row) + "\n")
    return out_path


def export_history_pdf(db: Database, out_path: Path, limit: int = 200) -> Path | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return None

    rows = db.fetch_recent_historico(limit=limit)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    y = height - 30
    c.setFont("Helvetica", 8)
    c.drawString(20, y, " | ".join(HEADER))
    y -= 16
    for row in rows:
        text = " | ".join(str(v) for v in row)
        c.drawString(20, y, text[:180])
        y -= 12
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 8)
            y = height - 30
    c.save()
    return out_path

