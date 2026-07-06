import logging
from rich.logging import RichHandler
from rich.traceback import install

# Install rich traceback handler globally for beautiful error reporting
# This catches any unhandled exceptions and prints a detailed stack trace with local variables.
install(show_locals=True)

def setup_logger(debug: bool = False) -> logging.Logger:
    """
    Configure and return a structured logger using rich.
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)]
    )
    
    logger = logging.getLogger("tdc")
    return logger

logger = setup_logger()
