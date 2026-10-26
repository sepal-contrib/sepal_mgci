"""Fetch data for the requested dashboard chart.

Results from the calculation step are used when they were computed with the
current inputs, so the dashboards show the same numbers as the report without
another Earth Engine request. Otherwise the chart data is computed live from
the selected source assets.
"""

import asyncio

import component.scripts as cs
from component.scripts.gee import reduce_regions


def freeze_input(value):
    """Turn nested model values into a hashable, order-independent tuple."""
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), freeze_input(item)) for key, item in value.items())
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_input(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return repr(value)


def _integer_matrix(matrix):
    return {int(source): int(target) for source, target in (matrix or {}).items()}


def results_context(model, scale, indicator):
    """Fingerprint the inputs that determine one indicator's numbers.

    The calculation step stores it next to ``model.results``; the dashboards
    compare it with the current inputs before they reuse those results.
    """
    aoi_model = model.aoi_model
    common = (
        id(aoi_model.feature_collection),
        getattr(aoi_model, "name", None),
        scale,
        model.rsa,
        model.dem,
    )
    if indicator == "sub_a":
        inputs = (model.reporting_years_sub_a, _integer_matrix(model.matrix_sub_a))
    else:
        inputs = (
            model.sub_b_year,
            _integer_matrix(model.matrix_sub_b),
            model.transition_matrix,
        )
    return freeze_input(common + inputs)


def _stored_results(model, indicator, scale):
    """Return the calculation results if they match the current inputs."""
    context = (getattr(model, "results_context", None) or {}).get(indicator)
    if context is None or context != results_context(model, scale, indicator):
        return {}
    return getattr(model, "results", None) or {}


async def calculate_a_dashboard(model, year, gee_interface, scale=None):
    year = int(year)
    sources = model.reporting_years_sub_a[year]
    if not sources:
        raise ValueError(f"No source images are selected for {year}.")

    keys = [str(source["year"]) for source in sources]
    stored = _stored_results(model, "sub_a", scale)
    if all("sub_a" in stored.get(key, {}) for key in keys):
        results = {key: stored[key] for key in keys}
    else:
        processes = [
            reduce_regions(
                model.aoi_model.feature_collection,
                _integer_matrix(model.matrix_sub_a),
                model.rsa,
                model.dem,
                [source],
                model.transition_matrix,
                scale,
            )
            for source in sources
        ]
        infos = await asyncio.gather(
            *(gee_interface.get_info_async(process) for process in processes)
        )
        results = dict(zip(keys, infos))

    return cs.parse_to_year_a(results, model.reporting_years_sub_a, year)


async def calculate_b_dashboard(model, selection, gee_interface, scale=None):
    baseline = model.sub_b_year["baseline"]
    reports = [value for key, value in model.sub_b_year.items() if key != "baseline"]
    if not reports:
        raise ValueError("Select a reporting year for sub-indicator B.")
    report_year = selection["report"][1] if "report" in selection else None
    report = (
        reports[0]
        if report_year is None
        else next((value for value in reports if value["year"] == report_year), None)
    )
    if report is None:
        raise ValueError(f"No source image is selected for {report_year}.")
    sources = [baseline["base"], baseline["report"], report]
    category = "baseline_transition" if "baseline" in selection else "report_transition"

    stored = _stored_results(model, "sub_b", scale).get(cs.years_from_dict(sources), {})
    if category in stored:
        result = stored
    else:
        process = reduce_regions(
            model.aoi_model.feature_collection,
            _integer_matrix(model.matrix_sub_b),
            model.rsa,
            model.dem,
            sources,
            model.transition_matrix,
            scale,
            bands=[category],
        )
        result = await gee_interface.get_info_async(process)

    if category not in result:
        raise ValueError(f"No {category.replace('_', ' ')} data was returned.")
    df = cs.parse_result({category: result[category]}, single=False)
    if df.empty:
        raise ValueError("No land-cover transitions were found for this period.")
    df["from_lc"] = df["transition"] // 100
    df["to_lc"] = df["transition"] % 100
    return df
