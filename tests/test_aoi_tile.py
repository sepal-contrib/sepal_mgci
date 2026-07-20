"""The AOI selector must never browse the filesystem of the container.

The module is served as a single Solara instance shared by every user, so the
local-file AOI methods leak the server's own file tree and do their parsing in
the process serving all sessions. See https://github.com/sepal-contrib/sepal_mgci/issues/84.
"""

import pytest

import component.parameter.module_parameter as param
from component.tile.aoi_tile import AoiView

LOCAL_FILE_METHODS = ("SHAPE", "POINTS")


@pytest.fixture()
def aoi_view() -> AoiView:
    """An AoiView built the way ``solara_app.Page`` builds it."""
    from sepal_ui.mapping import SepalMap
    from sepal_ui.scripts.gee_interface import GEEInterface

    return AoiView(map_=SepalMap(gee_interface=GEEInterface()))


def test_local_file_methods_are_not_offered() -> None:
    """The method dropdown only offers admin levels and GEE assets."""
    offered = [item["value"] for item in param.CUSTOM_AOI_ITEMS if "value" in item]

    assert offered == ["ADMIN0", "ADMIN1", "ADMIN2", "ASSET"]


def test_local_file_widgets_are_not_reachable(aoi_view: AoiView) -> None:
    """The local file browsers are neither selectable nor part of the widget tree."""
    assert not set(aoi_view.components) & set(LOCAL_FILE_METHODS)

    rendered = {id(child) for child in aoi_view.children}
    assert id(aoi_view.w_vector) not in rendered
    assert id(aoi_view.w_points) not in rendered


def test_no_file_browser_in_the_widget_tree(aoi_view: AoiView) -> None:
    """No widget in the AOI tile browses the filesystem of the container."""
    from sepal_ui.sepalwidgets.file_input import FileInput
    from sepal_ui.sepalwidgets.inputs import FileInput as LegacyFileInput

    def walk(widget, seen):
        if id(widget) in seen:
            return
        seen.add(id(widget))
        yield widget
        for child in getattr(widget, "children", None) or []:
            if hasattr(child, "children"):
                yield from walk(child, seen)

    browsers = [
        w for w in walk(aoi_view, set()) if isinstance(w, (FileInput, LegacyFileInput))
    ]

    assert browsers == []


def test_asset_method_stays_available(aoi_view: AoiView) -> None:
    """Custom geometries are still reachable, through GEE assets."""
    from sepal_ui.sepalwidgets.inputs import AssetSelect

    aoi_view.w_method.v_model = "ASSET"

    assert isinstance(aoi_view.components["ASSET"].w_file, AssetSelect)
    assert "d-none" not in aoi_view.components["ASSET"].class_
