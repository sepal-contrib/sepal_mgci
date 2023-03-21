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

    years = get_years(sub_a_year, sub_b_year, {}, {})

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

    years = get_years(sub_a_year, sub_b_year, {}, {})
    assert years == [
        [
            {"asset": "asset_x/2015", "year": 2015},
            {"asset": "asset_x/2020", "year": 2020},
        ],
        [{"asset": "asset_x/2010", "year": 2010}],
        [{"asset": "asset_x/2004", "year": 2004}],
    ]
