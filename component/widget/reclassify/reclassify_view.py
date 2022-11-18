from pathlib import Path

import ipyvuetify as v
import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui.message import ms
from sepal_ui.scripts import utils as su
from sepal_ui.scripts.utils import loading_button
from traitlets import Unicode

from component.message import cm
from component.parameter.module_parameter import LULC_DEFAULT

from .parameters import MATRIX_NAMES, NO_VALUE
from .reclassify_model import ReclassifyModel

__all__ = ["ReclassifyView"]


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
        self.w_file = sw.FileInput(label="filename", folder=folder)
        self.load_btn = sw.Btn("Load")
        cancel = sw.Btn("Cancel", outlined=True)
        actions = sw.CardActions(children=[cancel, self.load_btn])

        # default params
        self.value = False
        self.max_width = 500
        self.overlay_opacity = 0.7
        self.persistent = True
        self.children = [sw.Card(class_="pa-4", children=[title, self.w_file, actions])]

        # create the dialog
        super().__init__(**kwargs)

        # js behaviour
        cancel.on_event("click", self._cancel)

    def _cancel(self, widget, event, data):
        """exit and do nothing"""

        self.value = False

        return self

    def show(self):

        self.value = True

        return self


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
        self.w_file = sw.TextField(label="filename", v_model=None)
        btn = sw.Btn("Save matrix")
        cancel = sw.Btn("Cancel", outlined=True)
        actions = sw.CardActions(children=[cancel, btn])
        self.alert = sw.Alert(children=["Choose a name for the output"]).show()

        # default parameters
        self.value = False
        self.max_width = 500
        self.overlay_opcity = 0.7
        self.persistent = True
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

        self.w_file.v_model = None
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
        self.v_model = None
        self.clearable = True

        # init the select
        super().__init__(**kwargs)


class ReclassifyTable(sw.DataTable):
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

    HEADERS = ms.rec.rec.headers

    def __init__(self, model, dst_classes={}, src_classes={}, **kwargs):

        # default parameters
        self.dense = True

        # create the table
        super().__init__(**kwargs)

        # save the model
        self.model = model

        self.btn_save_table = sw.Btn(
            "save", "fas fa-save", color="secondary", small=True
        )
        self.btn_load_table = sw.Icon(
            "load", "fas fa-open", color="secondary", small=True
        )

        toolbar = [v.Spacer(children=["Actions"])]

        # create the table elements

        self.headers = [{"text": header, "value": header} for header in self.HEADERS]
        self.set_table(dst_classes, src_classes)

    def set_table(self, dst_classes, src_classes):
        """
        Rebuild the table content based on the new_classes and codes provided

        Args:
            dst_classes (dict|optional): a dictionnary that represent the classes of new the new classification table as {class_code: (class_name, class_color)}. class_code must be ints and class_name str.
            src_classes (dict|optional): the list of existing values within the input file {class_code: (class_name, class_color)}

        Return:
            self
        """

        # reset the matrix
        self.model.matrix = {code: 0 for code in src_classes.keys()}

        # create the select list
        # they need to observe each other to adapt the available class list dynamically
        self.class_select_list = {
            k: ClassSelect(dst_classes, k) for k in src_classes.keys()
        }

        items = [
            {
                self.headers[0]: f"{code}: {item[0]}",
                self.headers[1]: self.class_select_list[code],
            }
            for code, item in src_classes.items()
        ]

        self.items = items

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

        # bind it to classes in the dst classification
        self.model.matrix[code] = change["new"] if change["new"] else 0

        return self


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

    get_table_btn = None
    "sw.Btn: the btn to load the data in the reclassification table"

    w_dst_class_file = None
    "sw.FileInput: widget to select the new classification system file (3 headless columns: 'code', 'desc', 'color')"

    reclassify_table = None
    "ReclassifyTable: the reclassification table populated via the previous widgets"

    def __init__(
        self,
        model=None,
        class_path=Path.home(),
        out_path=Path.home() / "downloads",
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
            children=[sw.Html(tag="h2", children=[ms.rec.rec.title])]
        )

        # create the input widgets
        self.w_input_title = sw.Html(
            tag="h2", children=[ms.rec.rec.input.title], class_="mt-5"
        )

        self.w_src_class_file = sw.FileInput(
            [".csv"], label=ms.rec.rec.input.classif.label, folder=self.class_path
        )

        self.btn_get_table = sw.Btn(
            ms.rec.rec.input.btn,
            "mdi-table",
            color="success",
            small=True,
            class_="ml-2",
        )

        self.w_ic_select = sw.AssetSelect(
            types=["IMAGE_COLLECTION"], default_asset=[str(LULC_DEFAULT)]
        )

        w_asset_selection = v.Flex(
            class_="d-flex align-center",
            children=[self.w_ic_select, self.btn_get_table],
        )

        if not dst_class:
            self.w_dst_class_file = sw.FileInput(
                [".csv"], label=ms.rec.rec.input.classif.label, folder=self.class_path
            ).hide()
        else:
            # We could save a little of time without creating this
            self.w_dst_class_file.select_file(dst_class).hide()

        self.save_dialog = SaveMatrixDialog(folder=out_path)
        self.import_dialog = ImportMatrixDialog(folder=out_path)
        self.import_table = sw.Btn(
            "import",
            "fas fa-download",
            color="secondary",
            small=True,
            class_="ml-2 mr-2",
        )

        self.reclassify_table = ReclassifyTable(self.model)

        # bind to the model
        # bind to the 2 raster and asset as they cannot be displayed at the same time

        self.model.bind(self.w_dst_class_file, "dst_class_file")

        # create the layout
        self.children = [
            self.title,
            w_asset_selection,
            self.w_input_title,
            self.w_dst_class_file,
            self.alert,
            self.reclassify_table,
            self.save_dialog,
            self.import_dialog,
        ]

        # Decorate functions
        self.get_reclassify_table = loading_button(
            self.alert, self.btn_get_table, debug=True
        )(self.get_reclassify_table)
        self.load_matrix_content = loading_button(
            self.alert, self.import_table, debug=True
        )(self.load_matrix_content)

        # JS Events
        self.import_table.on_event("click", lambda *args: self.import_dialog.show())
        self.import_dialog.load_btn.on_event("click", self.load_matrix_content)
        self.reclassify_table.btn_save_table.on_event(
            "click", lambda *args: self.save_dialog.show(self.model.matrix)
        )
        # self.w_image.observe(self._update_band, "v_model")
        self.btn_get_table.on_event("click", self.get_reclassify_table)

    def load_matrix_content(self, widget, event, data):
        """Load the content of the file in the matrix. The table need to be already set to perform this operation

        Return:
            self
        """
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

        self.import_dialog.w_file.reset()

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

        # get the destination classes
        self.model.dst_class = self.model.get_classes()

        # get the src_classes
        self.model.src_class = self.model.unique()

        # if the src_class_file is set overwrite src_class:
        if self.w_src_class_file.v_model:
            self.model.src_class = self.model.get_classes()

        # reset the table
        self.reclassify_table.set_table(self.model.dst_class, self.model.src_class)

        # check if the duplicate_layout need to be displayed ?
        self.duplicate_layout.class_ = "d-none"
        if len(self.reclassify_table.children[0].children) - 1 > self.MAX_CLASS:
            self.duplicate_layout.class_ = "d-block"

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
