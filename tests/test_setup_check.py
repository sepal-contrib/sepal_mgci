import pandas as pd
import pytest

from component.model.model import MgciModel
from component.scripts.setup_check import (
    SetupError,
    check_calculation,
    check_land_cover,
    check_land_cover_step,
    check_setup,
    check_years,
)
from component.scripts import setup_check
from component.scripts.sub_a import get_mgci
from component.message import cm
from tests.setup_model import complete_model, custom_model, image

CUSTOM = "users/someone/land_cover"
CUSTOM_IMAGES = [f"{CUSTOM}/2000", f"{CUSTOM}/2015", f"{CUSTOM}/2018"]


def test_a_complete_setup_passes():
    model = complete_model()

    check_land_cover(model)
    check_setup(model, "sub_a")
    check_setup(model, "sub_b")
    check_calculation(model)


def test_the_check_reads_fields_that_the_model_has():
    names = vars(complete_model()).keys() - {"aoi_model", "answer_custom_lulc", "answer_need_reclassify"}
    assert all(hasattr(MgciModel, name) for name in names)


def test_a_missing_area_of_interest_is_refused():
    model = complete_model()
    model.aoi_model.feature_collection = None
    with pytest.raises(SetupError, match="area of interest"):
        check_setup(model, "sub_a")


def test_a_missing_land_cover_asset_is_refused():
    with pytest.raises(SetupError, match="land cover asset"):
        check_land_cover(complete_model(lc_asset_sub_a=""))


def test_the_default_asset_can_be_reclassified():
    model = complete_model(answer_custom_lulc=True, answer_need_reclassify=True)
    check_land_cover(model)


@pytest.mark.parametrize(
    "matrix",
    [{"10": 0, "20": 0}, {10: 1, 20: None}, {10: 1, 20: 999}, {"bad": 1}, {10: 1.5}],
)
def test_unreclassified_or_invalid_reclassification_is_refused(matrix):
    with pytest.raises(SetupError):
        check_land_cover(custom_model(matrix_sub_a=matrix), ("sub_a",))


def test_empty_rows_are_masked_out_not_refused():
    check_land_cover(custom_model(matrix_sub_a={"10": 1, "20": 0}), ("sub_a",))


def test_target_classes_must_match_the_reclassification():
    with pytest.raises(SetupError):
        check_land_cover(
            custom_model(
                matrix_sub_a={10: 12},
                lulc_classes_sub_a={1: ("Built", "#000000")},
            ),
            ("sub_a",),
        )


def test_b_checks_its_own_asset():
    with pytest.raises(SetupError):
        check_land_cover(custom_model(lc_asset_sub_b=""), ("sub_b",))


def test_transition_matrix_requires_every_pair_not_just_every_code(tmp_path):
    path = tmp_path / "transition.csv"
    path.write_text("from_code,to_code,impact_code\n1,1,2\n2,2,2\n")
    with pytest.raises(SetupError):
        check_land_cover(custom_model(transition_matrix=str(path)), ("sub_b",))


def test_transition_validation_reads_sepal_workspace_files(monkeypatch):
    path = "module_results/sdg_indicators/15.4.2/custom_transition/transition_matrix.csv"

    def read_workspace_file(selected_path):
        assert selected_path == path
        return pd.DataFrame(
            [(1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)],
            columns=["from_code", "to_code", "impact_code"],
        )

    monkeypatch.setattr(setup_check, "read_file", read_workspace_file, raising=False)
    check_land_cover(custom_model(transition_matrix=path), ("sub_b",))


def test_transition_file_access_error_identifies_the_file(monkeypatch):
    path = "module_results/unavailable.csv"

    def unreadable(_path):
        raise OSError("Access denied")

    monkeypatch.setattr(setup_check, "read_file", unreadable, raising=False)
    with pytest.raises(SetupError) as error:
        check_land_cover(custom_model(transition_matrix=path), ("sub_b",))
    assert path in str(error.value)
    assert "Access denied" in str(error.value)


def test_setup_validation_does_not_change_form_values():
    model = custom_model(matrix_sub_a={"10": "1", "20": "2"})
    before = dict(vars(model))
    check_land_cover(model)
    assert vars(model) == before


def test_a_custom_asset_whose_images_could_not_be_read_is_refused():
    model = complete_model(
        answer_custom_lulc=True, lc_asset_sub_a=CUSTOM, lc_asset_sub_b=CUSTOM, ic_items_sub_a=[]
    )
    with pytest.raises(SetupError, match="could not be read"):
        check_land_cover(model)


@pytest.mark.parametrize("indicator", ["sub_a", "sub_b"])
def test_a_reclassification_is_required_when_the_answers_ask_for_it(indicator):
    model = complete_model(
        answer_custom_lulc=True,
        answer_need_reclassify=True,
        lc_asset_sub_a=CUSTOM,
        lc_asset_sub_b=CUSTOM,
        ic_items_sub_a=CUSTOM_IMAGES,
        ic_items_sub_b=CUSTOM_IMAGES,
        **{f"matrix_{indicator}": {}},
    )
    with pytest.raises(SetupError, match="Reclassify"):
        check_land_cover(model)


def test_a_custom_map_that_needs_no_reclassification_needs_no_table():
    model = complete_model(
        answer_custom_lulc=True,
        answer_need_reclassify=False,
        lc_asset_sub_a=CUSTOM,
        lc_asset_sub_b=CUSTOM,
        ic_items_sub_a=CUSTOM_IMAGES,
        ic_items_sub_b=CUSTOM_IMAGES,
        matrix_sub_a={},
        matrix_sub_b={},
    )
    check_land_cover(model)


def test_sub_b_needs_a_transition_matrix():
    model = complete_model(transition_matrix="")
    check_setup(model, "sub_a")
    with pytest.raises(SetupError, match="transition matrix"):
        check_setup(model, "sub_b")


@pytest.mark.parametrize(
    "indicator, years",
    [
        ("sub_a", {}),
        ("sub_a", {1: {"asset": None, "year": None}}),
        ("sub_b", {}),
        ("sub_b", {"baseline": {"base": image(2000), "report": {"asset": None, "year": None}}}),
        ("sub_b", {"baseline": {"base": image(2000), "report": image(2015)}, 2: {"asset": None, "year": None}}),
    ],
)
def test_incomplete_years_are_refused(indicator, years):
    model = complete_model(**{f"{indicator}_year": years})
    with pytest.raises(SetupError, match="Indicator settings"):
        check_years(model, indicator)


def test_a_baseline_that_ends_before_it_starts_is_refused():
    years = {"baseline": {"base": image(2015), "report": image(2000)}, 2: image(2018)}
    with pytest.raises(SetupError, match="start year"):
        check_years(complete_model(sub_b_year=years), "sub_b")


@pytest.mark.parametrize("indicator", ["sub_a", "sub_b"])
def test_years_from_another_asset_are_refused(indicator):
    model = complete_model(**{f"ic_items_{indicator}": CUSTOM_IMAGES})
    with pytest.raises(SetupError, match="another land cover asset"):
        check_years(model, indicator)


def test_the_calculation_needs_a_sub_indicator():
    with pytest.raises(SetupError, match="at least one"):
        check_calculation(complete_model(calc_a=False, calc_b=False))


def test_the_calculation_checks_only_the_selected_sub_indicators():
    check_calculation(complete_model(calc_b=False, transition_matrix=""))


def test_classes_outside_the_target_classes_get_a_clear_error():
    parsed = pd.DataFrame({"belt_class": [1, 1], "lc_class": [1, 210], "sum": [5.0, 3.0]})
    with pytest.raises(ValueError, match="210"):
        get_mgci(parsed)


def test_the_land_cover_step_passes_without_warnings_when_both_sub_indicators_can_use_it():
    assert check_land_cover_step(custom_model()) == []


@pytest.mark.parametrize("missing, ready", [("sub_a", "B"), ("sub_b", "A")])
def test_the_land_cover_step_closes_with_one_reclassified_sub_indicator(missing, ready):
    model = custom_model(**{f"matrix_{missing}": {}})
    reason = cm.setup.no_matrix.format(
        indicator=missing[-1].upper(), step=cm.app.drawer_item.vegetation
    )

    warnings = check_land_cover_step(model)

    assert warnings == [cm.setup.partial.format(reason=reason, ready=ready)]


def test_the_land_cover_step_needs_at_least_one_reclassification():
    model = custom_model(matrix_sub_a={}, matrix_sub_b={})

    with pytest.raises(SetupError) as error:
        check_land_cover_step(model)

    assert str(error.value) == cm.setup.no_matrix_any.format(
        step=cm.app.drawer_item.vegetation
    )


def test_the_land_cover_step_gives_a_shared_problem_once():
    with pytest.raises(SetupError) as error:
        check_land_cover_step(custom_model(lc_asset_sub_a="", lc_asset_sub_b=""))

    assert str(error.value) == cm.setup.no_asset.format(
        step=cm.app.drawer_item.vegetation
    )


def test_the_land_cover_step_gives_each_problem_when_no_sub_indicator_can_use_it():
    model = custom_model(matrix_sub_a={}, transition_matrix="")

    with pytest.raises(SetupError) as error:
        check_land_cover_step(model)

    assert "Sub-indicator A" in str(error.value)
    assert "transition matrix" in str(error.value)
