"""Fetch data for the requested dashboard chart from its selected source assets."""

import component.scripts as cs
from component.scripts.gee import reduce_regions


def _integer_matrix(matrix):
    return {int(source): int(target) for source, target in (matrix or {}).items()}


async def calculate_a_dashboard(model, year, gee_interface, scale=None):
    year = int(year)
    sources = model.reporting_years_sub_a[year]
    if not sources:
        raise ValueError(f"No source images are selected for {year}.")

    results = {}
    for source in sources:
        process = reduce_regions(
            model.aoi_model.feature_collection,
            _integer_matrix(model.matrix_sub_a),
            model.rsa,
            model.dem,
            [source],
            model.transition_matrix,
            scale,
        )
        results[str(source["year"])] = await gee_interface.get_info_async(process)

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
    process = reduce_regions(
        model.aoi_model.feature_collection,
        _integer_matrix(model.matrix_sub_b),
        model.rsa,
        model.dem,
        sources,
        model.transition_matrix,
        scale,
    )
    result = await gee_interface.get_info_async(process)
    category = "baseline_transition" if "baseline" in selection else "report_transition"
    if category not in result:
        raise ValueError(f"No {category.replace('_', ' ')} data was returned.")
    df = cs.parse_result({category: result[category]}, single=False)
    if df.empty:
        raise ValueError("No land-cover transitions were found for this period.")
    df["from_lc"] = df["transition"] // 100
    df["to_lc"] = df["transition"] % 100
    return df
