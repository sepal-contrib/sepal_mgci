# It is strongly suggested to use a separate file to define the tiles of your process and then call them in your notebooks. 
# it will help you to have control over their fonctionalities using object oriented programming

from sepal_ui import sepalwidgets as sw
from sepal_ui import mapping as sm
from ipywidgets import Output
import ipyvuetify as v

from component.message import cm

# create an empty result tile that will be filled with displayable plot, map, links, text
class DefaultResultTile(sw.Tile):
    
    def __init__(self, **kwargs):
        
        # the result widgets that will be used by the process tile 
        self.down_btn = sw.DownloadBtn(cm.default_process.csv_btn)
        self.fig = Output()
        self.m = sm.SepalMap(['CartoDB.DarkMatter']) # you can choose in all the available basemaps of leaflet 
        
        # organise them in a layout 
        figs = v.Layout(
            Row = True,
            children = [
                v.Flex(xs6 = True, children = [self.fig]),
                v.Flex(xs6 = True, children = [self.m])
            ]
        )
        
        # note that btn and output are not a madatory attributes 
        super().__init__(
            id_ = "default_result_tile",
            title = cm.result.title,
            inputs = [self.down_btn, figs]
        )