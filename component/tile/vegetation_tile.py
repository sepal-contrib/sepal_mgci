import asyncio
from time import sleep
import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import directional_link
from component.model.model import MgciModel

from sepal_ui.scripts.sepal_client import SepalClient
import sepal_ui.scripts.decorator as sd
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.solara import get_current_gee_interface

from component.parameter.directory import dir_
from component.message import cm
from component.widget.questionnaire import Questionnaire
from component.widget.transition_matrix import TransitionMatrix
import component.parameter.module_parameter as param
from component.widget.buttons import TextBtn
import logging

log = logging.getLogger("MGCI.vegetation_tile")


from . import reclassify_tile as rt

__all__ = ["VegetationTile", "questionnaire"]


class VegetationTile(sw.Layout):
    def __init__(
        self,
        model: MgciModel,
        sepal_client: SepalClient = None,
        alert: sw.Alert = None,
        *args,
        **kwargs,
    ):
        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-0 ma-0"

        super().__init__(*args, **kwargs)

        alert = alert or sw.Alert()

        title = v.CardTitle(children=[cm.veg_layer.title])

        desc_sub_a = sw.Markdown(cm.veg_layer.questionnaire.sub_a)
        desc_sub_b = sw.Markdown(cm.veg_layer.questionnaire.sub_b)

        description = v.CardText(children=[desc_sub_a, desc_sub_b])

        self.w_questionnaire = Questionnaire()

        self.vegetation_view = VegetationView(
            model=model,
            aoi_model=model.aoi_model,
            questionnaire=self.w_questionnaire,
            alert=alert,
            sepal_client=sepal_client,
        )

        self.w_vegetation_dialog = VegetationDialog(self.vegetation_view, alert)

        self.btn_get_paramters = sw.Btn(
            cm.veg_layer.questionnaire.btn.label, class_="mt-4", small=True
        )

        self.children = [
            self.w_vegetation_dialog,
            # v.Card(children=[title, description], class_="ma-2"),
            v.Card(
                elevation=0,
                class_="ma-2 pa-0",
                children=[
                    sw.CardTitle(children=[cm.veg_layer.subtitle], class_="px-0 mx-0"),
                    self.w_questionnaire,
                    self.btn_get_paramters,
                ],
            ),
        ]
        # decorate the button
        self.open_settings_dialog = sd.loading_button(
            alert=alert, button=self.btn_get_paramters
        )(self.open_settings_dialog)

        self.btn_get_paramters.on_event("click", self.open_settings_dialog)

    def open_settings_dialog(self, *_):
        """Open the settings dialog"""
        self.w_vegetation_dialog.open_dialog()


class VegetationDialog(sw.Dialog):
    def __init__(self, vegetation_view: "VegetationView", alert, *args, **kwargs):
        kwargs["persistent"] = kwargs.get("persistent", True)
        kwargs["v_model"] = kwargs.get("v_model", False)
        kwargs["max_width"] = 1200

        self.alert = alert

        super().__init__(*args, **kwargs)

        self.btn_close = TextBtn("Validate & close", class_="ma-2")

        self.vegetation_view = vegetation_view
        self.children = [
            sw.Card(
                children=[
                    self.vegetation_view,
                    sw.CardActions(children=[v.Spacer(), self.btn_close]),
                ]
            )
        ]

        # Validate on close
        self.btn_close.on_event("click", self.close_dialog)

    def open_dialog(self, *_):
        """Call vegetation view build and open the dialog."""

        self.v_model = True

    @sd.switch("loading", on_widgets=["btn_close"])
    def close_dialog(self, *_):
        """Close dialog."""

        try:
            self.vegetation_view.validate()
        except Exception as e:
            self.alert.add_msg(str(e), type_="error")
            return

        self.v_model = False


class VegetationView(sw.Layout):
    def __init__(
        self,
        model: MgciModel,
        aoi_model: AoiModel,
        questionnaire: Questionnaire,
        alert: sw.Alert,
        sepal_client: SepalClient = None,
        *args,
        **kwargs,
    ):
        self.class_ = "d-block"
        self.elevation = 0

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.w_questionnaire = questionnaire
        self.alert = alert

        log.debug("Initializing reclassify tile a")

        gee_interface = get_current_gee_interface()

        folder = gee_interface.get_folder()

        log.debug(f"USING GET_CURRENT_GEE_INTERFACE {id(gee_interface)}")

        self.reclassify_tile_a = rt.ReclassifyTile(
            mgci_model=self.model,
            results_dir=dir_.class_dir,
            save=False,
            aoi_model=self.aoi_model,
            default_class={"SEEA": str(param.LC_CLASSES)},
            id_="sub_a",
            alert=self.alert,
            sepal_client=sepal_client,
            folder=folder,
        )

        self.reclassify_tile_a.w_reclass.reclassify_table.btn_load_target.hide()

        log.debug("Initializing reclassify tile b")

        self.reclassify_tile_b = rt.ReclassifyTile(
            mgci_model=self.model,
            results_dir=dir_.class_dir,
            save=False,
            aoi_model=self.aoi_model,
            default_class={"SEEA": str(param.LC_CLASSES)},
            id_="sub_b",
            alert=self.alert,
            sepal_client=sepal_client,
            folder=folder,
        )
        self.reclassify_tile_b.w_reclass.reclassify_table.btn_load_target.show()

        log.debug("Reclassify tile b initialized")

        self.reclassify_tile_b.elevation = 0
        self.reclassify_tile_a.elevation = 0

        self.w_reclass_a = self.reclassify_tile_a.w_reclass
        self.w_reclass_b = self.reclassify_tile_b.w_reclass

        # we will use the same asset for both datasets
        directional_link(
            (self.reclassify_tile_a.w_reclass.w_ic_select, "v_model"),
            (self.reclassify_tile_b.w_reclass.w_ic_select, "v_model"),
        )

        # Use the same asset for both datasets, and same button to get both tables
        # self.reclassify_tile_a.w_reclass.btn_get_table.on_event(
        #     "click", self.on_get_table
        # )

        self.transition_view = TransitionMatrix(model, sepal_client=sepal_client)

        # Define steppers in advance to avoid building on the fly and so avoid
        # long loading times
        self.stepper_a = StepperA(
            w_reclass_a=self.reclassify_tile_a.w_reclass,
            w_reclass_b=self.reclassify_tile_b.w_reclass,
            transition_view=self.transition_view,
            mgci_model=model,
        )

        self.stepper_b = StepperB(
            w_reclass_a=self.reclassify_tile_a.w_reclass,
            w_reclass_b=self.reclassify_tile_b.w_reclass,
            transition_view=self.transition_view,
        )

        self.model.observe(self.set_default_asset, "dash_ready")

        self.w_questionnaire.observe(
            self.on_questionnaire,
            ["ans_custom_lulc", "ans_transition_matrix", "ans_reclassify_custom_lulc"],
        )

        # run the questionnaire once to set the default values
        self.on_questionnaire(None)

        self._configure_task_button()

    async def get_unique_classes(self):
        return await self.reclassify_tile_a.w_reclass.get_unique_classes()

    def _configure_task_button(self):
        def get_reclassify_table():
            def callback(results):
                """
                Display a reclassify table which will lead the user to select
                a local code 'from user' to a target code based on a classes file

                Return:
                    self
                """
                log.debug(f"Setting reclassify table with {results}")

                self.reclassify_tile_a.w_reclass.on_get_classes_done(results)
                self.reclassify_tile_b.w_reclass.on_get_classes_done(results)

                log.debug(
                    f"destination classes set {self.reclassify_tile_b.w_reclass.model.dst_class}"
                )
                log.debug(
                    f"src_class classes set {self.reclassify_tile_b.w_reclass.model.src_class}"
                )

                if not results:
                    self.alert.add_msg(
                        "There's no data available for the selected classes, are you sure the land cover map selected covers the area of interest?",
                        type_="warning",
                    )
                    self.stepper_a.v_model = 1
                    self.stepper_a.disable_reclassify()
                    return

                self.stepper_a.enable_reclassify()
                self.stepper_a.v_model = 2

            gee_interface = get_current_gee_interface()
            return gee_interface.create_task(
                func=self.get_unique_classes,
                key="get_unique_classes",
                on_done=callback,
                on_error=lambda e: self.alert.add_msg(str(e), type_="error"),
            )

        self.reclassify_tile_a.w_reclass.btn_get_table.configure(
            task_factory=get_reclassify_table
        )

    def set_default_asset(self, change):
        """listen dash_ready model attribute and change w_ic_select default v_model. It
        will help to fill up the dialog baseline and report years for the very first
        time"""

        if change["new"]:
            log.debug(
                "==============Setting default asset for reclassify tiles=============="
            )
            self.reclassify_tile_a.use_default()
            self.reclassify_tile_b.use_default()

    def on_questionnaire(self, _):
        """Everytime the questionnaire answers change, we need to reset the reclassify components
        and display the proper view of the stepper.

        Depending if the self.indicator is A or B, the view will be different.
        When the indicator is A, the user will only be able to display the reclassify_tile
        with IPPC classes.

        When the indicator is B, the user will be able to display the reclassify_tile with
        custom classes and the transition matrix.
        """

        # Read the questionnaire answers and display the proper view
        custom_lulc = self.w_questionnaire.ans_custom_lulc
        need_reclassify = self.w_questionnaire.ans_reclassify_custom_lulc
        transition_matrix = self.w_questionnaire.ans_transition_matrix

        # Save answers to the model
        self.model.answer_custom_lulc = custom_lulc
        self.model.answer_transition_matrix = transition_matrix
        self.model.answer_need_reclassify = need_reclassify

        self.stepper_a.reset_reclassify()

        self.w_reclass_a.w_ic_select.disabled = not custom_lulc
        self.w_reclass_b.w_ic_select.disabled = not custom_lulc

        # Would you like to use a custom land use/land cover map?
        if custom_lulc:
            log.debug(
                "((((((QUESTIONNAIRE)))))) Custom land use/land cover map selected"
            )
            if need_reclassify:
                log.debug(
                    "((((((QUESTIONNAIRE)))))) Need to reclassify the custom land use/land cover map"
                )
                self.stepper_a.v_model = 1
                self.children = [self.stepper_a]
                self.transition_view.show_matrix = False
                self.w_reclass_a.show_button()
            else:
                log.debug(
                    "((((((QUESTIONNAIRE)))))) No need to reclassify the custom land use/land cover map"
                )
                self.stepper_b.v_model = 1
                self.children = [self.stepper_b]
                self.w_reclass_a.hide_button()
                self.w_reclass_a.reclassify_table.set_table({}, {})
                self.w_reclass_b.reclassify_table.set_table({}, {})
                self.transition_view.disabled = True
                self.transition_view.set_default_values()
                self.transition_view.show_matrix = True
        else:
            log.debug(
                "((((((QUESTIONNAIRE)))))) No custom land use/land cover map selected"
            )
            self.stepper_b.v_model = 1
            self.children = [self.stepper_b]
            self.w_reclass_a.hide_button()

            self.reclassify_tile_a.use_default()
            self.reclassify_tile_b.use_default()

            # Q2: Would you like to change the transition matrix?
            if transition_matrix:
                log.debug("((((((QUESTIONNAIRE)))))) Transition matrix selected")
                # Show transition matrix
                self.transition_view.show_matrix = True
                self.transition_view.disabled = False

            else:
                log.debug("((((((QUESTIONNAIRE)))))) No transition matrix selected")
                # show transition matrix but disabled
                self.transition_view.disabled = True
                self.transition_view.set_default_values()
                self.transition_view.show_matrix = True

    def validate(self):
        """Validate the questionnaire"""

        custom_lulc = self.w_questionnaire.ans_custom_lulc
        need_reclassify = self.w_questionnaire.ans_reclassify_custom_lulc
        need_change_transition = self.w_questionnaire.ans_transition_matrix

        if custom_lulc:
            if not need_reclassify:
                self.transition_view.set_default_values()

        if not custom_lulc:
            if not need_change_transition:
                self.transition_view.set_default_values()
            self.reclassify_tile_a.use_default()
            self.reclassify_tile_b.use_default()

        if not self.model.lc_asset_sub_a:
            raise ValueError("The land use/land cover map cannot be empty.")

        return True


class Stepper(sw.Stepper):
    def __init__(self, *args, **kwargs):
        self.elevation = 0
        self.style_ = (
            "box-shadow: inherit !important; background-color: inherit !important;"
        )
        super().__init__(*args, **kwargs)

    def set_steps(self, headers: list, steps: list):
        """Set the steps and titles of the stepper"""

        stepper_items = [
            [
                v.StepperStep(children=[c[0]], step=key, editable=True),
                v.StepperContent(key=key, step=key, children=[v.Card(children=[c[1]])]),
            ]
            for key, c in enumerate(zip(headers, steps), 1)
        ]

        # flatten the list
        self.steps = [item for sublist in stepper_items for item in sublist]

        self.children = self.steps

    def toggle_step(self, step_key: int, disable: bool = True):
        log.debug(f"Toggling step {step_key} to {'disabled' if disable else 'enabled'}")

        step = [step for step in self.steps if step.step == step_key]
        if step:
            step[0].editable = not disable


class StepperA(Stepper):
    def __init__(
        self, w_reclass_a, w_reclass_b, transition_view, mgci_model: MgciModel = None
    ):
        self.v_model = 0
        self.steps = {}
        self.mgci_model = mgci_model

        super().__init__(v_model=0, vertical=True)

        self.w_reclass_a = w_reclass_a
        self.w_reclass_b = w_reclass_b
        self.transition_view = transition_view
        self.description = v.CardText(children=[cm.reclass.description])

        headers = [
            cm.veg_layer.stepper.header.data_selection,
            cm.veg_layer.stepper.header.reclassify_a,
            cm.veg_layer.stepper.header.reclassify_b,
            cm.veg_layer.stepper.header.transition_matrix,
        ]

        steps = [
            self.w_reclass_a.w_asset_selection,
            v.Flex(
                class_="d-block",
                children=[
                    self.description,
                    self.w_reclass_a,
                ],
            ),
            self.w_reclass_b,
            self.transition_view,
        ]

        self.set_steps(headers=headers, steps=steps)
        self.disable_reclassify()

        if self.mgci_model:
            self.mgci_model.observe(self.reset_reclassify, "lc_asset_sub_a")

    def reset_reclassify(self, *_):
        """Reset the reclassify tiles when the land cover asset changes"""

        log.debug("Resetting reclassify tiles")
        self.w_reclass_a.reclassify_table.set_table({}, {})
        self.w_reclass_b.reclassify_table.set_table({}, {})

        # Reset the stepper to the first step
        self.v_model = 1

        # Disable the reclassify steps
        self.disable_reclassify()

    def disable_reclassify(self):
        """Disable 2,3,4 steps"""

        self.toggle_step(2, disable=True)
        self.toggle_step(3, disable=True)
        self.toggle_step(4, disable=True)

    def enable_reclassify(self):
        """Enable 2,3,4 steps"""

        self.toggle_step(2, disable=False)
        self.toggle_step(3, disable=False)
        self.toggle_step(4, disable=False)


class StepperB(Stepper):
    def __init__(self, w_reclass_a, w_reclass_b, transition_view):
        self.v_model = 0
        self.steps = {}
        super().__init__(v_model=0, vertical=True)

        self.w_reclass_a = w_reclass_a
        self.w_reclass_b = w_reclass_b
        self.transition_view = transition_view

        headers = [
            cm.veg_layer.stepper.header.data_selection,
            cm.veg_layer.stepper.header.transition_matrix,
        ]

        steps = [
            self.w_reclass_a.w_asset_selection,
            self.transition_view,
        ]

        self.set_steps(headers=headers, steps=steps)
