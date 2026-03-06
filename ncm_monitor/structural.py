import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .db import Database, HistoricoItem
from .utils import normalize_ncm


@dataclass
class StructuralResult:
    snapshot_path: Path
    novos: int = 0
    removidos: int = 0
    alterados: int = 0
    nao_encontrados: int = 0
    first_snapshot: bool = False


def load_monitoradas(path: Path) -> list[str]:
    out: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        next(f, None)
        for line in f:
            ncm = normalize_ncm(line.strip())
            if ncm:
                out.append(ncm)
    return out


def load_tabela(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as fh:
        first = fh.readline()
    delim = ";" if ";" in first else ","
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delim)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            ncm = normalize_ncm(row[0].strip())
            if ncm:
                out[ncm] = row[1].strip()
    return out


def filter_tabela(tabela: dict[str, str], monitoradas: list[str]) -> dict[str, str]:
    wanted = set(monitoradas)
    return {k: v for k, v in tabela.items() if k in wanted}


def save_snapshot(snapshots_dir: Path, tabela: dict[str, str]) -> Path:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    name = f"ncm_{datetime.now():%Y_%m_%d_%H%M%S_%f}.csv"
    path = snapshots_dir / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["NCM", "DESCRICAO"])
        for ncm in sorted(tabela):
            w.writerow([ncm, tabela[ncm]])
    return path


def previous_snapshot(snapshots_dir: Path) -> Path | None:
    if not snapshots_dir.exists():
        return None
    files = sorted([p for p in snapshots_dir.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])
    if len(files) < 2:
        return None
    return files[-2]


def run_structural_monitor(
    db: Database,
    tabela_path: Path,
    monitoradas_path: Path,
    snapshots_dir: Path,
) -> StructuralResult:
    monitoradas = load_monitoradas(monitoradas_path)
    tabela_atual = filter_tabela(load_tabela(tabela_path), monitoradas)
    snap = save_snapshot(snapshots_dir, tabela_atual)

    result = StructuralResult(snapshot_path=snap)
    prev_path = previous_snapshot(snapshots_dir)
    if prev_path is None:
        result.first_snapshot = True
        return result

    tabela_prev = filter_tabela(load_tabela(prev_path), monitoradas)
    for ncm in monitoradas:
        in_prev = ncm in tabela_prev
        in_now = ncm in tabela_atual

        if not in_prev and in_now:
            detalhe = f"NCM criada: {tabela_atual[ncm]}"
            if db.add_historico(HistoricoItem("RFB", ncm, "NOVA", "MEDIO", detalhe)):
                result.novos += 1
            continue

        if in_prev and not in_now:
            detalhe = f"NCM removida. Ultima descricao conhecida: {tabela_prev[ncm]}"
            if db.add_historico(HistoricoItem("RFB", ncm, "REMOVIDA", "ALTO", detalhe)):
                result.removidos += 1
            continue

        if in_prev and in_now and tabela_prev[ncm] != tabela_atual[ncm]:
            detalhe = f"Descricao alterada. Antes: {tabela_prev[ncm]} | Depois: {tabela_atual[ncm]}"
            if db.add_historico(
                HistoricoItem("RFB", ncm, "DESCRICAO_ALTERADA", "MEDIO", detalhe)
            ):
                result.alterados += 1
            continue

        if not in_now:
            if db.add_historico(
                HistoricoItem("RFB", ncm, "NAO_ENCONTRADA", "ALTO", "NCM nao consta na tabela atual")
            ):
                result.nao_encontrados += 1

    return result
