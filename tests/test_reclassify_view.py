from types import SimpleNamespace

import ee
import pysepal.sepalwidgets as sw

from component.widget.reclassify.reclassify_view import ReclassifyView

ASSET = "users/someone/land_cover"


def _view():
    view = ReclassifyView.__new__(ReclassifyView)
    view._tasks = {}
    view.model = SimpleNamespace(ic_items=[])
    view.alert = sw.Alert()
    view.w_ic_select = SimpleNamespace(v_model=ASSET)
    view._configure_tasks()
    return view


def test_failed_image_listing_shows_an_error():
    view = _view()
    task = view._tasks["set_ic_items"]

    async def fail(_collection_ids):
        raise ee.EEException(f"ImageCollection.load: Asset '{ASSET}' not found.")

    task.function = fail
    task.start(None).result(timeout=10)

    assert view.alert.type == "error"
    text = view.alert.children[0].children[0]
    assert ASSET in text
    assert "not found" in text
