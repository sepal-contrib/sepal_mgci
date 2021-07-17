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


def get_kapos(aoi, dem):
    """Get Kapos mountain classification layer
    
    Args:
        dem (ee.Image): Digital elevation model
        aoi (ee.Object): Area of interest to clip results
        
    Returns:
        ee.Image
    """
    
    # Validate inputs
    
    if not aoi:
        raise Exception('No AOI selected, please go ' + \
                        'to the previous step and select an area.')
    
    if dem == 'srtm_1':
        dem = ee.Image("USGS/SRTMGL1_003")
    elif dem == 'srtm_3':
        dem = ee.Image("CGIAR/SRTM90_V4")
    elif dem == 'alos':
        ""
        # TODO: 
        # dem = ee.Image('asset_id')
    else:
        ""
        # User has provided a custom id
        # TODO: Create the method to catch custom ids
        # custom
    
    
    aoi_dem = dem.clip(aoi)
    
    slope = ee.Terrain.slope(aoi_dem)
    
    local_range = aoi_dem.focal_max(7000,"circle","meters")\
                        .subtract(aoi_dem.focal_min(7000, "circle","meters"))
    # Kapos Mountain classes
    mountain_class = ee.Image(0).where(aoi_dem.gte(4500),1)\
        .where(aoi_dem.gte(3500).And(aoi_dem.lt(4500)),2)\
        .where(aoi_dem.gte(2500).And(aoi_dem.lt(3500)),3)\
        .where(aoi_dem.gte(1500).And(aoi_dem.lt(2500))\
               .And(slope.gt(2)),4)\
        .where(aoi_dem.gte(1000).And(aoi_dem.lt(1500))\
               .And(slope.gt(2).Or(local_range.gt(300))),5)\
        .where(aoi_dem.gte(300).And(aoi_dem.lt(1000))\
               .And(local_range.gt(300)),6)\
        .selfMask();


    return mountain_class
    # TODO: ADD CLASS 7
    #  Class 7: Inner isolated areas (<=25km2 in size) - 
    # don't meet criteria but surrounded by mountains
    # get pixels that are non-mountain areas by inversing the new mountain layer:

    inverse = (kapos_1_6_binary.unmask().Not()).eq(1).clip(aoi).selfMask()

    #  uniquely label the inverse areas.
    objectId = inverse.connectedComponents(
        connectedness=ee.Kernel.plus(1), 
        maxSize=255
    )

    #  Compute the number of pixels in each object defined by the " labels" band.
    objectSize = objectId.select('labels')\
            .connectedPixelCount(maxSize=255, eightConnected=True)

    # Get a pixel area image.
    pixelArea = ee.Image.pixelArea()

    #  Multiply pixel area by the number of pixels in an object to calculate the object area.
    objectArea = objectSize.multiply(pixelArea);

    #  Generate mask of objects below spcified area i.e 25km2 (25,000,000m2)
    #  3,299,188 15,369,098
    areaMask = objectArea.lte(25000000)

    kapos_c7 = areaMask.eq(1)\
            .selfMask()\
            .remap([1],[7])\
            .cast({'remapped': 'byte'})
    kapos_c7.getInfo()

    return ee.Image(ee.ImageCollection([kapos_1_6, kapos_c7]).mosaic())


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