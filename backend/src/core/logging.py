import logging
import sys

from core.config import SETTINGS

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] " "[%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LEVEL_COLOR = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[41m",
}

RESET_COLOR = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        if getattr(record, "no_color", False):
            color_prefix = ""
            color_suffix = ""
        else:
            color_prefix = LEVEL_COLOR.get(levelname, "")
            color_suffix = RESET_COLOR
        record.levelname = f"{color_prefix}{levelname}{color_suffix}"
        return super().format(record)


def setup_logging(log_level: str = "INFO"):
    level = getattr(logging, log_level.upper(), logging.INFO)

    use_color = (
        sys.stdout.isatty()
    )  # check if the output is a terminal to decide if we should use color

    handlers = []
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = (
        ColoredFormatter(LOG_FORMAT, DATE_FORMAT)
        if use_color
        else logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    )
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    logging.basicConfig(level=level, handlers=handlers)

    # set log handlers for 3rd party libraries
    for lib in SETTINGS.logging.third_party_libs:
        logger = logging.getLogger(lib)
        logger.handlers = handlers
        logger.propagate = False
