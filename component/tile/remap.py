from functools import partial
import ipyvuetify as v
from traitlets import Dict
from ..parameter import *

class Remap(v.SimpleTable):
    
    matrix = Dict({}).tag(sync=True)
    
    def __init__(self, *args, **kwargs):

        "Tile to display a remap values"
        
        self.dense = True

        # Create table
        super().__init__(*args, **kwargs)
    
    def _get_matrix(self, code_fields):
        
        self.matrix = {}
        headers = ['From: user code', 'To: Ipcc Code']
        
        # Instantiate an empty dictionary with code as keys and empty values
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
                self.get_ipcc_class(code),
                
            ]) for code in code_fields
        ]
        
        self.children = [v.Html(tag = 'tbody', children = header + rows)]
        
        
    def store(self, code, change):
        """Store user row code and new select value (ipcc class)"""
        self.matrix[code] = change['new']

    def get_ipcc_class(self, code):
        """Get widget selector on the fly and wire an event """
        
        items = [{ 'value':k, 'text':v[0] } for k, v in IPCC_CLASSES.items()]
        
        select = v.Combobox(
            _metadata={'name':code}, 
            items=items, 
            v_model=None, 
            dense=True,
            hide_details=True
        )
        
        select.observe(partial(self.store, code), 'v_model')
        
        return select
        