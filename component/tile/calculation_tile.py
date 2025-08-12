from datetime import datetime

import ee
import ipyvuetify as v
from traitlets import Bool, Int, directional_link, link

import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.decorator as sd
from sepal_ui.scripts.gee_interface import GEEInterface
from sepal_ui.sepalwidgets.btn import TaskButton


from component.parameter.directory import dir_
from component.scripts.deferred_calculation import perform_calculation, task_process
import component.scripts as cs
from component.scripts.validation import validate_calc_params, validate_model
import component.widget as cw
from component.message import cm
from component.model.model import MgciModel

__all__ = ["CalculationTile"]

import logging

log = logging.getLogger("MGCI")


class CalculationView(sw.Card):
    def __init__(
        self, model: MgciModel, sepal_client=None, gee_interface=None, *args, **kwargs
    ):
        """Dashboard tile to calculate and resume the zonal statistics for the
        vegetation layer by biobelt.

        Args:
            model (MgciModel): Mgci Model

        """
        self.sepal_client = sepal_client
        self.gee_interface = gee_interface
        self.class_ = "pa-2"
        self.elevation = 0

        self.attributes = {"id": "calculation_view"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.calculation = cw.Calculation(self.model)

        title = v.CardTitle(children=[cm.dashboard.title], class_="px-0 mx-0")
        description = v.CardText(children=[cm.dashboard.description])

        v.Icon(children=["mdi-help-circle"], small=True)

        # widgets
        self.w_use_rsa = v.Switch(
            v_model=self.model.rsa,
            label=cm.dashboard.label.rsa,
            value=True,
        )

        self.w_background = v.Switch(
            v_model=False,
            label=cm.dashboard.label.background,
            value=False,
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
                    top=True,
                    rigth=False,
                    max_width=300,
                )
            ],
        )

        advanced_options = v.ExpansionPanels(
            class_="my-2",
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
        self.btn = TaskButton(cm.dashboard.label.calculate, small=True)
        self.btn_export = sw.Btn(
            cm.dashboard.label.download, class_="ml-2", disabled=True, small=True
        )

        buttons = v.Flex(
            class_="mt-4",
            children=[
                self.btn,
                self.btn_export,
            ],
        )

        self.alert = cw.Alert()

        self.children = [
            # title,
            # description,
            self.calculation,
            advanced_options,
            buttons,
            self.alert,
        ]

        self.export_results = sd.loading_button(
            alert=self.alert, button=self.btn_export
        )(self.export_results)

        directional_link((self.w_use_rsa, "v_model"), (self.model, "rsa"))

        self.btn_export.on_event("click", self.export_results)
        # self.btn.on_event("click", self.run_statistics)
        self.model.observe(self.activate_download, "done")

        self.model.observe(lambda *_: self.alert.reset(), "sub_a_year")
        self.model.observe(lambda *_: self.alert.reset(), "sub_b_year")

        self._configure_statistics_button()

    def activate_download(self, change):
        """Verify if the process is done and activate button"""
        if change["new"]:
            self.btn_export.disabled = False
            return

        self.btn_export.disabled = True

    def export_results(self, *args):
        """Write the results on a comma separated values file, or an excel file"""

        validate_calc_params(
            self.model.calc_a,
            self.model.calc_b,
            self.model.sub_a_year,
            self.model.sub_b_year,
            None,
        )
        which = (
            "both"
            if self.model.calc_a and self.model.calc_b
            else "sub_a" if self.model.calc_a else "sub_b"
        )

        self.alert.add_msg("Exporting tables...")

        aoi_name = self.model.aoi_model.name
        report_folder = cs.get_report_folder(aoi_name, sepal_client=self.sepal_client)

        if not self.model.aoi_model.feature_collection:
            raise Exception(cm.error.no_aoi)

        output_report_path = cs.export_reports(
            results=self.model.results,
            **self.model.get_data(),
            which=which,
            sepal_client=self.sepal_client,
        )
        log.debug(
            f"Exported results to {output_report_path} for {which} in {report_folder}"
        )
        download_link = su.create_download_link(output_report_path)
        msg = sw.Markdown(
            f"Reporting tables successfull exported {report_folder}, <u><i><a href = '{download_link}'>Click to download</a><i></u>"
        )
        self.alert.add_msg(msg, type_="success")

    async def async_perform_calculation(self):

        area_type = (
            cm.dashboard.label.rsa_name
            if self.w_use_rsa.v_model
            else cm.dashboard.label.plan
        )

        # Catch errors from the ui validation
        sub_b_val_errors = self.calculation.w_content_b.errors

        validate_model(self.model)

        validate_calc_params(
            self.model.calc_a,
            self.model.calc_b,
            self.model.sub_a_year,
            self.model.sub_b_year,
            sub_b_val_errors,
        )

        which = (
            "both"
            if self.model.calc_a and self.model.calc_b
            else "sub_a" if self.model.calc_a else "sub_b"
        )

        if which == "sub_a" or which == "both":
            # Only check matrix if reclassification is needed
            # Custom LULC + No reclassify = matrix not needed
            if self.model.answer_custom_lulc and not self.model.answer_need_reclassify:
                pass  # Matrix not required
            else:
                # Either using default LULC or custom LULC that needs reclassification
                if not self.model.matrix_sub_a or not any(
                    self.model.matrix_sub_a.values()
                ):
                    raise Exception(
                        "No remap matrix for subindicator A, please remap your data in the previous step."
                    )

        if which == "sub_b" or which == "both":
            # Only check matrix if reclassification is needed
            # Custom LULC + No reclassify = matrix not needed
            if self.model.answer_custom_lulc and not self.model.answer_need_reclassify:
                pass  # Matrix not required
            else:
                # Either using default LULC or custom LULC that needs reclassification
                if not self.model.matrix_sub_b or not any(
                    self.model.matrix_sub_b.values()
                ):
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
        # dictionaries of int keys and int values, but only if they're not empty

        if self.model.matrix_sub_a:
            self.model.matrix_sub_a = {
                int(k): int(v) for k, v in self.model.matrix_sub_a.items()
            }

        if self.model.matrix_sub_b:
            self.model.matrix_sub_b = {
                int(k): int(v) for k, v in self.model.matrix_sub_b.items()
            }

        aoi_name = self.model.aoi_model.name
        report_folder = cs.get_report_folder(aoi_name, sepal_client=self.sepal_client)

        now = datetime.now()
        task_filepath = (
            dir_.tasks_dir
            / f"Task_{report_folder.stem}_{now.strftime('%Y-%m-%d-%H%M%S')}_{self.model.session_id}.json"
        )

        scale = None  # Default value

        if not self.w_scale.disabled:
            # Add the output scale to the name
            task_filepath = task_filepath.with_name(
                task_filepath.stem + f"_scale_{self.w_scale.v_model}"
            )
            scale = self.w_scale.v_model

        log.debug(f"Performing calculation with parameters:\n {self.model}")

        # Create a fucntion in order to be able to test it easily
        results = await perform_calculation(
            gee_interface=self.gee_interface,
            aoi=self.model.aoi_model.feature_collection,
            rsa=self.model.rsa,
            dem=self.model.dem,
            remap_matrix_a=self.model.matrix_sub_a,
            remap_matrix_b=self.model.matrix_sub_b,
            transition_matrix=self.model.transition_matrix,
            years=years,
            logger=self.alert,
            background=self.w_background.v_model,
            scale=scale,
        )

        if isinstance(results, ee.FeatureCollection):
            model_state = self.model.get_data()
            await task_process(
                results,
                task_filepath,
                model_state,
                sepal_client=self.sepal_client,
                gee_interface=self.gee_interface,
            )

        return results, task_filepath

    def _configure_statistics_button(self, *args):
        """Start the calculation of the statistics. It will start the process on the fly
        or making a task in the background depending if the rsa is selected or if the
        computation is taking so long."""
        # Clear previous loaded results

        def run_statistics(*args):
            def callback(results):
                results, task_filepath = results
                if isinstance(results, ee.FeatureCollection):
                    msg = sw.Markdown(
                        "The computation could not be completed on the fly. The task <i>'{}'</i> has been tasked in your <a href='https://code.earthengine.google.com/tasks'>GEE account</a>.".format(
                            task_filepath
                        )
                    )

                    self.alert.append_msg(msg, type_="warning")

                elif isinstance(results, dict):
                    self.model.results = results
                    self.model.done = True
                    self.alert.append_msg(
                        "The computation has been completed.", type_="success"
                    )

                else:
                    self.alert.append_msg(
                        "There was an error in one of the steps", type_="error"
                    )

            return self.gee_interface.create_task(
                func=self.async_perform_calculation,
                key="calculate_statistics",
                on_done=callback,
                on_error=lambda e: self.alert.add_msg(str(e), type_="error"),
            )

        self.btn.configure(
            task_factory=run_statistics,
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
