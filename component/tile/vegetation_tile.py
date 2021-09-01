from pathlib import Path

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.mapping as sm
from sepal_ui.scripts.utils import loading_button
from sepal_ui.reclassify import ReclassifyTile

from component.message import cm
import component.parameter as param


__all__ = ['VegetationTile']

class VegetationTile(v.Card, sw.SepalWidget):
    
    def __init__(self, model, *args, **kwargs):
        
        self._metadata={'mount_id': 'vegetation_tile'}

        self.class_ = 'pa-2'
        
        super().__init__(*args,  **kwargs)
                
        title = v.CardTitle(children=[cm.veg_layer.title])
        
        description = v.CardText(
            children=[sw.Markdown(cm.veg_layer.description)]
        )
        
        self.model = model
        
        self.reclassify_tile = ReclassifyTile(
            RESULTS_DIR, 
            save=False, 
            aoi_model=self.aoi_model,
            default_class = {
                'IPCC' : Path(__file__).parent/'parameter/ipcc',
                'Forest/Non Forest' : Path(__file__).parent/'parameter/binary',
            }
        )
        
        self.btn = sw.Btn('Display on map')
        self.btn.disabled = True
        
        self.map_ = sm.SepalMap()
        
        self.children=[
            title, 
            description,
            self.reclassify_tile,
            v.Card(class_='mt-2',
                children=[
                v.CardTitle(children=['Visualize results']),
                v.CardText(children=[self.btn, self.map_])
                
            ])
        ]
        
        #Decorate functions
        self.display_on_map = loading_button(
            alert=sw.Alert(), button=self.btn, debug=True
        )(self.display_on_map)
        
        self.reclassify_tile.model.observe(self.activate_display, 'remaped')
        self.btn.on_event('click', self.display_on_map)
        
    def activate_display(self, change):
        """Activate display button if an asset has been classified"""
        
        if change['new'] == True:
            self.btn.disabled = False
        else:
            self.btn.disabled = True        
    
    def display_on_map(self, widget, event, data):
        """Display reclassified raster on map"""
        
        reclass_asset = self.reclassify_tile.model.reclass_ee
        raw_ee_object = self.reclassify_tile.model.ee_object
        asset_type = self.reclassify_tile.model.asset_type
        code_col = self.reclassify_tile.model.code_col
        aoi = self.reclassify_tile.model.aoi
        
        if asset_type=='TABLE':
            unique_values = [
                int(v) for v 
                in self.reclassify_tile.model.get_fields(reclass_asset, code_col)
            ]
            
            empty = ee.Image().byte()
            # Paint the interior of the polygons with different colors.
            reclass_asset = empty.paint(
              featureCollection=reclass_asset,
              color=code_col,
            )
            
        else:
            # it's an image
            unique_values = [
                int(v) for v 
                in get_unique_ee(raw_ee_object, reclass_asset, code_col, aoi=aoi)
            ]

        min_ = min(unique_values)
        max_ = max(unique_values)

        vis_params = {
            'palette' : param.CLASSES_COLOR,
            'min' : min_,
            'max' : max_
        }

        self.map_.zoom_ee_object(raw_ee_object.geometry())
        self.map_.addLayer(reclass_asset, vis_params, 'Recoded')