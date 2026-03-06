import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ncm_monitor.settings import Settings
from ncm_monitor.utils import normalize_ncm


def carregar_tabela(path: Path) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        first = f.readline()
    delim = ";" if ";" in first else ","

    out: dict[str, tuple[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        r = csv.reader(f, delimiter=delim)
        next(r, None)
        for row in r:
            if len(row) < 2:
                continue
            raw = row[0].strip()
            n = normalize_ncm(raw)
            if n:
                out[n] = (raw, row[1].strip())
    return out


def consultar_historico(db_path: Path, ncm: str) -> list[tuple]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_execucao, origem, tipo_alteracao, risco, detalhe
        FROM historico_alteracoes
        WHERE ncm=?
        ORDER BY data_execucao DESC
        """,
        (ncm,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def consultar_snapshots(snapshots_dir: Path, ncm: str) -> list[tuple[str, str]]:
    if not snapshots_dir.exists():
        return []
    hits: list[tuple[str, str]] = []
    for p in sorted([x for x in snapshots_dir.glob("*.csv") if x.is_file()]):
        tabela = carregar_tabela(p)
        if ncm in tabela:
            _, desc = tabela[ncm]
            hits.append((p.name, desc))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Consulta historico e presenca de uma NCM.")
    parser.add_argument("ncm", help="NCM a consultar, com ou sem pontuacao.")
    args = parser.parse_args()

    settings = Settings.load(BASE_DIR)
    ncm = normalize_ncm(args.ncm)

    print(f"NCM consultada: {ncm}")

    historico = consultar_historico(settings.db_path, ncm)
    if not historico:
        print("Historico: sem registros.")
    else:
        print(f"Historico: {len(historico)} registro(s).")
        print(f"Ultima alteracao: {historico[0][0]} | {historico[0][1]} | {historico[0][2]} | {historico[0][4]}")
        print("Ultimos 10:")
        for row in historico[:10]:
            print(f"  - {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")

    tabela = carregar_tabela(settings.tabela_ncm_path)
    if ncm in tabela:
        raw, desc = tabela[ncm]
        print(f"Tabela atual: PRESENTE | codigo_raw={raw} | descricao={desc}")
    else:
        print("Tabela atual: NAO ENCONTRADA")

    snaps = consultar_snapshots(settings.snapshots_dir, ncm)
    if not snaps:
        print("Snapshots: nenhuma ocorrencia.")
    else:
        first = snaps[0]
        last = snaps[-1]
        print(f"Snapshots com a NCM: {len(snaps)}")
        print(f"Primeiro snapshot: {first[0]} | {first[1]}")
        print(f"Ultimo snapshot: {last[0]} | {last[1]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
