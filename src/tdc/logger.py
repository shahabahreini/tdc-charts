import logging

from rich.logging import RichHandler
from rich.traceback import install

# Install rich traceback handler globally for beautiful error reporting
# This catches any unhandled exceptions and prints a detailed stack trace with local variables.
install(show_locals=True)


def setup_logger(debug: bool = False, level_name: str = "INFO") -> logging.Logger:
    """
    Configure and return a structured logger using rich.
    """
    level = logging.DEBUG if debug else getattr(logging, level_name.upper(), logging.INFO)

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
        force=True,
    )

    configured_logger = logging.getLogger("tdc")
    configured_logger.setLevel(level)
    for noisy_logger in ("kaleido", "choreographer", "asyncio"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    return configured_logger


def configure_logger(debug: bool = False, level_name: str = "INFO") -> logging.Logger:
    """
    Reconfigure the shared project logger after YAML config is loaded.
    """
    global logger
    logger = setup_logger(debug=debug, level_name=level_name)
    return logger


logger = setup_logger()
