import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import directional_link
from component.model.model import MgciModel

import component.parameter.directory as dir_
from component.message import cm
from component.widget.questionnaire import Questionnaire
from component.widget.transition_matrix import TransitionMatrix
from component.widget.custom_widgets import AlertDialog
import component.parameter.module_parameter as param


import sepal_ui.scripts.decorator as sd
from sepal_ui.aoi.aoi_model import AoiModel

from . import reclassify_tile as rt

__all__ = ["VegetationTile", "questionnaire"]


class VegetationTile(sw.Layout):
    def __init__(self, model: MgciModel, *args, **kwargs):
        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        alert = sw.Alert()
        alert_dialog = AlertDialog(w_alert=alert)

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
        )

        self.w_vegetation_dialog = VegetationDialog(self.vegetation_view)

        self.btn_get_paramters = sw.Btn(
            cm.veg_layer.questionnaire.btn.label, class_="ma-2"
        )

        self.children = [
            alert_dialog,
            self.w_vegetation_dialog,
            # v.Card(children=[title, description], class_="ma-2"),
            v.Card(
                class_="ma-2",
                children=[
                    sw.CardTitle(children=[cm.veg_layer.subtitle]),
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
    def __init__(self, vegetation_view: "VegetationView", *args, **kwargs):
        kwargs["persistent"] = kwargs.get("persistent", False)
        kwargs["v_model"] = kwargs.get("v_model", False)
        kwargs["max_width"] = 1200

        super().__init__(*args, **kwargs)

        self.vegetation_view = vegetation_view
        self.children = [self.vegetation_view]

    def open_dialog(self, *_):
        """Call vegetation view build and open the dialog."""

        self.vegetation_view.get_view()
        self.v_model = True

    def close_dialog(self, *_):
        """Close dialog."""
        self.v_model = False


class VegetationView(sw.Layout):
    def __init__(
        self,
        model: MgciModel,
        aoi_model: AoiModel,
        questionnaire: Questionnaire,
        alert: sw.Alert,
        *args,
        **kwargs,
    ):
        self.class_ = "d-block"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.w_questionnaire = questionnaire
        self.alert = alert

        self.reclassify_tile_a = rt.ReclassifyTile(
            mgci_model=self.model,
            results_dir=dir_.CLASS_DIR,
            save=False,
            aoi_model=self.aoi_model,
            default_class={
                "SEEA": str(dir_.LOCAL_LC_CLASSES),
            },
            id_="sub_a",
            alert=self.alert,
        )

        self.reclassify_tile_a.w_reclass.w_ic_select.default_asset = [
            str(param.LULC_DEFAULT)
        ]
        self.reclassify_tile_a.w_reclass.reclassify_table.btn_load_target.hide()

        self.reclassify_tile_b = rt.ReclassifyTile(
            mgci_model=self.model,
            results_dir=dir_.CLASS_DIR,
            save=False,
            aoi_model=self.aoi_model,
            default_class={
                "SEEA": str(dir_.LOCAL_LC_CLASSES),
            },
            id_="sub_b",
            alert=self.alert,
            w_asset_selection=self.reclassify_tile_a.w_reclass.w_asset_selection,
        )
        self.reclassify_tile_b.w_reclass.reclassify_table.btn_load_target.show()

        self.w_reclass_a = self.reclassify_tile_a.w_reclass
        self.w_reclass_b = self.reclassify_tile_b.w_reclass

        # we will use the same asset for both datasets
        directional_link(
            (self.reclassify_tile_a.w_reclass.w_ic_select, "v_model"),
            (self.reclassify_tile_b.w_reclass.w_ic_select, "v_model"),
        )

        # Use the same asset for both datasets, and same button to get both tables
        self.reclassify_tile_a.w_reclass.btn_get_table.on_event(
            "click", self.on_get_table
        )

        self.transition_view = TransitionMatrix(model)

        # Define steppers in advance to avoid building on the fly and so avoid
        # long loading times
        self.stepper_a = StepperA(
            w_reclass_a=self.reclassify_tile_a.w_reclass,
            w_reclass_b=self.reclassify_tile_b.w_reclass,
            transition_view=self.transition_view,
        )

        self.stepper_b = StepperB(
            w_reclass_a=self.reclassify_tile_a.w_reclass,
            w_reclass_b=self.reclassify_tile_b.w_reclass,
            transition_view=self.transition_view,
        )

        self.model.observe(self.set_default_asset, "dash_ready")

        self.w_questionnaire.observe(
            self.on_questionnaire, ["ans_custom_lulc", "ans_transition_matrix"]
        )

    def on_get_table(self, *_):
        """Get reclassify table from both reclassification tables"""

        self.reclassify_tile_a.w_reclass.get_reclassify_table(
            self=self.reclassify_tile_a.w_reclass.get_reclassify_table
        )
        self.reclassify_tile_b.w_reclass.get_reclassify_table(
            self=self.reclassify_tile_b.w_reclass.get_reclassify_table
        )
        self.stepper_a.v_model = 2

    def set_default_asset(self, change):
        """listen dash_ready model attribute and change w_ic_select default v_model. It
        will help to fill up the dialog baseline and report years for the very first
        time"""

        if change["new"]:
            self.reclassify_tile_a.use_default()
            self.reclassify_tile_b.use_default()

    def on_questionnaire(self, _):
        """Everytime the questionnaire answers change, we need to reset the reclassify components"""

        self.w_reclass_a.reclassify_table.set_table({}, {})
        self.w_reclass_b.reclassify_table.set_table({}, {})

        if not self.w_questionnaire.ans_custom_lulc:
            self.reclassify_tile_a.use_default()
            self.reclassify_tile_b.use_default()

    def get_view(self):
        """Read the questionnaire answers and display the proper view of the stepper.

        Depending if the self.indicator is A or B, the view will be different.
        When the indicator is A, the user will only be able to display the reclassify_tile
        with IPPC classes.

        When the indicator is B, the user will be able to display the reclassify_tile with
        custom classes and the transition matrix.

        """

        custom_lulc = self.w_questionnaire.ans_custom_lulc
        transition_matrix = self.w_questionnaire.ans_transition_matrix

        self.w_reclass_a.w_ic_select.disabled = not custom_lulc
        self.w_reclass_b.w_ic_select.disabled = not custom_lulc

        # Would you like to use a custom land use/land cover map?
        if custom_lulc:
            self.stepper_a.v_model = 1
            self.children = [self.stepper_a]

            self.transition_view.show_matrix = False
            self.w_reclass_a.btn_get_table.show()

        else:
            self.stepper_b.v_model = 1
            self.children = [self.stepper_b]
            self.w_reclass_a.btn_get_table.hide()

            # Q2: Would you like to change the transition matrix?
            if transition_matrix:
                # Show transition matrix
                self.transition_view.show_matrix = True
                self.transition_view.disabled = False

            else:
                # show transition matrix but disabled
                self.transition_view.disabled = True
                self.transition_view.set_default_values()
                self.transition_view.show_matrix = True


class Stepper(sw.Stepper):
    def get_steps(self, headers: list, steps: list):
        """Set the steps and titles of the stepper"""

        stepper_items = [
            [
                v.StepperStep(children=[c[0]], step=key, editable=True),
                v.StepperContent(key=key, step=key, children=[v.Card(children=[c[1]])]),
            ]
            for key, c in enumerate(zip(headers, steps), 1)
        ]

        # flatten the list
        return [item for sublist in stepper_items for item in sublist]


class StepperA(Stepper):
    def __init__(self, w_reclass_a, w_reclass_b, transition_view):
        self.v_model = 0
        self.steps = {}
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

        self.children = self.get_steps(headers=headers, steps=steps)


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

        self.children = self.get_steps(headers=headers, steps=steps)
