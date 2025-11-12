import logging
import colorlog

_logger = None

def setup_logging():
    global _logger
    if _logger is not None:
        return _logger

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s%(reset)s:     %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    ))

    # Configure ROOT logger so ALL child loggers inherit the handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Also return the 'api' logger for backward compatibility
    _logger = logging.getLogger(__name__.split('.')[0])
    _logger.setLevel(logging.INFO)

    return _logger