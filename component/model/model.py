import random
from typing import List

from sepal_ui.model import Model
import sepal_ui.scripts.decorator as sd
import component.scripts as cs
from traitlets import Bool, CBool, Dict, List, Unicode, observe

import component.parameter.module_parameter as param
from component.scripts.sepal_ui_scripts import get_geoarea

import logging

log = logging.getLogger("MGCI.model")


class MgciModel(Model):
    """Model for MGCI calculation"""

    # Create a random session id of 4 digits
    session_id = random.randint(1000, 9999)

    use_custom = CBool(0).tag(sync=True)

    # output parameters
    year = Unicode("", allow_none=True).tag(sync=True)
    source = Unicode(
        "Food and Agriculture Organization of United Nations (FAO)", allow_none=True
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

    # Results
    results = Dict({}).tag(sync=True)
    "dict: results of the MGCI calculation. It will be used to create the dashboard"

    @observe(
        "use_custom",
        "year",
        "source",
        "impact_matrix",
        "rsa",
        "sub_a_year",
        "sub_b_year",
        "lc_asset_sub_a",
        "lc_asset_sub_b",
        "ic_items_sub_a",
        "ic_items_sub_b",
        "lulc_classes_sub_a",
        "lulc_classes_sub_b",
        "matrix_sub_a",
        "matrix_sub_b",
        "green_non_green",
        "reporting_years_sub_a",
        "reporting_years_sub_b",
        "transition_matrix",
        "green_non_green_file",
        "dash_ready",
        "calc_a",
        "calc_b",
        "done",
        "dem",
    )
    def log_change(self, change):
        prop_changed = change["name"]
        new_value = change["new"]
        old_value = change["old"]

        log.debug(f"MgciModel: {prop_changed} changed from {old_value} to {new_value}")

    @sd.need_ee
    def __init__(self, aoi_view=None, sepal_client=None, **kwargs):
        """

        Parameters:

            Dashboard
            ---------
            results_file (str): file containing a task .csv file with name and task_id

        """
        self.sepal_client = sepal_client
        self.results: Dict = {}
        self.aoi_view = aoi_view
        self.aoi_model = aoi_view.model

        # Styled results dataframe
        self.mgci_report = None

        # Save the GEE reduce to region json proces
        self.reduced_process = None

        # Set default dem asset
        # currently, we are not allowing user to change the dem
        self.dem = param.DEM_DEFAULT

        self.aoi_view.observe(self.on_aoi_change, "updated")

    def on_aoi_change(self, *args):
        """Callback to update the model when the AOI changes"""

        log.debug("MgciModel: AOI changed, resetting results")

        self.results = {}

    def get_geo_area_name(self):
        """Get the geographic area name from the AOI model

        Returns:
            str: The geographic area name

        Raises:
            Exception: If no AOI is selected
        """
        if not self.aoi_model:
            raise Exception("You have to select an AOI first.")

        return get_geoarea(self.aoi_model)[0]

    def get_ref_area(self):
        """Get the reference area from the AOI model

        Returns:
            float or str: The reference area value

        Raises:
            Exception: If no AOI is selected
        """
        if not self.aoi_model:
            raise Exception("You have to select an AOI first.")

        return get_geoarea(self.aoi_model)[1]

    def get_data(self):
        """Return the current state of the model"""

        if not self.aoi_model:
            raise Exception("You have to select an AOI first.")

        geo_area_name = self.get_geo_area_name()
        ref_area = self.get_ref_area()
        report_folder = cs.get_report_folder(self.aoi_model.name, self.sepal_client)

        return {
            "reporting_years_sub_a": self.reporting_years_sub_a,
            "sub_b_year": self.sub_b_year,
            "geo_area_name": geo_area_name,
            "ref_area": ref_area,
            "source_detail": self.source,
            "transition_matrix": str(self.transition_matrix),
            "session_id": self.session_id,
            "report_folder": str(report_folder),
        }
