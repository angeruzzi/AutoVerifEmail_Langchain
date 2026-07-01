import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from graph.graph_builder import build_graph

load_dotenv()

_LOG_FILE = "agent.log"
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE = "%Y-%m-%d %H:%M:%S"


def _setup_logging() -> None:
    """Configura logging para console e arquivo rotativo (agent.log)."""
    # Reconfigura stdout para UTF-8 no Windows (evita UnicodeEncodeError com emojis)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            _LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB por arquivo
            backupCount=3,
            encoding="utf-8",
        ),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format=_LOG_FORMAT,
        datefmt=_LOG_DATE,
        handlers=handlers,
    )


def run_agent() -> None:
    """Constrói e executa o grafo do agente."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Execução iniciada")

    try:
        graph = build_graph()
        graph.invoke({})
        logger.info("Execução concluída com sucesso")
    except Exception:
        logger.exception("Execução encerrada com erro crítico")

    logger.info("=" * 50)


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Agente de triagem de e-mails (LangGraph + Gmail + WhatsApp)"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Executa o agente imediatamente, sem aguardar o agendamento",
    )
    args = parser.parse_args()

    if args.run_now:
        run_agent()
        return

    # Agendamento via APScheduler
    cron_expr = os.getenv("SCHEDULE_CRON", "0 7 * * *").strip()
    timezone = os.getenv("SCHEDULE_TIMEZONE", "America/Sao_Paulo")

    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(
        run_agent,
        trigger=CronTrigger.from_crontab(cron_expr, timezone=timezone),
        id="email_agent",
        name="Agente de triagem de e-mails",
        max_instances=1,        # evita execuções sobrepostas
        misfire_grace_time=300, # até 5 min de tolerância se o processo estiver ocupado
    )

    next_run = scheduler.get_job("email_agent").next_run_time
    logger.info("Agendamento ativo: '%s' (%s)", cron_expr, timezone)
    logger.info("Próxima execução: %s", next_run)
    logger.info("Pressione Ctrl+C para encerrar")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agente encerrado pelo usuário")


if __name__ == "__main__":
    main()
