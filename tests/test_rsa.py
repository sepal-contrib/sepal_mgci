import pytest
import ee

from component.scripts.surface_area import get_real_surface_area
ee.Initialize()

def test_rsa_values():
    
    # Arrange
    
    dem = ee.Image("USGS/SRTMGL1_003")
    aoi = ee.FeatureCollection('users/dfgm2006/AOI_RSA').geometry()
    fixed_points = ee.FeatureCollection(
        'users/dfgm2006/FAO/MGCI/random_points_to_test_rsa'
    ).toList(10)
    
    expected_values = [
        1013.7524910185108,
        1060.7589862722355,
        1081.2027267729168,
        1120.2372290990027,
        1112.865797722857,
        1015.4672663133788,
        1016.7633145781048,
        1125.7877444223482,
        987.4451174021981,
        1165.4287937114916,
    ]
    
    # Act
    
    rsa = get_real_surface_area(dem, aoi)
    cellsize = rsa.projection().nominalScale().getInfo()
    
    def extract_values(point):
        """Extracts values from raster using a point"""
        feature = ee.Feature(point).geometry()
        return (
            ee.Number(
                rsa.reduceRegion(ee.Reducer.first(),feature, cellsize).get('sum')
            )
        )
    
    
    assert fixed_points.map(extract_values).getInfo() == expected_values