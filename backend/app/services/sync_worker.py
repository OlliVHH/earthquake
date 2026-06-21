"""Long-running sync worker entrypoint for Docker."""

from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.sync_service import run_incremental

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run incremental sync on a schedule until interrupted."""
    settings = get_settings()
    interval = max(1, settings.usgs_sync_interval_minutes) * 60
    logger.info("Sync worker started (interval=%ss)", interval)

    while True:
        db = SessionLocal()
        try:
            run_incremental(db, settings)
        except Exception:
            logger.exception("Sync cycle failed")
        finally:
            db.close()
        time.sleep(interval)


if __name__ == "__main__":
    main()
