import random
import ee
from sepal_ui.scripts import utils as su
from pandas import DataFrame

ee.Initialize()
    
def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_unique_ee(raw_object, ee_object, code_col=None, maxBuckets=40000):
    """Get raster classes"""
    
    print(raw_object)
    print(ee_object)
    print(code_col)

    if not code_col:
        # If not band name selected, use the first one
        code_col = ee_object.bandNames().getInfo()[0]

    # Reduce image
    reduced = ee_object.reduceRegion(
      reducer = ee.Reducer.autoHistogram(maxBuckets=maxBuckets), 
      geometry = raw_object.geometry(), 
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

    # Generate focal maximum elevation within range of 7km
    focalMax7km = aoi_dem.focal_max(
      radius =  7000,
      kernelType = 'circle',
      units = 'meters',
      iterations = 1)

    #  Generate focal minimum elevation within range of 7km
    focalMin7km = aoi_dem.focal_min(
      radius =  7000,
      kernelType =  'circle',
      units = 'meters',
      iterations = 1)

    #  Generate local (7 km radius) elevation range
    local = focalMax7km.subtract(focalMin7km)

    #  Generate slope
    slope = ee.Terrain.slope(aoi_dem);

    #  Class 1: elevation >= 4500 meters
    kapos_c1 = aoi_dem.gte(4500)\
            .selfMask()\
            .rename('remapped')\
            .cast({'remapped': 'byte'})

    #  Class 2: elevation < 4500 & elevation >= 3500
    kapos_c2 = aoi_dem.gte(3500)\
            .And(aoi_dem.lt(4500))\
            .selfMask()\
            .remap([1],[2])\
            .cast({'remapped': 'byte'})

    #  Class 3: elevation < 3500 & elevation >= 2500
    kapos_c3 = aoi_dem.gte(2500)\
            .And(aoi_dem.lt(3500))\
            .selfMask()\
            .remap([1],[3])\
            .cast({'remapped': 'byte'})

    # Class 4: elevation < 2500 & elevation >= 1500 & slope > 2 degrees
    kapos_c4 = aoi_dem.gte(1500)\
            .And(aoi_dem.lt(2500))\
            .And(slope.gt(2))\
            .selfMask()\
            .remap([1],[4])\
            .cast({'remapped': 'byte'})

    # Class 5a: elevation < 1500 & elevation >= 1000 & 
    # slope >= 5 degree

    kapos_c5a = aoi_dem.gte(1000)\
            .And(aoi_dem.lt(1500))\
            .And(slope.gt(5))\
            .selfMask().remap([1],[5])\
            .cast({'remapped': 'byte'})

    # Class 5b elevation <1500 & elevation >= 1000 & 
    # local (7 km radius) elevation range > 300 meters

    kapos_c5b = aoi_dem.gte(1000)\
            .And(aoi_dem.lt(1500))\
            .selfMask()\
            .And(local.gte(300).selfMask())\
            .remap([1],[5])\
            .cast({'remapped': 'byte'})

    # Class 6: elevation < 1000 & elevation >= 300 & local 
    # (7 km radius) elevation range > 300 meters

    kapos_c6 = aoi_dem.gte(300)\
            .And(aoi_dem.lt(1000).And(local.gte(300)))\
            .selfMask()\
            .remap([1],[6])\
            .cast({'remapped': 'byte'})

    kapos_mosaic = ee.ImageCollection([
        kapos_c1,kapos_c2,kapos_c3,
        kapos_c4,kapos_c5a,kapos_c5b,kapos_c6
    ]).mosaic();

    kapos_1_6 = ee.Image(kapos_mosaic)
    kapos_1_6_binary = kapos_1_6.remap([1,2,3,4,5,6], [1,1,1,1,1,1])

    #  Class 7: Inner isolated areas (<=25km2 in size) - don't meet criteria but surrounded by mountains
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