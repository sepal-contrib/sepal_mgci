"""Test scripts in scripts reduce regions"""

import ee
import sys
from math import isclose
from pathlib import Path

sys.path.append(str(Path(".").resolve()))

import pytest
from pathlib import Path
import component.parameter.module_parameter as param
from component.scripts.gee import (
    no_remap,
    reduce_by_regions,
    reduce_by_region,
    reduce_regions,
)
from component.scripts.gee_parse_reduce_regions import reduceGroups

from tests.utils import compare_nested_dicts


def flatten_groups(groups, group_keys):
    """Flatten a nested grouped-reducer result to ``{(g0, g1, ...): sum}``.

    Grouped ``reduceRegion(s)`` output is a list of nested dicts: each level carries
    one group key plus either a further ``groups`` list or a leaf ``sum``. Collapsing
    it to a flat dict keyed by the tuple of group values lets two structurally
    equivalent results be compared regardless of ordering.
    """
    flat = {}

    def walk(nodes, prefix):
        for node in nodes:
            key = next((k for k in group_keys if k in node), None)
            value = node.get(key)
            if "groups" in node:
                walk(node["groups"], prefix + (value,))
            else:
                path = prefix + (value,)
                flat[path] = flat.get(path, 0.0) + float(node["sum"])

    walk(groups, ())
    return flat


def test_reduce_by_regions_equals_reduce_region(
    test_land_cover, test_aoi, test_biobelt
):
    """Test that reduce regions and reduce region return the same results without remapping the image"""

    image_area = ee.Image.pixelArea()
    biobelt = test_biobelt
    image = test_land_cover.first()
    aoi = test_aoi
    scale = 1000

    result_regions = reduce_by_regions(
        image_area=image_area,
        biobelt=biobelt,
        image=image,
        aoi=aoi,
        scale=scale,
    ).getInfo()

    result_region = reduce_by_region(
        image_area=image_area,
        biobelt=biobelt,
        image=image,
        aoi=aoi,
        scale=scale,
    ).getInfo()

    assert compare_nested_dicts(result_regions, result_region)


def test_reduce_by_regions_equals_reduce_region_remap(
    test_land_cover, test_aoi, test_biobelt
):
    """Test that reduce regions and reduce region return the same results when the image is remapped"""

    image_area = ee.Image.pixelArea()
    biobelt = test_biobelt
    image = test_land_cover.first()
    aoi = test_aoi
    scale = 1000

    # Use only few values, it would throw empty groups so I can also test that those are filtered out
    image = no_remap(image, {0: 0, 12: 1, 15: 1})

    result_regions = reduce_by_regions(
        image_area=image_area,
        biobelt=biobelt,
        image=image,
        aoi=aoi,
        scale=scale,
    ).getInfo()

    result_region = reduce_by_region(
        image_area=image_area,
        biobelt=biobelt,
        image=image,
        aoi=aoi,
        scale=scale,
    ).getInfo()

    print(result_regions)
    print(result_region)
    # Compare the results with a relative tolerance of 1e-9
    assert compare_nested_dicts(result_regions, result_region)


def test_reduce_by_regions(test_land_cover, test_aoi, test_biobelt):
    """Test reduce by function that is used to calculate the areas with images remapped"""

    expected_result = [
        {"biobelt": 2, "groups": [{"lc": 1, "sum": 31.65054491544118}]},
        {"biobelt": 3, "groups": [{"lc": 1, "sum": 7179.607115900761}]},
        {"biobelt": 4, "groups": [{"lc": 1, "sum": 1976.3498643124992}]},
    ]

    remap_dict = {
        0: 0,
        12: 1,
        15: 1,
    }

    image_area = ee.Image.pixelArea()
    biobelt = test_biobelt
    image = no_remap(test_land_cover.first(), remap_dict)
    aoi = test_aoi
    scale = 1000

    result_regions = reduce_by_regions(
        image_area=image_area,
        biobelt=biobelt,
        image=image,
        aoi=aoi,
        scale=scale,
    ).getInfo()

    assert compare_nested_dicts(result_regions, expected_result)


def test_reduce_groups(test_multipolygon_aoi):
    """reduceGroups must faithfully aggregate the reduceRegions groups it is given.

    It parses a grouped ``reduceRegions`` FeatureCollection into one nested
    structure. Its contract is to reproduce those per-feature ``reduceRegions``
    leaves exactly (summing groups shared across features) -- NOT to match a direct
    ``reduceRegion`` on the unioned geometry. Native ``reduceRegions`` and
    ``reduceRegion`` weight boundary pixels differently and legitimately diverge
    (up to ~10% on small groups here), so comparing against ``reduceRegion`` is the
    wrong oracle. See https://github.com/sepal-contrib/sepal_mgci/issues/88.
    """
    group1 = ee.Image.random(1).multiply(2).round()
    group2 = ee.Image.random(2).multiply(2).round()
    group3 = ee.Image.random(3).multiply(2).round()
    image = ee.Image(group1.multiply(3).add(group2))

    reducer = ee.Reducer.sum().group(1, "group0").group(2, "group1").group(3, "group2")
    stacked = image.addBands(group1).addBands(group2).addBands(group3)

    # scale=1000 (the module's working resolution); scale=None samples the random
    # image at its ~1 deg native grid where boundary pixels dominate. aaf6ad0 flipped
    # this to None, which is what surfaced #88.
    reduceRegions = stacked.reduceRegions(
        collection=test_multipolygon_aoi, reducer=reducer, scale=1000
    )

    group_keys = ["group0", "group1", "group2"]

    # Ground truth: the native reduceRegions leaves, summed per group across features.
    expected = {}
    for feature_groups in reduceRegions.aggregate_array("groups").getInfo():
        for key, value in flatten_groups(feature_groups, group_keys).items():
            expected[key] = expected.get(key, 0.0) + value

    result = flatten_groups(
        reduceGroups(
            reducer=ee.Reducer.sum(),
            featureCollection=reduceRegions,
            groupKeys=group_keys,
        ).getInfo(),
        group_keys,
    )

    assert set(result) == set(expected), "reduceGroups produced different groups"
    for key in expected:
        assert isclose(
            result[key], expected[key], rel_tol=1e-7
        ), f"group {key}: {result[key]} != {expected[key]}"


def test_reduce_regions_rsa_is_scale_invariant(default_remap_matrix_a):
    """With rsa=True the total area must not depend on the reduce scale.

    The Jenness surface is only meaningful on the DEM grid, so before #93 reducing
    the RSA image at any other scale (the land cover default, or the app's
    30-10,000 m slider) changed the total by orders of magnitude. The image now
    carries a terrain factor re-applied to the true pixel area at the reduce scale.
    Only the grand total is compared: the split by class follows the land cover
    grid at each scale, and the 0.1 deg box is a single pixel at 10 km.
    """
    # 0.1 deg box in the Andes (Cajon del Maipo, Chile): fully inside the
    # bioclimatic belts, and small enough to reduce synchronously at 30 m.
    aoi = ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Rectangle([-70.20, -33.75, -70.10, -33.65]))]
    )
    lc_years = [{"asset": f"{param.LULC_DEFAULT}/2015", "year": 2015}]
    dem_scale = ee.Image(param.DEM_DEFAULT).projection().nominalScale().getInfo()

    def total(rsa, scale):
        result = reduce_regions(
            aoi,
            default_remap_matrix_a,
            rsa=rsa,
            dem=param.DEM_DEFAULT,
            lc_years=lc_years,
            transition_matrix=False,
            scale=scale,
        ).getInfo()
        return sum(flatten_groups(result["sub_a"], ["biobelt", "lc"]).values())

    scales = (dem_scale, None, 30, 1000, 10000)
    rsa_totals = {scale: total(True, scale) for scale in scales}
    plan_totals = {scale: total(False, scale) for scale in scales}
    print(f"RSA totals (km2) by requested scale: {rsa_totals}")

    reference = rsa_totals[dem_scale]
    assert reference > 0, "the test box must intersect the bioclimatic belts"
    for scale in scales:
        assert isclose(rsa_totals[scale], reference, rel_tol=0.01), scale
        # A real surface is never smaller than its planimetric footprint.
        assert rsa_totals[scale] >= plan_totals[scale], scale


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
