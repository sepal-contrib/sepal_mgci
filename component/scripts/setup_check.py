"""One check of the user's setup, shared by every step that computes results.

"Validate & close" in the land cover step, the calculation, the report export
and both dashboards call it, so they accept and refuse the same setups. It
reads only the model, never the widgets.
"""

from component.message import cm
from component.parameter.module_parameter import LULC_DEFAULT

INDICATORS = ("sub_a", "sub_b")


class SetupError(ValueError):
    """The setup is not complete; the message tells the user what to fix."""

    def __init__(self, message, key=None):
        super().__init__(message)
        self.key = key


def _fail(key, step, **values):
    message = getattr(cm.setup, key)
    raise SetupError(
        message.format(step=getattr(cm.app.drawer_item, step), **values), key=key
    )


def _letter(indicator):
    return indicator[-1].upper()


def check_land_cover(model, indicators=INDICATORS):
    """Check the choices of the land cover step that ``indicators`` use."""
    custom = getattr(model, "answer_custom_lulc", False)
    reclassify = getattr(model, "answer_need_reclassify", True)

    if not model.lc_asset_sub_a:
        _fail("no_asset", "vegetation")
    if custom and model.lc_asset_sub_a == LULC_DEFAULT:
        _fail("default_asset", "vegetation")

    for indicator in indicators:
        # The image list is emptied when the images of a new asset cannot be read.
        if custom and not getattr(model, f"ic_items_{indicator}"):
            _fail("no_images", "vegetation")
        matrix = getattr(model, f"matrix_{indicator}") or {}
        if (not custom or reclassify) and not any(matrix.values()):
            _fail("no_matrix", "vegetation", indicator=_letter(indicator))
        if indicator == "sub_b" and not model.transition_matrix:
            _fail("no_transition", "vegetation")


def check_land_cover_step(model):
    """Check "Validate & close" of the land cover step.

    The step is complete when at least one sub-indicator can use it, so that a
    user can report only one. Return a warning for each sub-indicator that cannot.
    """
    errors = {}
    for indicator in INDICATORS:
        try:
            check_land_cover(model, (indicator,))
        except SetupError as error:
            errors[indicator] = error

    ready = [_letter(indicator) for indicator in INDICATORS if indicator not in errors]
    if ready:
        return [
            cm.setup.partial.format(reason=str(error), ready=", ".join(ready))
            for error in errors.values()
        ]

    if all(error.key == "no_matrix" for error in errors.values()):
        _fail("no_matrix_any", "vegetation")
    # A problem that both sub-indicators share is given once.
    raise SetupError(" ".join(dict.fromkeys(str(error) for error in errors.values())))


def _selected_images(indicator, years):
    """The {asset, year} entries of the years selected for ``indicator``."""
    if indicator == "sub_a":
        return list(years.values())
    baseline = years.get("baseline") or {}
    reports = [value for key, value in years.items() if key != "baseline"]
    return [baseline.get("base"), baseline.get("report"), *reports]


def check_years(model, indicator):
    """Check the years selected for ``indicator`` in Indicator settings."""
    letter = _letter(indicator)
    years = getattr(model, f"{indicator}_year") or {}
    entries = _selected_images(indicator, years)

    if not years or any(
        not isinstance(entry, dict) or not entry.get("asset") or not entry.get("year")
        for entry in entries
    ):
        _fail("no_years", "calculation", indicator=letter)

    if indicator == "sub_b":
        try:
            ends_before_start = int(entries[0]["year"]) >= int(entries[1]["year"])
        except (TypeError, ValueError):
            ends_before_start = False
        if ends_before_start:
            _fail("baseline_order", "calculation")

    images = set(getattr(model, f"ic_items_{indicator}") or [])
    if any(entry["asset"] not in images for entry in entries):
        _fail("other_asset", "calculation", indicator=letter)


def check_setup(model, indicator):
    """Check everything that the results of ``indicator`` depend on."""
    if not model.aoi_model.feature_collection:
        _fail("no_aoi", "aoi")
    check_land_cover(model, (indicator,))
    check_years(model, indicator)


def selected_indicators(model):
    """The sub-indicators selected in Indicator settings, at least one."""
    selected = [
        indicator
        for indicator, wanted in (("sub_a", model.calc_a), ("sub_b", model.calc_b))
        if wanted
    ]
    if not selected:
        _fail("no_indicator", "calculation")
    return selected


def check_calculation(model):
    """Check the setup of every selected sub-indicator."""
    for indicator in selected_indicators(model):
        check_setup(model, indicator)
