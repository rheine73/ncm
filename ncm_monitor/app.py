from pathlib import Path

from .alerts import dispatch_alerts
from .db import Database
from .dou import run_dou_monitor
from .logger import append_json_event, build_logger
from .settings import Settings
from .structural import run_structural_monitor
from .utils import date_dou


def run(base_dir: Path) -> int:
    settings = Settings.load(base_dir)
    logger = build_logger(settings.logs_dir)
    db = Database(settings.db_path)
    db.init_schema()
    run_id = db.start_execucao()

    logger.info("====================================")
    logger.info("     MONITOR FISCAL COMPLETO")
    logger.info("====================================")

    status = "SUCCESS"
    resumo_parts: list[str] = []
    alert_lines: list[str] = []

    try:
        if settings.tabela_ncm_path.exists() and settings.ncms_monitoradas_path.exists():
            logger.info("\n=== MONITOR ESTRUTURAL NCM (RFB) ===")
            structural = run_structural_monitor(
                db=db,
                tabela_path=settings.tabela_ncm_path,
                monitoradas_path=settings.ncms_monitoradas_path,
                snapshots_dir=settings.snapshots_dir,
            )

            if structural.first_snapshot:
                logger.info("Primeiro snapshot criado.")
            if structural.novos:
                logger.info(f"NCM NOVA: {structural.novos}")
            if structural.removidos:
                logger.info(f"NCM REMOVIDA: {structural.removidos}")
            if structural.alterados:
                logger.info(f"DESCRICAO ALTERADA: {structural.alterados}")
            if structural.nao_encontrados:
                logger.info(f"NCM NAO ENCONTRADA: {structural.nao_encontrados}")

            resumo_parts.append(
                f"RFB novos={structural.novos} removidos={structural.removidos} "
                f"alterados={structural.alterados} nao_encontrados={structural.nao_encontrados}"
            )

        if settings.ncms_monitoradas_path.exists():
            logger.info("\n=== MONITOR DOU (CONFAZ) ===")
            dou = run_dou_monitor(settings=settings, db=db, data_ref=date_dou())
            for term in dou.termos:
                logger.info(
                    f"[DOU] termo='{term.termo}' resultados={term.resultados} "
                    f"paginas={term.total_pages} atos={term.atos_coletados}"
                )

            if dou.novos_atos == 0:
                logger.info("Nenhum ato novo para processar.")
            elif dou.novos_eventos == 0:
                logger.info("Nenhuma nova publicacao relevante.")
            else:
                logger.info(f"Novas publicacoes relevantes detectadas: {dou.novos_eventos}")

            alert_lines.extend(dou.mensagens_alerta)
            resumo_parts.append(f"DOU novos_atos={dou.novos_atos} novos_eventos={dou.novos_eventos}")

        delivery = dispatch_alerts(settings, alert_lines)
        if alert_lines:
            if delivery.get("preview_file"):
                logger.info(f"Email preview salvo em: {delivery['preview_file']}")
            logger.info(f"Alertas enviados -> telegram={delivery['telegram']} email={delivery['email']}")
    except Exception as exc:
        status = "ERROR"
        resumo_parts.append(str(exc))
        logger.exception("Falha durante execucao: %s", exc)
    finally:
        resumo = " | ".join(resumo_parts)[:4000]
        db.end_execucao(run_id, status, resumo)
        append_json_event(settings.logs_dir, {"run_id": run_id, "status": status, "resumo": resumo})
        logger.info("\nProcesso finalizado.")

    return 0 if status == "SUCCESS" else 1
