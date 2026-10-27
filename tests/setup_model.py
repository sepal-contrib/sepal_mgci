"""A model whose setup passes every check, for tests that break one rule at a time."""

from types import SimpleNamespace

from component.parameter.module_parameter import LULC_DEFAULT, TRANSITION_MATRIX_FILE

IMAGES = [f"{LULC_DEFAULT}/{year}" for year in (2000, 2015, 2018)]


def image(year):
    return {"asset": f"{LULC_DEFAULT}/{year}", "year": year}


def complete_model(**overrides):
    model = SimpleNamespace(
        aoi_model=SimpleNamespace(feature_collection=object(), name="Test area"),
        answer_custom_lulc=False,
        answer_need_reclassify=False,
        lc_asset_sub_a=LULC_DEFAULT,
        lc_asset_sub_b=LULC_DEFAULT,
        ic_items_sub_a=list(IMAGES),
        ic_items_sub_b=list(IMAGES),
        matrix_sub_a={10: 1, 20: 2},
        matrix_sub_b={10: 1, 20: 2},
        transition_matrix=str(TRANSITION_MATRIX_FILE),
        calc_a=True,
        calc_b=True,
        sub_a_year={1: image(2000)},
        sub_b_year={
            "baseline": {"base": image(2000), "report": image(2015)},
            2: image(2018),
        },
    )
    for name, value in overrides.items():
        setattr(model, name, value)
    return model
