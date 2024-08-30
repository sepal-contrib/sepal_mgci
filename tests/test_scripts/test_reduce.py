"""Test scripts in scripts reduce regions"""

import ee
import sys
from pathlib import Path

sys.path.append(str(Path(".").resolve()))

import pytest
from pathlib import Path
from component.scripts.gee import no_remap, reduce_by_regions, reduce_by_region
from component.scripts.gee_parse_reduce_regions import reduceGroups
from pytest import approx


def sort_dict(d):
    """Recursively sort a dictionary by its keys."""
    if isinstance(d, dict):
        return {k: sort_dict(v) for k, v in sorted(d.items())}
    elif isinstance(d, list):
        # Sort lists of dictionaries by converting them to tuples of sorted key-value pairs
        return sorted(
            [sort_dict(item) for item in d],
            key=lambda x: sorted(x.items()) if isinstance(x, dict) else x,
        )
    else:
        return d


def sort_list_of_dicts(lst):
    """Sort a list of dictionaries by the keys of the dictionaries."""
    return sorted([sort_dict(d) for d in lst], key=lambda x: sorted(x.items()))


def compare_nested_dicts(dict1, dict2, rel_tol=1e-9):
    """Recursively compare two dictionaries or lists, allowing for float comparisons with tolerance."""
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        for key in dict1:
            assert key in dict2, f"Key '{key}' not found in second dictionary"
            compare_nested_dicts(dict1[key], dict2[key], rel_tol)
    elif isinstance(dict1, list) and isinstance(dict2, list):
        assert len(dict1) == len(dict2), "Lists are of different lengths"
        for item1, item2 in zip(dict1, dict2):
            compare_nested_dicts(item1, item2, rel_tol)
    elif isinstance(dict1, float) and isinstance(dict2, float):
        assert dict1 == approx(
            dict2, rel=rel_tol
        ), f"{dict1} and {dict2} are not approximately equal"
    else:
        assert dict1 == dict2, f"{dict1} and {dict2} are not equal"

    return True


def test_reduce_by_regions_no_remap(test_land_cover, test_aoi, test_biobelt):
    """Test reduce by function that is used to calculate the areas"""

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

    # Sort the dictionaries for comparison
    sorted_result_regions = sort_list_of_dicts(result_regions)
    sorted_result_region = sort_list_of_dicts(result_region)

    # Compare the results with a relative tolerance of 1e-9
    assert compare_nested_dicts(
        sorted_result_regions, sorted_result_region, rel_tol=1e-9
    )


def test_reduce_by_regions_remap(test_land_cover, test_aoi, test_biobelt):
    """Test reduce by function that is used to calculate the areas with images remapped"""

    # TODO: Add remap_matrix

    return True


def test_reduce_groups(test_multipolygon_aoi):
    """Test reduce groups parsing method.

    Reduce groups is a method that parses the result of a reduceRegions method to mimic the result of a reduceRegion method.

    """

    group1 = ee.Image.random(1).multiply(2).round()
    group2 = ee.Image.random(2).multiply(2).round()
    group3 = ee.Image.random(3).multiply(2).round()
    image = ee.Image(group1.multiply(3).add(group2))

    reducer = ee.Reducer.sum().group(1, "group0").group(2, "group1").group(3, "group2")

    reduceRegion = (
        image.addBands(group1)
        .addBands(group2)
        .addBands(group3)
        .reduceRegion(
            **{
                "reducer": reducer,
                "geometry": test_multipolygon_aoi.geometry(),
                "scale": 1000,
            }
        )
    )

    reduceRegions = (
        image.addBands(group1)
        .addBands(group2)
        .addBands(group3)
        .reduceRegions(
            **{"collection": test_multipolygon_aoi, "reducer": reducer, "scale": 1000}
        )
    )

    result_region = reduceRegion.get("groups").getInfo()

    # Act: ReduceGroups
    result_regions = reduceGroups(
        reducer=ee.Reducer.sum(),
        featureCollection=reduceRegions,
        groupKeys=["group0", "group1", "group2"],
    ).getInfo()

    # Sort the dictionaries for comparison
    sorted_result_regions = sort_list_of_dicts(result_region)
    sorted_result_region = sort_list_of_dicts(result_regions)

    # Compare the results with a relative tolerance of 1e-9
    assert compare_nested_dicts(
        sorted_result_regions, sorted_result_region, rel_tol=1e-9
    )


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
