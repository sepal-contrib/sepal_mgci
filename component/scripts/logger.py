"""Logging configuration for the MGCI project.

To use this logging configuration, set the environment variable
MGCI_LOG_CFG to the path of the logging configuration file.
The repo has a sample configuration file in the root directory.

"""

import logging
import logging.config
import os
from pathlib import Path

import tomli

logger = logging.getLogger("MGCI")


def setup_logging():
    """Set up logging configuration from a TOML file.

    The configuration file path can be set using the MGCI_LOG_CFG environment variable.
    If the file does not exist, a NullHandler is added to the logger.
    If the file exists, it is loaded and the logging configuration is applied.
    """
    cfg_path = (
        os.getenv("MGCI_LOG_CFG")
        or Path(__file__).parent.parent.parent / "logging_config.toml"
    )
    cfg_path = Path(cfg_path)
    if not cfg_path.exists():
        MGCI_logger = logging.getLogger("MGCI")
        for handler in MGCI_logger.handlers[:]:
            MGCI_logger.removeHandler(handler)
        MGCI_logger.addHandler(logging.NullHandler())
        return

    if not cfg_path.is_file():
        raise FileNotFoundError(f"Logging config not found at {cfg_path}")

    with cfg_path.open("rb") as f:
        cfg = tomli.load(f)

    logger.debug(f"Loading logging configuration from {cfg_path}")

    logging.config.dictConfig(cfg)


setup_logging()
