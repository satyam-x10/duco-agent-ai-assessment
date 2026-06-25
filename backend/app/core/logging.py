import logging
import sys
from app.config.settings import settings


def setup_logging() -> None:
    """Configures system-wide logging formatting and levels based on running environment."""
    log_level = logging.DEBUG if settings.ENV == "development" else logging.INFO
    
    # Reset existing logging configurations to bind clean handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set logger levels for noisy libraries
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
