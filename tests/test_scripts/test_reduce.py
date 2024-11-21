"""Test scripts in scripts reduce regions"""

import ee
import sys
from pathlib import Path

sys.path.append(str(Path(".").resolve()))

import pytest
from pathlib import Path
from component.scripts.gee import no_remap, reduce_by_regions, reduce_by_region
from component.scripts.gee_parse_reduce_regions import reduceGroups

from tests.utils import compare_nested_dicts


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
                "scale": None,
            }
        )
    )

    reduceRegions = (
        image.addBands(group1)
        .addBands(group2)
        .addBands(group3)
        .reduceRegions(
            **{"collection": test_multipolygon_aoi, "reducer": reducer, "scale": None}
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
    # Compare the results with a relative tolerance of 1e-9
    assert compare_nested_dicts(result_regions, result_region)


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
