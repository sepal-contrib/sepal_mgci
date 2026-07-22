"""Test scripts in scripts/frequency_hist.py"""

import sys
from pathlib import Path

sys.path.append(str(Path(".").resolve()))


import asyncio

import pytest
from component.scripts.frequency_hist import (
    get_unique_classes,
    get_unique_classes_by_year,
)


def test_get_unique_classes_by_year(test_aoi, test_land_cover):

    expected_output = {
        "projects/ee-cheprotich22/assets/Argentina_Landcover/Argentina_2015": [
            "0",
            "11",
            "12",
            "15",
            "18",
            "21",
            "22",
            "27",
            "3",
            "33",
            "34",
            "36",
            "4",
            "45",
            "59",
            "6",
            "63",
            "9",
        ],
        "projects/ee-cheprotich22/assets/Argentina_Landcover/Argentina_2021": [
            "0",
            "11",
            "12",
            "15",
            "18",
            "21",
            "22",
            "27",
            "3",
            "33",
            "34",
            "36",
            "4",
            "45",
            "6",
            "63",
            "9",
        ],
        "projects/ee-cheprotich22/assets/Argentina_Landcover/Argentina_2000": [
            "0",
            "11",
            "12",
            "15",
            "18",
            "21",
            "22",
            "27",
            "3",
            "33",
            "34",
            "36",
            "4",
            "45",
            "6",
            "63",
            "9",
        ],
    }
    # get_unique_classes_by_year returns one class list per sampled image
    # (first/middle/last), not a dict keyed by asset. Compare as sorted sets,
    # independent of ordering and of the image asset keys.
    result = asyncio.run(get_unique_classes_by_year(test_aoi, test_land_cover))

    assert sorted(sorted(classes) for classes in result) == sorted(
        sorted(classes) for classes in expected_output.values()
    )


def test_frequency_hist(mgci_model, test_aoi, test_land_cover):
    expected_output = {
        "0": ("no_name", "#000000"),
        "3": ("no_name", "#000000"),
        "4": ("no_name", "#000000"),
        "6": ("no_name", "#000000"),
        "9": ("no_name", "#000000"),
        "11": ("no_name", "#000000"),
        "12": ("no_name", "#000000"),
        "15": ("no_name", "#000000"),
        "18": ("no_name", "#000000"),
        "21": ("no_name", "#000000"),
        "22": ("no_name", "#000000"),
        "27": ("no_name", "#000000"),
        "33": ("no_name", "#000000"),
        "34": ("no_name", "#000000"),
        "36": ("no_name", "#000000"),
        "45": ("no_name", "#000000"),
        "59": (
            "no_name",
            "#000000",
        ),  # https://code.earthengine.google.com/4a6e102f1dac4b266b5ffc66f840c9d0
        "63": ("no_name", "#000000"),
    }

    # get_unique_classes reads the AOI from model.aoi_model.feature_collection.
    mgci_model.aoi_model.feature_collection = test_aoi

    result = asyncio.run(get_unique_classes(mgci_model, test_land_cover))

    assert result == expected_output


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s"])
