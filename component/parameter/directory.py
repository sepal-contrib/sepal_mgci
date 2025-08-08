import logging
import os
import shutil
from pathlib import Path, PurePosixPath

import component.parameter.module_parameter as param

log = logging.getLogger("MGCI")

DEPLOY_ENV = os.getenv("DEPLOY_ENV")

# Define root and subfolder names only once
ROOT_RELATIVE = "module_results/sdg_indicators/15.4.2"
SUBFOLDERS = {
    "class_dir": "custom_classifications",
    "matrix_dir": "custom_map_matrix",
    "transition_dir": "custom_transition",
    "reports_dir": "reports",
    "tasks_dir": "tasks",
}

# Precompute relative paths for remote creation
RELATIVE_PATHS = [ROOT_RELATIVE] + [
    f"{ROOT_RELATIVE}/{sub}" for sub in SUBFOLDERS.values()
]


class Dirs:
    def __init__(self, base):
        # base: Path or PurePosixPath
        self.base = base
        self.results_dir = base / ROOT_RELATIVE
        for attr, sub in SUBFOLDERS.items():
            setattr(self, attr, self.results_dir / sub)

    @property
    def all_dirs(self):
        return [self.results_dir] + [getattr(self, k) for k in SUBFOLDERS]


def initialize_local():
    """
    Create local directories and copy default files.
    """
    for d in dir_.all_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Default classification
    lc = dir_.class_dir / "default_lc_classification.csv"
    if not lc.exists():
        shutil.copy(param.LC_CLASSES, lc)
        lc.chmod(0o444)

    # Default map matrix
    mm = dir_.matrix_dir / "default_lc_map_matrix.csv"
    if not mm.exists():
        shutil.copy(param.LC_MAP_MATRIX, mm)
        mm.chmod(0o444)

    # Transition matrix always
    tr = dir_.transition_dir / "transition_matrix.csv"
    shutil.copy(param.TRANSITION_MATRIX_FILE, tr)


def initialize_remote(client):
    """
    Create remote directories and upload default files via API client.
    Args:
        client: REST client with get_remote_dir and set_file
    """

    log.debug("Initializing remote directories and files")

    [log.debug(f"{rel}") for rel in RELATIVE_PATHS]

    for rel in RELATIVE_PATHS:
        log.debug(f"Creating remote directory: {rel}")
        client.get_remote_dir(rel, parents=True)

    # Upload default classification
    lc_path = dir_.class_dir / "default_lc_classification.csv"
    content = Path(param.LC_CLASSES).read_text()
    client.set_file(str(lc_path), content)

    # Upload default map matrix
    mm_path = dir_.matrix_dir / "default_lc_map_matrix.csv"
    content = Path(param.LC_MAP_MATRIX).read_text()
    client.set_file(str(mm_path), content)

    # Transition matrix
    tr_path = dir_.transition_dir / "transition_matrix.csv"
    content = Path(param.TRANSITION_MATRIX_FILE).read_text()
    client.set_file(str(tr_path), content)


# Always construct dir_ for attribute access
if DEPLOY_ENV == "sepal_solara":
    # Remote environment: no local creation
    base = PurePosixPath("")
else:
    # Local environment: base is user home and run initialization
    base = Path.home()

dir_ = Dirs(base)

# Auto-initialize only if local
if DEPLOY_ENV != "sepal_solara":
    initialize_local()
