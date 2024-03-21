from component.scripts.gee import get_transition, no_remap, read_asset
import component.parameter.module_parameter as param
import component.scripts.scripts as cs
import component.parameter.visualization as visuals


def get_layer_a(selection, remap_matrix, aoi):
    layer = (
        no_remap(read_asset(selection), remap_matrix)
        .updateMask(read_asset(param.BIOBELT).mask())
        .clip(aoi)
    )

    vis_params = visuals.VIS_PARAMS["land_cover"]

    return layer, vis_params


def get_layer_b(selection, remap_matrix, aoi, sub_b_year, transition_matrix):
    # I have to get the transition image from baseline with each of the report
    # years selected in the modedatal

    sub_b_years = cs.get_b_years(sub_b_year)

    transition_images = []
    for lc_years in sub_b_years:
        ee_lc_start = read_asset(lc_years[0].get("asset")).select(0)
        ee_end_base = read_asset(lc_years[1].get("asset")).select(0)
        ee_report = read_asset(lc_years[2].get("asset")).select(0)

        transition_images.append(
            get_transition(
                ee_lc_start,
                ee_end_base,
                ee_report,
                aoi,
                transition_matrix,
                remap_matrix,
            )
        )

    if selection == "baseline_degradation":
        # We can take either, they have the same baseline
        layer = transition_images[0].select("baseline_degradation")
        vis_params = visuals.VIS_PARAMS["degradation"]

    else:
        reporting_years = cs.get_reporting_years(sub_b_year, "sub_b")
        if "land_cover" in selection:
            year = int(selection.split("_")[-1])

            # The first tuple returned is the baseline
            baseline_years = reporting_years[0]

            if year in baseline_years:
                # I can use either, they have the same baseline
                transition_image = transition_images[0]
                layer_name = (
                    "land_cover_start"
                    if year == baseline_years[0]
                    else f"land_cover_end"
                )
            else:
                years = reporting_years[1:]
                index = years.index(year)
                transition_image = transition_images[index]

                layer_name = f"land_cover_report"
            # TODO: use random visualizaion if remap is not default
            layer = transition_image.select(layer_name)
            vis_params = visuals.VIS_PARAMS["land_cover"]

        else:
            years = reporting_years[1:]
            index = years.index(int(selection.split("_")[-1]))
            transition_image = transition_images[index]

            # Select the required band
            if selection.startswith("final_degradation"):
                layer = transition_image.select("final_degradation")
                vis_params = visuals.VIS_PARAMS["degradation"]

            elif selection.startswith("report_degradation"):
                layer = transition_image.select("report_degradation")
                vis_params = visuals.VIS_PARAMS["degradation"]

    return layer.updateMask(read_asset(param.BIOBELT).mask()), vis_params
