"""Utilities to handle logging in the whole project."""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

UTC = timezone.utc
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(LEVEL)


def _is_interactive():  # noqa: ANN202
    import __main__ as main

    return not hasattr(main, "__file__")


def get_logger(file_path: str, level: Optional[str] = None) -> logging.Logger:
    if level is None:
        level = LEVEL
    name = Path(file_path).stem
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(handler)
        if level == "DEBUG":
            # Ensure the log directory exists
            log_dir = Path(__file__).parent.parent / "log"
            log_dir.mkdir(exist_ok=True)

            # Create and add the file handler
            file_handler = logging.FileHandler(log_dir / f"{datetime.now(UTC).isoformat()}.log")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
    return logger
