import ee
import ipyvuetify as v
from sepal_ui.message import ms
from sepal_ui.scripts import gee
from sepal_ui.scripts import utils as su
from sepal_ui.sepalwidgets import SepalWidget
from traitlets import Any, List, observe

ee.Initialize()


class AssetSelect(v.Combobox, SepalWidget):
    """
    Custom widget input to select an asset inside the asset folder of the user
    Args:
        label (str): the label of the input
        folder (str): the folder of the user assets
        default_asset (str, list): the id of a default asset or a list of defaults
        types ([str]): the list of asset type you want to display to the user. type need to be from: ['IMAGE', 'FOLDER', 'IMAGE_COLLECTION', 'TABLE','ALGORITHM']. Default to 'IMAGE' & 'TABLE'
        kwargs (optional): any parameter from a v.ComboBox.
    """

    TYPES = {
        "IMAGE": ms.widgets.asset_select.types[0],
        "TABLE": ms.widgets.asset_select.types[1],
        "IMAGE_COLLECTION": ms.widgets.asset_select.types[2],
        "ALGORITHM": ms.widgets.asset_select.types[3],
        "FOLDER": ms.widgets.asset_select.types[4],
        # UNKNOWN type is ignored
    }
    "dict: Valid ypes of asset"

    folder = None
    "str: the folder of the user assets, mainly for debug"

    valid = True
    "Bool: whether the selected asset is valid (user has access) or not"

    asset_info = {}
    "dict: The selected asset informations"

    default_asset = Any().tag(sync=True)
    "str: the id of a default asset or a list of default assets"

    types = List().tag(sync=True)
    "List: the list of types accepted by the asset selector. names need to be valide TYPES and changing this value will trigger the reload of the asset items."

    @su.need_ee
    def __init__(
        self,
        label=ms.widgets.asset_select.label,
        folder=None,
        types=["IMAGE", "TABLE"],
        default_asset=[],
        **kwargs,
    ):
        self.valid = False
        self.asset_info = None

        # if folder is not set use the root one
        self.folder = folder if folder else ee.data.getAssetRoots()[0]["id"]
        self.types = types

        # load the default assets
        self.default_asset = default_asset

        # Validate the input as soon as the object is instantiated
        self.observe(self._validate, "v_model")

        # set the default parameters
        kwargs["v_model"] = kwargs.pop("v_model", None)
        kwargs["clearable"] = kwargs.pop("clearable", True)
        kwargs["dense"] = kwargs.pop("dense", True)
        kwargs["prepend_icon"] = kwargs.pop("prepend_icon", "mdi-sync")
        kwargs["class_"] = kwargs.pop("class_", "my-5")
        kwargs["placeholder"] = kwargs.pop(
            "placeholder", ms.widgets.asset_select.placeholder
        )

        # create the widget
        super().__init__(**kwargs)

        # load the assets in the combobox
        self._get_items()

        # add js behaviours
        self.on_event("click:prepend", self._get_items)
        self.observe(self._get_items, "default_asset")

    @su.switch("loading")
    def _validate(self, change):
        """
        Validate the selected asset. Throw an error message if is not accesible or not in the type list.
        """

        self.error_messages = None

        if change["new"]:

            # check that the asset can be accessed
            try:
                self.asset_info = ee.data.getAsset(change["new"])

                # check that the asset has the correct type
                if not self.asset_info["type"] in self.types:
                    self.error_messages = ms.widgets.asset_select.wrong_type.format(
                        self.asset_info["type"], ",".join(self.types)
                    )

            except Exception:

                self.error_messages = ms.widgets.asset_select.no_access

            self.valid = self.error_messages is None
            self.error = self.error_messages is not None

        return

    @su.switch("loading", "disabled")
    def _get_items(self, *args):
        """custom method to only accept custom assets. Anything else."""
        # init the item list
        items = []

        # add the default values if needed
        if self.default_asset:

            if isinstance(self.default_asset, str):
                self.default_asset = [self.default_asset]

            self.v_model = self.default_asset[0]

            header = ms.widgets.asset_select.custom
            items += [{"divider": True}, {"header": header}]
            items += [default for default in self.default_asset]

        self.items = items

        return self

    @observe("types")
    def _check_types(self, change):
        """clean the type list, keeping only the valid one"""

        self.v_model = None

        # check the type
        self.types = [t for t in self.types if t in self.TYPES]

        # trigger the reload
        self._get_items()

        return
