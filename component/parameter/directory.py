import shutil
from pathlib import Path

import component.parameter.module_parameter as param

__all__ = [
    "BASE_DIR",
    "RESULTS_DIR",
    "CLASS_DIR",
    "REPORTS_DIR",
    "MATRIX_DIR",
    "TASKS_DIR",
]

BASE_DIR = Path("~").expanduser()
RESULTS_DIR = BASE_DIR / "module_results/sdg_indicators/mgci"

CLASS_DIR = RESULTS_DIR / "custom_classifications"
"Path: location where custom target classification are stored"

MATRIX_DIR = RESULTS_DIR / "reclass_matrix"
"Path: location where custom mapper matrix are stored"

TRANSITION_DIR = RESULTS_DIR / "custom_transition"
"Path: location where custom transition matrix and green_non_green files are stored"


REPORTS_DIR = RESULTS_DIR / "reports"
TASKS_DIR = RESULTS_DIR / "tasks"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CLASS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MATRIX_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)
TRANSITION_DIR.mkdir(parents=True, exist_ok=True)

# As soon as the folders are created, copy the default classification files

# copy param.LC_CLASSES to CLASS_DIR and make it read only if it doesn't exist
LOCAL_LC_CLASSES = CLASS_DIR.joinpath("lc_classification.csv")
if not LOCAL_LC_CLASSES.exists():
    shutil.copy(param.LC_CLASSES, CLASS_DIR)
    LOCAL_LC_CLASSES.chmod(0o444)

# copy param.LC_MAP_MATRIX to MATRIX_DIR and make it read only
LOCAL_LCMAP_MATRIX = MATRIX_DIR.joinpath("lc_map_matrix.csv")
if not LOCAL_LCMAP_MATRIX.exists():
    shutil.copy(param.LC_MAP_MATRIX, MATRIX_DIR)
    LOCAL_LCMAP_MATRIX.chmod(0o444)
