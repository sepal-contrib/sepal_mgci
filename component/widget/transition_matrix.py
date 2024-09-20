from typing import Tuple
import ipyvuetify as v
import numpy as np
import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from sepal_ui.scripts.decorator import switch
from traitlets import Bool, Dict, List, Unicode, directional_link, observe
from component.model.model import MgciModel

import component.parameter.directory as dir_
import component.parameter.module_parameter as param
from component.scripts import validation as validation
from component.scripts.scripts import set_transition_code


class CustomTransitionMatrix(sw.Layout):
    """Widget with FileInput to allow user to upload a custom transition matrix"""

    custom_transition_matrix = Unicode("").tag(sync=True)
    "str: path to the transition matrix file"

    lulc_classes_sub_b = Dict([]).tag(sync=True)
    "Dict[int, Tuple[str, str]]: list of sub-b classes names. Comes from land cover classification file"

    def __init__(self, lulc_classes_sub_b={}):

        super().__init__()

        self.attributes = {"id": "custom_inputs"}
        self.hide()

        self.lulc_classes_sub_b = lulc_classes_sub_b

        # Create input file widget wrapped in a layout
        self.input_impact = sw.FileInput(
            ".csv", folder=dir_.TRANSITION_DIR, root=dir_.RESULTS_DIR
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
            text_field_msg = change["owner"].children[-1]
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

    transition_matrix = Unicode(str(param.TRANSITION_MATRIX_FILE)).tag(sync=True)
    "str: path to the transition matrix file"

    def __init__(self, model: MgciModel = None):
        self.model = model
        # Create a random suffix to avoid conflict between multiple instances
        self.suffix = (
            str(np.random.randint(0, 10000, 1)[0]) if not model else model.session_id
        )

        self.custom_transition_file_path = (
            dir_.TRANSITION_DIR / f"custom_transition_{self.suffix}.csv"
        )

        self.class_ = "d-block"

        self.w_labels = [
            (
                sw.Tooltip(
                    v.Html(tag="th", children=[self.truncate_string(class_)]),
                    (class_),
                    bottom=True,
                    max_width=175,
                )
                if len(class_) > 20
                else v.Html(tag="th", children=class_)
            )
            for class_ in self.CLASSES
        ]

        # create a header
        self.header = [
            v.Html(
                tag="tr",
                children=([v.Html(tag="th", children=[""])] + self.w_labels),
            )
        ]

        btn_clear = v.Btn(icon=True, children=[v.Icon(children=["mdi-broom"])])
        toolbar = v.Toolbar(
            attributes={"id": "transition_matrix"},
            flat=True,
            children=[
                "Transition matrix",
                v.Spacer(),
                v.Divider(vertical=True, class_="mx-2"),
                btn_clear,
            ],
        )

        self.progress = sw.ProgressLinear(
            attributes={"id": "transition_matrix"},
            v_model=False,
            height=5,
            indeterminate=False,
        )

        self.custom_transition_matrix = CustomTransitionMatrix()

        directional_link(
            (self.custom_transition_matrix, "custom_transition_matrix"),
            (self, "transition_matrix"),
        )
        directional_link(
            (self.model, "lulc_classes_sub_b"),
            (self.custom_transition_matrix, "lulc_classes_sub_b"),
        )

        # create the simple table
        super().__init__()

        self.children = [
            toolbar,
            self.progress,
            self.custom_transition_matrix,
        ]

        self.set_rows()

        btn_clear.on_event("click", lambda *args: self.set_default_values())

        # Create a link between the transition matrix and the model
        directional_link(
            (self, "transition_matrix"),
            (self.model, "transition_matrix"),
        )

    @observe("show_matrix")
    def toggle_viz(self, change):
        """toogle visualization style, show only impact matrix or input_impact_file widget"""

        if change["new"]:
            # hide inputs to custom transition matrix and custom green/non green
            [ch.hide() for ch in self.get_children(id_="custom_inputs")]

            # show impact matrix
            [ch.show() for ch in self.get_children(id_="transition_matrix")]
            # And also set the default values again
            self.set_default_values()

        else:
            # show inputs to custom transition matrix and custom green/non green
            [ch.show() for ch in self.get_children(id_="custom_inputs")]
            [ch.hide() for ch in self.get_children(id_="transition_matrix")]

            self.custom_transition_matrix.input_impact.reset()
            self.transition_matrix = ""

    @switch("indeterminate", on_widgets=["progress"], targets=[False])
    def set_rows(self):
        """Create selectable matrix with default transition matrix file.

        It will always returns the default transition matrix file.
        """

        # Set all inputs to default values
        self.transition_matrix = str(param.TRANSITION_MATRIX_FILE)
        self.default_df = pd.read_csv(param.TRANSITION_MATRIX_FILE)
        self.edited_df = self.default_df.copy()

        # Remove table if exists
        self.children = [
            chld for chld in self.children if not isinstance(chld, sw.SimpleTable)
        ]
        # create a row
        rows = []
        for i, baseline in enumerate(self.CLASSES, 1):
            inputs = []
            for j, target in enumerate(self.CLASSES, 1):
                # create a input with default matrix value
                default_value = param.DECODE[
                    self.default_df[
                        (self.default_df.from_code == i)
                        & (self.default_df.to_code == j)
                    ]["impact_code"].iloc[0]
                ].get("abrv")
                matrix_input = MatrixInput(i, j, default_value)
                matrix_input.color_change({"new": default_value})
                matrix_input.observe(self.update_dataframe, "v_model")

                input_ = v.Html(tag="td", class_="ma-0 pa-0", children=[matrix_input])
                inputs.append(input_)

            row = v.Html(tag="tr", children=([self.w_labels[i - 1]] + inputs))
            rows.append(row)

        self.set_children(
            sw.SimpleTable(
                attributes={"id": "transition_matrix"},
                children=[v.Html(tag="tbody", children=self.header + rows)],
            ),
            "last",
        )

    def set_default_values(self):
        """Manually set default values to the matrix"""

        # Get all select inputs and change their values to the default ones
        for i, _ in enumerate(self.CLASSES, 1):
            for j, _ in enumerate(self.CLASSES, 1):
                val = param.DECODE[
                    self.default_df[
                        (self.default_df.from_code == i)
                        & (self.default_df.to_code == j)
                    ]["impact_code"].iloc[0]
                ].get("abrv")

                self.get_children(id_=f"{i}_{j}")[0].val.v_model = val

        # Set default transition matrix
        self.transition_matrix = str(param.TRANSITION_MATRIX_FILE)

    def update_dataframe(self, change):
        """Update dataframe when user changes a value in the matrix and save it to a csv file"""

        # get the value of the matrix
        val = change["new"]

        self.edited_df.loc[
            (self.edited_df.from_code == val["row"])
            & (self.edited_df.to_code == val["col"]),
            "impact_code",
        ] = val["value"]

        self.transition_matrix = str(self.custom_transition_file_path)

        # Here I want to create a new column containing the "transition" code
        # that is the concatenation of the from_code and to_code
        self.edited_df = set_transition_code(self.edited_df)

        self.edited_df[["from_code", "to_code", "impact_code", "transition"]].to_csv(
            self.custom_transition_file_path, index=False
        )

    @observe("disabled")
    def disable_edition(self, change):
        """disable all selectable elements in the table. As we'll have a lot of them
        create execute them as a pool executor"""

        selectables = self.get_children(id_="impact")
        [setattr(s, "disabled", not s.disabled) for s in selectables]

    def truncate_string(self, string):
        """truncate the content if it's too long"""
        return string[:7] + "..." + string[-7:]


class MatrixInput(v.Html):
    v_model = Dict().tag(sync=True)

    def __init__(self, line, column, default_value):
        # get the line and column of the td in the matrix
        self.column = column
        self.line = line
        self.attributes = {"id": f"{line}_{column}"}

        self.val = sw.Select(
            dense=True,
            color="white",
            items=[*[param.DECODE[val].get("abrv") for val in param.DECODE.keys()]],
            class_="ma-1",
            v_model=default_value,
            attributes={"id": "impact"},
        )

        super().__init__(
            style_=f"background-color: {color.primary}",
            tag="td",
            children=[self.val],
        )

        # connect the color to the value
        self.val.observe(self.color_change, "v_model")

    def color_change(self, change):
        """change the color of the td depending on the value of the select"""

        val = [
            key
            for key, value in param.DECODE.items()
            if value.get("abrv") == change["new"]
        ][0]

        color = param.DECODE[val].get("color")

        self.style_ = f"background-color: {color}"

        v_model = {
            "row": self.line,
            "col": self.column,
            "value": val,
        }

        self.v_model = v_model
