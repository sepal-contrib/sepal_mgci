from copy import deepcopy
from pathlib import Path

import ipyvuetify as v
import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from component.message import cm
from sepal_ui.scripts import utils as su
from sepal_ui.scripts.decorator import switch, loading_button
from traitlets import Unicode

import component.scripts.frequency_hist as scripts
from component.message import cm
import component.parameter.directory as dir_
from component.widget.reclassify.parameters import MATRIX_NAMES, NO_VALUE
from component.widget.reclassify.reclassify_model import ReclassifyModel
import component.parameter.directory as dir_

__all__ = ["ReclassifyView"]


class ReclassifyView(sw.Card):
    """
    Stand-alone Card object allowing the user to reclassify a input file. the input can be of any type (vector or raster) and from any source (local or GEE).
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
        model=None,
        class_path=Path.home(),
        out_path=dir_.MATRIX_DIR,
        gee=False,
        dst_class=None,
        default_class={},
        aoi_model=None,
        save=True,
        folder=None,
        enforce_aoi=False,
        **kwargs,
    ):
        # create metadata to make it compatible with the framwork app system
        self._metadata = {"mount_id": "reclassify_tile"}

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
        self.alert = sw.Alert()

        # set the title of the card
        self.title = sw.CardTitle(
            children=[sw.Html(tag="h2", children=[cm.rec.rec.title])]
        )

        self.w_src_class_file = sw.FileInput(
            [".csv"], label=cm.rec.rec.input.classif.label, folder=self.class_path
        )

        self.btn_get_table = Btn(
            children=[cm.reclass.get_classes],
            color="primary",
            small=True,
            class_="ml-2",
            attributes={"id": "btn_get_table"},
        ).hide()

        self.w_ic_select = sw.AssetSelect(
            types=["IMAGE_COLLECTION"],
            label=cm.reclass_view.ic_default_label,
            disabled=True,
        )

        w_asset_selection = v.Flex(
            class_="d-flex align-center",
            children=[self.w_ic_select, self.btn_get_table],
        )

        # Create a list of buttons containing the different types of
        # target land cover classes

        self.reclassify_table = ReclassifyTable(self.model).hide()

        self.save_dialog = SaveMatrixDialog(folder=out_path)
        self.import_dialog = ImportMatrixDialog(folder=out_path, attributes={"id": "2"})
        self.target_dialog = TargetClassesDialog(
            model=self.model,
            reclassify_table=self.reclassify_table,
            default_class=default_class,
        )

        # create the layout
        self.children = [
            self.title,
            w_asset_selection,
            self.alert,
            self.reclassify_table,
            self.save_dialog,
            self.import_dialog,
            self.target_dialog,
        ]

        # Decorate functions
        self.get_reclassify_table = loading_button(
            self.alert, self.btn_get_table, debug=True
        )(self.get_reclassify_table)

        # JS Events
        self.import_dialog.load_btn.on_event("click", self.load_matrix_content)

        self.reclassify_table.btn_load_table.on_event(
            "click", lambda *args: self.import_dialog.show()
        )

        self.reclassify_table.btn_save_table.on_event(
            "click", lambda *args: self.save_dialog.show(self.model.matrix)
        )

        self.reclassify_table.btn_load_target.on_event(
            "click", lambda *args: self.target_dialog.show()
        )

        self.btn_get_table.on_event("click", self.get_reclassify_table)

        # Reset table everytime an image image collection is changed.

        self.w_ic_select.observe(self.set_ids, "v_model")

    def set_ids(self, change):
        """set image collection ids to ic_items model attribute on change. set empty
        table"""

        self.model.ic_items = scripts.get_image_collection_ids(change["new"])
        self.reclassify_table.set_table({}, {})

    def load_matrix_content(self, widget, event, data):
        """Load the content of the file in the matrix. The table need to be already set
        to perform this operation"""

        self.import_dialog.value = False
        file = self.import_dialog.w_file.v_model

        # exit if no files are selected
        if not file:
            raise Exception("No file has been selected")
        # exit if no table is loaded
        if not self.model.table_created:
            raise Exception("You have to get the table before.")
        # load the file
        # sanity checks
        input_data = pd.read_csv(file).fillna(NO_VALUE)

        try:
            input_data.astype("int64")
        except Exception:
            raise Exception(
                "This file may contain non supported charaters for reclassification."
            )
        if len(input_data.columns) != 2:
            # Try to identify the oclumns and subset them
            if all([colname in list(input_data.columns) for colname in MATRIX_NAMES]):
                input_data = input_data[MATRIX_NAMES]
            else:
                raise Exception(
                    "This file is not a properly formatted as classification matrix"
                )
        # check that the destination values are all available
        widget = list(self.reclassify_table.class_select_list.values())[0]
        classes = [i["value"] for i in widget.items]
        if not all(v in classes for v in input_data.dst.unique()):
            raise Exception(
                "Some of the destination data are not existing in the destination dataset"
            )
        # fill the data
        for _, row in input_data.iterrows():
            src_code, dst_code = row.src, row.dst
            if str(src_code) in self.reclassify_table.class_select_list:
                self.reclassify_table.class_select_list[
                    str(src_code)
                ].v_model = dst_code

        # self.import_dialog.w_file.reset()

        return self

    @su.switch("loading", "disabled", on_widgets=["w_code"])
    def _update_band(self, change):
        """Update the band possibility to the available bands/properties of the input"""

        # guess the file type and save it in the model
        self.model.get_type()
        # update the bands values
        self.w_code.v_model = None
        self.w_code.items = self.model.get_bands()

        return self

    @su.switch("table_created", on_widgets=["model"], targets=[True])
    def get_reclassify_table(self, widget, event, data):
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
        self.model.src_class = scripts.get_unique_classes(self.model, image_collection)

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


class ImportMatrixDialog(sw.Dialog):
    """
    Dialog to select the file to use and fill the matrix

    Args:
        folder (pathlike object): the path to the saved classifications

    Attributes:
        file (str): the file to use
    """

    file = Unicode("").tag(sync=True)

    def __init__(self, folder, **kwargs):
        # create the 3 widgets
        title = sw.CardTitle(children=["Load reclassification matrix"])
        self.w_file = sw.FileInput(
            label="filename", folder=folder, attributes={"id": "1"}
        )
        self.load_btn = sw.Btn(msg="Load", small=True, color="secondary")
        cancel = sw.Btn(msg="Cancel", small=True, color="secondary")
        actions = sw.CardActions(
            children=[
                v.Spacer(),
                cancel,
                self.load_btn,
            ]
        )

        # default params
        self.value = False
        self.max_width = 600
        self.overlay_opacity = 0.7
        self.children = [sw.Card(class_="pa-4", children=[title, self.w_file, actions])]

        # create the dialog
        super().__init__(**kwargs)

        # js behaviour
        cancel.on_event("click", self._cancel)

    def _cancel(self, widget, event, data):
        """exit and do nothing"""

        self.value = False

    def show(self):
        self.value = True


class SaveMatrixDialog(sw.Dialog):
    """
    Dialog to setup the name of the output matrix file

    Args:
        folder (pathlike object): the path to the save folder. default to ~/
    """

    def __init__(self, folder=Path.home(), **kwargs):
        # save the matrix
        self._matrix = {}
        self.folder = Path(folder)

        # create the widgets
        title = sw.CardTitle(children=["Save matrix"])
        self.w_file = sw.TextField(label="Set a matrix file name: ", v_model=None)
        btn = sw.Btn(msg="Save", small=True, color="secondary")
        cancel = sw.Btn(msg="Cancel", small=True, color="secondary")
        actions = sw.CardActions(
            children=[
                v.Spacer(),
                cancel,
                btn,
            ]
        )
        self.alert = sw.Alert(children=["Choose a name for the output"]).show()

        # default parameters
        self.value = False
        self.max_width = 600
        self.overlay_opcity = 0.7
        self.children = [
            sw.Card(class_="pa-4", children=[title, self.w_file, self.alert, actions])
        ]

        # create the dialog
        super().__init__(**kwargs)

        # js behaviour
        cancel.on_event("click", self._cancel)
        btn.on_event("click", self._save)
        self.w_file.on_event("blur", self._sanitize)
        self.w_file.observe(self._store_info, "v_model")

    def _store_info(self, change):
        """Display where will be the file written"""

        new_val = change["new"]

        out_file = self.folder / f"{su.normalize_str(new_val)}.csv"
        msg = f"Your file will be saved as: {out_file}"

        if not new_val:
            msg = "Choose a name for the output"
        self.alert.add_msg(msg)

    def _cancel(self, widget, event, data):
        """do nothing and exit"""

        self.w_file.v_model = ""
        self.value = False

        return self

    def _save(self, widget, event, data):
        """save the matrix in a specified file"""

        file = self.folder / f"{su.normalize_str(self.w_file.v_model)}.csv"

        matrix = pd.DataFrame.from_dict(self._matrix, orient="index").reset_index()
        matrix.columns = MATRIX_NAMES
        matrix.to_csv(file, index=False)

        # hide the dialog
        self.value = False

        return self

    def show(self, matrix):
        """show the dialog and set the matrix values"""

        self._matrix = matrix

        # Reset file name
        self.w_file.v_model = ""

        self.value = True

        return self

    def _sanitize(self, widget, event, data):
        """sanitize the used name when saving"""

        if not self.w_file.v_model:
            return self
        self.w_file.v_model = su.normalize_str(self.w_file.v_model)

        return self


class TargetClassesDialog(sw.Dialog):
    """Custom dialog to select target Land Cover classification classes

    Args:
        default_class (dict): classes and path to default classes files (multiple classifications)
        reclassify_table (ReclassifyTable): used to call set_target_classes method from here.
    """

    def __init__(self, model, reclassify_table, default_class: dict = {}):

        self.attributes = {"id": "target_classes_dialog"}
        self.model = model
        self.reclassify_table = reclassify_table

        super().__init__()

        self.value = False
        self.max_width = 750

        # Create an alert to display errors
        self.alert = sw.Alert()

        title = sw.CardTitle(children=[cm.reclass.tooltip.load_target.title])
        description = cm.reclass.target_dialog.description

        load_btn = sw.Btn(msg="Load", small=True, color="secondary")
        cancel_btn = sw.Btn(msg="Cancel", small=True, color="secondary")

        actions = sw.CardActions(
            children=[
                v.Spacer(),
                cancel_btn,
                load_btn,
            ]
        )

        # from default_class dictionary get the first value (it's the path of the default)
        dst_class_file = list(default_class.values())[0]

        self.w_dst_class_file = sw.FileInput(
            [".csv"], label=cm.rec.rec.input.classif.label, folder=dir_.RESULTS_DIR
        )
        self.w_dst_class_file.select_file(dst_class_file)

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

        self.children = [
            sw.Card(
                children=[
                    title,
                    sw.CardText(
                        class_="pa-4",
                        children=[
                            description,
                            self.w_default,
                            self.w_dst_class_file,
                            self.alert,
                            actions,
                        ],
                    ),
                ]
            )
        ]

        # Events
        [btn.on_event("click", self._set_dst_class_file) for btn in self.btn_list]
        
        self.btn_list[0].fire_event("click", None)

        cancel_btn.on_event("click", self._cancel)

        # bind selected file (containing destination classes) with model
        self.model.bind(self.w_dst_class_file, "dst_class_file")

        load_btn.on_event("click", self.set_dst_items_event)

        # Decorate set_dst_items_event with loading button
        self.set_dst_items_event = loading_button(alert=self.alert, button=load_btn)(
            self.set_dst_items_event
        )

    def set_dst_items_event(self, *args):
        """Set the event to update the destination class file"""

        self.reclassify_table.set_target_classes()

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

    def _cancel(self, *args):
        """close the dialog"""
        self.value = False

    def show(self):
        """show the dialog"""
        self.value = True


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

    def __init__(self, model, **kwargs):

        self.class_ = "d-block"
        self.attributes = {"id": "reclassify_table"}

        # create the table
        super().__init__(**kwargs)

        # save the model
        self.model = model

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
        self.btn_load_target = sw.Btn(
            gliph="mdi-table",
            icon=True,
            color="primary",
            attributes={"id": "btn_load_target"},
        ).set_tooltip(cm.reclass.tooltip.load_target.btn, bottom=True).hide()

        self.message = sw.Html(tag="span", style_=f"color: {color.warning}")

        self.toolbar = v.Toolbar(
            flat=True,
            children=[
                cm.reclass.title,
                v.Spacer(),
                v.Divider(vertical=True, class_="mx-2"),
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

        # Check that there are widgets
        if select_target_classes:

            # Get target classes from model
            self.model.dst_class = self.model.get_classes()

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
