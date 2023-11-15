from pathlib import Path
from typing import List

import pandas as pd
from sepal_ui.scripts.warning import SepalWarning
from sepal_ui.model import Model
import sepal_ui.scripts.decorator as sd
from traitlets import Bool, CBool, Dict, List, Unicode

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
from component.scripts.gdrive import GDrive


class MgciModel(Model):
    """Model for MGCI calculation"""

    session_id = 1824

    use_custom = CBool(0).tag(sync=True)

    # output parameters
    year = Unicode("", allow_none=True).tag(sync=True)
    source = Unicode(
        "Food and Agriculture Organisation of United Nations (FAO)", allow_none=True
    ).tag(sync=True)

    # Custom
    impact_matrix = Bool(allow_none=False).tag(sync=True)
    "bool: either user will provide a custom transition matrix (impact) or not"

    rsa = Bool(False, allow_none=True).tag(sync=True)

    # Input parameters from dashboard

    sub_a_year = Dict({}).tag(sync=True)
    "dict: list of year(s) selected in dashboard.calculation_view.calculation.w_content_a.v_model"

    sub_b_year = Dict({}).tag(sync=True)
    "dict: list of year(s) selected in dashboard.calculation_view.calculation.w_content_b.v_model"

    # Observation variables

    # We need two different variables to store each subindicator assets

    lc_asset_sub_a = Unicode(allow_none=True).tag(sync=True)
    "str: asset id of the land cover image selected on subindicator A"

    lc_asset_sub_b = Unicode(allow_none=True).tag(sync=True)
    "str: asset id of the land cover image selected on subindicator B"

    ic_items_sub_a = List([]).tag(sync=True)
    "list: list of select.items containing image ids and image names selected on subindicator A"

    ic_items_sub_b = List([]).tag(sync=True)
    "list: list of select.items containing image ids and image names selected on subindicator B"

    lulc_classes_sub_a = Dict(allow_none=True).tag(sync=True)
    "dict: LCLU Classes. Are the target classes from subindicator A. Fixed."

    lulc_classes_sub_b = Dict(allow_none=True).tag(sync=True)
    "dict: LCLU Classes. Are the target classes from subindicator B."

    matrix_sub_a = Dict({}).tag(sync=True)
    "dict: comes from reclassify_tile.viewa.model.matrix which are the {src:dst} classes"

    matrix_sub_b = Dict({}).tag(sync=True)
    "dict: comes from reclassify_tile.viewb.model.matrix which are the {src:dst} classes"

    green_non_green = Bool(False).tag(sync=True)

    reporting_years_sub_a = Dict({}).tag(sync=True)
    """dict: Dict list of reporting years based on user selection. It's calculated when chips are created and it's used to alert dashboard of which years are available for statistics"""

    reporting_years_sub_b = List([]).tag(sync=True)
    """list: list of reporting years based on user selection. It's calculated when chips are created and it's used to alert dashboard of which years are available for statistics"""

    # Results

    biobelt_image = None
    "ee.Image: clipped bioclimatic belt image with aoi_model.feature_collection"

    transition_matrix = Unicode().tag(sync=True)
    "str: transition matrix file used to calculate the sub_b indicator"

    green_non_green_file = Unicode().tag(sync=True)
    "str: custom green non green matrix file used to calculate the sub_b indicator when user has a custom transition matrix"

    dash_ready = Bool(False).tag(sync=True)
    "bool: this attribute will receive the dashboard status. True when it has loaded successfully"

    calc_a = Bool(True).tag(sync=True)
    "bool: comes from Calculation swtich A. Either user wants to calculate subindicator A or not"

    calc_b = Bool(True).tag(sync=True)
    "bool: comes from Calculation swtich B. Either user wants to calculate subindicator B or not"

    done = Bool(True).tag(sync=True)
    "bool: bool trait to indicate that MGCI calculation has been performed. It will be listen by different widgets (i.e.dashboard tile)."

    dem = Unicode().tag(sync=True)
    "str: DEM file used to calculate surface area"

    @sd.need_ee
    def __init__(self, aoi_model=None):
        """

        Parameters:

            Dashboard
            ---------
            results_file (str): file containing a task .csv file with name and task_id

        """

        self.biobelt_imaga = None
        self.vegetation_image = None
        self.aoi_model = aoi_model

        self.ic_items_label = None

        # Styled results dataframe
        self.mgci_report = None

        # Save the GEE reduce to region json proces
        self.reduced_process = None

        # Set default dem asset
        # currently, we are not allowing user to change the dem
        self.dem = param.DEM_DEFAULT

    def download_from_task_file(self, task_id, tasks_file, task_filename):
        """Download csv file result from GDrive

        Args:
            task_id (str): id of the task tasked in GEE.
            tasks_file (Path): path file containing all task_id, task_name
            task_filename (str): name of the task file to be downloaded.
        """

        gdrive = GDrive()

        # Check if the task is completed
        task = gdrive.get_task(task_id.strip())

        if task.state == "COMPLETED":
            tmp_result_folder = Path(DIR.TASKS_DIR, Path(tasks_file.name).stem)
            tmp_result_folder.mkdir(exist_ok=True)

            tmp_result_file = tmp_result_folder / task_filename
            print(task_filename)
            gdrive.download_file(task_filename, tmp_result_file)

            return tmp_result_file

        elif task.state == "FAILED":
            raise Exception(f"The task {Path(task_filename).stem} failed.")

        else:
            raise SepalWarning(
                f"The task '{Path(task_filename).stem}' state is: {task.state}."
            )

    def read_tasks_file(self, tasks_file):
        """read tasks file"""

        if not tasks_file.exists():
            raise Exception("You have to download and select a task file.")

        tasks_df = pd.read_csv(tasks_file, header=None).astype(str)

        return tasks_df
