"""
Safe Unified Logger.
Uses Loguru if installed, otherwise falls back to standard Python logging seamlessly.
"""

try:
    from loguru import logger
except ImportError:
    import logging
    import sys

    class SafeLogger:
        def __init__(self):
            self._logger = logging.getLogger("jobhunter")
            if not self._logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(logging.Formatter(
                    "%(asctime)s | %(levelname)-7s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                ))
                self._logger.addHandler(handler)
                self._logger.setLevel(logging.INFO)

        def info(self, msg, *args, **kwargs):
            self._logger.info(msg, *args)

        def debug(self, msg, *args, **kwargs):
            self._logger.debug(msg, *args)

        def warning(self, msg, *args, **kwargs):
            self._logger.warning(msg, *args)

        def error(self, msg, *args, **kwargs):
            self._logger.error(msg, *args)

        def critical(self, msg, *args, **kwargs):
            self._logger.critical(msg, *args)

        def log(self, level, msg, *args, **kwargs):
            lvl = getattr(logging, str(level).upper(), logging.INFO)
            self._logger.log(lvl, msg, *args)

    logger = SafeLogger()
