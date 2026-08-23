"""控制台与文件双输出日志。"""

# 控制台便于开发观察，滚动文件用于定位历史运行问题。
import logging
from logging.handlers import RotatingFileHandler

from backend.core.config import Settings

LOGGER_NAME = "taxmind"


def configure_logging(settings: Settings) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if getattr(logger, "_taxmind_configured", False):
        return
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        settings.log_file, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger._taxmind_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
