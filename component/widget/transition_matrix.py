import concurrent.futures

import ipyvuetify as v
import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from sepal_ui.scripts.decorator import switch
from traitlets import Bool, observe

import component.parameter.directory as dir_
import component.parameter.module_parameter as param


class MatrixInput(v.Html):
    VALUES = {
        "I": (1, color.success),
        "S": (0, color.primary),
        "D": (-1, color.error),
    }

    def __init__(self, line, column, model, default_value):
        # get the io for dynamic modification
        self.model = model

        # get the line and column of the td in the matrix
        self.column = column
        self.line = line
        self.val = sw.Select(
            dense=True,
            color="white",
            items=[*self.VALUES],
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
        val, color = self.VALUES[change["new"]]

        self.style_ = f"background-color: {color}"

        tmp_matrix = self.model.transition_matrix.copy()
        tmp_matrix.loc[
            (tmp_matrix.from_code == self.line) & (tmp_matrix.to_code == self.column),
            "impact_code",
        ] = val

        self.model.transition_matrix = tmp_matrix


class TransitionMatrix(sw.Layout):
    CLASSES = param.LC_COLOR.iloc[:, 0].tolist()
    "list: list of land cover classes names. Comes from lc_classification.csv file"

    DECODE = {1: "I", 0: "S", -1: "D"}
    "dict: dictionary containing the displayed labels for transition classes"

    disabled = Bool(False).tag(sync=True)

    show_matrix = Bool(True).tag(sync=True)
    "bool: either to show or hide the impact matrix and replace by input file widget"

    def __init__(self, model):
        self.class_ = "d-block"
        self.model = model

        self.w_labels = [
            sw.Tooltip(
                v.Html(tag="th", children=[self.truncate_string(class_)]),
                (class_),
                bottom=True,
                max_width=175,
            )
            if len(class_) > 20
            else v.Html(tag="th", children=class_)
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

        # Create input file widget wrapped in a layout
        self.input_impact = sw.FileInput(
            ".csv", folder=dir_.TRANSITION_DIR, root=dir_.RESULTS_DIR
        )
        self.input_impact_layout = sw.Card(
            attributes={"id": "custom_inputs"},
            row=True,
            children=[
                sw.CardTitle(children=["transition file"]),
                sw.CardText(
                    children=[
                        "Select a custom transition file containing all the possible transitions in your custom data. The file must contain the following columns: from_code, to_code, impact_code, columns names have to be exactly the same.",
                        self.input_impact,
                    ]
                ),
            ],
        ).hide()

        self.input_green = sw.FileInput(
            ".csv", folder=dir_.TRANSITION_DIR, root=dir_.RESULTS_DIR
        )
        self.input_green_layout = sw.Card(
            attributes={"id": "custom_inputs"},
            row=True,
            children=[
                sw.CardTitle(children=["Green non green file"]),
                sw.CardText(
                    children=[
                        "Select a custom green non green file containing all your custom land cover classes and its corresponding green/non green classification. The file must contain the following columns: lc_class and green. Columns names have to be exactly the same.",
                        self.input_green,
                    ]
                ),
            ],
        ).hide()

        self.input_impact.observe(
            lambda chg: self.read_inputs(change=chg, type_="impact"), "v_model"
        )
        self.input_green.observe(
            lambda chg: self.read_inputs(change=chg, type_="green"), "v_model"
        )

        # create the simple table
        super().__init__()

        self.children = [
            toolbar,
            self.progress,
            self.input_impact_layout,
            self.input_green_layout,
        ]
        self.set_rows()

        btn_clear.on_event("click", lambda *args: self.set_rows())

        # Link custom inputs with model

    @observe("show_matrix")
    def toggle_viz(self, change):
        """toogle visualization style, show only impact matrix or input_impact_file wiedget"""

        if change["new"]:

            # hide inputs to custom transition matrix and custom green/non green
            [ch.hide() for ch in self.get_children(id_="custom_inputs")]

            [ch.show() for ch in self.get_children(id_="transition_matrix")]

        else:
            # show inputs to custom transition matrix and custom green/non green
            [ch.show() for ch in self.get_children(id_="custom_inputs")]

            [ch.hide() for ch in self.get_children(id_="transition_matrix")]

    def read_inputs(self, change, type_):
        """Read user inputs from custom transition matrix and custom green/non green"""

        # Get TextField from change widget
        text_field_msg = change["owner"].children[-1]
        text_field_msg.error_messages = []

        try:
            df = pd.read_csv(change["new"])
        except pd.errors.ParserError:
            # Raise a more specific error for when the file cannot be parsed as a csv
            error_msg = "The file could not be read. Please check that the file is a valid csv file"
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

        except FileNotFoundError:
            # Raise a more specific error for when the file cannot be found
            error_msg = "The file could not be found. Please check the file path."
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

        # Define column requirements for each type
        column_requirements = {
            "impact": {
                "required_cols": ["from_code", "to_code", "impact_code"],
                "int_cols": ["from_code", "to_code", "impact_code"],
                "allowed_values": {"impact_code": [0, -1, 1]},
            },
            "green": {
                "required_cols": ["lc_class", "green"],
                "int_cols": ["lc_class", "green"],
                "allowed_values": {"green": [0, 1]},
            },
        }

        # Get column requirements for the given type
        req_cols = column_requirements.get(type_, {}).get("required_cols", [])
        allowed_values = column_requirements.get(type_, {}).get("allowed_values", {})

        # Check that the file contains the required columns
        if not set(req_cols).issubset(df.columns):
            error_msg = (
                f"The file must contain the following columns: {', '.join(req_cols)}"
            )
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

        # Check that all values are integers
        for col in df.columns:
            if not pd.api.types.is_integer_dtype(df[col]):

                error_msg = f"The {col} column must contain only integer values."
                text_field_msg.error_messages = error_msg
                raise ValueError(error_msg)

        print(allowed_values)
        # Check that there are no values outside the allowed values in the column requirements
        for col, allowed_vals in allowed_values.items():
            if not set(df[col].unique()).issubset(allowed_vals):

                join_vals = ", ".join([str(val) for val in allowed_vals])
                error_msg = f"The {col} column must contain only the following values: {join_vals}"
                text_field_msg.error_messages = error_msg
                raise ValueError(error_msg)

    @switch("indeterminate", on_widgets=["progress"], targets=[False])
    def set_rows(self, df=param.TRANSITION_MATRIX):
        """create an returns matrix"""

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
                default_value = self.DECODE[
                    df[(df.from_code == i) & (df.to_code == j)]["impact_code"].iloc[0]
                ]
                matrix_input = MatrixInput(i, j, self.model, default_value)
                matrix_input.color_change({"new": default_value})

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

    @observe("disabled")
    def disable_edition(self, change):
        """disable all selectable elements in the table. As we'll have a lot of them
        create execute them as a pool executor"""

        selectables = self.get_children(id_="impact")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(lambda s: setattr(s, "disabled", not s.disabled), selectables)

    def truncate_string(self, string):
        """truncate the content if it's too long"""
        return string[:7] + "..." + string[-7:]
