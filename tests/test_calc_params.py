import pytest

import component.parameter.module_parameter as param
from component.widget.calc_params import Calculation

LULC = param.LULC_DEFAULT
IMAGES = [f"{LULC}/2000", f"{LULC}/2015", f"{LULC}/2018"]


def assert_default_years(calculation):
    assert calculation.w_content_a.v_model == {1: {"asset": f"{LULC}/2000", "year": 2000}}
    sub_b = calculation.w_content_b.v_model
    assert sub_b["baseline"]["base"]["asset"] == f"{LULC}/2000"
    assert sub_b["baseline"]["report"]["asset"] == f"{LULC}/2015"


@pytest.mark.parametrize("lists_arrive", ["before", "after"])
def test_default_years_are_set_whenever_the_image_lists_arrive(mgci_model, lists_arrive):
    """The land cover step can list the images before Indicator settings exists."""
    if lists_arrive == "before":
        mgci_model.ic_items_sub_a = IMAGES
        mgci_model.ic_items_sub_b = IMAGES

    calculation = Calculation(mgci_model)

    if lists_arrive == "after":
        mgci_model.ic_items_sub_a = IMAGES
        mgci_model.ic_items_sub_b = IMAGES

    assert_default_years(calculation)


def test_years_are_cleared_when_the_image_lists_are_emptied(mgci_model):
    """An asset whose images cannot be read must not keep the previous asset's years."""
    calculation = Calculation(mgci_model)
    mgci_model.ic_items_sub_a = IMAGES
    mgci_model.ic_items_sub_b = IMAGES

    mgci_model.ic_items_sub_a = []
    mgci_model.ic_items_sub_b = []

    assert calculation.w_content_a.items == []
    assert calculation.w_content_b.items == []
    assert [year["asset"] for year in mgci_model.sub_a_year.values()] == [None]
    baseline = mgci_model.sub_b_year["baseline"]
    assert baseline["base"]["asset"] is None
    assert baseline["report"]["asset"] is None
