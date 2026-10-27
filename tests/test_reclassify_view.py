from types import SimpleNamespace

import ee

from component.widget.reclassify.reclassify_view import ReclassifyView

ASSET = "users/someone/land_cover"


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
