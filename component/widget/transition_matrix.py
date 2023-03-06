import concurrent.futures

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from sepal_ui.scripts.decorator import switch
from traitlets import Bool, observe

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

        self.input_impact = sw.FileInput(".csv").hide()

        # create the simple table
        super().__init__()

        self.children = [toolbar, self.progress, self.input_impact]
        self.set_rows()

        btn_clear.on_event("click", lambda *args: self.set_rows())

    @observe("show_matrix")
    def toggle_viz(self, change):
        """toogle visualization style, show only impact matrix or input_impact_file wiedget"""

        if change["new"]:
            self.input_impact.hide()
            [ch.show() for ch in self.get_children(id_="transition_matrix")]

        else:
            self.input_impact.show()
            [ch.hide() for ch in self.get_children(id_="transition_matrix")]

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
