import random
import ee
from sepal_ui.scripts import utils as su
from pandas import DataFrame
from component.parameter import *

ee.Initialize()
    
def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_unique_ee(
    raw_object, 
    ee_object, 
    code_col=None, 
    maxBuckets=40000, 
    aoi=None):
    
    """Get raster classes"""

    if not code_col:
        # If not band name selected, use the first one
        code_col = ee_object.bandNames().getInfo()[0]

    # Reduce image
    
    geometry = raw_object.geometry() if not aoi else aoi
    
    reduced = ee_object.reduceRegion(
      reducer = ee.Reducer.autoHistogram(maxBuckets=maxBuckets), 
      geometry = geometry, 
      scale=30, 
      maxPixels=1e13
    )

    array = ee.Array(ee.List(reduced.get(code_col))).getInfo()
    
    print(array)
    
    if len(array) > 256:
        raise Exception("Too many values to reclassify. Are you trying " + \
        "to reclassify a categorical Asset?")

    df = DataFrame(data=array, columns=['code', 'count'])

    return list(df[df['count']>0]['code'].unique())



def get_lulc_area_per_class(lulc, kapos, aoi, scale=30):
    
    """Reduce land use/land cover image to kapos regions
    
    Args:
        lulc (ee.Image, categorical): Input image to reduce
        kapos (ee.Image, categorical): Input region
        aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image
        scale (int, optional): By default using 30meters as scale
        
    Return:
        Dictionary with land cover class area per kapos mountain range
    """

    result = ee.Image.pixelArea().divide(10000)\
      .updateMask(lulc.mask().And(kapos.mask()))\
      .addBands(lulc)\
      .addBands(kapos)\
      .reduceRegion(**{
        'reducer': ee.Reducer.sum().group(1).group(2), 
        'geometry': aoi, 
        'maxPixels': 1e13,
        'scale': scale,
        'bestEffort':True,
        'tileScale':4
      }).getInfo()
    
    class_area_per_kapos = {}
    for group in result['groups']:

        temp_group_dict = {}
        for nested_group in group['groups']:
            temp_group_dict[nested_group['group']] = nested_group['sum']

        # Create classes key with zero area when are empty
        for class_ in DISPLAY_CLASSES:
            if class_ not in temp_group_dict:
                temp_group_dict[class_] = 0
        
        # Sort dictionary by its key
        temp_group_dict = {
            k:v for k,v in sorted(temp_group_dict.items(), key=lambda item: item[0])
        }

        class_area_per_kapos[group['group']] = temp_group_dict
        
    return class_area_per_kapos