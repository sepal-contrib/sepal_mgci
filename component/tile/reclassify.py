from pandas import DataFrame
from functools import partial
from traitlets import (
    Dict, Any, link, observe
)

import ipyvuetify as v

from ..widget.custom_widgets import *
from ..scripts import *
from ..tile import *
from ..message import cm
from ..frontend.styles import *

import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts import utils as su

su.init_ee()

class ReclassifyTable(v.SimpleTable):
    
    matrix = Dict({}).tag(sync=True)
    
    def __init__(self, classes_file, *args, **kwargs):
        """Widget to reclassify raster/feature_class into local classes
        
        Args:
        
            classes_file: classes .csv file containing lines of (code_class, description)
        """
        
        self.dense = True

        # Create table
        super().__init__(*args, **kwargs)
        

    
    def _get_matrix(self, classes_file, code_fields):
        """ Init table reading local classes file and code/categories fields
        
        Args:
            classes_file (str) : Classes file containing code/categorie and description
            code_fields (list) : List of codes/categories of raster/feature collection
        """
        
        
        self.matrix = {}
        
        self.items = self.read_classes_from_file(classes_file)
        
        headers = ['From: user code', 'To: Custom Code']
        
        # Instantiate an empty dictionary with code as 
        # keys and empty values
        for code in code_fields:
            self.matrix[code] = ''
            
        header = [
            v.Html(
                tag = 'tr', 
                children = (
                    [v.Html(tag = 'th', children = [h]) for h in headers]
                )
            )
        ]
        
        rows = [
            v.Html(tag='tr', children=[
                v.Html(tag = 'td', children=[str(code)]), 
                self.get_classes(code),
                
            ]) for code in code_fields
        ]
        
        self.children = [v.Html(tag = 'tbody', children = header + rows)]

        
    def read_classes_from_file(self, class_file):
        """ Read classes from .csv file
        
        Args:
            class_file (str): classes .csv file containing lines of (code_class, description)
        """
        items = []
        with open(class_file) as f:
            for cl in f.readlines():
                item = [{'value': c, 'text': d.replace('\n','')} for c, d in [cl.split(',')]]
                items+=item
                
        return items
        
    def store(self, code, change):
        """Store user row code and new select value (file class)"""
        self.matrix[code] = change['new']
        

    def get_classes(self, class_file, code):
        """ Get class selector on the fly and store code to matrix
        
        Args:
            code (str) : id to link local (raster, fc) with new classes (from file)
        """
                
        select = v.Combobox(
            _metadata={'name':code}, 
            items=self.items, 
            v_model=None, 
            dense=True,
            hide_details=True
        )
        
        select.observe(partial(self.store, code), 'v_model')
        
        return select
        
        
        
class GeeSelector(v.Card):
    
    asset = Any('').tag(sync=True)
    code_col = Any('').tag(sync=True)
    
    def __init__(self, classes_file, *args, **kwargs):
        
        self.classes_file = classes_file
        self.class_ = 'pa-4'
        title = v.CardTitle(children=[cm.ui.title])
        description = v.CardText(
            class_='py-0', 
            children=[sw.Markdown(cm.ui.description)]
        )
        
        super().__init__(*args, **kwargs)

        
        self.ee_asset = None
        self.w_reclassify = ReclassifyTable(
            dense=True, 
            max_height=400,
            _metadata={'name':'mapper'}
        )
        
        self.asset_selector = AssetSelect(
            label=cm.remap.label, 
            default_asset = 'users/dafguerrerom/FAO/LULC_2012_AOI'
        )
        
        self.w_code = v.Select(label='', class_='pr-4', v_model='')
        self.mapper_btn = sw.Btn(cm.remap.btn, small=True)
        
        self.w_asset = Flex(
            _metadata = {'name':'code'},
            class_='d-flex align-center mb-2',
            children=[self.w_code, self.mapper_btn]
        )
        
        # List of components whose could be hidden/showed
        
        self.components = {
            'mapper': self.w_reclassify,
            'code' : self.w_asset
        }
        
        # Define view
        self.children = [
            title,
            description,
            self.asset_selector,
        ]
        
        #Link traits
        link((self, 'asset'), (self.asset_selector, 'v_model'))
        link((self.w_code, 'v_model'), (self, 'code_col'))
        
        # Create Events
        self.mapper_btn.on_event('click', self._get_mapper_matrix_event)
        
        # Decorate functions
        self._get_mapper_matrix = loading(self.alert_dialog, self.mapper_btn)(self._get_mapper_matrix)
        self._validate_asset = loading(self.alert_dialog)(self._validate_asset)
        
        
    def _get_mapper_matrix_event(self, widget, event, data):
        self._get_mapper_matrix()
        
    def _get_mapper_matrix(self):
        
        assert (self.code_col != ''), cm.remap.error.no_code_col
        
        if self.asset_type == 'TABLE':
            code_fields = self._get_fields()
        elif self.asset_type == 'IMAGE':
            code_fields = self._get_classes()
        
        # Create mapper widget
        self.w_reclassify._get_matrix(classes_file.v_model, code_fields)

        add_widget(self, self.w_reclassify, 'mapper')

    def _hide_components(self):
        """Hide all possible componentes"""
        self.code_col = ''
        for component in self.components.values():
            su.hide_component(component)
    
    def _validate_asset(self, asset):
        
        asset_info = ee.data.getAsset(asset)
        self.asset_type = asset_info['type']
        
        if self.asset_type == 'TABLE':
            self.w_code.label = cm.remap.code_label
            self.ee_asset = ee.FeatureCollection(asset)

        elif self.asset_type == 'IMAGE':
            self.w_code.label = cm.remap.band_label
            self.ee_asset = ee.Image(asset)
        else:
            err_str = cm.remap.error_type
            raise AttributeError(err_str)

    @observe('asset')
    def _get_items(self, change):
        
        asset = change['new']
        
        if asset:
            
            # Hide previous loaded components
            self._hide_components()
            self.w_code.items=[]
            add_widget(self, self.w_asset, 'code')
            self._validate_asset(asset)

            self.w_code.loading=True

            # Get columns of dataset
            if self.asset_type == 'TABLE':
                columns = self._get_cols()

            elif self.asset_type == 'IMAGE':
                columns = self._get_bands()

            # Fill widgets with column names
            self.w_code.items = columns

            self.w_code.loading=False

    def _get_bands(self):
        """Get bands from Image asset"""
        return list(self.ee_asset.bandTypes().getInfo().keys())
        
    def _get_fields(self):
        """Get fields from Feature Collection"""
        return sorted(list(set(self.ee_asset.aggregate_array(self.code_col).getInfo())))

    def _get_cols(self):
        
        if self.ee_asset:
            columns = ee.Feature(self.ee_asset.first()).propertyNames().getInfo()
            return sorted([str(col) for col in columns if col not in ['system:index', 'Shape_Area']])
        
    def _get_classes(self):
        """Get raster classes"""
        
        # Reduce image
        reduced = self.ee_asset.reduceRegion(
          reducer = ee.Reducer.autoHistogram(maxBuckets=40000), 
          geometry = self.ee_asset.geometry(), 
          scale=30, 
          maxPixels=1e13
        )

        array = ee.Array(ee.List(reduced.get(self.code_col))).getInfo()
        df = DataFrame(data=array, columns=['code', 'count'])
        
        return list(df[df['count']>0]['code'].unique())
        