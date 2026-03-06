from pathlib import Path

from ncm_monitor.app import run


if __name__ == "__main__":
    raise SystemExit(run(Path(__file__).resolve().parent))

