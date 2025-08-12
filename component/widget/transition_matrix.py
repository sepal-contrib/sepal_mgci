from pathlib import Path
import ipyvuetify as v
import numpy as np
import pandas as pd

from traitlets import Bool, Dict, List, Unicode, directional_link, link, observe

from component.scripts.file_handler import df_to_csv, read_file
import sepal_ui.sepalwidgets as sw

from sepal_ui.sepalwidgets.file_input import FileInput
from sepal_ui.scripts.sepal_client import SepalClient


from component.model.model import MgciModel
from component.parameter.directory import dir_
import component.parameter.module_parameter as param
from component.scripts import validation as validation
from component.scripts.scripts import set_transition_code
import logging

log = logging.getLogger("MGCI.transition_matrix")


class CustomTransitionMatrix(sw.Layout):
    """Widget with FileInput to allow user to upload a custom transition matrix"""

    custom_transition_matrix = Unicode("").tag(sync=True)
    "str: path to the transition matrix file"

    lulc_classes_sub_b = Dict([]).tag(sync=True)
    "Dict[int, Tuple[str, str]]: list of sub-b classes names. Comes from land cover classification file"

    def __init__(self, sepal_client: SepalClient = None, lulc_classes_sub_b={}):

        super().__init__()

        self.attributes = {"id": "custom_inputs"}

        self.lulc_classes_sub_b = lulc_classes_sub_b

        # Create input file widget wrapped in a layout
        self.input_impact = FileInput(
            extensions=[".csv"],
            initial_folder=str(dir_.transition_dir),
            root=str(dir_.results_dir),
            sepal_client=sepal_client,
        )
        self.children = [
            sw.Card(
                row=True,
                children=[
                    sw.CardTitle(children=["Transition file"]),
                    sw.CardText(
                        children=[
                            "Select a custom transition file containing all the possible transitions in your custom data. The file must contain the following columns: from_code, to_code, impact_code, columns names have to be exactly the same.",
                            self.input_impact,
                        ]
                    ),
                ],
            )
        ]
        self.input_impact.observe(self.read_inputs, "v_model")

    def read_inputs(self, change):
        """Read user custom input from custom transition matrix"""

        if change["new"]:
            # Get TextField from change widget
            text_field_msg = change["owner"]
            text_field_msg.error_messages = []

            validation.validate_transition_matrix(
                change["new"], self.lulc_classes_sub_b, text_field_msg
            )

            self.custom_transition_matrix = change["new"]


class TransitionMatrix(sw.Layout):
    """Transition matrix widget"""

    CLASSES = param.LC_COLOR.iloc[:, 0].tolist()
    "list: list of land cover classes names. Comes from lc_classification.csv file"

    disabled = Bool(False).tag(sync=True)

    show_matrix = Bool(True).tag(sync=True)
    "bool: either to show or hide the impact matrix and replace by input file widget"

    transition_matrix = Unicode(str(dir_.transition_dir / "transition_matrix.csv")).tag(
        sync=True
    )

    "str: path to the transition matrix file"

    def __init__(self, model: MgciModel = None, sepal_client: SepalClient = None):
        self.model = model
        # Create a random suffix to avoid conflict between multiple instances
        super().__init__()

        self.class_ = "d-block"

        self.custom_transition_matrix = CustomTransitionMatrix(
            sepal_client=sepal_client
        )
        self.transition_matrix_view = TransitionMatrixInput(
            transition_matrix_file=str(dir_.transition_dir / "transition_matrix.csv"),
            classes=self.CLASSES,
            decode_options=param.DECODE,
        )

        directional_link(
            (self.custom_transition_matrix, "custom_transition_matrix"),
            (self, "transition_matrix"),
        )
        directional_link(
            (self.model, "lulc_classes_sub_b"),
            (self.custom_transition_matrix, "lulc_classes_sub_b"),
        )

        link(
            (self.transition_matrix_view, "transition_matrix"),
            (self, "transition_matrix"),
        )

        self.children = [self.transition_matrix_view]

        # Create a link between the transition matrix and the model
        directional_link(
            (self.transition_matrix_view, "transition_matrix"),
            (self.model, "transition_matrix"),
        )

    @observe("show_matrix")
    def toggle_viz(self, change):
        """toogle visualization style, show only impact matrix or input_impact_file widget"""
        change_new = change["new"]
        log.debug(f"TransitionMatrix toggle_viz>>>>: {change_new}")

        if change["new"]:
            log.debug("TransitionMatrix toggle_viz: showing transition matrix")
            self.children = [self.transition_matrix_view]
            self.transition_matrix_view.reset()

        else:
            self.children = [self.custom_transition_matrix]
            self.custom_transition_matrix.input_impact.reset()

            self.transition_matrix_view.transition_matrix = (
                ""  # TODO: check why this???
            )

    @observe("disabled")
    def disable_edition(self, change):
        """disable all selectable elements in the table. As we'll have a lot of them
        create execute them as a pool executor"""

        self.transition_matrix_view.disabled = change["new"]

    def set_default_values(self):
        """Set the default values for the transition matrix."""
        self.transition_matrix_view.reset()


class TransitionMatrixInput(v.VuetifyTemplate, sw.SepalWidget):
    """Vue-based Transition Matrix widget."""

    template_file = Unicode(
        str(Path(__file__).parent / "vue/transitionMatrix.vue")
    ).tag(sync=True)

    # Synchronized properties with Vue component
    classes = List([]).tag(sync=True)
    matrix_data = List([]).tag(sync=True)
    decode_options = Dict({}).tag(sync=True)
    disabled = Bool(False).tag(sync=True)
    loading = Bool(False).tag(sync=True)

    # Additional properties
    transition_matrix = Unicode().tag(sync=True)

    def __init__(
        self,
        transition_matrix_file: str,
        classes: list,
        decode_options: dict,
        model: MgciModel = None,
        **kwargs,
    ):
        """Initialize the TransitionMatrix widget.

        Args:
            transition_matrix_file: Path to the transition matrix CSV file
            classes: List of land cover class names
            decode_options: Dictionary mapping impact codes to colors and abbreviations
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)

        # Set traitlets directly (like FileInput does)
        self.classes = classes
        self.matrix_data = []  # Will be loaded later
        self.decode_options = decode_options
        self.transition_matrix = transition_matrix_file

        self.suffix = (
            str(np.random.randint(0, 10000, 1)[0]) if not model else model.session_id
        )

        self.custom_transition_file_path = (
            dir_.transition_dir / f"custom_transition_{self.suffix}.csv"
        )

        # Store original values for reset functionality
        self.original_transition_matrix_file = transition_matrix_file

        # Load the matrix data after setting up the basic properties
        self.load_matrix_data()

        # Set up observers like FileInput does
        # (No observers needed for this component yet)

        # Create a link between the transition matrix and the model
        if hasattr(self, "model") and self.model:
            directional_link(
                (self, "transition_matrix"),
                (self.model, "transition_matrix"),
            )

        # Vue methods will be called directly from the template
        # vue_cell_changed() and vue_reset_to_default() are available

    def load_matrix_data(self):
        """Load the transition matrix data from the file."""
        try:
            self.loading = True

            # Read the default transition matrix
            self.default_df = read_file(self.transition_matrix)
            self.edited_df = self.default_df.copy()

            # Convert dataframe to format expected by Vue component
            matrix_data = []
            for _, row in self.default_df.iterrows():
                matrix_data.append(
                    {
                        "from_code": int(row["from_code"]),
                        "to_code": int(row["to_code"]),
                        "impact_code": row["impact_code"],
                    }
                )

            self.matrix_data = matrix_data

        except Exception as e:
            log.error(f"Error loading transition matrix data: {e}")
            self.matrix_data = []
        finally:
            self.loading = False

    def vue_cell_changed(self, data=None):
        """Handle cell value changes from the Vue component."""
        try:
            row = data["row"]
            col = data["col"]
            impact_code = data["value"]

            # Update the dataframe - explicitly cast impact_code to match column dtype
            mask = (self.edited_df.from_code == row) & (self.edited_df.to_code == col)
            # Cast to the same dtype as the impact_code column to avoid FutureWarning
            impact_code_dtype = self.edited_df["impact_code"].dtype
            self.edited_df.loc[mask, "impact_code"] = impact_code_dtype.type(
                impact_code
            )

            # Set custom transition matrix path
            self.transition_matrix = str(self.custom_transition_file_path)

            self.edited_df = set_transition_code(self.edited_df)

            # Save to CSV using pandas
            df_output = self.edited_df[
                ["from_code", "to_code", "impact_code", "transition"]
            ]

            df_to_csv(
                df_output,
                self.custom_transition_file_path,
                index=False,
            )

            # Update matrix_data to reflect the change
            self._update_matrix_data_from_df()

        except Exception as e:
            log.error(f"Error in vue_cell_changed: {e}")
            raise ValueError(
                "Invalid data format. Ensure the data contains 'row', 'col', and 'value' keys."
            )

    def vue_reset_to_default(self, data=None):
        """Reset the matrix to default values."""
        try:
            self.loading = True

            # Reset to default dataframe
            self.edited_df = self.default_df.copy()
            self.transition_matrix = (
                self.original_transition_matrix_file
            )  # Use original file

            # Update Vue component data with the reset values
            self._update_matrix_data_from_df()

            # Force Vue component refresh by clearing and setting the RESET data
            reset_matrix_data = self.matrix_data.copy()  # Get the reset data
            self.matrix_data = (
                reset_matrix_data  # Then set the RESET data (not old data)
            )

        except Exception as e:
            log.error(f"Error resetting to default: {e}")
            raise ValueError("Failed to reset the transition matrix to default values.")
        finally:
            self.loading = False

    def _update_matrix_data_from_df(self):
        """Update the matrix_data property from the current dataframe."""
        try:
            matrix_data = []
            for _, row in self.edited_df.iterrows():
                # Convert all values to plain Python types to avoid Vue reactivity issues
                entry = {
                    "from_code": int(row["from_code"]),
                    "to_code": int(row["to_code"]),
                    "impact_code": (
                        int(row["impact_code"])
                        if pd.notna(row["impact_code"])
                        else None
                    ),
                }
                matrix_data.append(entry)

            # Set the data
            self.matrix_data = matrix_data

        except Exception as e:
            log.error(f"Error updating matrix data from DataFrame: {e}")
            raise ValueError("Failed to update matrix data from DataFrame.")

    @observe("disabled")
    def _on_disabled_changed(self, change):
        """Handle disabled state changes.

        The Vue component automatically handles the disabled state,
        """
        pass  # Vue component handles this automatically

    def reset(self):
        """Reset the widget to its initial state."""
        log.debug("Resetting TransitionMatrixInput to default values")
        self.vue_reset_to_default()

    def get_transition_matrix_path(self) -> str:
        """Get the current transition matrix file path."""
        return self.transition_matrix
