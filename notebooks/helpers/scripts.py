import ee
from component.scripts import sub_b
from component.scripts.scripts import get_reporting_years, get_sub_b_years, parse_result


def get_countries_to_process(
    admin_fc: ee.FeatureCollection,
    property_name: str,
    filter_countries: list = None,
    filter_codes: list = None,
    code_property: str = "M49Code",
) -> list:
    """
    Get list of countries to process from an admin boundary feature collection.

    Args:
        admin_fc: Earth Engine FeatureCollection with admin boundaries
        property_name: Property name to use for country names (e.g., 'M49Name')
        filter_countries: Optional list of country names to filter (e.g., ['Spain', 'France'])
        filter_codes: Optional list of country codes to filter (e.g., [724, 250])
        code_property: Property name for country codes (default: 'M49Code')

    Returns:
        List of unique country names to process
    """
    fc = admin_fc

    # Apply filters if provided
    if filter_countries:
        fc = fc.filter(ee.Filter.inList(property_name, filter_countries))
    elif filter_codes:
        fc = fc.filter(ee.Filter.inList(code_property, filter_codes))

    # Get unique country names
    countries = fc.aggregate_array(property_name).getInfo()
    countries = list(set(countries))  # Remove duplicates

    return countries


def parse_sub_b_year_safe(results: dict, target_year: dict):
    """
    Safely parse sub_b year data, handling empty results.
    Returns None if data is empty or invalid.
    """
    if "baseline" in target_year:
        for key in results.keys():
            if len(key.split("_")) > 1:
                df = parse_result(results[key], single=False)
                # Handle empty results
                if df.empty or "transition" not in df.columns:
                    return None
                # Decode transition to from_code and to_code
                df.loc[:, "from_lc"] = df.transition // 100
                df.loc[:, "to_lc"] = df.transition % 100
                return df[df.category == "baseline_transition"]

    # target_year is a tuple of the (start_baseline, report_year)
    year = target_year.get("report")[1]
    for key in results.keys():
        if len(key.split("_")) > 1:
            if str(year) in key:
                df = parse_result(results[key], single=False)
                # Handle empty results
                if df.empty:
                    return None
                return df[df.category == "final_degradation"]
    return None


def get_sub_b_data_reports_safe(
    results: dict,
    sub_b_year: dict,
    transition_matrix,
    geo_area_name: str,
    ref_area: str,
    source_detail: str,
):
    """
    Safely generate sub_b reports, handling empty data.
    """
    sub_b_reports = []

    reporting_years_sub_b = get_reporting_years(sub_b_year, "sub_b")
    sub_b_years_list = get_sub_b_years(reporting_years_sub_b)

    for year in sub_b_years_list:
        print(f"Reporting {year} for sub_b")
        parsed_df = parse_sub_b_year_safe(results, year)

        # Skip empty DataFrames
        if parsed_df is None or parsed_df.empty:
            print(f"  Skipping {year} - no data available")
            continue

        sub_b_reports.append(
            sub_b.get_reports(
                parsed_df,
                year,
                geo_area_name,
                ref_area,
                source_detail,
                transition_matrix,
            )
        )

    return sub_b_reports
