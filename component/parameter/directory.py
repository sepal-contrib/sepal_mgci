from pathlib import Path

BASE_DIR = Path('~').expanduser()

RESULTS_DIR = BASE_DIR/'module_results/mgci'
CLASS_DIR = RESULTS_DIR/'custom_classifications'

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CLASS_DIR.mkdir(parents=True, exist_ok=True)
