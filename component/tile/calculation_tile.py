from pathlib import Path
from time import sleep

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.decorator as sd
from traitlets import Bool, Int, directional_link, link
import component.parameter.directory as DIR
from component.scripts.deferred_calculation import perform_calculation
import component.scripts as cs
from component.scripts.validation import validate_calc_params
import component.widget as cw
from component.message import cm
from component.model.model import MgciModel

__all__ = ["CalculationTile"]


class CalculationTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, *args, **kwargs):
        self.class_ = "d-block"
        self._metadata = {"mount_id": "calculation_tile"}

        super().__init__(*args, **kwargs)

        self.model = model

        self.calculation_view = CalculationView(self.model)
        self.download_task_view = DownloadTaskView(self.model)

        self.children = [
            cw.Tabs(
                titles=[
                    "Calculation",
                    "Calculation from Task",
                ],
                content=[
                    self.calculation_view,
                    self.download_task_view,
                ],
                class_="mb-2",
            ),
        ]


class CalculationView(sw.Card):
    def __init__(self, model: MgciModel, *args, **kwargs):
        """Dashboard tile to calculate and resume the zonal statistics for the
        vegetation layer by biobelt.

        Args:
            model (MgciModel): Mgci Model

        """

        self.class_ = "pa-2"
        self.attributes = {"id": "calculation_view"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.calculation = cw.Calculation(self.model)

        title = v.CardTitle(children=[cm.dashboard.title])
        description = v.CardText(children=[cm.dashboard.description])

        v.Icon(children=["mdi-help-circle"], small=True)

        # widgets
        self.w_use_rsa = v.Switch(
            v_model=self.model.rsa,
            label=cm.dashboard.label.rsa,
            value=True,
        )

        self.w_background = v.Switch(
            v_model=True,
            label=cm.dashboard.label.background,
            value=True,
        )

        self.w_scale = Slider()

        t_rsa = v.Flex(
            class_="d-flex",
            children=[
                sw.Tooltip(
                    self.w_use_rsa, cm.dashboard.help.rsa, right=True, max_width=300
                )
            ],
        )

        t_background = v.Flex(
            class_="d-flex",
            children=[
                sw.Tooltip(
                    self.w_background,
                    cm.dashboard.help.background,
                    right=True,
                    max_width=300,
                )
            ],
        )

        t_scale = v.Flex(
            class_="d-flex",
            children=[
                sw.Tooltip(
                    self.w_scale,
                    cm.dashboard.help.scale,
                    right=True,
                    max_width=300,
                )
            ],
        )

        advanced_options = v.ExpansionPanels(
            class_="mb-2",
            v_model=True,
            children=[
                v.ExpansionPanel(
                    children=[
                        v.ExpansionPanelHeader(
                            children=[cm.dashboard.advanced_options]
                        ),
                        v.ExpansionPanelContent(
                            children=[
                                t_rsa,
                                t_background,
                                t_scale,
                            ]
                        ),
                    ]
                )
            ],
        )

        # buttons
        self.btn = sw.Btn(cm.dashboard.label.calculate)
        self.btn_export = sw.Btn(
            cm.dashboard.label.download, class_="ml-2", disabled=True
        )

        self.alert = cw.Alert()

        self.children = [
            title,
            # description,
            self.calculation,
            advanced_options,
            self.btn,
            self.btn_export,
            self.alert,
        ]

        self.export_results = sd.loading_button(
            alert=self.alert, button=self.btn_export
        )(self.export_results)

        directional_link((self.w_use_rsa, "v_model"), (self.model, "rsa"))

        self.btn_export.on_event("click", self.export_results)
        self.btn.on_event("click", self.run_statistics)
        self.model.observe(self.activate_download, "done")

        self.model.observe(lambda *_: self.alert.reset(), "sub_a_year")
        self.model.observe(lambda *_: self.alert.reset(), "sub_b_year")

    def activate_download(self, change):
        """Verify if the process is done and activate button"""
        if change["new"]:
            self.btn_export.disabled = False
            return

        self.btn_export.disabled = True

    @su.loading_button()
    def export_results(self, *args):
        """Write the results on a comma separated values file, or an excel file"""

        self.alert.add_msg("Exporting tables...")

        report_folder = cs.get_report_folder(self.model)

        if not self.model.aoi_model.feature_collection:
            raise Exception(cm.error.no_aoi)

        cs.export_reports(self.model, report_folder)

        self.alert.add_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )

    @su.loading_button()
    def run_statistics(self, *args):
        """Start the calculation of the statistics. It will start the process on the fly
        or making a task in the background depending if the rsa is selected or if the
        computation is taking so long."""
        # Clear previous loaded results

        area_type = (
            cm.dashboard.label.rsa_name
            if self.w_use_rsa.v_model
            else cm.dashboard.label.plan
        )

        # Catch errors from the ui validation
        sub_b_val = self.get_children(id_="custom_list_sub_b")[0]

        validate_calc_params(
            self.model.calc_a,
            self.model.calc_b,
            self.model.sub_a_year,
            self.model.sub_b_year,
            sub_b_val,
        )

        which = (
            "both"
            if self.model.calc_a and self.model.calc_b
            else "sub_a" if self.model.calc_a else "sub_b"
        )

        if which == "sub_a" or which == "both":
            if not self.model.matrix_sub_a:
                raise Exception(
                    "No remap matrix for subindicator A, please remap your data in the previous step."
                )

        if which == "sub_b" or which == "both":
            if not self.model.matrix_sub_b:
                raise Exception(
                    "No remap matrix for subindicator B, please remap your data in the previous step."
                )
            if not self.model.transition_matrix:
                raise Exception(
                    "No transition matrix for subindicator B, please upload one in the previous step."
                )

        # Calculate regions
        head_msg = sw.Flex(children=[cm.dashboard.alert.computing.format(area_type)])

        self.alert.add_msg(head_msg)

        sub_a_years = cs.get_a_years(self.model.sub_a_year)
        sub_b_years = cs.get_b_years(self.model.sub_b_year)

        # Define a dictionary to map 'which' values to 'years' values
        which_to_years = {
            "both": sub_a_years + sub_b_years,
            "sub_a": sub_a_years,
            "sub_b": sub_b_years,
        }

        # Get the 'years' value for the given 'which' value
        years = which_to_years.get(which)

        # Reset results
        self.model.results, results = {}, {}
        self.model.done = False

        # As pre step, make sure model.matrix_sub_a and model.matrix_sub_b are
        # dictionaries of int keys and int values

        self.model.matrix_sub_a = {
            int(k): int(v) for k, v in self.model.matrix_sub_a.items()
        }

        self.model.matrix_sub_b = {
            int(k): int(v) for k, v in self.model.matrix_sub_b.items()
        }

        report_folder = cs.get_report_folder(self.model)
        task_filepath = (
            DIR.TASKS_DIR / f"Task_{report_folder.stem}_{self.model.session_id}.csv"
        )

        scale = None  # Default value

        if not self.w_scale.disabled:
            # Add the output scale to the name
            task_filepath = task_filepath.with_name(
                task_filepath.stem + f"_scale_{self.w_scale.v_model}"
            )
            scale = self.w_scale.v_model

        # Create a fucntion in order to be able to test it easily
        results = perform_calculation(
            aoi=self.model.aoi_model.feature_collection,
            rsa=self.model.rsa,
            dem=self.model.dem,
            remap_matrix_a=self.model.matrix_sub_a,
            remap_matrix_b=self.model.matrix_sub_b,
            transition_matrix=self.model.transition_matrix,
            years=years,
            task_filepath=task_filepath,
            logger=self.alert,
            background=self.w_background.v_model,
            scale=scale,
        )

        # If result is None, we assume the computation was tasked

        if not all(results.values()):
            task_filename = task_filepath.with_suffix(".csv")

            msg = sw.Markdown(
                "The computation could not be completed on the fly. The task <i>'{}'</i> has been tasked in your <a href='https://code.earthengine.google.com/tasks'>GEE account</a>.".format(
                    task_filename
                )
            )

            self.alert.append_msg(msg, type_="warning")

        elif all(results.values()):
            self.model.results = results
            self.model.done = True
            self.alert.append_msg(
                "The computation has been performed.", type_="success"
            )

        else:
            self.alert.append_msg(
                "There was an error in one of the steps", type_="error"
            )


class DownloadTaskView(v.Card):
    def __init__(self, model, *args, **kwargs):
        """
        Download tile tab: to search and select the tasks_id file, check if the task is
        complete and then download the file.

        """
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.model = model

        # Widgets
        title = v.CardTitle(children=[cm.dashboard.tasks.title])
        description = v.CardText(
            children=[sw.Markdown(cm.dashboard.tasks.description.format(DIR.TASKS_DIR))]
        )

        v.Icon(children=["mdi-help-circle"], small=True)

        self.w_file_input = sw.FileInput(
            folder=DIR.TASKS_DIR, extentions=[".csv"], root=DIR.RESULTS_DIR
        )

        self.alert = sw.Alert()
        self.alert.add_msg(cm.dashboard.tasks.warning, type_="warning")

        self.btn = sw.Btn(cm.dashboard.label.calculate_from_task)

        self.children = [
            title,
            description,
            self.alert,
            self.w_file_input,
            self.btn,
        ]

        self.btn.on_event("click", self.run_statistics)

    @su.loading_button()
    def run_statistics(self, *_):
        """From the gee result dictionary, extract the values and give a proper
        format in a pd.DataFrame.

        Args:
            process (ee.reduceRegion): ee process (without execution).
            task_file (path, str): full path of task file containing task_id(s)
        """

        self.model.done = False
        self.model.results = {}

        # Get and read file
        tasks_file = Path(self.w_file_input.v_model)
        task_df = self.model.read_tasks_file(tasks_file)

        task_id = task_df.iloc[0, 1]
        process_id = task_df.iloc[0, 0]

        # re-build the filename
        task_filename = f"{tasks_file.stem}.csv"

        # Dowload from file
        msg = cw.TaskMsg(f"Processing {process_id}..", process_id)
        self.alert.append_msg(msg)

        result_file = self.model.download_from_task_file(
            task_id, tasks_file, task_filename
        )

        self.model.results = cs.read_from_csv(result_file)
        msg.set_state("success")
        self.model.done = True

        # Write the results on a comma separated values file, or an excel file

        self.alert.append_msg("Exporting tables...")

        report_folder = cs.get_report_folder(self.model)

        if not self.model.aoi_model.feature_collection:
            raise Exception(cm.error.no_aoi)

        cs.export_reports(self.model, report_folder)

        self.alert.add_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )


class Slider(v.Row):

    v_model = Int().tag(sync=True)
    disabled = Bool().tag(sync=True)

    def __init__(self, *args, **kwargs):

        # self.class_ = "d-flex pa-4"
        self.no_gutters = True
        self.align = "center"

        self.slider = v.Slider(
            label=cm.dashboard.label.scale,
            class_="mt-5",
            v_model=90,
            min=30,
            max=10000,
            thumb_label="always",
            step=10,
            disabled=True,
        )

        switch = v.Switch(
            class_="mt-5",
            v_model=False,
            value=True,
        )

        self.children = [switch, self.slider]

        super().__init__(*args, **kwargs)

        switch.observe(self.toggle_slider, "v_model")
        link((self.slider, "v_model"), (self, "v_model"))
        link((self.slider, "disabled"), (self, "disabled"))

    def toggle_slider(self, change):
        """de/activate slider according with the user's input in switch"""

        self.slider.disabled = not change["new"]
