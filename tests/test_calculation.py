# Test calculation

model.sub_a_year = {
    1: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2018", "year": 2018},
    2: {"year": 2021, "asset": "users/amitghosh/sdg_module/esa/cci_landcover/2020"},
}

model.sub_b_year = {
    1: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2009", "year": 2009},
    2: {"year": 2011, "asset": "users/amitghosh/sdg_module/esa/cci_landcover/2011"},
    3: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2015", "year": 2015},
    4: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2004", "year": 2004},
    5: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2005", "year": 2005},
}


# Test when the user has not created a reclassification (he'll use native layer classification)
# model.matrix_sub_b = {}

# Run statistics
# calculation_tile.get_children(id_="calculation_view")[0].run_statistics()

# Check results stored in the model
# model.results
