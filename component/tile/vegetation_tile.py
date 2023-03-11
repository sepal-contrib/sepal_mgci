from typing import Literal

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from ipywidgets import Layout
from traitlets import CBool, Unicode, directional_link, link, observe

import component.parameter.directory as dir_
import component.parameter.module_parameter as param
import component.widget as cw
from component.message import cm
from component.widget.transition_matrix import TransitionMatrix

from . import reclassify_tile as rt

__all__ = ["VegetationTile", "Questionaire"]


class VegetationTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, aoi_model, *args, **kwargs):
        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model

        title = v.CardTitle(children=[cm.veg_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.veg_layer.description)])

        expansion_panel_a = ExpansionIndicator(self.model, self.aoi_model, "sub_a")
        expansion_panel_b = ExpansionIndicator(self.model, self.aoi_model, "sub_b")

        self.veg_parameters = sw.ExpansionPanels(
            v_model=0, children=[expansion_panel_a, expansion_panel_b]
        )

        self.children = [
            v.Card(children=[title, description], class_="pa-2 mb-2"),
            v.Card(
                children=[
                    v.CardTitle(children=[cm.veg_layer.customize.title]),
                    v.CardText(
                        children=[
                            cm.veg_layer.customize.description,
                            self.veg_parameters,
                        ]
                    ),
                ]
            ),
        ]

        expansion_panel_a.view.reclassify_tile.use_default()
        expansion_panel_b.view.reclassify_tile.use_default()


class ExpansionIndicator(sw.ExpansionPanel):
    """Expansion panel to customize subindicator parameters.

    Every expansion panel will have a questionaire with different questions that
    will be used to customize the VegetationView, where is the reclassify tile and
    the transition matrix.
    """

    def __init__(self, model, aoi_model, indicator: Literal["sub_a", "sub_b"]):

        super().__init__()

        self.model = model
        self.aoi_model = aoi_model

        w_questionaire = Questionaire(indicator=indicator)

        self.view = VegetationView(
            model=self.model,
            aoi_model=self.aoi_model,
            questionaire=w_questionaire,
            indicator=indicator,
        )

        self.expanded = False
        self.children = [
            sw.ExpansionPanelHeader(
                children=[
                    cm.veg_layer.sub_a_title
                    if indicator == "sub_a"
                    else cm.veg_layer.sub_b_title
                ]
            ),
            sw.ExpansionPanelContent(
                children=[
                    w_questionaire,
                    self.view,
                ]
            ),
        ]


class VegetationView(v.Layout, sw.SepalWidget):
    def __init__(
        self,
        model,
        aoi_model,
        questionaire,
        indicator: Literal["sub_a", "sub_b"],
        *args,
        **kwargs,
    ):

        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.indicator = indicator
        self.w_questionaire = questionaire

        self.reclassify_tile = rt.ReclassifyTile(
            results_dir=dir_.CLASS_DIR,
            save=False,
            aoi_model=self.aoi_model,
            default_class={
                "IPCC": str(param.LC_CLASSES),
            },
        )

        self.w_reclass = self.reclassify_tile.w_reclass

        self.transition_view = TransitionMatrix(self.model)
        self.transition_view.hide()

        sub_a_tabs = cw.Tabs(
            [cm.veg_layer.tabs.lc_classification],
            [self.reclassify_tile],
        )

        sub_b_tabs = cw.Tabs(
            [cm.veg_layer.tabs.lc_classification, cm.veg_layer.tabs.transition_matrix],
            [self.reclassify_tile, self.transition_view],
        )

        self.children = [sub_a_tabs if self.indicator == "sub_a" else sub_b_tabs]

        directional_link((self.reclassify_tile.model, "matrix"), (self.model, "matrix"))

        # Link with model depending on the indicator
        directional_link(
            (self.reclassify_tile.model, "ic_items"),
            (self.model, f"ic_items_{self.indicator}"),
        )
        directional_link(
            (self.reclassify_tile.model, "dst_class"),
            (self.model, f"lulc_classes_{self.indicator}"),
        )

        self.w_questionaire.observe(self.get_reclassify_view)

        self.model.observe(self.set_default_asset, "dash_ready")

        self.get_reclassify_view()

    def set_default_asset(self, change):
        """listen dash_ready model attribute and change w_ic_select default v_model. It
        will help to fill up the dialog baseline and report years for the very first
        time"""

        if change["new"]:
            self.reclassify_tile.w_reclass.w_ic_select.v_model = str(param.LULC_DEFAULT)
            self.reclassify_tile.use_default()

    def get_reclassify_view(self, change=None):
        """Observe the questionaire answers and display the proper view of the
        reclassify widget.

        Depending if the self.indicator is A or B, the view will be different.
        When the indicator is A, the user will only be able to display the reclassify_tile
        with IPPC classes.

        When the indicator is B, the user will be able to display the reclassify_tile with
        custom classes and the transition matrix.
        """

        custom_lulc = self.w_questionaire.ans_custom_lulc
        transition_matrix = self.w_questionaire.ans_transition_matrix
        need_reclassify = self.w_questionaire.ans_need_reclassify

        self.w_reclass.w_ic_select.disabled = not custom_lulc
        self.w_reclass.w_ic_select.label = cm.reclass_view.ic_custom_label

        # Would you like to use a custom land use/land cover map?
        if custom_lulc:
            hide_show = sw.SepalWidget.show
            self.w_reclass.reclassify_table.set_table({}, {})
        else:
            hide_show = sw.SepalWidget.hide
            self.w_reclass.w_ic_select.v_model = param.LULC_DEFAULT
            self.reclassify_tile.use_default()

        hide_show(self.w_reclass.get_children(id_="btn_get_table")[0])
        hide_show(self.w_reclass.get_children(id_="reclassify_table")[0])

        if self.indicator == "sub_b":

            # Would you like to use a custom land use/land cover map?
            if custom_lulc:

                # Would you like to change the default land cover transition matrix??
                if need_reclassify:

                    # Hide transition matrix
                    self.transition_view.show_matrix = False

                    # TODO: add a loader to load different types of target LC classes

                else:
                    self.w_reclass.get_children(id_="btn_get_table")[0].hide()
                    self.w_reclass.get_children(id_="reclassify_table")[0].hide()

                    # Hide transition matrix
                    self.transition_view.show_matrix = False
            else:

                # Q2: Would you like to change the transition matrix?
                if transition_matrix:
                    # Show transition matrix
                    self.transition_view.show()
                    self.transition_view.show_matrix = True
                    self.transition_view.disabled = False

                else:
                    # show transition matrix but disabled
                    self.transition_view.show()
                    self.transition_view.show_matrix = True
                    self.transition_view.disabled = True

    def display_map(self, *args):
        """Display reclassified raster on map. Get the reclassify visualization
        image.

        .. deprecated:
            this is an orphan method. I will try to use later if requested
        """

        # Manually trigger the reclassify method
        self.reclassify_tile.w_reclass.reclassify(None, None, None)

        # Create a three band representation as this function was removed from the
        # reclassify tool

        reclass_model = self.reclassify_tile.w_reclass.model

        code, desc, color = zip(
            *[
                (str(k), str(v[0]), str(v[1]))
                for k, v in reclass_model.dst_class.items()
            ]
        )

        layer = reclass_model.dst_gee_memory.mask(self.model.kapos_image).visualize(
            **{
                "bands": reclass_model.band,
                "palette": color,
                "min": min(code),
                "max": max(code),
            }
        )

        # Create legend based on the lulc classes.
        self.map_.add_legend(
            legend_title="Legend", legend_dict=dict(self.model.lulc_classes.values())
        )
        # Do this trick to remove the scrolling bar in the legend output
        self.map_.legend_widget.layout = Layout(width="120px", overflow="none")

        # Remove previusly loaded layers
        [self.map_.remove_last_layer() for _ in range(len(self.map_.layers))]

        self.map_.zoom_ee_object(layer.geometry())
        self.map_.addLayer(layer)


class Questionaire(v.Layout, sw.SepalWidget):
    """Vegetation questionaire widget.

    Do some questions to the user, save the answers
    in the traits and use them later to display the proper Vegetation View
    """

    ans_custom_lulc = CBool().tag(sync=True)
    "bool: answer Would you like to use a custom land use/land cover map?"

    ans_transition_matrix = CBool().tag(sync=True)
    "bool: answer do you have a custom land cover transition matrix (.csv)?"

    ans_need_reclassify = CBool().tag(sync=True)
    "bool: answer do you need to reclassify the land cover map?"

    indicator = Unicode().tag(sync=True)

    def __init__(self, indicator: Literal["sub_a", "sub_b"]) -> v.Layout:

        self.class_ = "d-block"
        self.indicator = indicator

        super().__init__()

        # define questions when using sub_a indicator

        # Set widget questions
        self.wq_custom_lulc = cw.BoolQuestion(cm.veg_layer.questionaire.q1)
        self.wq_transition_matrix = cw.BoolQuestion(cm.veg_layer.questionaire.q2).hide()
        self.wq_reclassify = cw.BoolQuestion(cm.veg_layer.questionaire.q3).hide()

        # show by default the second question if "sub_b" indicator is used
        self.indicator == "sub_a" or self.wq_transition_matrix.show()

        self.children = [
            self.wq_custom_lulc,
            self.wq_transition_matrix,
            self.wq_reclassify,
        ]

        link((self.wq_custom_lulc, "v_model"), (self, "ans_custom_lulc"))
        link((self.wq_transition_matrix, "v_model"), (self, "ans_transition_matrix"))
        link((self.wq_reclassify, "v_model"), (self, "ans_need_reclassify"))

    @observe("ans_custom_lulc")
    def toggle_question(self, change):
        """Toggle second question, based on the first answer"""

        if self.indicator == "sub_b":
            if change["new"]:
                self.wq_transition_matrix.hide()
                self.wq_reclassify.show()
            else:
                self.wq_transition_matrix.show()
                self.wq_reclassify.hide()
