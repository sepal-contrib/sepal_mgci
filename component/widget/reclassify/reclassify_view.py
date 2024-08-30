from copy import deepcopy
from pathlib import Path

import ipyvuetify as v
import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from sepal_ui.scripts import utils as su
import sepal_ui.scripts.decorator as sd
from sepal_ui.scripts.decorator import loading_button, switch
from traitlets import Unicode, directional_link

from component.scripts.validation import (
    validate_remapping_table,
    validate_target_class_file,
)
import component.parameter.directory as dir_
import component.scripts.frequency_hist as scripts
from component.message import cm
from component.parameter.reclassify_parameters import MATRIX_NAMES
from component.widget.reclassify.reclassify_model import ReclassifyModel
from component.widget.base_dialog import BaseDialog

__all__ = ["ReclassifyView"]


class ReclassifyView(sw.Card):
    """Stand-alone Card object allowing the user to reclassify a input file.

    The input can be of any type (vector or raster) and from any source (local or GEE).
    The user need to provide a destination classification file (table) in the following format : 3 headless columns: 'code', 'desc', 'color'. Once all the old class have been attributed to their new class the file can be exported in the source format to local memory or GEE. the output is also savec in memory for further use in the app. It can be used as a tile in a sepal_ui app. The id\_ of the tile is set to "reclassify_tile"

    Args:
        model (ReclassifyModel): the reclassify model to manipulate the
            classification dataset. default to a new one
        class_path (str,optional): Folder path containing already existing
            classes. Default to ~/
        out_path (str,optional): the folder to save the created classifications.
            default to ~/downloads
        gee (bool): either or not to set :code:`gee` to True. default to False
        dst_class (str|pathlib.Path, optional): the file to be used as destination classification. for app that require specific code system the file can be set prior and the user won't have the oportunity to change it
        default_class (dict|optional): the default classification system to use, need to point to existing sytem: {name: absolute_path}
        folder(str, optional): the init GEE asset folder where the asset selector should start looking (debugging purpose)
        save (bool, optional): Whether to write/export the result or not.
        enforce_aoi (bool, optional): either or not an aoi should be set to allow the reclassification
    """

    MAX_CLASS = 20
    "int: the number of line in the table to trigger the display of an extra toolbar and alert"

    model = None
    "ReclassifyModel: the reclassify model to manipulate the classification dataset"

    gee = None
    "bool: either being linked to gee or not (use local file or GEE asset for the rest of the app)"

    alert = None
    "sw.Alert: the alert to display informations about computation"

    title = None
    "sw.Cardtitle: the title of the card"

    reclassify_table = None
    "ReclassifyTable: the reclassification table populated via the previous widgets"

    def __init__(
        self,
        model: ReclassifyModel = None,
        class_path=Path.home(),
        out_path=dir_.MATRIX_DIR,
        gee=False,
        dst_class=None,
        default_class={},
        aoi_model=None,
        save=True,
        folder=None,
        enforce_aoi=False,
        id_="",
        alert: sw.Alert = None,
        **kwargs,
    ):
        # create metadata to make it compatible with the framwork app system
        self._metadata = {"mount_id": "reclassify_tile"}
        self.attributes = {"id": f"reclassify_view_{id_}"}

        # init card parameters
        self.class_ = "pa-5"

        # create the object
        super().__init__(**kwargs)

        # set up a default model
        self.model = model or ReclassifyModel(
            gee=gee,
            dst_dir=out_path,
            aoi_model=aoi_model,
            folder=folder,
            save=save,
            enforce_aoi=enforce_aoi,
        )

        if enforce_aoi != self.model.enforce_aoi:
            raise Exception(
                "Both reclassify_model.gee and reclassify_view parameters has to be equals."
                + f"Received {enforce_aoi} for reclassify_view and {self.model.enforce_aoi} for reclassify_model."
            )
        # set the folders
        self.class_path = Path(class_path)
        self.out_path = Path(out_path)

        # save the gee binding
        self.gee = gee
        if gee:
            su.init_ee()
        # create an alert to display information to the user
        self.alert = alert or sw.Alert()
        self.btn_get_table = Btn(
            children=[cm.reclass.get_classes],
            color="primary",
            small=True,
            class_="ml-2",
            attributes={"id": "btn_get_table"},
        )

        self.w_ic_select = sw.AssetSelect(
            types=["IMAGE_COLLECTION"],
            label=cm.reclass_view.ic_default_label,
            disabled=True,
        )

        # Reuse component from a different instance or create a new one
        self.w_asset_selection = sw.Flex(
            class_="d-flex align-center mx-2",
            children=[self.w_ic_select, self.btn_get_table],
        )

        # Create a list of buttons containing the different types of
        # target land cover classes

        self.reclassify_table = ReclassifyTable(self.model)

        self.save_dialog = SaveMatrixDialog(folder=out_path, error_alert=self.alert)
        self.import_dialog = ImportMatrixDialog(
            model=self.model,
            folder=out_path,
            error_alert=self.alert,
            attributes={"id": "2"},
        )
        self.target_dialog = TargetClassesDialog(
            model=self.model,
            reclassify_table=self.reclassify_table,
            error_alert=self.alert,
            default_class=default_class,
        )

        # create the layout
        self.children = [
            self.reclassify_table,
            self.save_dialog,
            self.import_dialog,
            self.target_dialog,
        ]

        # Decorate functions
        self.get_reclassify_table = loading_button(self.alert, self.btn_get_table)(
            self.get_reclassify_table
        )

        # Decorate functions
        self.load_matrix_content = loading_button(
            self.alert, self.import_dialog.action_btn
        )(self.load_matrix_content)

        self.import_dialog.action_btn.on_event("click", self.load_matrix_content)
        self.reclassify_table.btn_load_table.on_event(
            "click", lambda *_: self.import_dialog.open_dialog()
        )

        self.reclassify_table.btn_save_table.on_event(
            "click", lambda *_: self.save_dialog.open_dialog(self.model.matrix)
        )

        self.reclassify_table.btn_load_target.on_event(
            "click", lambda *_: self.target_dialog.open_dialog()
        )

        # link feature collection asset selection with model
        directional_link((self.w_ic_select, "v_model"), (self.model, "src_gee"))

        # Reset table everytime an image image collection is changed.
        self.w_ic_select.observe(self.set_ids, "v_model")

    def load_matrix_content(self, *_):
        if not self.import_dialog.w_map_matrix_file.v_model:
            raise Exception(cm.reclass.dialog.import_.error.no_file)

        # exit if no table is loaded
        if not self.model.table_created:
            raise Exception(cm.reclass.dialog.import_.error.no_table)

        if not self.model.matrix_file:
            raise Exception(cm.reclass.dialog.import_.error.no_valid)

        input_data = pd.read_csv(self.model.matrix_file)

        # check that the destination values are all available
        widget = list(self.reclassify_table.class_select_list.values())[0]
        classes = [i["value"] for i in widget.items]
        if not all(v in classes for v in input_data.to_code.unique()):
            # get the missing values
            missing_values = ",".join(
                [str(v) for v in input_data.to_code.unique() if v not in classes]
            )
            raise Exception(
                f"Some of the target land cover classes ({missing_values}) are not present in the destination land cover classes."
            )

        # fill the data
        for _, row in input_data.iterrows():
            src_code, dst_code = row.from_code, row.to_code
            if str(src_code) in self.reclassify_table.class_select_list:
                self.reclassify_table.class_select_list[str(src_code)].v_model = (
                    dst_code
                )

        self.import_dialog.close_dialog()

    def set_ids(self, change):
        """set image collection ids to ic_items model attribute on change. set empty
        table"""

        self.model.ic_items = scripts.get_image_collection_ids(change["new"])
        self.reclassify_table.set_table({}, {})

    @sd.switch("loading", "disabled", on_widgets=["w_code"])
    def _update_band(self, change):
        """Update the band possibility to the available bands/properties of the input"""

        # guess the file type and save it in the model
        self.model.get_type()
        # update the bands values
        self.w_code.v_model = None
        self.w_code.items = self.model.get_bands()

        return self

    @sd.switch("table_created", on_widgets=["model"], targets=[True])
    def get_reclassify_table(self, *_):
        """
        Display a reclassify table which will lead the user to select
        a local code 'from user' to a target code based on a classes file

        Return:
            self
        """

        image_collection = self.w_ic_select.v_model

        # get the destination classes
        self.model.dst_class = self.model.get_classes()

        # get the src_classes and selected image collection items (aka images)
        self.model.src_class = scripts.get_unique_classes(
            self.model.aoi_model.feature_collection, image_collection
        )

        self.reclassify_table.set_table(self.model.dst_class, self.model.src_class)

        return self

    def nest_tile(self):
        """
        Prepare the view to be used as a nested component in a tile.
        the elevation will be set to 0 and the title remove from children.
        The mount_id will also be changed to nested

        Return:
            self
        """

        # remove id
        self._metadata["mount_id"] = "nested_tile"

        # remove elevation
        self.elevation = False

        # remove title
        without_title = self.children.copy()
        without_title.remove(self.title)
        self.children = without_title

        return self


class ImportMatrixDialog(BaseDialog):
    """
    Dialog to select the file to use and fill the matrix

    Args:
        folder (pathlike object): the path to the saved classifications

    Attributes:
        file (str): the file to use
        error_alert (sw.Alert): the alert to display errors
    """

    file = Unicode("").tag(sync=True)

    def __init__(self, model: ReclassifyModel, folder, error_alert: sw.Alert, **kwargs):
        self.model = model

        self.w_map_matrix_file = sw.FileInput(
            label="filename",
            folder=folder,
            attributes={"id": "1"},
            root=dir_.RESULTS_DIR,
        )

        content = [self.w_map_matrix_file]

        super().__init__(
            title=cm.reclass.dialog.import_.title,
            action_text=cm.reclass.dialog.import_.btn_label,
            content=content,
        )

        # Decorate load_matrix_content with loading button
        self.cancel_btn.on_event("click", lambda *_: self.close_dialog())
        self.w_map_matrix_file.observe(self.on_validate_input, "v_model")

    def on_validate_input(self, change):
        """Load the content of the file in the matrix. The table need to be already set
        to perform this operation"""

        self.model.matrix_file = ""

        if not change["new"]:
            return

        # Get TextField from change widget
        text_field_msg = change["owner"].children[-1]
        text_field_msg.error_messages = []

        self.model.matrix_file = validate_remapping_table(change["new"], text_field_msg)

    def open_dialog(self):
        """show the dialog and set the matrix values"""
        self.w_map_matrix_file.unobserve(self.on_validate_input, "v_model")

        # Reset file name
        self.w_map_matrix_file.v_model = ""

        self.w_map_matrix_file.observe(self.on_validate_input, "v_model")

        super().open_dialog()


class SaveMatrixDialog(BaseDialog):
    """
    Dialog to setup the name of the output matrix file

    Args:
        folder (pathlike object): the path to the save folder. default to ~/
    """

    def __init__(self, error_alert: sw.Alert, folder=Path.home(), **kwargs):
        # save the matrix
        self._matrix = {}
        self.folder = Path(folder)

        # create the widgets
        self.w_file = sw.TextField(
            label=cm.reclass.dialog.save.w_file_label, v_model=None
        )

        self.alert = sw.Alert(children=[cm.reclass.dialog.save.alert.default]).show()

        content = [self.w_file, self.alert]

        # create the dialog
        super().__init__(
            title=cm.reclass.dialog.save.title,
            action_text=cm.reclass.dialog.save.btn_label,
            content=content,
            **kwargs,
        )

        # decorate the buttons with the loading button decorator
        self._save = loading_button(error_alert, self.action_btn)(self._save)

        # js behaviour
        self.action_btn.on_event("click", self._save)
        self.cancel_btn.on_event("click", self.close_dialog)

        self.w_file.on_event("blur", self._sanitize)
        self.w_file.observe(self._store_info, "v_model")

    def _store_info(self, change):
        """Display where will be the file written"""

        new_val = change["new"]

        out_file = self.folder / f"{su.normalize_str(new_val)}.csv"

        msg = sw.Markdown(
            cm.reclass.dialog.save.alert.active.format(out_file.parent, out_file.name)
        )

        if not new_val:
            msg = cm.reclass.dialog.save.alert.default
        self.alert.add_msg(msg)

    def close_dialog(self, *_):
        """do nothing and exit"""

        self.w_file.v_model = ""
        super().close_dialog()

    def _save(self, *_):
        """save the matrix in a specified file"""

        if not self._matrix:
            raise Exception(cm.reclass.dialog.save.error.no_matrix)

        if not self.w_file.v_model:
            raise Exception(cm.reclass.dialog.save.error.no_name)

        file = self.folder / f"{su.normalize_str(self.w_file.v_model)}.csv"

        matrix = pd.DataFrame.from_dict(self._matrix, orient="index").reset_index()
        matrix.columns = MATRIX_NAMES
        matrix.to_csv(file, index=False)

        # hide the dialog
        super().close_dialog()

        return self

    def open_dialog(self, matrix):
        """show the dialog and set the matrix values"""

        self._matrix = matrix

        # Reset file name
        self.w_file.v_model = ""

        super().open_dialog()

    def _sanitize(self, *_):
        """sanitize the used name when saving"""

        if not self.w_file.v_model:
            return self
        self.w_file.v_model = su.normalize_str(self.w_file.v_model)

        return self


class TargetClassesDialog(BaseDialog):
    """Custom dialog to select target Land Cover classification classes

    Args:
        default_class (dict): classes and path to default classes files (multiple classifications)
        reclassify_table (ReclassifyTable): used to call set_target_classes method from here.
    """

    def __init__(
        self,
        model,
        reclassify_table,
        error_alert: sw.Alert,
        default_class: dict = {},
    ):
        self.attributes = {"id": "target_classes_dialog"}
        self.model = model
        self.reclassify_table = reclassify_table

        # Create an alert to display errors
        self.alert = sw.Alert()

        # from default_class dictionary get the first value (it's the path of the default)
        self.dst_class_file = list(default_class.values())[0]

        self.w_dst_class_file = sw.FileInput(
            [".csv"],
            label=cm.rec.rec.input.classif.label,
            folder=dir_.RESULTS_DIR,
            root=dir_.RESULTS_DIR,
        )
        self.w_dst_class_file.select_file(self.dst_class_file)

        self.btn_list = [
            sw.Btn(
                msg=f"use {name}",
                _metadata={"path": path},
                small=True,
                class_="mr-2",
                outlined=True,
            )
            for name, path in default_class.items()
        ] + [
            sw.Btn(
                msg="Custom",
                _metadata={"path": "custom"},
                small=True,
                class_="mr-2",
                outlined=True,
            )
        ]

        self.w_default = v.Flex(class_="mt-5", children=self.btn_list)

        content = [
            cm.reclass.dialog.target.description,
            self.w_default,
            self.w_dst_class_file,
            self.alert,
        ]

        super().__init__(
            title=cm.reclass.tooltip.load_target.title,
            action_text=cm.reclass.dialog.target.btn_label,
            content=content,
        )

        # Events
        [btn.on_event("click", self._set_dst_class_file) for btn in self.btn_list]

        self.btn_list[0].fire_event("click", None)

        self.cancel_btn.on_event("click", lambda *_: self.close_dialog())

        self.action_btn.on_event("click", self.set_dst_items_event)

        # Decorate set_dst_items_event with loading button
        self.set_dst_items_event = loading_button(
            alert=self.alert, button=self.action_btn
        )(self.set_dst_items_event)

        self.w_dst_class_file.observe(self.on_validate_input, "v_model")

    def close_dialog(self, to_default=True, *_):
        """Set the default destination class file and close the dialog.

        Args:
            to_default (bool): whether to set the default class file or not. default to True
        """

        to_default and self.w_dst_class_file.select_file(self.dst_class_file)
        super().close_dialog()

    def on_validate_input(self, change):
        """Validate the input file and display error message if needed"""

        self.model.dst_class_file = None

        # Get TextField from change widget
        text_field_msg = change["owner"].children[-1]
        text_field_msg.error_messages = []

        self.model.dst_class_file = validate_target_class_file(
            change["new"], text_field_msg
        )

    def set_dst_items_event(self, *_):
        """Set the event to update the destination class file"""

        if not self.model.dst_class_file:
            return

        self.reclassify_table.set_target_classes()
        self.close_dialog(to_default=False)

    def _set_dst_class_file(self, widget: v.VuetifyWidget, *args):
        """
        Set the destination classification according to the one selected with btn.

        Alter the widgets properties to reflect this change.
        """
        # get the filename
        filename = widget._metadata["path"]

        if filename == "custom":
            self.w_dst_class_file.show()
        else:
            self.w_dst_class_file.hide()
            self.w_dst_class_file.select_file(filename)

        # change the visibility of the btns
        for btn in self.btn_list:
            btn.outlined = False if btn == widget else True

        return self


class ReclassifyTable(sw.Layout):
    """
    Table to store the reclassifying information.
    2 columns are integrated, the new class value and the values in the original input
    One can select multiple class to be reclassify in the new classification

    Args:
        model (ReclassifyModel): model embeding the traitlet dict to store the reclassifying matrix. keys: class value in dst, values: list of values in src.
        dst_classes (dict|optional): a dictionnary that represent the classes of new the new classification table as {class_code: (class_name, class_color)}. class_code must be ints and class_name str.
        src_classes (dict|optional): the list of existing values within the input file {class_code: (class_name, class_color)}

    Attributes:
        HEADER (list): name of the column header (from, to)
        model (ReclassifyModel): the reclassifyModel object to manipulate the
            input file and save parameters
    """

    HEADERS = cm.rec.rec.headers

    def __init__(self, model: ReclassifyModel, **kwargs):
        self.class_ = "d-block"
        self.attributes = {"id": "reclassify_table"}

        # create the table
        super().__init__(**kwargs)

        # save the model
        self.model = model

        default_lc_dialog = InfoDialog()

        # Create button to show the default classification
        self.btn_info = (
            sw.Btn(
                gliph="mdi-information",
                icon=True,
                color="primary",
                class_="mr-2",
            )
            .set_tooltip(cm.reclass.tooltip.info, bottom=True)
            .hide()
        )

        # Create button to save the matrix from a file
        self.btn_save_table = sw.Btn(
            gliph="mdi-content-save",
            icon=True,
            color="primary",
            class_="mr-2",
        ).set_tooltip(cm.reclass.tooltip.save_matrix, bottom=True)

        # Create button to load the matrix from a file
        self.btn_load_table = sw.Btn(
            gliph="mdi-upload",
            icon=True,
            color="primary",
        ).set_tooltip(cm.reclass.tooltip.load_matrix, bottom=True)

        # Create a button to load target classes
        self.btn_load_target = (
            sw.Btn(
                gliph="mdi-table",
                icon=True,
                color="primary",
                attributes={"id": "btn_load_target"},
            )
            .set_tooltip(cm.reclass.tooltip.load_target.btn, bottom=True)
            .hide()
        )

        self.message = sw.Html(tag="span", style_=f"color: {color.warning}")

        self.toolbar = v.Toolbar(
            flat=True,
            children=[
                default_lc_dialog,
                cm.reclass.title,
                v.Spacer(),
                v.Divider(vertical=True, class_="mx-2"),
                self.btn_info.with_tooltip,
                self.btn_load_target.with_tooltip,
                self.btn_save_table.with_tooltip,
                self.btn_load_table.with_tooltip,
            ],
        )

        self.progress = sw.ProgressLinear(v_model=False, height=5, color="error")

        # create the table elements

        self.headers = [
            v.Html(
                tag="thead",
                children=[
                    v.Html(
                        tag="tr",
                        children=[v.Html(tag="th", children=[h]) for h in self.HEADERS],
                    ),
                ],
            )
        ]

        self.table = sw.SimpleTable(
            dense=True,
            class_="elevation-1",
            fixed_header=True,
            height="300px",
        )

        self.children = [self.toolbar, self.progress, self.table]
        self.set_table({}, {})

        self.model.observe(self.set_info_message, "matrix")
        self.progress.observe(self.set_progress_color, "v_model")
        self.btn_info.on_event("click", lambda *_: default_lc_dialog.open_dialog())

    def set_progress_color(self, change):
        """set progress bar colors based on v_model trait instead of setting when
        table changes"""

        if change["new"] == 0:
            self.progress.color = "error"
        elif change["new"] < 100:
            self.progress.color = "warning"
        else:
            self.progress.color = "success"

    def set_info_message(self, change):
        """sets info message in table header. If a destination class is empty, it will
        return a warning message."""

        total_classes = len(change["new"])
        filled = len([clss for clss in change["new"].values() if clss])

        if filled == total_classes == 0:
            # Case when there are not source classes
            self.message.children = []
            self.progress.v_model = 0

        elif filled < total_classes:
            classes_msg = f"{filled} of {total_classes}"
            self.message.children = [cm.reclass.non_complete.format(classes_msg)]
            self.progress.v_model = round(filled / total_classes * 100)

        elif filled == total_classes:
            self.message.children = []
            self.progress.v_model = 100

    def set_target_classes(self):
        """Get all select_select_target_class widgets and set their items.

        It will receive target items coming from TargetClassesDialog and set them
        to all select_select_target_class widgets.

        This method is called when the user clicks on the "Load target classes" button
        and in the TargetClassesDialog.

        Remember that this methos has to be called only when there is a dst_classes file
        selected and therefore part of the model.
        """

        # Get all select_select_target_class widgets
        select_target_classes = self.get_children(id_="select_target_class")

        # Get target classes from model
        self.model.dst_class = self.model.get_classes()

        # Check that there are widgets
        if select_target_classes:
            # Create items from self.model.get_classes()

            target_classes_items = [
                {"text": f"{code} - {name}", "value": code}
                for code, (name, _) in self.model.dst_class.items()
            ]

            # Set items to all widgets
            for select in select_target_classes:
                select.v_model = 0
                select.items = target_classes_items

    @switch("indeterminate", on_widgets=["progress"])
    def set_table(self, dst_classes, src_classes):
        """
        Rebuild the table content based on the new_classes and codes provided

        Args:
            dst_classes (dict|optional): a dictionnary that represent the classes of
            new the new classification table as {class_code: (class_name, class_color)}.
            class_code must be ints and class_name str.
            src_classes (dict|optional): the list of existing values within the input
            file {class_code: (class_name, class_color)}
        """

        # reset the matrix
        self.progress.v_model = 0
        self.model.matrix = {code: 0 for code in src_classes.keys()}

        # create the select list
        # they need to observe each other to adapt the available class list dynamically
        self.class_select_list = {
            k: ClassSelect(dst_classes, k) for k in src_classes.keys()
        }

        rows = [
            v.Html(
                tag="tr",
                children=[
                    v.Html(
                        tag="td",
                        style_="min-width: 115px !important;",
                        children=[f"{code}: {item[0]}"],
                    ),
                    v.Html(
                        tag="td",
                        style_="min-width: 550px !important;",
                        children=[self.class_select_list[code]],
                    ),
                ],
            )
            for code, item in src_classes.items()
        ]

        # add an empty row at the end to make the table more visible when it's empty
        rows += [
            v.Html(
                tag="tr",
                children=[
                    v.Html(tag="td", children=[""]),
                    v.Html(
                        tag="td",
                        children=["" if src_classes else "No data available"],
                    ),
                ],
            )
        ]

        self.table.children = self.headers + [v.Html(tag="tbody", children=rows)]

        # js behaviour
        [
            w.observe(self._update_matrix_values, "v_model")
            for w in self.class_select_list.values()
        ]

        return self

    def _update_matrix_values(self, change):
        """Update the appropriate matrix value when a Combo select change"""

        # get the code of the class in the src classification
        code = change["owner"]._metadata["class"]

        # Make a copy of matrix, so we can use it as an observable trait
        temp_matrix = deepcopy(self.model.matrix)

        # bind it to classes in the dst classification
        temp_matrix[code] = change["new"] if change["new"] else 0

        self.model.matrix = temp_matrix

        return self


class ClassSelect(sw.Select):
    """
    Custom widget to pick the value of a original class in the new classification system

    Args:
        new_codes(dict): the dict of the new codes to use as items {code: (name, color)}
        code (int): the orginal code of the class
    """

    def __init__(self, new_codes, old_code, **kwargs):
        # set default parameters
        self.items = [
            {"text": f"{code}: {item[0]}", "value": code}
            for code, item in new_codes.items()
        ]
        self.dense = True
        self.multiple = False
        self.chips = True
        self._metadata = {"class": old_code}
        self.attributes = {"id": "select_target_class"}
        self.v_model = None
        self.clearable = True

        # init the select
        super().__init__(**kwargs)


class Btn(v.Btn, sw.SepalWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def toggle_loading(self):
        """
        Jump between two states : disabled and loading - enabled and not loading

        Return:
            self
        """
        self.loading = not self.loading
        self.disabled = self.loading

        return self


def InfoDialog():
    # read csv
    df = pd.read_csv(dir_.LOCAL_LC_CLASSES, header=0)
    headers = [cm.reclass.default_table.header[col] for col in df.columns.tolist()]
    content = df.values.tolist()

    thead = v.Html(
        tag="thead",
        children=[
            v.Html(tag="tr", children=[v.Html(tag="th", children=[h]) for h in headers])
        ],
    )

    tbody = v.Html(
        tag="tbody",
        children=[
            v.Html(
                tag="tr",
                children=[
                    v.Html(
                        tag="td", class_="caption text-center", children=[str(row[0])]
                    ),
                    v.Html(tag="td", class_="caption", children=[str(row[1])]),
                    v.Html(
                        tag="td",
                        style_=f"background-color: {row[-1]};",
                        class_="caption",
                        children=["  "],
                    ),
                ],
            )
            for row in content
        ],
    )

    table = v.SimpleTable(
        max_width="500px",
        dense=True,
        children=[
            thead,
            tbody,
        ],
    )

    dialog = BaseDialog(title="Default classification", content=[table], action_text="")
    dialog.cancel_btn.on_event("click", lambda *_: dialog.close_dialog())

    dialog.action_btn.hide()

    return dialog
