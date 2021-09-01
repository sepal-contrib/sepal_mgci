import pandas as pd
import ee
from traitlets import Unicode, Any, Int

from sepal_ui.scripts.utils import need_ee
from sepal_ui.model import Model

import component.parameter as param

class MgciModel(Model):
    
    dem_type = Unicode('').tag(sync=True)
    custom_dem_id = Any('').tag(sync=True)
    
    # output parameters
    scale = Int(300).tag(sync=True)
    year = Int().tag(sync=True)
    
    @need_ee
    def __init__(self, aoi_model):
        
        self.kapos_image = None
        self.aoi_model = aoi_model
        
        # Results
        self.summary_df = None
    
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
        
    def get_lulc_area_per_class(self, lulc):

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
          .updateMask(lulc.mask().And(self.kapos_image.mask()))\
          .addBands(lulc)\
          .addBands(self.kapos_image)\
          .reduceRegion(**{
            'reducer': ee.Reducer.sum().group(1).group(2), 
            'geometry': self.aoi_model.feature_collection.geometry(), 
            'maxPixels': 1e13,
            'scale': self.scale,
            'bestEffort':True,
            'tileScale':4
          }).getInfo()

        class_area_per_kapos = {}
        for group in result['groups']:

            # initialize classes key with zero area
            temp_group_dict = {class_:0 for class_ in param.DISPLAY_CLASSES}

            for nested_group in group['groups']:

                if nested_group['group'] not in param.DISPLAY_CLASSES:
                    # attach its area to "other classes (6)"
                    # TODO: add warning?
                    temp_group_dict[6] = temp_group_dict[6]+nested_group['sum']
                else:
                    temp_group_dict[nested_group['group']] = nested_group['sum']

            # Sort dictionary by its key
            temp_group_dict = {
                k:v for k,v in sorted(temp_group_dict.items(), key=lambda item: item[0])
            }

            class_area_per_kapos[group['group']] = temp_group_dict
        
        # kapos classes are the rows and lulc are the columns
        df = pd.DataFrame.from_dict(class_area_per_kapos, orient='index')
        df['green_area'] = df[param.GREEN_CLASSES].sum(axis=1)
        df['krange_area'] = df.sum(axis=1)
        df['mgci'] = df['green_area']/df['krange_area']
        
        self.summary_df = df
    
    def get_mgci(self, krange=None):
        """Get the MGCI for the overall area or for the Kapos Range if krange 
        is specified
        
        Args:
            krange (int): Kapos range [1-6].
        
        """
        
        if krange:
            mgci = self.summary_df.loc[krange]['mgci']
        else:
            mgci = self.summary_df['green_area'].sum()/\
                    self.summary_df['krange_area'].sum()
            
        return round(mgci,2)