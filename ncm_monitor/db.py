import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .utils import now_str


@dataclass
class HistoricoItem:
    origem: str
    ncm: str
    tipo_alteracao: str
    risco: str
    detalhe: str


class Database:
    def __init__(self, path: Path):
        self.path = path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def init_schema(self) -> None:
        conn = self._conn()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_alteracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_execucao TEXT,
                origem TEXT,
                ncm TEXT,
                tipo_alteracao TEXT,
                risco TEXT,
                detalhe TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dou_hash (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dou_atos_processados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_execucao TEXT,
                url TEXT UNIQUE,
                url_title TEXT,
                titulo TEXT,
                data_publicacao TEXT,
                termo_origem TEXT,
                possui_ncm INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS execucoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inicio TEXT,
                fim TEXT,
                status TEXT,
                resumo TEXT
            )
            """
        )

        self._ensure_col(cur, "historico_alteracoes", "origem", "TEXT")
        self._ensure_col(cur, "historico_alteracoes", "detalhe", "TEXT")

        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_col(cur: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
        cur.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in cur.fetchall()}
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def add_historico(self, item: HistoricoItem, dedupe_daily: bool = True) -> bool:
        conn = self._conn()
        cur = conn.cursor()
        if dedupe_daily:
            cur.execute(
                """
                SELECT id FROM historico_alteracoes
                WHERE date(data_execucao)=date('now','localtime')
                  AND origem=? AND ncm=? AND tipo_alteracao=? AND detalhe=?
                LIMIT 1
                """,
                (item.origem, item.ncm, item.tipo_alteracao, item.detalhe),
            )
            if cur.fetchone():
                conn.close()
                return False

        cur.execute(
            """
            INSERT INTO historico_alteracoes
            (data_execucao, origem, ncm, tipo_alteracao, risco, detalhe)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_str(), item.origem, item.ncm, item.tipo_alteracao, item.risco, item.detalhe),
        )
        conn.commit()
        conn.close()
        return True

    def has_dou_hash(self, hash_value: str) -> bool:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM dou_hash WHERE hash=?", (hash_value,))
        ok = cur.fetchone() is not None
        conn.close()
        return ok

    def save_dou_hash(self, hash_value: str) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO dou_hash (hash) VALUES (?)", (hash_value,))
        conn.commit()
        conn.close()

    def ato_processado(self, url: str) -> bool:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM dou_atos_processados WHERE url=?", (url,))
        ok = cur.fetchone() is not None
        conn.close()
        return ok

    def save_ato_processado(
        self,
        url: str,
        url_title: str,
        titulo: str,
        data_publicacao: str,
        termo_origem: str,
        possui_ncm: bool,
    ) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO dou_atos_processados
            (data_execucao, url, url_title, titulo, data_publicacao, termo_origem, possui_ncm)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now_str(), url, url_title, titulo, data_publicacao, termo_origem, 1 if possui_ncm else 0),
        )
        conn.commit()
        conn.close()

    def start_execucao(self) -> int:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO execucoes (inicio, status, resumo) VALUES (?, ?, ?)", (now_str(), "RUNNING", ""))
        run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return int(run_id)

    def end_execucao(self, run_id: int, status: str, resumo: str) -> None:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE execucoes SET fim=?, status=?, resumo=? WHERE id=?",
            (now_str(), status, resumo[:4000], run_id),
        )
        conn.commit()
        conn.close()

    def fetch_recent_historico(self, limit: int = 100) -> list[tuple]:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT data_execucao, origem, ncm, tipo_alteracao, risco, detalhe
            FROM historico_alteracoes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def fetch_historico_by_ncm(self, ncm: str, limit: int = 5) -> list[tuple]:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT data_execucao, origem, ncm, tipo_alteracao, risco, detalhe
            FROM historico_alteracoes
            WHERE ncm=?
            ORDER BY data_execucao DESC
            LIMIT ?
            """,
            (ncm, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return rows
