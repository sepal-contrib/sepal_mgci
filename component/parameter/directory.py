from pathlib import Path

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
MATRIX_DIR = RESULTS_DIR / "reclass_matrix"
REPORTS_DIR = RESULTS_DIR / "reports"
TASKS_DIR = RESULTS_DIR / "tasks"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CLASS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MATRIX_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)
