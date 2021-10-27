import pandas as pd
import ee
from traitlets import Unicode, Any, Int, Dict, CBool, Bool

import sepal_ui.scripts.utils as su
from sepal_ui.model import Model

import component.scripts as cs
import component.parameter as param
from component.parameter.report_template import *


class MgciModel(Model):

    use_custom = CBool(0).tag(sync=True)

    # output parameters
    year = Unicode("", allow_none=True).tag(sync=True)
    source = Unicode("", allow_none=True).tag(sync=True)
    
    # Custom
    custom_lulc = Bool(allow_none=True).tag(sync=True)
    # LCLU Classes (came from the reclassify model)
    lulc_classes = Dict(allow_none=True).tag(sync=True)
    rsa = Bool(False, allow_none=True).tag(sync=True) 

    # Observation variables
    kapos_done = Int(0).tag(sync=True)
    reduce_done = Bool(False).tag(sync=True)

    @su.need_ee
    def __init__(self, aoi_model):

        self.kapos_image = None
        self.vegetation_image = None
        self.aoi_model = aoi_model

        # Results
        self.summary_df = None

        # Styled results dataframe
        self.mgci_report = None

    def get_kapos(self):
        """Get Kapos mountain classification layer within the area of interest"""

        # Validate inputs
        aoi = self.aoi_model.feature_collection

        if not aoi:
            raise Exception(
                "No AOI selected, please go "
                + "to the previous step and select an area."
            )

        if self.use_custom:
            self.dem = ee.Image(self.custom_dem_id)

        else:
            # TODO: decide which of the assets use
            # dem = ee.Image("USGS/SRTMGL1_003") # srtm_1
            self.dem = ee.Image("CGIAR/SRTM90_V4")  # srtm_3

        aoi_dem = self.dem.clip(aoi)

        slope = ee.Terrain.slope(aoi_dem)

        local_range = aoi_dem.focal_max(7000, "circle", "meters").subtract(
            aoi_dem.focal_min(7000, "circle", "meters")
        )
        # Kapos Mountain classes
        self.kapos_image = (
            ee.Image(0)
            .where(aoi_dem.gte(4500), 1)
            .where(aoi_dem.gte(3500).And(aoi_dem.lt(4500)), 2)
            .where(aoi_dem.gte(2500).And(aoi_dem.lt(3500)), 3)
            .where(aoi_dem.gte(1500).And(aoi_dem.lt(2500)).And(slope.gt(2)), 4)
            .where(
                aoi_dem.gte(1000)
                .And(aoi_dem.lt(1500))
                .And(slope.gt(5).Or(local_range.gt(300))),
                5,
            )
            .where(aoi_dem.gte(300).And(aoi_dem.lt(1000)).And(local_range.gt(300)), 6)
            .selfMask()
        )

    #         # Create the 7th class
    #         # The 7th class won't be a class by itself, we have to find areas that
    #         # are surrounded by the first 6 classes and assign them to its neighbors

    #         inverse_kapos = kapos_1_6.unmask().Not().eq(1).selfMask()

    #         connected = inverse_kapos.connectedComponents(
    #             **{"connectedness": ee.Kernel.plus(1), "maxSize": 128}
    #         )

    #         connected_size = connected.select("labels").connectedPixelCount(
    #             **{"maxSize": 128, "eightConnected": False}
    #         )
    #         connected_area = (
    #             ee.Image.pixelArea()
    #             .addBands(connected_size)
    #             .lte(25000000)
    #             .eq(1)
    #             .selfMask()
    #             .select("labels")
    #         )

    #         kapos_fill10 = (
    #             kapos_1_6.focal_mean(1, "square", "pixels", 10)
    #             .updateMask(connected_area)
    #             .selfMask()
    #         )

    #         self.kapos_image = kapos_1_6.addBands(kapos_fill10).reduce(ee.Reducer.max())
    
    @su.switch('reduce_done', targets=[True])
    def reduce_to_regions(self, units):
        """Reduce land use/land cover image to kapos regions
        
        Args:
            units (str): Units to display the results. Available [{}]
        Attr:
            lulc (ee.Image, categorical): Input image to reduce
            kapos (ee.Image, categorical): Input region
            aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image
            scale (int, optional): By default using 30meters as scale

        Return:
            Dictionary with land cover class area per kapos mountain range
        """.format(
            list(param.UNITS.keys())
        )

        if not self.kapos_image:
            raise Exception(
                "Please go to the mountain descriptor layer"
                " and calculate the kapos layer."
            )
        if not self.vegetation_image:
            raise Exception(
                "Please go to the vegetation descriptor layer and reclassify an image"
            )
        
        lulc = self.vegetation_image.select(
            [self.vegetation_image.bandNames().get(0)]
        )

        aoi = self.aoi_model.feature_collection.geometry()

        if self.rsa:
            image_area = cs.get_real_surface_area(self.dem, aoi)
        else:
            image_area = ee.Image.pixelArea()

        scale = (
            self.dem.projection()
            .nominalScale()
            .max(lulc.projection().nominalScale())
            .getInfo()
        )

        result = (
            image_area.divide(param.UNITS[units][0])
            .updateMask(lulc.mask().And(self.kapos_image.mask()))
            .addBands(lulc)
            .addBands(self.kapos_image)
            .reduceRegion(
                **{
                    "reducer": ee.Reducer.sum().group(1).group(2),
                    "geometry": aoi,
                    "maxPixels": 1e19,
                    "scale": scale,
                    "bestEffort": True,
                    "tileScale": 4,
                }
            )
            .getInfo()
        )

        class_area_per_kapos = {}
        for group in result["groups"]:

            # initialize classes key with zero area
            temp_group_dict = {class_: 0 for class_ in param.DISPLAY_CLASSES}

            for nested_group in group["groups"]:

                if nested_group["group"] not in param.DISPLAY_CLASSES:
                    # attach its area to "other classes (6)"
                    # TODO: add warning?
                    temp_group_dict[6] = temp_group_dict[6] + nested_group["sum"]
                else:
                    temp_group_dict[nested_group["group"]] = nested_group["sum"]

            # Sort dictionary by its key
            temp_group_dict = {
                k: v
                for k, v in sorted(temp_group_dict.items(), key=lambda item: item[0])
            }

            class_area_per_kapos[group["group"]] = temp_group_dict

        # kapos classes are the rows and lulc are the columns
        df = pd.DataFrame.from_dict(class_area_per_kapos, orient="index")
        
        # Create the kapos class even if is not present in the dataset.
        for kapos_range in list(range(1,7)):
            if not kapos_range in df.index:
                df.loc[kapos_range]=0
        
        df.sort_index(inplace=True)
        df["green_area"] = df[param.GREEN_CLASSES].sum(axis=1)
        df["krange_area"] = df[list(self.lulc_classes.keys())].sum(axis=1)
        df["mgci"] = df["green_area"] / df["krange_area"]
        df.fillna(0, inplace=True)

        self.summary_df = df

    def get_mgci(self, krange=None):
        """Get the MGCI for the overall area or for the Kapos Range if krange
        is specified

        Args:
            krange (int): Kapos range [1-6].
        """

        if krange:
            mgci = (self.summary_df.loc[krange]["mgci"]) * 100
        else:
            mgci = (
                self.summary_df["green_area"].sum()
                / self.summary_df["krange_area"].sum()
            ) * 100

        return round(mgci, 2)

    def get_report(self, units):
        """From the summary df, create a styled df to align format with the
        report"""

        # The following format respects
        # https://github.com/dfguerrerom/sepal_mgci/issues/23

        assert self.summary_df is not None, "How did you ended here?"

        # Create a df with the report columns
        base_df = pd.DataFrame(columns=BASE_COLS)

        vegetation_names = {k: v[0] for k, v in self.lulc_classes.items()}
        vegetation_columns = list(vegetation_names.values())


        # Create the base columns for the statistics dataframe
        stats_df = self.summary_df.copy()
        # Replace 0 vals with "N" according with requirements.
        stats_df.replace(0,NO_VALUE, inplace=True)
        stats_df.rename(columns=vegetation_names, inplace=True)
        stats_df[INDICATOR] = INDICATOR_NUM
        stats_df[GEOAREANAM] = cs.get_geoarea(self.aoi_model)[0]
        stats_df[GEOAREACODE] = cs.get_geoarea(self.aoi_model)[1]
        stats_df[TIMEPERIOD] = self.year
        stats_df[TIMEDETAIL] = self.year
        stats_df[SOURCE] = self.source
        stats_df[NATURE] = CUSTOM_ if self.custom_lulc==True else GLOBAL_
        stats_df[REPORTING] = REPORTING_VALUE
        stats_df[MOUNTAINCLASS] = "C" + stats_df.mgci.index.astype(str)
        stats_df = stats_df.reset_index()

        # We have to create three tables
        # ER_MTN_GRNCVI
        def get_mgci_report():
            """Returns df with MGC index for every mountain range"""

            # Merge dataframes
            mgci_df = pd.merge(
                base_df, stats_df.rename(columns={"mgci": VALUE}), how="right"
            )

            # Rename
            mgci_df[VALUE] = stats_df.mgci
            mgci_df[SERIESDESC] = SERIESDESC_GRNCVI
            mgci_df[UNITSNAME] = UNITSNAME_GRNCVI
            mgci_df[SERIESCOD] = SERIESCOD_GRNCVI

            return mgci_df[BASE_COLS]
        
        #ER_MTN_GRNCOV
        def get_green_cov_report():
            """Returns df with green cover and total mountain area for every mountain
            range"""

            unit = param.UNITS[units][1]

            green_area_df = pd.merge(base_df, stats_df, how="right")
            green_area_df[VALUE] = stats_df.green_area
            green_area_df[SERIESDESC] = SERIESDESC_GRNCOV_1.format(unit=unit)
            green_area_df[SERIESCOD] = SERIESCOD_GRNCOV_1

            mountain_area_df = pd.merge(base_df, stats_df, how="right")
            mountain_area_df[VALUE] = stats_df.krange_area
            mountain_area_df[SERIESDESC] = SERIESDESC_GRNCOV_2.format(unit=unit)
            mountain_area_df[SERIESCOD] = SERIESCOD_GRNCOV_2

            greencov_df = pd.concat([green_area_df, mountain_area_df])

            greencov_df[UNITSNAME] = units.upper()

            return greencov_df[BASE_COLS].sort_values(by=[MOUNTAINCLASS])

        def get_land_cov_report():
            """Returns df with land cover area per every mountain range"""

            landcov_df = base_df.copy()

            melt_df = (
                pd.melt(
                    stats_df,
                    id_vars=[
                        col
                        for col in stats_df.columns.to_list()
                        if col not in vegetation_columns
                    ],
                    value_vars=vegetation_columns,
                )
                .sort_values(by=[MOUNTAINCLASS])
                .rename(columns={"variable": LULCCLASS, "value": VALUE})
            )
            # Merge dataframes

            unit = param.UNITS[units][1]

            landcov_df = pd.merge(base_df, melt_df, how="right")
            landcov_df[SERIESDESC] = SERIESDESC_TTL.format(unit=unit)
            landcov_df[UNITSNAME] = units.upper()
            landcov_df[SERIESCOD] = SERIESCOD_TTL

            # Return in order
            return landcov_df[BASE_COLS_TOTL].sort_values(by=[MOUNTAINCLASS, LULCCLASS])

        return [get_mgci_report(), get_green_cov_report(), get_land_cov_report()]
