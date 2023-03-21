# Test calculation

# model.sub_a_year = {
#     1: {
#         "base": {
#             "asset": "users/amitghosh/sdg_module/esa/cci_landcover/1992",
#             "year": "1990",
#         }
#     },
#     2: {
#         "base": {
#             "asset": "users/amitghosh/sdg_module/esa/cci_landcover/1992",
#             "year": "1992",
#         }
#     },
# }

# model.sub_b_year = {
#     1: {
#         "base": {
#             "asset": "users/amitghosh/sdg_module/esa/cci_landcover/1992",
#             "year": "1992",
#         },
#         "report": {
#             "asset": "users/amitghosh/sdg_module/esa/cci_landcover/1994",
#             "year": "1994",
#         },
#     }
# }

# Test when the user has not created a reclassification (he'll use native layer classification)
# model.matrix_sub_b = {}

# Run statistics
# calculation_tile.get_children(id_="calculation_view")[0].run_statistics()

# Check results stored in the model
# model.results
