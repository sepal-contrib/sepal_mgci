import component.scripts.scripts as cs


def test_get_years():
    """Test get_years function"""

    # Arrange when using same year but different assets
    sub_a_year = {
        1: {"asset": "asset_x/2020", "year": 2020},
        2: {"asset": "asset_x/2015", "year": 2015},
    }

    sub_b_year = {
        1: {"asset": "asset_y/2020", "year": 2020},
        2: {"asset": "asset_y/2015", "year": 2015},
    }

    years = cs.get_years(sub_a_year, sub_b_year, {}, {})

    assert years == [
        [
            {"asset": "asset_y/2015", "year": 2015},
            {"asset": "asset_y/2020", "year": 2020},
        ],
        [{"asset": "asset_x/2015", "year": 2015}],
        [{"asset": "asset_x/2020", "year": 2020}],
    ]

    # Arrange when using same asset but different years
    sub_a_year = {
        1: {"asset": "asset_x/2004", "year": 2004},
        2: {"asset": "asset_x/2010", "year": 2010},
    }

    sub_b_year = {
        1: {"asset": "asset_x/2020", "year": 2020},
        2: {"asset": "asset_x/2015", "year": 2015},
    }

    years = cs.get_years(sub_a_year, sub_b_year, {}, {})
    assert years == [
        [
            {"asset": "asset_x/2015", "year": 2015},
            {"asset": "asset_x/2020", "year": 2020},
        ],
        [{"asset": "asset_x/2010", "year": 2010}],
        [{"asset": "asset_x/2004", "year": 2004}],
    ]


def test_parse_to_year_a():
    results = {"2018_2021": {}, "2005": {}, "2011": {}, "2009": {}, "2015": {}}

    assert cs.parse_to_year_a(results, int("2018"), "sub_b") == {
        "2018_2021": results["2018_2021"]
    }
    assert cs.parse_to_year_a(results, int("2021"), "sub_b") == {
        "2018_2021": results["2018_2021"]
    }
    assert cs.parse_to_year_a(results, int("2005"), "sub_a") == {
        "2005": results["2005"]
    }
    assert cs.parse_to_year_a(results, int("2011"), "sub_a") == {
        "2011": results["2011"]
    }
    assert cs.parse_to_year_a(results, int("2009"), "sub_a") == {
        "2009": results["2009"]
    }
    assert cs.parse_to_year_a(results, int("2015"), "sub_a") == {
        "2015": results["2015"]
    }
