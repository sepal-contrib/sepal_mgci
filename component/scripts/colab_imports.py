import os

import ee  # google earth engine

from datetime import datetime  # for time stamping error log
import pandas as pd  # pandas library for tabular data manipulation
import re  # for manipulating strings
from unidecode import (
    unidecode,
)  # converting symbols in country names to ascii compliant (required for naming GEE tasks)

# formatting excel report file
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from pathlib import Path

# # Change current directory to sepal_mgci (i.e. the local copy of the github repository)
# %cd "/content/sepal_mgci"

# Import parameters for the default DEM asset and a lookup table for land cover reclassification
DEM_DEFAULT = "CGIAR/SRTM90_V4"

# Define the translation matrix between ESA and MGCI LC classes

LC_MAP_MATRIX = Path(__file__).parents[1] / "parameter/lc_map_matrix.csv"

TRANSITION_MATRIX_FILE = Path(__file__).parents[1] / "parameter/transition_matrix.csv"

# # # # Import scripts and modules from cloned GitHub repository (i.e., functions for indicator calculation and formatting)
from component.scripts.gee import (
    reduce_regions,
)  # for running summary statistics in GEE

from component.scripts.scripts import (
    get_a_years,
    map_matrix_to_dict,
    parse_result,
    read_from_csv,
    get_b_years,
    map_matrix_to_dict,
    get_sub_b_items,
    get_reporting_years,
    parse_to_year,
)  # parameter prep and reformatting
from component.scripts import (
    sub_a,
    sub_b,
    mountain_area as mntn,
)  ###TO DO: ADD DESCRIPTIONS

from component.scripts.colab_combining_files import (
    sanitize_description,
    append_excel_files,
)

from component.scripts.colab_drive_folders import (
    folder_exists,
    create_folder,
    create_folder_if_not_exists,
)

print("Imports complete")
