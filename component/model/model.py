from pathlib import Path

import ee
import pandas as pd
import sepal_ui.scripts.utils as su
from sepal_ui.model import Model
from sepal_ui.scripts.warning import SepalWarning
from traitlets import Any, Bool, CBool, Dict, List, Unicode

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
import component.scripts as cs
from component.parameter.report_template import *


class MgciModel(Model):
    use_custom = CBool(0).tag(sync=True)

    # output parameters
    year = Unicode("", allow_none=True).tag(sync=True)
    source = Unicode("", allow_none=True).tag(sync=True)

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

    # Results

    biobelt_image = None
    "ee.Image: clipped bioclimatic belt image with aoi_model.feature_collection"

    transition_matrix = Any(param.TRANSITION_MATRIX).tag(sync=True)
    "pd.DataFrame: containing at least 3 columns: from_code, to_code, impact_code"

    dash_ready = Bool(False).tag(sync=True)
    "bool: this attribute will receive the dashboard status. True when it has loaded successfully"

    calc_a = Bool(True).tag(sync=True)
    "bool: comes from Calculation swtich A. Either user wants to calculate subindicator A or not"

    calc_b = Bool(True).tag(sync=True)
    "bool: comes from Calculation swtich B. Either user wants to calculate subindicator B or not"

    done = Bool(True).tag(sync=True)
    "bool: bool trait to indicate that MGCI calculation has been performed. It will be listen by different widgets (i.e.dashboard tile)."

    @su.need_ee
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

    def reduce_to_regions(self, indicator, lc_start, lc_end=None):
        """Reduce land use/land cover image to bioclimatic belts regions using planimetric
        or real surface area

        Attributes:
            indicator (str): either 'sub_a' or 'sub_b'
            lc_start (string): first year of the report or baseline.
            lc_end (string): last year of the report.
            aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image

        Return:
            GEE Dicionary process (is not yet executed), with land cover class area
            per land cover (when both dates are input) and biobelts
        """

        if not lc_start:
            raise Exception("Please select at least one year")

        matrix = getattr(self, f"matrix_{indicator}")

        def no_remap(image):
            """return remapped or raw image if there's a matrix"""

            if matrix:
                from_, to_ = list(zip(*matrix.items()))
                return image.remap(from_, to_, 0)

            return image

        # Define two ways of calculation, with only one date and with both
        ee_lc_start_band = ee.Image(lc_start).bandNames().get(0)
        ee_lc_start = ee.Image(lc_start).select([ee_lc_start_band])
        ee_lc_start = no_remap(ee_lc_start)

        aoi = self.aoi_model.feature_collection.geometry()
        clip_biobelt = ee.Image(param.BIOBELT).clip(aoi)

        if self.rsa:
            # When using rsa, we need to use the dem scale, otherwise
            # we will end with wrong results.
            image_area = cs.get_real_surface_area(self.dem, aoi)
            scale = ee_lc_start.projection().nominalScale().getInfo()
        else:
            # Otherwise, we will use the coarse scale to the output.
            image_area = ee.Image.pixelArea()
            scale = (
                ee_lc_start.projection()
                .nominalScale()
                .max(ee_lc_start.projection().nominalScale())
                .getInfo()
            )

        if indicator == "sub_b":

            ee_lc_end_band = ee.Image(lc_end).bandNames().get(0)
            ee_lc_end = ee.Image(lc_end).select([ee_lc_end_band])
            ee_lc_end = no_remap(ee_lc_end)

            return (
                image_area.divide(param.UNITS["sqkm"][0])
                .updateMask(clip_biobelt.mask())
                .addBands(ee_lc_end)
                .addBands(ee_lc_start)
                .addBands(clip_biobelt)
                .reduceRegion(
                    **{
                        "reducer": ee.Reducer.sum().group(1).group(2).group(3),
                        "geometry": aoi,
                        "maxPixels": 1e19,
                        "scale": scale,
                        "bestEffort": True,
                        "tileScale": 4,
                    }
                )
            )

        return (
            image_area.divide(param.UNITS["sqkm"][0])
            .updateMask(clip_biobelt.mask())
            .addBands(ee_lc_start)
            .addBands(clip_biobelt)
            .reduceRegion(
                **{
                    "reducer": ee.Reducer.sum().group(1).group(2),
                    "geometry": aoi,
                    "maxPixels": 1e19,
                    "scale": scale,
                    "bestEffort": True,
                    "tileScale": 4,
                }
            )
        )

    def task_process(self, process, task_file, process_id):
        """Send the task to the GEE servers and process it in background. This will be
        neccessary when the process is timed out."""

        task_name = Path(f"{task_file.name}_{process_id}")

        task = ee.batch.Export.table.toDrive(
            **{
                "collection": ee.FeatureCollection([ee.Feature(None, process)]),
                "description": str(task_name),
                "fileFormat": "CSV",
            }
        )

        task.start()

        # Create a file containing the task id to track when the process is done.
        with open(task_file.with_suffix(".csv"), "a") as file:
            file.write(f"{process_id}, {task.id}" + "\n")

    def download_from_task_file(self, task_id, tasks_file, task_filename):
        """Download csv file result from GDrive

        Args:
            task_id (str): id of the task tasked in GEE.
            tasks_file (Path): path file containing all task_id, task_name
            task_filename (str): name of the task file to be downloaded.
        """

        gdrive = cs.GDrive()

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
