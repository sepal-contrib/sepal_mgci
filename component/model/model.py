import ee
from traitlets import Unicode, Any
from sepal_ui.model import Model

ee.Initialize()

class MgciModel(Model):
    
    dem_type = Unicode('').tag(sync=True)
    custom_dem_id = Any('').tag(sync=True)
    
    def __init__(self, aoi_model):
        
        self.kapos_image = None
        self.aoi_model = aoi_model
        
    def get_kapos(self):
        """Get Kapos mountain classification layer within the area of interest
        """

        # Validate inputs
        aoi = self.aoi_model.feature_collection
        
        if not aoi:
            raise Exception('No AOI selected, please go ' + \
                            'to the previous step and select an area.')

        if self.dem_type == 'srtm_1':
            dem = ee.Image("USGS/SRTMGL1_003")
        elif self.dem_type == 'srtm_3':
            dem = ee.Image("CGIAR/SRTM90_V4")
        elif self.dem_type == 'alos':
            ""
            # TODO: 
            # dem = ee.Image('asset_id')
        else:
            # User has selected a custom layer
            dem = ee.Image(self.custom_dem_id)


        aoi_dem = dem.clip(aoi)

        slope = ee.Terrain.slope(aoi_dem)

        local_range = aoi_dem.focal_max(7000,"circle","meters")\
                            .subtract(aoi_dem.focal_min(7000, "circle","meters"))
        # Kapos Mountain classes
        self.kapos_image = ee.Image(0).where(aoi_dem.gte(4500),1)\
            .where(aoi_dem.gte(3500).And(aoi_dem.lt(4500)),2)\
            .where(aoi_dem.gte(2500).And(aoi_dem.lt(3500)),3)\
            .where(aoi_dem.gte(1500).And(aoi_dem.lt(2500))\
                   .And(slope.gt(2)),4)\
            .where(aoi_dem.gte(1000).And(aoi_dem.lt(1500))\
                   .And(slope.gt(2).Or(local_range.gt(300))),5)\
            .where(aoi_dem.gte(300).And(aoi_dem.lt(1000))\
                   .And(local_range.gt(300)),6)\
            .selfMask()