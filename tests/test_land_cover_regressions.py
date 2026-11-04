import asyncio
from types import SimpleNamespace

import pytest

from component.scripts.gee import no_remap
from component.scripts.setup_check import SetupError
from component.widget.map import LayerHandler
from component.widget.export_dialog import ExportMapDialog
from tests.setup_model import custom_model


def test_remap_normalizes_histogram_and_saved_json_codes():
    class Image:
        def remap(self, sources, targets, default):
            assert list(sources) == [10, 20]
            assert list(targets) == [1, 2]
            assert default == 0
            return self

        def selfMask(self):
            return self

    image = Image()
    assert no_remap(image, {"10": "1", "20": 2}) is image


@pytest.mark.parametrize("indicator", ["a", "b"])
def test_map_refuses_unreclassified_form_before_requesting_earth_engine(indicator):
    view = LayerHandler.__new__(LayerHandler)
    view.model = custom_model(
        matrix_sub_a={10: 0, 20: 0}, matrix_sub_b={10: 0, 20: 0}
    )
    view.w_layers = SimpleNamespace(v_model=[indicator, "land_cover_2000", "Land cover"])
    with pytest.raises(SetupError):
        asyncio.run(view.add_layer_async())


def test_export_refuses_unreclassified_form_before_building_image():
    view = ExportMapDialog.__new__(ExportMapDialog)
    view.model = custom_model(matrix_sub_a={10: 0, 20: 0})
    view.w_layers = SimpleNamespace(v_model=["a", "land_cover_2000", "Land cover"])
    with pytest.raises(SetupError):
        view.get_ee_image()
