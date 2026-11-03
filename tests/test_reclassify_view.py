from types import SimpleNamespace

import ee

from component.widget.reclassify import reclassify_view
from component.widget.reclassify.reclassify_view import ReclassifyView

ASSET = "users/someone/land_cover"


def test_clearing_asset_invalidates_previous_images_and_reclassification():
    view = ReclassifyView.__new__(ReclassifyView)
    view.model = SimpleNamespace(
        ic_items=["previous/2000"],
        matrix={10: 1},
        src_class={10: ("class", "#000")},
        table_created=True,
    )
    view.reclassify_table = SimpleNamespace(set_table=lambda *_: None)
    view.set_ids({"new": ""})
    assert view.model.ic_items == []
    assert view.model.matrix == {}
    assert view.model.src_class == {}
    assert view.model.table_created is False


def test_late_image_listing_cannot_restore_previous_asset(monkeypatch):
    interface = SimpleNamespace(
        get_info_async=None,
        create_task=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(reclassify_view, "get_current_gee_interface", lambda: interface)
    view = ReclassifyView.__new__(ReclassifyView)
    view._tasks = {}
    view.model = SimpleNamespace(src_gee="old", ic_items=[])
    view._configure_tasks()
    old_request = view._tasks["set_ic_items"]
    view.model.src_gee = "new"
    view.model.ic_items = ["new/2000"]

    old_request.on_done(["old/2000"])
    assert view.model.ic_items == ["new/2000"]
    old_request.on_error(ValueError("old request failed"))
    assert view.model.ic_items == ["new/2000"]


def test_a_failed_image_listing_empties_the_image_list():
    view = ReclassifyView.__new__(ReclassifyView)
    view._tasks = {}
    view.model = SimpleNamespace(ic_items=["users/someone/previous/2000"])
    view._configure_tasks()
    task = view._tasks["set_ic_items"]

    async def fail(_collection_ids):
        raise ee.EEException(f"ImageCollection.load: Asset '{ASSET}' not found.")

    task.function = fail
    task.start(None).result(timeout=10)

    assert view.model.ic_items == []
